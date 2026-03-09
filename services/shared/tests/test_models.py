"""Tests for the base model."""

import uuid
from datetime import datetime, timezone

from services.shared.models import BaseModel


class TestBaseModel:
    """Tests for BaseModel common fields."""

    def test_base_model_is_abstract(self) -> None:
        """BaseModel should be abstract and not directly instantiable as a table."""
        assert BaseModel.__abstract__ is True

    def test_base_model_has_required_columns(self) -> None:
        """BaseModel should define id, created_at, updated_at, deleted_at columns."""
        assert hasattr(BaseModel, "id")
        assert hasattr(BaseModel, "created_at")
        assert hasattr(BaseModel, "updated_at")
        assert hasattr(BaseModel, "deleted_at")
