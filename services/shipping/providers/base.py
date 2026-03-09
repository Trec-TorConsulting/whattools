"""Abstract base class for shipping providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class LabelResult:
    """Result of a label creation request."""

    success: bool
    label_url: str
    tracking_number: str
    error: str | None = None


@dataclass
class RateResult:
    """Result of a rate quote request."""

    carrier: str
    service: str
    rate: float
    currency: str = "USD"
    estimated_days: int | None = None


@dataclass
class TrackingResult:
    """Result of a tracking lookup."""

    status: str
    location: str | None = None
    estimated_delivery: str | None = None
    events: list[dict[str, Any]] | None = None


class ShippingProvider(ABC):
    """Abstract interface for shipping label generation and tracking.

    Implementations: ManualProvider (MVP), ShippoProvider (future), EasyPostProvider (future).
    """

    @abstractmethod
    def create_label(
        self,
        *,
        from_address: dict[str, str],
        to_address: dict[str, str],
        weight_oz: float,
        carrier: str | None = None,
    ) -> LabelResult:
        """Create a shipping label."""

    @abstractmethod
    def get_rates(
        self,
        *,
        from_address: dict[str, str],
        to_address: dict[str, str],
        weight_oz: float,
    ) -> list[RateResult]:
        """Get shipping rate quotes."""

    @abstractmethod
    def track_shipment(self, carrier: str, tracking_number: str) -> TrackingResult:
        """Look up tracking information for a shipment."""
