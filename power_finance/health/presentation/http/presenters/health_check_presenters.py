from health.application.dtos import ApplicationReadyReportDTO, ApplicationInitializedReportDTO


class HealthCheckPresenters:
    @staticmethod
    def present_ready_report(report: ApplicationReadyReportDTO) -> dict:
        return {
            "status": report.status if report.status == "ok" or report.status == "degraded" else "unknown",
            "checks": {
                "postgres": report.postgres,
                "rabbitmq": report.rabbitmq,
                "redis": report.redis,
            }
        }

    @staticmethod
    def present_started_report(report: ApplicationInitializedReportDTO) -> dict:
        return {
            "status": report.status if report.status == "ok" or report.status == "degraded" else "unknown",
            "checks": {
                "postgres": report.postgres,
                "migrations": report.migrations,
            }
        }