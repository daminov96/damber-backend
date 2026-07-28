from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.modules.bookings.router import router as bookings_router
from app.modules.listings.router import router as listings_router
from app.modules.users.router import router as users_router
from app.modules.wallet.router import router as wallet_router

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(listings_router)
app.include_router(wallet_router)
app.include_router(bookings_router)

uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok"}
