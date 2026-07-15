from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import checkout, webhook, checkin

# Creates the tickets table if it doesn't exist yet. Fine for this project's scale;
# for anything bigger you'd switch to a migration tool (Alembic) instead.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Turaren Wuta Carnival Ticketing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(checkout.router)
app.include_router(webhook.router)
app.include_router(checkin.router)


@app.get("/health")
def health():
    return {"status": "ok"}
