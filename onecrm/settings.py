import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text or text.startswith("#") or "=" not in text:
                continue
            key, value = text.split("=", 1)
            values[key.strip()] = value.strip()
    values.update({key: value for key, value in os.environ.items() if key.startswith(("ONECRM_", "GUACAMOLE_", "AUTH_", "PORT", "BIND_"))})
    return values


CONFIG = load_env()


def env(name: str, default: str = "") -> str:
    return CONFIG.get(name, default)


def env_int(name: str, default: int) -> int:
    try:
        return int(env(name, str(default)))
    except ValueError:
        return default


APP_NAME = "OneCRM"
VERSION = "2.5.10"
PORT = env_int("PORT", 8999)
BIND_ADDRESS = env("BIND_ADDRESS", "0.0.0.0")
AUTH_PASSWORD = env("AUTH_PASSWORD", "nho1234567")

DATABASE_URL = env("ONECRM_DATABASE_URL", "postgresql://onecrm:onecrm_pass@127.0.0.1:15432/onecrm")
REDIS_URL = env("ONECRM_REDIS_URL", "redis://127.0.0.1:16379/0")
MINIO_ENDPOINT = env("ONECRM_MINIO_ENDPOINT", "127.0.0.1:19000")
MINIO_ACCESS_KEY = env("ONECRM_MINIO_ACCESS_KEY", "onecrm")
MINIO_SECRET_KEY = env("ONECRM_MINIO_SECRET_KEY", "onecrm_minio_pass")
MINIO_BUCKET = env("ONECRM_MINIO_BUCKET", "onecrm")
APP_SECRET_KEY = env("ONECRM_SECRET_KEY", AUTH_PASSWORD or "onecrm-local-secret")

AI_ENDPOINT = env("ONECRM_AI_ENDPOINT", "").rstrip("/")
AI_MODEL = env("ONECRM_AI_MODEL", "gpt-5.4-mini")
AI_CREDENTIAL_FILE = env("ONECRM_AI_CREDENTIAL_FILE", "")
AI_TIMEOUT_SECONDS = env_int("ONECRM_AI_TIMEOUT_SECONDS", 60)

SESSION_DAYS = env_int("ONECRM_SESSION_DAYS", 7)
PASSWORD_RESET_MINUTES = env_int("ONECRM_PASSWORD_RESET_MINUTES", 30)
PUBLIC_URL = env("ONECRM_PUBLIC_URL", f"http://127.0.0.1:{PORT}")

MAIL_MODE = env("ONECRM_MAIL_MODE", "smtp")
SMTP_HOST = env("ONECRM_SMTP_HOST", "")
SMTP_PORT = env_int("ONECRM_SMTP_PORT", 25)
SMTP_USERNAME = env("ONECRM_SMTP_USERNAME", "")
SMTP_PASSWORD = env("ONECRM_SMTP_PASSWORD", "")
SMTP_FROM = env("ONECRM_SMTP_FROM", "onecrm@example.local")

HERMES_URL = env("ONECRM_HERMES_URL", "http://127.0.0.1:19100").rstrip("/")
HERMES_TIMEOUT_SECONDS = env_int("ONECRM_HERMES_TIMEOUT_SECONDS", 600)
UPLOAD_REJECT_EXTENSIONS = tuple(
    item.strip().lower()
    for item in env("ONECRM_UPLOAD_REJECT_EXTENSIONS", ".dmp").split(",")
    if item.strip()
)
UPLOAD_MAX_FILE_MB = env_int("ONECRM_UPLOAD_MAX_FILE_MB", 100)
UPLOAD_MAX_JOB_MB = env_int("ONECRM_UPLOAD_MAX_JOB_MB", 1024)
