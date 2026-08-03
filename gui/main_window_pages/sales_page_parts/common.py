_ORPHAN_QTHREADS = []


def _orphan_qthread(thread) -> None:
    """Evita crash al destruir widgets: mantiene vivo el QThread hasta que termine."""
    if thread is None:
        return
    try:
        for t in _ORPHAN_QTHREADS:
            if t is thread:
                return
    except Exception:
        pass
    try:
        thread.setParent(None)
    except Exception:
        pass
    try:
        _ORPHAN_QTHREADS.append(thread)
    except Exception:
        return

    def _cleanup():
        try:
            _ORPHAN_QTHREADS.remove(thread)
        except Exception:
            pass
        try:
            thread.deleteLater()
        except Exception:
            pass

    try:
        thread.finished.connect(_cleanup)
    except Exception:
        pass
