import logging
from typing import List

from PyQt5.QtCore import QThread

logger = logging.getLogger(__name__)

LAN_DISABLED_MESSAGE = (
    "El servicio LAN fue deshabilitado completamente por mantenimiento. "
    "No inicia servidor, no acepta clientes y no realiza sincronizacion."
)


def run_standalone_server(*_args, **_kwargs):
    logger.warning("[LAN DISABLED] Se intento iniciar el servidor LAN en modo standalone.")
    print(LAN_DISABLED_MESSAGE)
    return False


class LanServerWorker(QThread):
    def __init__(self, *args, **kwargs):
        super().__init__(kwargs.get("parent"))
        self._running = False

    def run(self):
        self._running = False
        logger.warning("[LAN DISABLED] LanServerWorker.run() ignorado.")

    def stop_server(self):
        self._running = False
        logger.warning("[LAN DISABLED] stop_server() llamado en stub.")


class LanAutoSyncWorker(QThread):
    def __init__(self, *args, **kwargs):
        super().__init__(kwargs.get("parent"))
        self._running = False

    def run(self):
        self._running = False
        logger.warning("[LAN DISABLED] LanAutoSyncWorker.run() ignorado.")

    def stop(self):
        self._running = False
        logger.warning("[LAN DISABLED] stop() llamado en auto-sync stub.")


class LanClient:
    def __init__(self, username):
        self.username = username

    def sincronizar_todo(self, _host, _port) -> List[str]:
        logger.warning("[LAN DISABLED] Se intento sincronizar por LAN para username=%s.", self.username)
        return [LAN_DISABLED_MESSAGE]
