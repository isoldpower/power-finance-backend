from write_service.common.logging import get_main_logger


def log_command_started(label: str, args: object, kwargs: object) -> None:
    logger = get_main_logger("commands")
    logger.info("%s: handle() start args=%s kwargs=%s", label, args, kwargs)


def log_command_finished(label: str) -> None:
    logger = get_main_logger("commands")
    logger.info("%s: handle() done", label)
