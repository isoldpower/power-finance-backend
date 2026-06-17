from logging import getLogger


def get_http_logger(*chunks: str):
    iterable: list[str] = ["http", *chunks]
    final_logger_path: str = str.join(".", iterable)

    return getLogger(final_logger_path)


def get_workers_logger(*chunks: str):
    iterable: list[str] = ["background_workers", *chunks]
    final_logger_path: str = str.join(".", iterable)

    return getLogger(final_logger_path)


def get_main_logger(*chunks: str):
    iterable: list[str] = ["data_write_core", *chunks]
    final_logger_path: str = str.join(".", iterable)

    return getLogger(final_logger_path)
