from dataclasses import dataclass


@dataclass
class ApplicationReadyReportDTO:
    status: str
    postgres: str
    rabbitmq: str
    redis: str


@dataclass
class ApplicationInitializedReportDTO:
    status: str
    postgres: str
    migrations: str