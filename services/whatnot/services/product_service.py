"""Product sync service — pull/push products between Whatnot and WhatTools."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.inventory.models.models import InventoryItem, ItemStatus
from services.shared.logging import get_logger
from services.whatnot.graphql.client import WhatnotClient, WhatnotApiError, WhatnotUserError
from services.whatnot.graphql.queries import PRODUCTS_QUERY, PRODUCT_QUERY, TAXONOMY_NODES_QUERY, TAXONOMY_NODE_QUERY, PRODUCT_ATTRIBUTES_QUERY
from services.whatnot.graphql.mutations import PRODUCT_CREATE_MUTATION, PRODUCT_UPDATE_MUTATION, PRODUCT_DELETE_MUTATION
from services.whatnot.repositories.whatnot_repository import SyncLogRepository
from services.whatnot.models import SyncType

logger = get_logger("whatnot.product_service")


class ProductServiceError(Exception):
    """Error during product sync operations."""

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class ProductService:
    """Syncs products between Whatnot Seller API and WhatTools inventory."""

    def __init__(self, db: Session, account_id: uuid.UUID, client: WhatnotClient) -> None:
        self.db = db
        self.account_id = account_id
        self.client = client
        self.sync_log_repo = SyncLogRepository(db, account_id)

    def pull_products(self) -> dict[str, Any]:
        """Pull all products from Whatnot and upsert into local inventory.

        Returns:
            Dict with sync stats (created, updated, failed, synced).
        """
        sync_log = self.sync_log_repo.create(SyncType.PRODUCTS)
        sync_log.status = "running"
        self.db.flush()

        created = 0
        updated = 0
        failed = 0
        cursor = None

        try:
            while True:
                variables: dict[str, Any] = {"first": 50}
                if cursor:
                    variables["after"] = cursor

                data = self.client.execute(PRODUCTS_QUERY, variables)
                products_conn = data.get("products", {})
                edges = products_conn.get("edges", [])

                for edge in edges:
                    node = edge.get("node", {})
                    try:
                        was_created = self._upsert_product(node)
                        if was_created:
                            created += 1
                        else:
                            updated += 1
                    except Exception as exc:
                        logger.warning("product_pull_item_error", whatnot_id=node.get("id"), error=str(exc))
                        failed += 1

                page_info = products_conn.get("pageInfo", {})
                if not page_info.get("hasNextPage"):
                    break
                cursor = page_info.get("endCursor")

            self.db.commit()
            self.sync_log_repo.complete(
                sync_log,
                items_synced=created + updated,
                items_created=created,
                items_updated=updated,
                items_failed=failed,
            )
            self.db.commit()

        except (WhatnotApiError, WhatnotUserError) as exc:
            self.db.rollback()
            self.sync_log_repo.fail(sync_log, str(exc))
            self.db.commit()
            raise ProductServiceError(str(exc), "sync_error", 502) from exc

        return {
            "synced": created + updated,
            "created": created,
            "updated": updated,
            "failed": failed,
        }

    def _upsert_product(self, whatnot_product: dict[str, Any]) -> bool:
        """Create or update a local inventory item from Whatnot product data.

        Returns:
            True if created, False if updated.
        """
        whatnot_id = whatnot_product["id"]
        title = whatnot_product.get("title", "")
        description = whatnot_product.get("description", "")
        external_id = whatnot_product.get("externalId")

        # Extract first variant info for quantity and images
        variants = _extract_edges(whatnot_product.get("variants", {}))
        total_quantity = 0
        image_urls: list[str] = []
        first_variant_id = None
        first_listing_id = None

        for v in variants:
            inv_level = v.get("inventoryLevel", {})
            total_quantity += inv_level.get("available", 0) if inv_level else 0
            if not first_variant_id:
                first_variant_id = v.get("id")
            # Get variant listings
            listings = _extract_edges(v.get("listings", {}))
            for listing in listings:
                if not first_listing_id:
                    first_listing_id = listing.get("id")

        # Get product-level media
        media = _extract_edges(whatnot_product.get("media", {}))
        for m in media:
            url = m.get("url")
            if url:
                image_urls.append(url)

        # Check if item already exists by whatnot_product_id
        query = (
            select(InventoryItem)
            .where(InventoryItem.account_id == self.account_id)
            .where(InventoryItem.whatnot_product_id == whatnot_id)
            .where(InventoryItem.deleted_at.is_(None))
        )
        existing = self.db.execute(query).scalar_one_or_none()

        if existing:
            existing.name = title
            existing.description = description
            existing.quantity = total_quantity
            existing.whatnot_variant_id = first_variant_id
            existing.whatnot_listing_id = first_listing_id
            existing.image_urls = image_urls
            existing.updated_at = datetime.now(timezone.utc)
            self.db.flush()
            return False
        else:
            item = InventoryItem(
                account_id=self.account_id,
                name=title,
                description=description,
                quantity=total_quantity,
                status=ItemStatus.AVAILABLE,
                cogs=0.0,
            )
            # Set Whatnot link fields
            item.whatnot_product_id = whatnot_id
            item.whatnot_variant_id = first_variant_id
            item.whatnot_listing_id = first_listing_id
            item.image_urls = image_urls
            self.db.add(item)
            self.db.flush()
            return True

    def push_product(self, item_id: uuid.UUID) -> dict[str, Any]:
        """Push a local inventory item to Whatnot as a new product.

        Args:
            item_id: The local inventory item ID.

        Returns:
            Dict with the created Whatnot product info.
        """
        query = (
            select(InventoryItem)
            .where(InventoryItem.id == item_id)
            .where(InventoryItem.account_id == self.account_id)
            .where(InventoryItem.deleted_at.is_(None))
        )
        item = self.db.execute(query).scalar_one_or_none()
        if not item:
            raise ProductServiceError("Item not found", "not_found", 404)

        if item.whatnot_product_id:
            raise ProductServiceError(
                "Item already linked to Whatnot product", "already_linked", 409
            )

        variables: dict[str, Any] = {
            "input": {
                "title": item.name,
                "description": item.description or "",
            }
        }

        try:
            result = self.client.execute_mutation(
                PRODUCT_CREATE_MUTATION,
                variables,
                mutation_name="productCreate",
            )
        except WhatnotUserError as exc:
            raise ProductServiceError(exc.message, "whatnot_error", 422) from exc
        except WhatnotApiError as exc:
            raise ProductServiceError(str(exc), "whatnot_error", 502) from exc

        product = result.get("product", {})
        item.whatnot_product_id = product.get("id")

        # Get variant ID if created
        variants = _extract_edges(product.get("variants", {}))
        if variants:
            item.whatnot_variant_id = variants[0].get("id")

        item.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return {
            "whatnot_product_id": product.get("id"),
            "title": product.get("title"),
            "item_id": str(item.id),
        }

    def update_product(self, item_id: uuid.UUID) -> dict[str, Any]:
        """Push updates from a local item to its linked Whatnot product.

        Args:
            item_id: The local inventory item ID.

        Returns:
            Dict with the updated Whatnot product info.
        """
        query = (
            select(InventoryItem)
            .where(InventoryItem.id == item_id)
            .where(InventoryItem.account_id == self.account_id)
            .where(InventoryItem.deleted_at.is_(None))
        )
        item = self.db.execute(query).scalar_one_or_none()
        if not item:
            raise ProductServiceError("Item not found", "not_found", 404)

        if not item.whatnot_product_id:
            raise ProductServiceError(
                "Item not linked to Whatnot", "not_linked", 400
            )

        variables: dict[str, Any] = {
            "input": {
                "id": item.whatnot_product_id,
                "title": item.name,
                "description": item.description or "",
            }
        }

        try:
            result = self.client.execute_mutation(
                PRODUCT_UPDATE_MUTATION,
                variables,
                mutation_name="productUpdate",
            )
        except WhatnotUserError as exc:
            raise ProductServiceError(exc.message, "whatnot_error", 422) from exc
        except WhatnotApiError as exc:
            raise ProductServiceError(str(exc), "whatnot_error", 502) from exc

        product = result.get("product", {})
        item.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return {
            "whatnot_product_id": product.get("id"),
            "title": product.get("title"),
        }

    def delete_product(self, item_id: uuid.UUID) -> dict[str, Any]:
        """Delete a product from Whatnot and unlink the local item.

        Args:
            item_id: The local inventory item ID.

        Returns:
            Dict with the deleted product ID.
        """
        query = (
            select(InventoryItem)
            .where(InventoryItem.id == item_id)
            .where(InventoryItem.account_id == self.account_id)
            .where(InventoryItem.deleted_at.is_(None))
        )
        item = self.db.execute(query).scalar_one_or_none()
        if not item:
            raise ProductServiceError("Item not found", "not_found", 404)

        if not item.whatnot_product_id:
            raise ProductServiceError(
                "Item not linked to Whatnot", "not_linked", 400
            )

        try:
            self.client.execute_mutation(
                PRODUCT_DELETE_MUTATION,
                {"input": {"id": item.whatnot_product_id}},
                mutation_name="productDelete",
            )
        except WhatnotUserError as exc:
            raise ProductServiceError(exc.message, "whatnot_error", 422) from exc
        except WhatnotApiError as exc:
            raise ProductServiceError(str(exc), "whatnot_error", 502) from exc

        item.whatnot_product_id = None
        item.whatnot_variant_id = None
        item.whatnot_listing_id = None
        item.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return {"deleted": True, "item_id": str(item.id)}

    def get_taxonomy(self, *, parent_id: str | None = None) -> list[dict[str, Any]]:
        """Browse the Whatnot product taxonomy tree.

        Args:
            parent_id: Optional parent node ID to filter children.

        Returns:
            List of taxonomy node dicts.
        """
        variables: dict[str, Any] = {"first": 100}
        if parent_id:
            variables["filter"] = {"parentId": parent_id}

        data = self.client.execute(TAXONOMY_NODES_QUERY, variables)
        nodes = _extract_edges(data.get("productTaxonomyNodes", {}))
        return nodes

    def get_taxonomy_node(self, node_id: str) -> dict[str, Any]:
        """Get a specific taxonomy node by ID.

        Args:
            node_id: The Whatnot taxonomy node ID.

        Returns:
            Taxonomy node dict.
        """
        data = self.client.execute(TAXONOMY_NODE_QUERY, {"id": node_id})
        return data.get("productTaxonomyNode", {})

    def get_taxonomy_attributes(self, node_id: str) -> list[dict[str, Any]]:
        """Get product attributes for a taxonomy node.

        Args:
            node_id: The Whatnot taxonomy node ID.

        Returns:
            List of attribute dicts.
        """
        variables: dict[str, Any] = {
            "first": 100,
            "filter": {"productTaxonomyNodeId": node_id},
        }
        data = self.client.execute(PRODUCT_ATTRIBUTES_QUERY, variables)
        return _extract_edges(data.get("productAttributes", {}))


def _extract_edges(connection: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract node data from a GraphQL connection/edges structure."""
    edges = connection.get("edges", [])
    return [edge.get("node", {}) for edge in edges]
