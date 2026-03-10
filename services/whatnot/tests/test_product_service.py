"""Tests for product service."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from services.inventory.models.models import InventoryItem, ItemStatus
from services.whatnot.graphql.client import WhatnotApiError, WhatnotUserError
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
        assert result["created"] >= 0

    def test_pull_products_pagination(self, db_session, sample_account, mock_whatnot_client):
        page1 = {
            "products": {
                "edges": [{"node": {"id": "p1", "title": "P1", "description": "", "variants": {"edges": [{"node": {"id": "v1", "price": {"amount": 100}, "quantity": 1}}]}, "media": {"edges": []}}}],
                "pageInfo": {"hasNextPage": True, "endCursor": "c1"},
            }
        }
        page2 = {
            "products": {
                "edges": [{"node": {"id": "p2", "title": "P2", "description": "", "variants": {"edges": [{"node": {"id": "v2", "price": {"amount": 200}, "quantity": 2}}]}, "media": {"edges": []}}}],
                "pageInfo": {"hasNextPage": False},
            }
        }
        mock_whatnot_client.execute.side_effect = [page1, page2]

        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.pull_products()

        assert result["synced"] == 2
        assert mock_whatnot_client.execute.call_count == 2

    def test_pull_products_api_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.side_effect = WhatnotApiError("API failure")

        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ProductServiceError) as exc_info:
            svc.pull_products()
        assert exc_info.value.status_code == 502

    def test_pull_products_item_failure_continues(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.return_value = {
            "products": {
                "edges": [
                    {"node": {"id": "p_ok", "title": "OK", "description": "", "variants": {"edges": [{"node": {"id": "v1", "price": {"amount": 100}, "quantity": 1}}]}, "media": {"edges": []}}},
                    {"node": {}},  # Missing required fields — will fail
                ],
                "pageInfo": {"hasNextPage": False},
            }
        }

        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.pull_products()

        assert result["synced"] >= 1
        assert result["failed"] >= 1

    def test_pull_products_updates_existing(self, db_session, sample_account, mock_whatnot_client):
        inv = InventoryItem(
            account_id=sample_account.id, name="Old Name", status=ItemStatus.AVAILABLE,
            cogs=5.0, quantity=1,
        )
        inv.whatnot_product_id = "prod_exist"
        db_session.add(inv)
        db_session.flush()

        mock_whatnot_client.execute.return_value = {
            "products": {
                "edges": [{
                    "node": {
                        "id": "prod_exist",
                        "title": "New Name",
                        "description": "desc",
                        "variants": {"edges": [{"node": {"id": "v1", "price": {"amount": 2000}, "quantity": 3}}]},
                        "media": {"edges": [{"node": {"url": "https://example.com/img.jpg"}}]},
                    },
                }],
                "pageInfo": {"hasNextPage": False},
            }
        }

        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.pull_products()

        assert result["updated"] >= 1
        db_session.refresh(inv)
        assert inv.name == "New Name"

    def test_push_product_not_found(self, db_session, sample_account, mock_whatnot_client):
        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        fake_id = uuid.uuid4()

        with pytest.raises(ProductServiceError):
            svc.push_product(fake_id)

    def test_push_product_already_linked(self, db_session, sample_account, mock_whatnot_client):
        inv = InventoryItem(
            account_id=sample_account.id, name="Item", status=ItemStatus.AVAILABLE,
            cogs=5.0, quantity=1,
        )
        inv.whatnot_product_id = "already_linked"
        db_session.add(inv)
        db_session.flush()

        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ProductServiceError, match="already linked"):
            svc.push_product(inv.id)

    def test_push_product_success(self, db_session, sample_account, mock_whatnot_client):
        inv = InventoryItem(
            account_id=sample_account.id, name="Push Me", description="desc",
            status=ItemStatus.AVAILABLE, cogs=5.0, quantity=1,
        )
        db_session.add(inv)
        db_session.flush()

        mock_whatnot_client.execute_mutation.return_value = {
            "product": {
                "id": "wn_push_1",
                "title": "Push Me",
                "variants": {"edges": [{"node": {"id": "wn_var_1"}}]},
            }
        }

        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.push_product(inv.id)

        assert result["whatnot_product_id"] == "wn_push_1"
        db_session.refresh(inv)
        assert inv.whatnot_product_id == "wn_push_1"
        assert inv.whatnot_variant_id == "wn_var_1"

    def test_push_product_user_error(self, db_session, sample_account, mock_whatnot_client):
        inv = InventoryItem(
            account_id=sample_account.id, name="Item", status=ItemStatus.AVAILABLE,
            cogs=5.0, quantity=1,
        )
        db_session.add(inv)
        db_session.flush()

        mock_whatnot_client.execute_mutation.side_effect = WhatnotUserError("Bad input")
        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ProductServiceError) as exc_info:
            svc.push_product(inv.id)
        assert exc_info.value.status_code == 422

    def test_push_product_api_error(self, db_session, sample_account, mock_whatnot_client):
        inv = InventoryItem(
            account_id=sample_account.id, name="Item", status=ItemStatus.AVAILABLE,
            cogs=5.0, quantity=1,
        )
        db_session.add(inv)
        db_session.flush()

        mock_whatnot_client.execute_mutation.side_effect = WhatnotApiError("down")
        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ProductServiceError) as exc_info:
            svc.push_product(inv.id)
        assert exc_info.value.status_code == 502

    def test_update_product_not_found(self, db_session, sample_account, mock_whatnot_client):
        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ProductServiceError):
            svc.update_product(uuid.uuid4())

    def test_update_product_not_linked(self, db_session, sample_account, mock_whatnot_client):
        inv = InventoryItem(
            account_id=sample_account.id, name="Item", status=ItemStatus.AVAILABLE,
            cogs=5.0, quantity=1,
        )
        db_session.add(inv)
        db_session.flush()

        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ProductServiceError, match="not linked"):
            svc.update_product(inv.id)

    def test_update_product_success(self, db_session, sample_account, mock_whatnot_client):
        inv = InventoryItem(
            account_id=sample_account.id, name="Updated Name", description="desc",
            status=ItemStatus.AVAILABLE, cogs=5.0, quantity=1,
        )
        inv.whatnot_product_id = "wn_up_1"
        db_session.add(inv)
        db_session.flush()

        mock_whatnot_client.execute_mutation.return_value = {
            "product": {"id": "wn_up_1", "title": "Updated Name"}
        }

        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.update_product(inv.id)
        assert result["whatnot_product_id"] == "wn_up_1"

    def test_update_product_user_error(self, db_session, sample_account, mock_whatnot_client):
        inv = InventoryItem(
            account_id=sample_account.id, name="Item", status=ItemStatus.AVAILABLE,
            cogs=5.0, quantity=1,
        )
        inv.whatnot_product_id = "wn_u"
        db_session.add(inv)
        db_session.flush()

        mock_whatnot_client.execute_mutation.side_effect = WhatnotUserError("Bad")
        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ProductServiceError) as exc_info:
            svc.update_product(inv.id)
        assert exc_info.value.status_code == 422

    def test_update_product_api_error(self, db_session, sample_account, mock_whatnot_client):
        inv = InventoryItem(
            account_id=sample_account.id, name="Item", status=ItemStatus.AVAILABLE,
            cogs=5.0, quantity=1,
        )
        inv.whatnot_product_id = "wn_u"
        db_session.add(inv)
        db_session.flush()

        mock_whatnot_client.execute_mutation.side_effect = WhatnotApiError("fail")
        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ProductServiceError) as exc_info:
            svc.update_product(inv.id)
        assert exc_info.value.status_code == 502

    def test_delete_product_not_found(self, db_session, sample_account, mock_whatnot_client):
        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        fake_id = uuid.uuid4()

        with pytest.raises(ProductServiceError):
            svc.delete_product(fake_id)

    def test_delete_product_not_linked(self, db_session, sample_account, mock_whatnot_client):
        inv = InventoryItem(
            account_id=sample_account.id, name="Item", status=ItemStatus.AVAILABLE,
            cogs=5.0, quantity=1,
        )
        db_session.add(inv)
        db_session.flush()

        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ProductServiceError, match="not linked"):
            svc.delete_product(inv.id)

    def test_delete_product_success(self, db_session, sample_account, mock_whatnot_client):
        inv = InventoryItem(
            account_id=sample_account.id, name="Item", status=ItemStatus.AVAILABLE,
            cogs=5.0, quantity=1,
        )
        inv.whatnot_product_id = "wn_del"
        inv.whatnot_variant_id = "wn_var_del"
        inv.whatnot_listing_id = "wn_lst_del"
        db_session.add(inv)
        db_session.flush()

        mock_whatnot_client.execute_mutation.return_value = {"deletedProductId": "wn_del"}

        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.delete_product(inv.id)

        assert result["deleted"] is True
        db_session.refresh(inv)
        assert inv.whatnot_product_id is None
        assert inv.whatnot_variant_id is None
        assert inv.whatnot_listing_id is None

    def test_delete_product_user_error(self, db_session, sample_account, mock_whatnot_client):
        inv = InventoryItem(
            account_id=sample_account.id, name="Item", status=ItemStatus.AVAILABLE,
            cogs=5.0, quantity=1,
        )
        inv.whatnot_product_id = "wn_d"
        db_session.add(inv)
        db_session.flush()

        mock_whatnot_client.execute_mutation.side_effect = WhatnotUserError("Cannot delete")
        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ProductServiceError) as exc_info:
            svc.delete_product(inv.id)
        assert exc_info.value.status_code == 422

    def test_delete_product_api_error(self, db_session, sample_account, mock_whatnot_client):
        inv = InventoryItem(
            account_id=sample_account.id, name="Item", status=ItemStatus.AVAILABLE,
            cogs=5.0, quantity=1,
        )
        inv.whatnot_product_id = "wn_d"
        db_session.add(inv)
        db_session.flush()

        mock_whatnot_client.execute_mutation.side_effect = WhatnotApiError("fail")
        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ProductServiceError) as exc_info:
            svc.delete_product(inv.id)
        assert exc_info.value.status_code == 502

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

    def test_get_taxonomy_with_parent(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.return_value = {
            "productTaxonomyNodes": {
                "edges": [{"node": {"id": "tax_child", "name": "Pokemon"}}],
            }
        }

        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.get_taxonomy(parent_id="tax_1")

        assert len(result) == 1
        call_vars = mock_whatnot_client.execute.call_args[0][1]
        assert call_vars["filter"]["parentId"] == "tax_1"

    def test_get_taxonomy_node(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.return_value = {
            "productTaxonomyNode": {"id": "tax_1", "name": "Cards"}
        }

        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.get_taxonomy_node("tax_1")

        assert result["id"] == "tax_1"
        assert result["name"] == "Cards"

    def test_get_taxonomy_attributes(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.return_value = {
            "productAttributes": {
                "edges": [
                    {"node": {"id": "attr_1", "name": "Condition"}},
                    {"node": {"id": "attr_2", "name": "Grade"}},
                ],
            }
        }

        svc = ProductService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.get_taxonomy_attributes("tax_1")

        assert len(result) == 2
        assert result[0]["name"] == "Condition"
