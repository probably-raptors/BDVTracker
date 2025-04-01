from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, ForeignKey, DateTime
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from app.db import Base


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    scryfall_id: Mapped[UUID] = mapped_column(unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    set_name: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str] = mapped_column(Text)

    # Scryfall enrichment
    mana_cost: Mapped[str] = mapped_column(Text, nullable=True)
    mana_value: Mapped[int] = mapped_column(nullable=True)
    types: Mapped[list[str]] = mapped_column(ARRAY(Text), default=[])
    power: Mapped[str] = mapped_column(nullable=True)
    toughness: Mapped[str] = mapped_column(nullable=True)
    legality: Mapped[list[str]] = mapped_column(ARRAY(Text), default=[])

    # Relationships
    listings: Mapped[list["Listing"]] = relationship(
        "Listing", back_populates="card", cascade="all, delete-orphan"
    )


class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    store_url: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    listings: Mapped[list["Listing"]] = relationship(
        "Listing", back_populates="seller", cascade="all, delete-orphan"
    )


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    bdv_listing_id: Mapped[int] = mapped_column(unique=True, nullable=False)

    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id", ondelete="CASCADE"))
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"))

    price: Mapped[float] = mapped_column(nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    condition: Mapped[str] = mapped_column(Text, nullable=False)
    foil: Mapped[bool] = mapped_column(default=False)
    language: Mapped[str] = mapped_column(Text, nullable=False)

    last_seen: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    seller: Mapped["Seller"] = relationship("Seller", back_populates="listings")
    card: Mapped["Card"] = relationship("Card", back_populates="listings")
