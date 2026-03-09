"""Tests for shipping providers."""

from services.shipping.providers.base import LabelResult, RateResult, TrackingResult
from services.shipping.providers.manual import ManualProvider


class TestManualProvider:
    """Tests for ManualProvider stub implementation."""

    def setup_method(self):
        self.provider = ManualProvider()

    def test_create_label_returns_success(self):
        result = self.provider.create_label(
            from_address={"street1": "456 Oak Ave"},
            to_address={"street1": "123 Main St", "city": "Springfield"},
            weight_oz=12.0,
            carrier="usps",
        )
        assert isinstance(result, LabelResult)
        assert result.success is True
        assert result.label_url == ""
        assert result.tracking_number == ""

    def test_create_label_no_carrier(self):
        result = self.provider.create_label(
            from_address={},
            to_address={},
            weight_oz=1.0,
        )
        assert result.success is True

    def test_get_rates_returns_empty(self):
        result = self.provider.get_rates(
            from_address={},
            to_address={},
            weight_oz=10.0,
        )
        assert isinstance(result, list)
        assert len(result) == 0

    def test_track_shipment_returns_unknown(self):
        result = self.provider.track_shipment("usps", "123456")
        assert isinstance(result, TrackingResult)
        assert result.status == "unknown"
        assert result.events == []


class TestDataClasses:
    """Tests for provider data classes."""

    def test_label_result_defaults(self):
        result = LabelResult(success=True, label_url="url", tracking_number="123")
        assert result.error is None

    def test_label_result_with_error(self):
        result = LabelResult(success=False, label_url="", tracking_number="", error="API down")
        assert result.error == "API down"

    def test_rate_result_defaults(self):
        result = RateResult(carrier="usps", service="priority", rate=5.99)
        assert result.currency == "USD"
        assert result.estimated_days is None

    def test_rate_result_full(self):
        result = RateResult(carrier="fedex", service="ground", rate=7.50, currency="USD", estimated_days=3)
        assert result.estimated_days == 3

    def test_tracking_result_defaults(self):
        result = TrackingResult(status="in_transit")
        assert result.location is None
        assert result.estimated_delivery is None
        assert result.events is None

    def test_tracking_result_full(self):
        result = TrackingResult(
            status="delivered",
            location="Springfield, IL",
            estimated_delivery="2024-01-15",
            events=[{"event": "delivered", "timestamp": "2024-01-14T10:00:00Z"}],
        )
        assert result.location == "Springfield, IL"
        assert len(result.events) == 1
