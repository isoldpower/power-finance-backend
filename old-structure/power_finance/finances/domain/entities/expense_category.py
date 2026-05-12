from enum import Enum


class ExpenseCategory(str, Enum):
    FOOD = "food"
    TRANSPORTATION = "transportation"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    OTHER = "other"
    HEALTH = "health"
    EDUCATION = "education"
    TRAVEL = "travel"
    BILLS = "bills"