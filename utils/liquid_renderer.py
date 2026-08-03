import html
import re


_TOKEN_RE = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})", re.DOTALL)


def _resolve_path(context, path):
    current = context
    for part in [segment for segment in str(path or "").strip().split(".") if segment]:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, (list, tuple)) and part.isdigit():
            index = int(part)
            current = current[index] if 0 <= index < len(current) else None
        else:
            current = getattr(current, part, None)
        if current is None:
            break
    return current


def _is_truthy(value):
    if isinstance(value, (list, tuple, dict, str)):
        return len(value) > 0
    return bool(value)


def _render_tokens(tokens, context):
    output = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.startswith("{{") and token.endswith("}}"):
            expr = token[2:-2].strip()
            value = _resolve_path(context, expr)
            output.append(html.escape("" if value is None else str(value)))
            i += 1
            continue

        if token.startswith("{%") and token.endswith("%}"):
            expr = token[2:-2].strip()

            if expr.startswith("for ") and " in " in expr:
                left, right = expr[4:].split(" in ", 1)
                loop_var = left.strip()
                iterable = _resolve_path(context, right.strip())
                iterable = iterable if isinstance(iterable, (list, tuple)) else []

                depth = 1
                j = i + 1
                block_tokens = []
                while j < len(tokens):
                    inner = tokens[j]
                    if inner.startswith("{%") and inner.endswith("%}"):
                        inner_expr = inner[2:-2].strip()
                        if inner_expr.startswith("for "):
                            depth += 1
                        elif inner_expr == "endfor":
                            depth -= 1
                            if depth == 0:
                                break
                    block_tokens.append(inner)
                    j += 1

                for item in iterable:
                    loop_context = dict(context)
                    loop_context[loop_var] = item
                    output.append(_render_tokens(block_tokens, loop_context))
                i = j + 1
                continue

            if expr.startswith("if "):
                condition_path = expr[3:].strip()
                depth = 1
                j = i + 1
                true_tokens = []
                false_tokens = []
                in_false = False
                while j < len(tokens):
                    inner = tokens[j]
                    if inner.startswith("{%") and inner.endswith("%}"):
                        inner_expr = inner[2:-2].strip()
                        if inner_expr.startswith("if "):
                            depth += 1
                        elif inner_expr == "endif":
                            depth -= 1
                            if depth == 0:
                                break
                        elif inner_expr == "else" and depth == 1:
                            in_false = True
                            j += 1
                            continue
                    if in_false:
                        false_tokens.append(inner)
                    else:
                        true_tokens.append(inner)
                    j += 1

                chosen = true_tokens if _is_truthy(_resolve_path(context, condition_path)) else false_tokens
                output.append(_render_tokens(chosen, context))
                i = j + 1
                continue

            if expr in {"endfor", "endif", "else"}:
                i += 1
                continue

        output.append(token)
        i += 1
    return "".join(output)


def render_liquid_template(template_text, context):
    tokens = _TOKEN_RE.split(str(template_text or ""))
    return _render_tokens(tokens, context if isinstance(context, dict) else {})
