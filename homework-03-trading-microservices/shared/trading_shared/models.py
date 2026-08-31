from sqlalchemy import BigInteger, Text, Numeric, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional
import uuid


class Base(DeclarativeBase):
    pass


class Books(Base):
    __tablename__ = "Books"

    book_id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_asset_class: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_by: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Trades(Base):
    __tablename__ = "Trades"

    trade_id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("Books.book_id"), nullable=False)
    asset_class: Mapped[str] = mapped_column(Text, nullable=False)
    instrument_id: Mapped[str] = mapped_column(Text, nullable=False)
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    side: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric, nullable=False)
    trade_price: Mapped[float] = mapped_column(Numeric, nullable=False)
    trade_currency: Mapped[str] = mapped_column(Text, nullable=False)
    trade_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="ACTIVE")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    close_price: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    close_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_settled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="GENERATED")
    client_request_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True, unique=True)
    trade_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Valuations(Base):
    __tablename__ = "Valuations"

    valuation_id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trade_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("Trades.trade_id"), nullable=False)
    book_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("Books.book_id"), nullable=False)
    asset_class: Mapped[str] = mapped_column(Text, nullable=False)
    valuation_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fair_value: Mapped[float] = mapped_column(Numeric, nullable=False)
    market_value: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    unrealized_pnl: Mapped[float] = mapped_column(Numeric, nullable=False, default=0)
    realized_pnl: Mapped[float] = mapped_column(Numeric, nullable=False, default=0)
    total_pnl: Mapped[float] = mapped_column(Numeric, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    market_data_reference: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valuation_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class MarketDataSpotPrices(Base):
    __tablename__ = "MarketDataSpotPrices"

    market_data_id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    asset_class: Mapped[str] = mapped_column(Text, nullable=False)
    bid: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    ask: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    mid: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    last: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    spot: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    currency: Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="SIMULATED")
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class MarketDataCurves(Base):
    __tablename__ = "MarketDataCurves"

    curve_id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    curve_name: Mapped[str] = mapped_column(Text, nullable=False)
    curve_type: Mapped[str] = mapped_column(Text, nullable=False)
    currency: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tenors: Mapped[list] = mapped_column(JSONB, nullable=False)
    rates: Mapped[list] = mapped_column(JSONB, nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class MarketDataSnapshots(Base):
    __tablename__ = "MarketDataSnapshots"

    snapshot_id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    snapshot_type: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class AuditLogs(Base):
    __tablename__ = "AuditLogs"

    audit_id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(Text, nullable=False, default="INFO")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
