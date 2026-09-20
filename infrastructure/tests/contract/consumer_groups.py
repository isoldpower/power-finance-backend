"""Where each consumer's group id is written down, in code and in compose.

Both mappings below are keyed by the variable name and hold the pair of files
that must agree on it: the settings module and the compose file.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

GROUP_ID_SOURCES = {
    "KAFKA_READ_GROUP_ID": (
        "services/read-service/read_service/settings/base.py",
        "services/read-service/compose.yaml",
    ),
    "KAFKA_AUTOMATION_ENGINE_GROUP_ID": (
        "services/write-service/write_service/settings/base.py",
        "services/write-service/compose.yaml",
    ),
    "KAFKA_FRAUD_ALERTS_GROUP_ID": (
        "services/write-service/write_service/settings/base.py",
        "services/write-service/compose.yaml",
    ),
    "KAFKA_NOTIFICATIONS_INBOUND_GROUP_ID": (
        "services/write-service/write_service/settings/base.py",
        "services/write-service/compose.yaml",
    ),
}

ENVIRONMENT_SOURCES = {
    "KAFKA_AI_GROUP_ID": (
        "services/ai-service/.env.example",
        "services/ai-service/compose.yaml",
    ),
}


def settings_default(variable: str, path: str) -> str | None:
    text = (REPO_ROOT / path).read_text()
    match = re.search(rf'{variable}=\(str, "([^"]+)"\)', text)

    return match.group(1) if match else None


def environment_value(variable: str, path: str) -> str | None:
    text = (REPO_ROOT / path).read_text()
    match = re.search(rf"^{variable}=(.+)$", text, re.M)

    return match.group(1).strip() if match else None


def compose_default(variable: str, path: str) -> str | None:
    text = (REPO_ROOT / path).read_text()
    match = re.search(rf"{variable}:?=?\s*\$\{{{variable}:-([^}}]+)\}}", text)

    return match.group(1) if match else None


def generator_pin(variable: str) -> str | None:
    text = (REPO_ROOT / "infrastructure/dev-host/generate_sandbox_env.sh").read_text()
    match = re.search(rf"{variable}=\$\{{{variable}:-([^}}]+)\}}", text)

    return match.group(1) if match else None
