from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Dev mode — bypass auth, use mock external APIs
    dev_mode: bool = False

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Supabase Auth (not required in dev_mode)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_jwt_secret: str = "dev-secret"

    # External APIs
    serpapi_key: str = ""
    firecrawl_api_key: str = ""
    otterly_api_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    youtube_api_key: str = ""
    anthropic_api_key: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""
    stripe_agency_price_id: str = ""

    # Notifications
    telegram_bot_token: str = ""
    resend_api_key: str = ""

    # LLM provider: "anthropic", "perplexity", or "ollama"
    llm_provider: str = ""  # auto-detect if empty: anthropic > perplexity > ollama

    # Perplexity
    perplexity_api_key: str = ""
    perplexity_model: str = "sonar"

    # Ollama (local LLM fallback)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_api_key: str = ""

    # App
    app_url: str = "http://localhost:5173"
    landing_url: str = "http://localhost:5174"
    api_url: str = "http://localhost:8000"
    kothaykhabo_url: str = "http://localhost:5175"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
