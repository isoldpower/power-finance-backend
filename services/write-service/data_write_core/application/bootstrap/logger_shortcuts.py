from write_service.common.logging import get_workers_logger


def log_gate_skipped_testing(label: str) -> None:
    logger = get_workers_logger("bootstrap")
    logger.info("%s: skipped — settings.TESTING is truthy", label)


def log_gate_skipped_infra_free(label: str, command: str) -> None:
    logger = get_workers_logger("bootstrap")
    logger.info("%s: skipped — infra-free command '%s'", label, command)
