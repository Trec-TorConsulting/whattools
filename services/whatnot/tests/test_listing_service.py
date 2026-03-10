"""Tests for listing service."""

from unittest.mock import MagicMock

import pytest

from services.whatnot.services.listing_service import ListingService, ListingServiceError


class TestListingService:
    def test_list_listings(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.return_value = {
            "listings": {
                "edges": [
                    {"node": {"id": "lst_1", "title": "Test Listing", "status": "PUBLISHED"}},
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.list_listings()

        assert "listings" in result
        assert len(result["listings"]) == 1

    def test_get_listing(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.return_value = {
            "listing": {"id": "lst_1", "title": "Test"}
        }

        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.get_listing("lst_1")

        assert result["id"] == "lst_1"

    def test_update_listing(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.return_value = {
            "listing": {"id": "lst_1", "title": "Updated"},
        }

        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.update_listing("lst_1", {"title": "Updated"})

        mock_whatnot_client.execute_mutation.assert_called_once()

    def test_publish_listing(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.return_value = {
            "listing": {"id": "lst_1", "status": "PUBLISHED"},
        }

        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        svc.publish("lst_1")

        mock_whatnot_client.execute_mutation.assert_called_once()

    def test_unpublish_listing(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.return_value = {
            "listing": {"id": "lst_1", "status": "DRAFT"},
        }

        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        svc.unpublish("lst_1")

        mock_whatnot_client.execute_mutation.assert_called_once()

    def test_delete_listing(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.return_value = {
            "deletedListingId": "lst_1",
        }

        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        svc.delete_listing("lst_1")

        mock_whatnot_client.execute_mutation.assert_called_once()
