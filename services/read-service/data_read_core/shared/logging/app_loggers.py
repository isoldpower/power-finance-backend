from logging import getLogger


def get_query_logger(*chunks: str):
    iterable: list[str] = ["query_slices", *chunks]
    final_logger_path: str = str.join(".", iterable)

    return getLogger(final_logger_path)


def get_workers_logger(*chunks: str):
    iterable: list[str] = ["background_workers", *chunks]
    final_logger_path: str = str.join(".", iterable)

    return getLogger(final_logger_path)


def get_main_logger(*chunks: str):
    iterable: list[str] = ["data_read_core", *chunks]
    final_logger_path: str = str.join(".", iterable)

    return getLogger(final_logger_path)
