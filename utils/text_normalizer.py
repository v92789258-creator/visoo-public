"""Normalizador de textos para corregir mojibake (tildes/caracteres rotos)."""

import re
from typing import Any


_SUSPECT_TOKENS = (
    "Ã",
    "Â",
    "â",
    "\ufffd",
)

_QUESTION_WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]\?[A-Za-zÁÉÍÓÚáéíóúÑñ]")
_QUESTION_RUN_BETWEEN_LETTERS_RE = re.compile(r"(?<=[A-Za-z])\?{2,}(?=[A-Za-z])")

_REPLACEMENTS = {
    # Mojibake clásico UTF-8 leído como latin1/cp1252
    "Ã¡": "á",
    "Ã©": "é",
    "Ã­": "í",
    "Ã³": "ó",
    "Ãº": "ú",
    "Ã": "Á",
    "Ã‰": "É",
    "Ã": "Í",
    "Ã“": "Ó",
    "Ãš": "Ú",
    "Ã±": "ñ",
    "Ã‘": "Ñ",
    "Â¿": "¿",
    "Â¡": "¡",
    "â€œ": '"',
    "â€": '"',
    "â€™": "'",
    "â€“": "-",
    "â€”": "-",
    "Mi Ãƒâ€œptica": "Mi Óptica",
    "Ãƒâ€œ": "Ó",
    # Mojibake de emojis/botones (se limpia para mostrar texto legible)
    "Ã°Å¸â€ž ": "",
    "Ã°Å¸Â´ ": "",
    "Ã°Å¸Å¸Â¢ ": "",
    "Ã¢Å¡Â Ã¯Â¸Â ": "",
    "Ã¢Å“â€œ ": "✓ ",
    "Ã¢Å“â€” ": "✗ ",
    "Ã¢ÂÅ’ ": "",
    "Ã¢â€”Â": "●",
    "Ã¢â€“Â¦": "⋮",
    "Ã¢â‚¬â€œ": "–",
    "Ã¢â‚¬â€": "—",
    "Ã¢â‚¬â„¢": "'",
    "Ã¢â‚¬Å“": '"',
    "Ã¢â‚¬": '"',
    # Palabras con '?' en lugar de acento/ñ
    "Aseg?rate": "Asegúrate",
    "acci?n": "acción",
    "activaci?n": "activación",
    "afiliaci?n": "afiliación",
    "autom?tica": "automática",
    "autom?ticamente": "automáticamente",
    "Bot?n": "Botón",
    "c?dula": "cédula",
    "combinaci?n": "combinación",
    "Comunicaci?n": "Comunicación",
    "comparaci?n": "comparación",
    "confirmaci?n": "confirmación",
    "Condici?n": "Condición",
    "Configuraci?n": "Configuración",
    "configuraci?n": "configuración",
    "Conexi?n": "Conexión",
    "conexi?n": "conexión",
    "Contrase?a": "Contraseña",
    "cr?ditos": "créditos",
    "Cr?tico": "Crítico",
    "creaci?n": "creación",
    "cumplea?os": "cumpleaños",
    "Cumplea?os": "Cumpleaños",
    "Direcci?n": "Dirección",
    "d?gitos": "dígitos",
    "descripci?n": "descripción",
    "Dise?o": "Diseño",
    "Electr?nica": "Electrónica",
    "electr?nicas": "electrónicas",
    "electr?nico": "electrónico",
    "emisi?n": "emisión",
    "est?": "está",
    "est?bamos": "estábamos",
    "Gesti?n": "Gestión",
    "gesti?n": "gestión",
    "Habilitaci?n": "Habilitación",
    "Informaci?n": "Información",
    "informaci?n": "información",
    "Inv?lida": "Inválida",
    "inv?lido": "inválido",
    "funci?n": "función",
    "im?genes": "imágenes",
    "Importaci?n": "Importación",
    "importaci?n": "importación",
    "importar?n": "importarán",
    "l?gica": "lógica",
    "librer?a": "librería",
    "librer?as": "librerías",
    "Luc?a": "Lucía",
    "M?todo": "Método",
    "M?todos": "Métodos",
    "Mar?a": "María",
    "m?nima": "mínima",
    "M?nimo": "Mínimo",
    "m?quina": "máquina",
    "m?todo": "método",
    "m?todos": "métodos",
    "m?vil": "móvil",
    "m?s": "más",
    "min?sculas": "minúsculas",
    "n?Deseas": "¿Deseas",
    "?Deseas": "¿Deseas",
    "?Est?s": "¿Estás",
    "?Qu?": "¿Qué",
    "?Necesitas": "¿Necesitas",
    "n?mero": "número",
    "operaci?n": "operación",
    "num?rica": "numérica",
    "Opci?n": "Opción",
    "Operaci?n": "Operación",
    "opt?metra": "optómetra",
    "Opt?metra": "Optómetra",
    "opt?metras": "optómetras",
    "Opt?metras": "Optómetras",
    "p?gina": "página",
    "P?gina": "Página",
    "P?rez": "Pérez",
    "p?ginas": "páginas",
    "pesta?a": "pestaña",
    "Podr?amos": "Podríamos",
    "Producci?n": "Producción",
    "registrar?n": "registrarán",
    "r?pida": "rápida",
    "r?pido": "rápido",
    "raz?n": "razón",
    "Raz?n": "Razón",
    "Rodr?guez": "Rodríguez",
    "se?al": "señal",
    "Secci?n": "Sección",
    "seg?n": "según",
    "selecci?n": "selección",
    "ser?n": "serán",
    "sincronizaci?n": "sincronización",
    "sin?nimos": "sinónimos",
    "soluci?n": "solución",
    "T?cnico": "Técnico",
    "t?rmicas": "térmicas",
    "T?rminos": "Términos",
    "T?tulo": "Título",
    "tama?o": "tamaño",
    "tel?fono": "teléfono",
    "telef?nico": "telefónico",
    "todav?a": "todavía",
    "aqu?": "aquí",
    "Aqu?": "Aquí",
    "sesi?n": "sesión",
    "Sesi?n": "Sesión",
    "vac?a": "vacía",
    "vac?as": "vacías",
    "vac?o": "vacío",
    "vac?os": "vacíos",
    "Validaci?n": "Validación",
    "validaci?n": "validación",
    "Ubicaci?n": "Ubicación",
    "v?lidas": "válidas",
    "v?lido": "válido",
    "V?lido": "Válido",
    "v?lidos": "válidos",
    "Fern?ndez": "Fernández",
    "G?mez": "Gómez",
    "Garc?a": "García",
    "?ptica": "óptica",
    "?pticas": "ópticas",
    "?xito": "Éxito",
    # Casos adicionales observados en Configuración
    "afectar?": "afectará",
    "dise?o": "diseño",
    "Dise?o": "Diseño",
    "direcci?n": "dirección",
    "electr?nica": "electrónica",
    "Emisi?n": "Emisión",
    "espec?ficas": "específicas",
    "Im?genes": "Imágenes",
    "men?": "menú",
    "N?mero": "Número",
    "Peque?o": "Pequeño",
    "peque?o": "pequeño",
    "podr?": "podrá",
    "registr?": "registró",
    "reiniciar?": "reiniciará",
    "secci?n": "sección",
    "Confirmaci?n": "Confirmación",
    "t?rminos": "términos",
    "Tel?fono": "Teléfono",
    "Vac?o": "Vacío",
    "?Completado!": "Completado!",
    "?Copiado!": "Copiado!",
    "?Desea reemplazar todos los datos actuales con los del respaldo?\n\n": "¿Desea reemplazar todos los datos actuales con los del respaldo?\n\n",
    "\\¿Deseas continuar con la importaci?n?": "¿Deseas continuar con la importación?",
    "\n\\¿Deseas continuar con la importaci?n?": "\n¿Deseas continuar con la importación?",
    # Prefijos de iconos rotos (se eliminan para texto limpio)
    "ÃƒÆ’Ã‚Â¢Ãƒâ€¦¡Ãƒâ€šÃ‚Â\xa0ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸ ": "",
    "ÃƒÆ’Ã‚Â¢Ãƒâ€¦¡? ": "",
    "ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¹ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸ ": "• ",
    "ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã…\"ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¹ ": "",
    "ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã…\"ÃƒÂ¢Ã¢â€šÂ¬Ã‹Å“ ": "",
    "ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã…\"ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾ ": "",
    # Frases completas muy corruptas
    "<h3>ÃƒÆ’Ã‚Â¢Ãƒâ€¦¡? Emisi?n Electrónica a SUNAT</h3>": "<h3>Emisión Electrónica a SUNAT</h3>",
    "ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã…\"ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¹ Diseño Peque?o": "Diseño Pequeño",
    "ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã…\"ÃƒÂ¢Ã¢â€šÂ¬Ã‹Å“ Diseño Extra Largo": "Diseño Extra Largo",
    "ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã…\"ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾ Diseño A4": "Diseño A4",
}


def _score_mojibake(text: str) -> int:
    if not text:
        return 0
    score = 0
    for token in _SUSPECT_TOKENS:
        score += text.count(token) * 4
    for token in ("ÃƒÆ’", "ÃƒÂ¢", "Ã‚Â¿", "Ã‚Â¡", "Ã¢â‚¬", "Ã¢Å“", "Ã°Å¸", "Ã¢Å¡"):
        score += text.count(token) * 6
    return score


def _apply_known_replacements(text: str) -> str:
    fixed = text.replace("\ufffd", "?")
    fixed = _QUESTION_RUN_BETWEEN_LETTERS_RE.sub("?", fixed)
    for src, dst in _REPLACEMENTS.items():
        fixed = fixed.replace(src, dst)
    if fixed:
        fixed = re.sub(r"^[\?\s!\"#$%&'()*+,\-./:;<=>@\[\]^_`{|}~]{2,}(?=[A-Za-z])", "", fixed)
    return fixed


def normalize_ui_text(value: Any) -> str:
    text = "" if value is None else str(value)
    if not text:
        return text

    best = _apply_known_replacements(text)
    best_score = _score_mojibake(best)

    frontier = [best]
    seen = {best}
    for _ in range(6):
        next_frontier = []
        for candidate in frontier:
            for encoding in ("latin1", "cp1252"):
                try:
                    decoded = candidate.encode(encoding).decode("utf-8")
                except Exception:
                    continue

                if not decoded or decoded in seen:
                    continue
                seen.add(decoded)
                decoded = _apply_known_replacements(decoded)
                next_frontier.append(decoded)

                score = _score_mojibake(decoded)
                if score < best_score:
                    best = decoded
                    best_score = score
        frontier = next_frontier
        if not frontier:
            break

    return _apply_known_replacements(best)


def maybe_normalize_ui_text(value: Any) -> str:
    text = "" if value is None else str(value)
    if not text:
        return text
    if (
        any(token in text for token in _SUSPECT_TOKENS)
        or ("Ãƒ" in text)
        or ("Ã‚" in text)
        or ("Ã¢" in text)
        or ("?" in text)
        or bool(_QUESTION_WORD_RE.search(text))
    ):
        return normalize_ui_text(text)
    return text
