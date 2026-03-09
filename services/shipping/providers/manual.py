"""Manual shipping provider — stub for MVP with no external API calls."""

from typing import Any

from services.shipping.providers.base import (
    LabelResult,
    RateResult,
    ShippingProvider,
    TrackingResult,
)


class ManualProvider(ShippingProvider):
    """Stub provider for manual tracking number entry.

    No external API calls — labels and tracking are entered manually by the seller.
    This provider is the default at MVP; swap in ShippoProvider or EasyPostProvider later.
    """

    def create_label(
        self,
        *,
        from_address: dict[str, str],
        to_address: dict[str, str],
        weight_oz: float,
        carrier: str | None = None,
    ) -> LabelResult:
        """Return a success stub — no actual label is generated."""
        return LabelResult(
            success=True,
            label_url="",
            tracking_number="",
        )

    def get_rates(
        self,
        *,
        from_address: dict[str, str],
        to_address: dict[str, str],
        weight_oz: float,
    ) -> list[RateResult]:
        """Return empty rates — manual provider doesn't support rate comparison."""
        return []

    def track_shipment(self, carrier: str, tracking_number: str) -> TrackingResult:
        """Return unknown status — manual provider doesn't support tracking lookup."""
        return TrackingResult(
            status="unknown",
            events=[],
        )
