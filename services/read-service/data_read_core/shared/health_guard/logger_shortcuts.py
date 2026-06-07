from data_read_core.shared.logging import get_workers_logger


def warn_probe_unavailable(title: str, poll_seconds: float):
    logger = get_workers_logger("health")
    logger.warning(
        "%s still unavailable; next health check in %.1fs.",
        title,
        poll_seconds,
    )


def warn_projection_unavailable(title: str, event_id: str, error: str):
    logger = get_workers_logger("health")
    logger.warning(
        "%s unavailable while projecting event %s; " "blocking consumption until recovery (%s).",
        title,
        event_id,
        error,
    )


def log_probe_available_again(title: str):
    logger = get_workers_logger("health")
    logger.info("%s available again; resuming.", title)
