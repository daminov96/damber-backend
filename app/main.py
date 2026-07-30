from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.modules.bookings.router import router as bookings_router
from app.modules.guides.router import router as guides_router
from app.modules.listings.router import router as listings_router
from app.modules.operators.router import router as operators_router
from app.modules.plans.router import router as plans_router
from app.modules.rent_companies.router import router as rent_companies_router
from app.modules.reviews.router import router as reviews_router
from app.modules.tours.router import router as tours_router
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
app.include_router(guides_router)
app.include_router(operators_router)
app.include_router(plans_router)
app.include_router(rent_companies_router)
app.include_router(reviews_router)
app.include_router(tours_router)

uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok"}
