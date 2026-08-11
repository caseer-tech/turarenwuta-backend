from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    paystack_secret_key: str
    paystack_public_key: str

    resend_api_key: str
    from_email: str

    qr_secret: str
    admin_key: str  # protects /admin/* endpoints — pick a long random string

    ticket_price_kobo_regular: int = 2_500_000  # NGN 25,000
    ticket_price_kobo_vip: int  # required — set explicitly, no silent default for a new price tier
    capacity: int = 500
    vip_capacity: int = 20

    frontend_success_url: str
    allowed_origins: str = "http://localhost:5173"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
