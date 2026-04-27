import logging


class ContextLogger:
    """
    Structured logger that always includes project and correlation_id in log messages.
    """

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger()

    def info(self, msg, project=None, correlation_id=None, **kwargs):
        self.logger.info(self._format(msg, project, correlation_id), **kwargs)

    def error(self, msg, project=None, correlation_id=None, **kwargs):
        self.logger.error(self._format(msg, project, correlation_id), **kwargs)

    def warning(self, msg, project=None, correlation_id=None, **kwargs):
        self.logger.warning(self._format(msg, project, correlation_id), **kwargs)

    def debug(self, msg, project=None, correlation_id=None, **kwargs):
        self.logger.debug(self._format(msg, project, correlation_id), **kwargs)

    def _format(self, msg, project, correlation_id):
        return f"[project={project or 'unknown'}] [correlation_id={correlation_id or 'none'}] {msg}"
