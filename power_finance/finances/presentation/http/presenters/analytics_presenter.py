from typing import Any
from finances.application.dtos import (
    CategoryAnalyticsResultDTO,
    ExpenditureAnalyticsResultDTO,
    SpendingHeatmapResultDTO,
    WalletBalanceHistoryResultDTO,
    MoneyFlowResultDTO,
)


class AnalyticsHttpPresenter:
    @staticmethod
    def present_analytics_data(
        data: Any,
        metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return {
            "data": data,
            "metadata": metadata or {}
        }

    @staticmethod
    def present_categories(result: CategoryAnalyticsResultDTO) -> list[dict[str, Any]]:
        return [{
            "category": item.category,
            "amount": item.amount
        } for item in result.items]

    @staticmethod
    def present_expenditures(result: ExpenditureAnalyticsResultDTO) -> dict[str, dict[str, float]]:
        return result.expenditure_by_month

    @staticmethod
    def present_spending_heatmap(result: SpendingHeatmapResultDTO) -> dict[str, float]:
        return result.spending_by_day

    @staticmethod
    def present_wallet_balance_history(result: WalletBalanceHistoryResultDTO) -> list[dict[str, Any]]:
        return [{
            "date": item.date,
            "balance": item.balance
        } for item in result.history]

    @staticmethod
    def present_money_flow(result: MoneyFlowResultDTO) -> dict[str, list[dict[str, Any]]]:
        return {
            "nodes": [{
                "name": node.name,
                "level": node.level
            } for node in result.nodes],
            "links": [{
                "source": link.source_id,
                "target": link.target_id,
                "value": link.value
            } for link in result.links],
        }