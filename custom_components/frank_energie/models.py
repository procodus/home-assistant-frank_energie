"""Data models for the Frank Energie integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from dateutil.parser import parse as parse_datetime


def _utcnow() -> datetime:
    """Return current UTC time. Separated for easy mocking in tests."""
    return datetime.now(timezone.utc)


@dataclass
class Price:
    """Represents a single hourly energy price."""

    date_from: datetime
    date_till: datetime
    market_price: float
    market_price_tax: float
    sourcing_markup_price: float
    energy_tax_price: float

    @property
    def total(self) -> float:
        return round(
            self.market_price + self.market_price_tax + self.sourcing_markup_price + self.energy_tax_price,
            5,
        )

    @property
    def market_price_with_tax(self) -> float:
        return round(self.market_price + self.market_price_tax, 5)

    @property
    def for_current_hour(self) -> bool:
        now = _utcnow()
        return self.date_from <= now < self.date_till

    @property
    def for_today(self) -> bool:
        today = _utcnow().date()
        # Compare in UTC to avoid timezone date boundary issues
        date_from_utc = self.date_from.astimezone(timezone.utc).date()
        return date_from_utc == today

    @property
    def for_upcoming(self) -> bool:
        return self.date_till > _utcnow()

    @classmethod
    def from_dict(cls, data: dict) -> Price:
        return cls(
            date_from=parse_datetime(data["from"]),
            date_till=parse_datetime(data["till"]),
            market_price=data.get("marketPrice", 0.0),
            market_price_tax=data.get("marketPriceTax", 0.0),
            sourcing_markup_price=data.get("sourcingMarkupPrice", 0.0),
            energy_tax_price=data.get("energyTaxPrice", 0.0),
        )

    @classmethod
    def from_user_prices_dict(cls, data: dict) -> Price:
        """Parse from customerMarketPrices response which uses different field names."""
        return cls(
            date_from=parse_datetime(data["from"]),
            date_till=parse_datetime(data["till"]),
            market_price=data.get("marketPrice", 0.0),
            market_price_tax=data.get("marketPriceTax", 0.0),
            sourcing_markup_price=data.get("consumptionSourcingMarkupPrice", 0.0),
            energy_tax_price=data.get("energyTax", 0.0),
        )


@dataclass
class PriceData:
    """Collection of hourly prices with statistical methods."""

    price_data: list[Price] = field(default_factory=list)

    @property
    def current_hour(self) -> Price | None:
        return next((p for p in self.price_data if p.for_current_hour), None)

    @property
    def today(self) -> list[Price]:
        return [p for p in self.price_data if p.for_today]

    @property
    def today_min(self) -> Price | None:
        today = self.today
        return min(today, key=lambda p: p.total) if today else None

    @property
    def today_max(self) -> Price | None:
        today = self.today
        return max(today, key=lambda p: p.total) if today else None

    @property
    def today_avg(self) -> float | None:
        today = self.today
        if not today:
            return None
        return round(sum(p.total for p in today) / len(today), 5)

    @property
    def upcoming(self) -> list[Price]:
        return [p for p in self.price_data if p.for_upcoming]

    @property
    def all(self) -> list[Price]:
        return self.price_data

    def asdict(self, attr: str) -> list[dict]:
        """Convert prices to list of dicts for sensor attributes."""
        result = []
        for price in self.price_data:
            result.append({
                "from": price.date_from.isoformat(),
                "till": price.date_till.isoformat(),
                "price": getattr(price, attr),
            })
        return result

    def __add__(self, other: PriceData) -> PriceData:
        return PriceData(price_data=self.price_data + other.price_data)


@dataclass
class MarketPrices:
    """Container for electricity and gas prices."""

    electricity: PriceData
    gas: PriceData


@dataclass
class MonthSummary:
    """Monthly cost summary."""

    actualCostsUntilLastMeterReadingDate: float | None = None
    expectedCostsUntilLastMeterReadingDate: float | None = None
    lastMeterReadingDate: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> MonthSummary:
        return cls(
            actualCostsUntilLastMeterReadingDate=data.get("actualCostsUntilLastMeterReadingDate"),
            expectedCostsUntilLastMeterReadingDate=data.get("expectedCostsUntilLastMeterReadingDate"),
            lastMeterReadingDate=data.get("lastMeterReadingDate"),
        )


@dataclass
class Invoice:
    """A single invoice period."""

    totalAmount: float | None = None
    startDate: str | None = None
    periodDescription: str | None = None

    @classmethod
    def from_dict(cls, data: dict | None) -> Invoice | None:
        if data is None:
            return None
        return cls(
            totalAmount=data.get("totalAmount"),
            startDate=data.get("startDate"),
            periodDescription=data.get("periodDescription"),
        )


@dataclass
class Invoices:
    """Collection of invoice periods."""

    previousPeriodInvoice: Invoice | None = None
    currentPeriodInvoice: Invoice | None = None
    upcomingPeriodInvoice: Invoice | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Invoices:
        return cls(
            previousPeriodInvoice=Invoice.from_dict(data.get("previousPeriodInvoice")),
            currentPeriodInvoice=Invoice.from_dict(data.get("currentPeriodInvoice")),
            upcomingPeriodInvoice=Invoice.from_dict(data.get("upcomingPeriodInvoice")),
        )


@dataclass
class UserSite:
    """A delivery site for the user."""

    reference: str
    status: str
    address: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> UserSite:
        address = None
        addr_data = data.get("address")
        if addr_data:
            formatted = addr_data.get("addressFormatted")
            if formatted and isinstance(formatted, list) and len(formatted) > 0:
                address = formatted[0]
        return cls(
            reference=data.get("reference", ""),
            status=data.get("status", ""),
            address=address,
        )
