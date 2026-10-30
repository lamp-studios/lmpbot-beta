import os

from dotenv import load_dotenv

load_dotenv()


def _env(name: str) -> str | None:
    """An environment variable, with blank values treated as unset."""
    value = os.getenv(name)
    return value if value else None


class Config:
    token = _env("DANGER_DONTSHARETOYKEN")
    gemini_api_key = _env("GEMINI_API_KEY")
    openai_api_key = _env("OPENAI_API_KEY")
    openai_base_url = _env("OPENAI_BASE_URL")
    ollama_host = _env("OLLAMA_HOST")
    mongo_uri = _env("MONGODB_URI")
    supabase_url = _env("SUPABASE_URL")
    supabase_key = _env("SUPABASE_KEY")
    neon_database_url = _env("DATABASE_URL")
    neon_database_url_unpooled = _env("DATABASE_URL_UNPOOLED")
    turso_database_url = _env("TURSO_DATABASE_URL")
    turso_auth_token = _env("TURSO_AUTH_TOKEN")
    kuma_push_url = _env("KUMA_PUSH_URL")
    pushgateway_url = _env("PUSHGATEWAY_URL")
    prefix = "."


config = Config()
