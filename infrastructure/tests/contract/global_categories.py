import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

CATALOGUE_SOURCES = {
    "write-service migration": (
        "services/write-service/data_write_core/infrastructure/orm/migrations/"
        "0018_category_foreign_keys.py"
    ),
    "read-service migration": "services/read-service/data_read_core/migrations/0020_categories.py",
}

NAMESPACE_SOURCES = {
    **CATALOGUE_SOURCES,
    "write-service domain": "services/write-service/data_write_core/domain/value_objects/category.py",
    "read-service test fixtures": (
        "services/read-service/data_read_core/query_slices/__tests__/category_fixtures.py"
    ),
}

CATALOGUE_NAMES = (
    "GLOBAL_TRANSACTION_CATEGORIES",
    "GLOBAL_WALLET_CATEGORIES",
)


def module_constants(relative_path: str) -> dict[str, object]:
    module = ast.parse((REPO_ROOT / relative_path).read_text())
    constants: dict[str, object] = {}
    for statement in module.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if not isinstance(target, ast.Name):
            continue
        constants[target.id] = _literal_or_uuid_text(statement.value)

    return constants


def _literal_or_uuid_text(node: ast.expr) -> object:
    if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "UUID":
        return ast.literal_eval(node.args[0])

    try:
        return ast.literal_eval(node)
    except ValueError:
        return None
