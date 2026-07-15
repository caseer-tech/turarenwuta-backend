from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    paystack_secret_key: str
    paystack_public_key: str

    resend_api_key: str
    from_email: str

    qr_secret: str

    ticket_price_kobo: int = 2_500_000  # NGN 25,000 — Paystack amounts are always in kobo
    capacity: int = 500

    frontend_success_url: str
    allowed_origins: str = "http://localhost:5173"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
