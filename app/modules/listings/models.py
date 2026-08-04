import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class ListingType(enum.StrEnum):
    Dacha = "Dacha"
    Hotel = "Hotel"
    Boutique = "Boutique"
    Hostel = "Hostel"
    Recreation = "Recreation"
    Camping = "Camping"
    Villa = "Villa"
    Sanatorium = "Sanatorium"
    RentCar = "RentCar"
    Dining = "Dining"
    Aqua = "Aqua"


class Region(enum.StrEnum):
    Bostanliq = "Bostanliq"
    Zomin = "Zomin"
    Khiva = "Khiva"
    Samarkand = "Samarkand"
    Bukhara = "Bukhara"
    Tashkent = "Tashkent"
    ToshkentViloyat = "ToshkentViloyat"
    Namangan = "Namangan"
    Andijan = "Andijan"
    Fergana = "Fergana"
    Surkhandarya = "Surkhandarya"
    Kashkadarya = "Kashkadarya"
    Navoi = "Navoi"
    Syrdarya = "Syrdarya"
    Jizzakh = "Jizzakh"
    Khorezm = "Khorezm"
    Karakalpakstan = "Karakalpakstan"


class Amenity(enum.StrEnum):
    pool = "pool"
    sauna = "sauna"
    wifi = "wifi"
    kitchen = "kitchen"
    breakfast = "breakfast"
    aircon = "aircon"
    parking = "parking"
    petFriendly = "petFriendly"
    tents = "tents"
    campfire = "campfire"
    shower = "shower"
    water = "water"
    electricity = "electricity"
    restaurant = "restaurant"
    lift = "lift"
    tv = "tv"
    phone = "phone"
    laundry = "laundry"
    lockers = "lockers"
    reception24 = "reception24"
    sportzone = "sportzone"
    medical = "medical"
    doctor = "doctor"
    fullboard = "fullboard"
    withDriver = "withDriver"
    withoutDriver = "withoutDriver"
    gps = "gps"
    childSeat = "childSeat"
    deliveryToClient = "deliveryToClient"
    liveMusic = "liveMusic"
    banquetHall = "banquetHall"
    delivery = "delivery"
    outdoorSeating = "outdoorSeating"
    bar = "bar"
    minibar = "minibar"
    safe = "safe"
    gym = "gym"
    spa = "spa"
    billiards = "billiards"
    tableTennis = "tableTennis"
    conference = "conference"
    roomService = "roomService"
    airportTransfer = "airportTransfer"
    evCharging = "evCharging"
    accessible = "accessible"
    iron = "iron"

    # Dam olish maskani / resort
    heatedPool = "heatedPool"
    beach = "beach"
    gazebo = "gazebo"
    horseRiding = "horseRiding"
    bikeRental = "bikeRental"
    skiRental = "skiRental"
    waterSports = "waterSports"
    animator = "animator"

    # Avtomobil ijarasi
    insuranceKasko = "insuranceKasko"
    insuranceOsago = "insuranceOsago"
    dashcam = "dashcam"
    sunroof = "sunroof"
    heatedSeats = "heatedSeats"
    winterTires = "winterTires"
    usbBluetooth = "usbBluetooth"

    # Hostel
    luggage = "luggage"
    cctv = "cctv"
    coworking = "coworking"
    freeCoffee = "freeCoffee"
    microwave = "microwave"
    fridge = "fridge"
    hairdryer = "hairdryer"
    towels = "towels"

    # Sanatoriya / kurort
    park = "park"
    pharmacy = "pharmacy"
    library = "library"
    cinema = "cinema"
    kidsPlayground = "kidsPlayground"
    atm = "atm"
    excursions = "excursions"
    mineralWater = "mineralWater"

    # Ovqatlanish maskani
    panorama = "panorama"
    tapchan = "tapchan"
    hookah = "hookah"
    dancefloor = "dancefloor"
    karaoke = "karaoke"
    dj = "dj"
    vipRoom = "vipRoom"
    sportsTv = "sportsTv"
    smokingArea = "smokingArea"
    valet = "valet"
    halal = "halal"
    alcoholFree = "alcoholFree"
    terrace = "terrace"


class SortOption(enum.StrEnum):
    price_asc = "price_asc"
    price_desc = "price_desc"
    rating = "rating"
    newest = "newest"
    hot = "hot"
    most_saved = "most_saved"
    discount = "discount"


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rent_companies.id", ondelete="SET NULL"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[ListingType] = mapped_column(Enum(ListingType, name="listing_type"), index=True)
    region: Mapped[Region] = mapped_column(Enum(Region, name="listing_region"), index=True)

    weekday_price: Mapped[float] = mapped_column(Numeric(14, 2))
    weekend_price: Mapped[float] = mapped_column(Numeric(14, 2))
    old_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)

    rating: Mapped[float] = mapped_column(Float, default=0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)

    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    rejected: Mapped[bool] = mapped_column(Boolean, default=False)
    reject_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    capacity: Mapped[int] = mapped_column(Integer)
    amenities: Mapped[list[str]] = mapped_column(ARRAY(String(50)), default=list)

    description: Mapped[str] = mapped_column(String(5000))

    license: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)

    views: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int] = mapped_column(Integer, default=0)
    is_hot: Mapped[bool] = mapped_column(Boolean, default=False)
    discount: Mapped[int] = mapped_column(Integer, default=0)

    extra: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    photos: Mapped[list["ListingPhoto"]] = relationship(
        back_populates="listing",
        cascade="all, delete-orphan",
        order_by="ListingPhoto.position",
    )


class ListingPhoto(Base):
    __tablename__ = "listing_photos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0)

    listing: Mapped["Listing"] = relationship(back_populates="photos")


AMENITY_VALUES: frozenset[str] = frozenset(a.value for a in Amenity)
