import argparse
import asyncio
import sys

from kafka_consumer_py import ConsumerConfig
from service_core.shared.db_connection import dispose_engine
from service_core.shared.logging import get_service_logger

from .config import (
    WorkerSettings,
    build_consumer_config,
    configure_logging,
    get_worker_settings,
)
from .services import build_event_router


def build_argument_parser(settings: WorkerSettings) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-dispatcher",
        description="Consume write-service events and dispatch the postings behind them.",
    )
    parser.add_argument(
        "--bootstrap-servers",
        default=settings.kafka_bootstrap_servers,
        help=f"Kafka bootstrap servers (default: {settings.kafka_bootstrap_servers}).",
    )
    parser.add_argument(
        "--topic",
        action="append",
        dest="topics",
        help=f"Topic to consume; repeatable (default: {settings.kafka_outbox_topic}).",
    )
    parser.add_argument(
        "--group-id",
        default=settings.kafka_group_id,
        help=f"Consumer group id (default: {settings.kafka_group_id}).",
    )
    parser.add_argument(
        "--from-beginning",
        action="store_true",
        help="Read from the earliest offset instead of the latest.",
    )

    return parser


async def run(config: ConsumerConfig) -> None:
    try:
        await build_event_router(config)
    finally:
        await dispose_engine()


def main(argv: list[str] | None = None) -> int:
    settings = get_worker_settings()
    configure_logging(settings.log_level)

    arguments = build_argument_parser(settings).parse_args(argv)
    config = build_consumer_config(settings, arguments)

    logger = get_service_logger("dispatcher")
    logger.info(
        "starting dispatcher — servers=%s group=%s topics=%s",
        config.bootstrap_servers,
        config.group_id,
        list(config.topics),
    )

    try:
        asyncio.run(run(config))
    except KeyboardInterrupt:
        logger.warning("interrupted — shutting down")

    return 0


if __name__ == "__main__":
    sys.exit(main())
