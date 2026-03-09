"""Tests for inventory schemas."""

import uuid

import pytest
from marshmallow import ValidationError

from services.inventory.schemas.schemas import (
    CategoryCreateSchema,
    CategoryUpdateSchema,
    CSVMappingSchema,
    ItemCreateSchema,
    ItemListQuerySchema,
    ItemUpdateSchema,
)


class TestItemCreateSchema:
    def test_valid_full(self) -> None:
        schema = ItemCreateSchema()
        data = schema.load({
            "name": "Widget",
            "description": "A widget",
            "cogs": 10.50,
            "quantity": 5,
            "status": "available",
        })
        assert data["name"] == "Widget"
        assert data["cogs"] == 10.50

    def test_valid_minimal(self) -> None:
        schema = ItemCreateSchema()
        data = schema.load({"name": "Widget"})
        assert data["name"] == "Widget"
        assert data["description"] == ""
        assert data["cogs"] == 0.0
        assert data["quantity"] == 1
        assert data["status"] == "available"

    def test_missing_name(self) -> None:
        schema = ItemCreateSchema()
        with pytest.raises(ValidationError) as exc:
            schema.load({})
        assert "name" in exc.value.messages

    def test_empty_name(self) -> None:
        schema = ItemCreateSchema()
        with pytest.raises(ValidationError):
            schema.load({"name": ""})

    def test_invalid_status(self) -> None:
        schema = ItemCreateSchema()
        with pytest.raises(ValidationError):
            schema.load({"name": "X", "status": "invalid"})

    def test_negative_cogs(self) -> None:
        schema = ItemCreateSchema()
        with pytest.raises(ValidationError):
            schema.load({"name": "X", "cogs": -5.0})

    def test_negative_quantity(self) -> None:
        schema = ItemCreateSchema()
        with pytest.raises(ValidationError):
            schema.load({"name": "X", "quantity": -1})


class TestItemUpdateSchema:
    def test_partial_update(self) -> None:
        schema = ItemUpdateSchema()
        data = schema.load({"name": "New Name"})
        assert data == {"name": "New Name"}

    def test_empty_update(self) -> None:
        schema = ItemUpdateSchema()
        data = schema.load({})
        assert data == {}

    def test_invalid_status(self) -> None:
        schema = ItemUpdateSchema()
        with pytest.raises(ValidationError):
            schema.load({"status": "bad"})


class TestItemListQuerySchema:
    def test_defaults(self) -> None:
        schema = ItemListQuerySchema()
        data = schema.load({})
        assert data["cursor"] is None
        assert data["limit"] == 50
        assert data["search"] is None
        assert data["status"] is None

    def test_all_filters(self) -> None:
        schema = ItemListQuerySchema()
        cat_id = str(uuid.uuid4())
        data = schema.load({
            "cursor": "abc",
            "limit": "25",
            "search": "widget",
            "category_id": cat_id,
            "status": "sold",
            "min_cogs": "5.0",
            "max_cogs": "100.0",
        })
        assert data["limit"] == 25
        assert data["search"] == "widget"
        assert data["status"] == "sold"

    def test_limit_too_large(self) -> None:
        schema = ItemListQuerySchema()
        with pytest.raises(ValidationError):
            schema.load({"limit": "200"})


class TestCategoryCreateSchema:
    def test_valid(self) -> None:
        schema = CategoryCreateSchema()
        data = schema.load({"name": "Electronics"})
        assert data["name"] == "Electronics"
        assert data["description"] == ""

    def test_missing_name(self) -> None:
        schema = CategoryCreateSchema()
        with pytest.raises(ValidationError):
            schema.load({})

    def test_empty_name(self) -> None:
        schema = CategoryCreateSchema()
        with pytest.raises(ValidationError):
            schema.load({"name": ""})


class TestCategoryUpdateSchema:
    def test_partial(self) -> None:
        schema = CategoryUpdateSchema()
        data = schema.load({"name": "Updated"})
        assert data == {"name": "Updated"}

    def test_empty(self) -> None:
        schema = CategoryUpdateSchema()
        data = schema.load({})
        assert data == {}


class TestCSVMappingSchema:
    def test_valid_mapping(self) -> None:
        schema = CSVMappingSchema()
        data = schema.load({"mapping": {"Col A": "name", "Col B": "cogs"}})
        assert data["mapping"]["Col A"] == "name"

    def test_invalid_target(self) -> None:
        schema = CSVMappingSchema()
        with pytest.raises(ValidationError):
            schema.load({"mapping": {"Col A": "bad_field"}})

    def test_missing_mapping(self) -> None:
        schema = CSVMappingSchema()
        with pytest.raises(ValidationError):
            schema.load({})
