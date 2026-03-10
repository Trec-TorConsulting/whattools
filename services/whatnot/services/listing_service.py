"""Listing management service — create/update/publish/unpublish Whatnot listings."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from services.shared.logging import get_logger
from services.whatnot.graphql.client import WhatnotClient, WhatnotApiError, WhatnotUserError
from services.whatnot.graphql.queries import LISTINGS_QUERY, LISTING_QUERY
from services.whatnot.graphql.mutations import (
    LISTING_ADJUST_QUANTITY_MUTATION,
    LISTING_ASSIGN_TO_LIVESTREAM_MUTATION,
    LISTING_DELETE_MUTATION,
    LISTING_PUBLISH_MUTATION,
    LISTING_REMOVE_FROM_LIVESTREAM_MUTATION,
    LISTING_UNPUBLISH_MUTATION,
    LISTING_UPDATE_MUTATION,
)

logger = get_logger("whatnot.listing_service")


class ListingServiceError(Exception):
    """Error during listing operations."""

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class ListingService:
    """Manages Whatnot listings — CRUD, publish/unpublish, livestream assignment."""

    def __init__(self, db: Session, account_id: uuid.UUID, client: WhatnotClient) -> None:
        self.db = db
        self.account_id = account_id
        self.client = client

    def list_listings(
        self,
        *,
        first: int = 50,
        after: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Fetch listings from Whatnot.

        Args:
            first: Number of items per page.
            after: Cursor for pagination.
            status: Optional filter by listing status.

        Returns:
            Dict with listings and pagination info.
        """
        variables: dict[str, Any] = {"first": first}
        if after:
            variables["after"] = after
        if status:
            variables["filter"] = {"status": status}

        try:
            data = self.client.execute(LISTINGS_QUERY, variables)
        except WhatnotApiError as exc:
            raise ListingServiceError(str(exc), "whatnot_error", 502) from exc

        connection = data.get("listings", {})
        edges = connection.get("edges", [])
        page_info = connection.get("pageInfo", {})

        return {
            "listings": [edge.get("node", {}) for edge in edges],
            "page_info": page_info,
        }

    def get_listing(self, listing_id: str) -> dict[str, Any]:
        """Get a single listing by ID.

        Args:
            listing_id: The Whatnot listing ID.

        Returns:
            Listing data dict.
        """
        try:
            data = self.client.execute(LISTING_QUERY, {"id": listing_id})
        except WhatnotApiError as exc:
            raise ListingServiceError(str(exc), "whatnot_error", 502) from exc
        return data.get("listing", {})

    def update_listing(self, listing_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update a listing on Whatnot.

        Args:
            listing_id: The Whatnot listing ID.
            updates: Fields to update.

        Returns:
            Updated listing data.
        """
        input_data = {"id": listing_id, **updates}
        try:
            result = self.client.execute_mutation(
                LISTING_UPDATE_MUTATION,
                {"input": input_data},
                mutation_name="listingUpdate",
            )
        except WhatnotUserError as exc:
            raise ListingServiceError(exc.message, "whatnot_error", 422) from exc
        except WhatnotApiError as exc:
            raise ListingServiceError(str(exc), "whatnot_error", 502) from exc

        return result.get("listing", {})

    def delete_listing(self, listing_id: str) -> dict[str, Any]:
        """Delete a listing on Whatnot.

        Args:
            listing_id: The Whatnot listing ID.

        Returns:
            Dict with deleted listing ID.
        """
        try:
            result = self.client.execute_mutation(
                LISTING_DELETE_MUTATION,
                {"input": {"id": listing_id}},
                mutation_name="listingDelete",
            )
        except WhatnotUserError as exc:
            raise ListingServiceError(exc.message, "whatnot_error", 422) from exc
        except WhatnotApiError as exc:
            raise ListingServiceError(str(exc), "whatnot_error", 502) from exc

        return {"deleted_listing_id": result.get("deletedListingId")}

    def publish(self, listing_id: str) -> dict[str, Any]:
        """Publish a listing on Whatnot.

        Args:
            listing_id: The Whatnot listing ID.

        Returns:
            Updated listing data.
        """
        try:
            result = self.client.execute_mutation(
                LISTING_PUBLISH_MUTATION,
                {"input": {"id": listing_id}},
                mutation_name="listingPublish",
            )
        except WhatnotUserError as exc:
            raise ListingServiceError(exc.message, "whatnot_error", 422) from exc
        except WhatnotApiError as exc:
            raise ListingServiceError(str(exc), "whatnot_error", 502) from exc

        return result.get("listing", {})

    def unpublish(self, listing_id: str) -> dict[str, Any]:
        """Unpublish a listing on Whatnot.

        Args:
            listing_id: The Whatnot listing ID.

        Returns:
            Updated listing data.
        """
        try:
            result = self.client.execute_mutation(
                LISTING_UNPUBLISH_MUTATION,
                {"input": {"id": listing_id}},
                mutation_name="listingUnpublish",
            )
        except WhatnotUserError as exc:
            raise ListingServiceError(exc.message, "whatnot_error", 422) from exc
        except WhatnotApiError as exc:
            raise ListingServiceError(str(exc), "whatnot_error", 502) from exc

        return result.get("listing", {})

    def assign_to_livestream(self, listing_id: str, livestream_id: str) -> dict[str, Any]:
        """Assign a listing to a livestream.

        Args:
            listing_id: The Whatnot listing ID.
            livestream_id: The Whatnot livestream ID.

        Returns:
            Updated listing data.
        """
        try:
            result = self.client.execute_mutation(
                LISTING_ASSIGN_TO_LIVESTREAM_MUTATION,
                {"input": {"id": listing_id, "livestreamId": livestream_id}},
                mutation_name="listingAssignToLivestream",
            )
        except WhatnotUserError as exc:
            raise ListingServiceError(exc.message, "whatnot_error", 422) from exc
        except WhatnotApiError as exc:
            raise ListingServiceError(str(exc), "whatnot_error", 502) from exc

        return result.get("listing", {})

    def remove_from_livestream(self, listing_id: str, livestream_id: str) -> dict[str, Any]:
        """Remove a listing from a livestream.

        Args:
            listing_id: The Whatnot listing ID.
            livestream_id: The Whatnot livestream ID.

        Returns:
            Updated listing data.
        """
        try:
            result = self.client.execute_mutation(
                LISTING_REMOVE_FROM_LIVESTREAM_MUTATION,
                {"input": {"id": listing_id, "livestreamId": livestream_id}},
                mutation_name="listingRemoveFromLivestream",
            )
        except WhatnotUserError as exc:
            raise ListingServiceError(exc.message, "whatnot_error", 422) from exc
        except WhatnotApiError as exc:
            raise ListingServiceError(str(exc), "whatnot_error", 502) from exc

        return result.get("listing", {})

    def adjust_quantity(self, listing_id: str, quantity_delta: int) -> dict[str, Any]:
        """Adjust the quantity of a listing.

        Args:
            listing_id: The Whatnot listing ID.
            quantity_delta: Positive to increase, negative to decrease.

        Returns:
            Updated listing data.
        """
        try:
            result = self.client.execute_mutation(
                LISTING_ADJUST_QUANTITY_MUTATION,
                {"input": {"id": listing_id, "quantityDelta": quantity_delta}},
                mutation_name="listingAdjustQuantity",
            )
        except WhatnotUserError as exc:
            raise ListingServiceError(exc.message, "whatnot_error", 422) from exc
        except WhatnotApiError as exc:
            raise ListingServiceError(str(exc), "whatnot_error", 502) from exc

        return result.get("listing", {})
