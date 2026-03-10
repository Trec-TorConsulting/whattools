"""Tests for product service."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from services.whatnot.services.product_service import ProductService, ProductServiceError


class TestProductService:
    def test_pull_products_empty(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.return_value = {
            "products": {"edges": [], "pageInfo": {"hasNextPage": False}}
        }

        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.pull_products()

        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["synced"] == 0

    def test_pull_products_creates_items(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.return_value = {
            "products": {
                "edges": [
                    {
                        "node": {
                            "id": "prod_1",
                            "title": "Test Product",
                            "description": "A test product",
                            "variants": {
                                "edges": [
                                    {
                                        "node": {
                                            "id": "var_1",
                                            "price": {"amount": 1500, "currencyCode": "USD"},
                                            "quantity": 5,
                                        }
                                    }
                                ]
                            },
                            "media": {"edges": []},
                        },
                        "cursor": "cursor_1",
                    }
                ],
                "pageInfo": {"hasNextPage": False},
            }
        }

        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.pull_products()

        assert result["synced"] == 1
        assert result["created"] >= 0  # May be created or updated

    def test_push_product_not_found(self, db_session, sample_account, mock_whatnot_client):
        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        fake_id = uuid.uuid4()

        with pytest.raises(ProductServiceError):
            svc.push_product(fake_id)

    def test_delete_product_not_found(self, db_session, sample_account, mock_whatnot_client):
        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        fake_id = uuid.uuid4()

        with pytest.raises(ProductServiceError):
            svc.delete_product(fake_id)

    def test_get_taxonomy(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.return_value = {
            "productTaxonomyNodes": {
                "edges": [
                    {"node": {"id": "tax_1", "name": "Trading Cards"}}
                ],
                "pageInfo": {"hasNextPage": False},
            }
        }

        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.get_taxonomy()

        assert len(result) >= 1
