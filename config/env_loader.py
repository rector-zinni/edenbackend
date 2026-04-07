import os
from pathlib import Path


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _has_balanced_braces(value: str) -> bool:
    balance = 0
    in_string = False
    escape = False

    for char in value:
        if escape:
            escape = False
            continue

        if char == "\\":
            escape = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":
            balance += 1
        elif char == "}":
            balance -= 1

    return balance == 0


def load_env_file(dotenv_path: str | None = None) -> None:
    env_path = Path(dotenv_path) if dotenv_path else Path(__file__).resolve().parent.parent / ".env"

    if not env_path.exists():
        return

    lines = env_path.read_text(encoding="utf-8").splitlines()
    index = 0

    while index < len(lines):
        raw_line = lines[index]
        stripped_line = raw_line.strip()

        if not stripped_line or stripped_line.startswith("#") or "=" not in raw_line:
            index += 1
            continue

        raw_key, raw_value = raw_line.split("=", 1)
        key = raw_key.strip()
        value = raw_value.strip()

        if value.startswith("{") and not _has_balanced_braces(value):
            json_lines = [value]
            index += 1

            while index < len(lines):
                json_lines.append(lines[index])
                combined = "\n".join(json_lines)
                if _has_balanced_braces(combined):
                    break
                index += 1

            value = "\n".join(json_lines)

        os.environ.setdefault(key, _strip_wrapping_quotes(value))
        index += 1
