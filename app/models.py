from datetime import datetime
import uuid
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Seller(Base):
    __tablename__ = "sellers"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    store_url = Column(Text, nullable=False)

    # A seller can have many listings.
    listings = relationship(
        "Listing", back_populates="seller", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Seller(name={self.name}, store_url={self.store_url})>"


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True)
    scryfall_id = Column(
        PG_UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4
    )
    name = Column(Text, nullable=False)
    set_name = Column(Text, nullable=False)
    image_url = Column(Text, nullable=True)
    mana_cost = Column(Text, nullable=True)
    mana_value = Column(Integer, nullable=True)
    types = Column(
        ARRAY(String), nullable=False, default=[]
    )  # List of card types, e.g. ["Creature", "Legendary"]
    power = Column(Text, nullable=True)
    toughness = Column(Text, nullable=True)

    # A card can be listed by multiple sellers.
    listings = relationship(
        "Listing", back_populates="card", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Card(name={self.name}, set_name={self.set_name})>"


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True)
    bdv_listing_id = Column(Integer, nullable=False, unique=True)

    seller_id = Column(
        Integer, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False
    )
    card_id = Column(
        Integer, ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )

    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    condition = Column(Text, nullable=False)
    foil = Column(Boolean, default=False)
    language = Column(Text, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow)

    # Relationships: each listing is associated with one seller and one card.
    seller = relationship("Seller", back_populates="listings")
    card = relationship("Card", back_populates="listings")

    def __repr__(self):
        return f"<Listing(seller_id={self.seller_id}, card_id={self.card_id}, price={self.price})>"
