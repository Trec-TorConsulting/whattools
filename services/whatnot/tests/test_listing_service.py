"""Tests for listing service."""

from unittest.mock import MagicMock

import pytest

from services.whatnot.graphql.client import WhatnotApiError, WhatnotUserError
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

    def test_list_listings_with_filters(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.return_value = {
            "listings": {"edges": [], "pageInfo": {"hasNextPage": False}}
        }
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.list_listings(after="cursor_1", status="PUBLISHED")
        assert result["listings"] == []
        # Verify variables were passed correctly
        call_vars = mock_whatnot_client.execute.call_args[0][1]
        assert call_vars["after"] == "cursor_1"
        assert call_vars["filter"]["status"] == "PUBLISHED"

    def test_list_listings_api_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.side_effect = WhatnotApiError("API down")
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ListingServiceError) as exc_info:
            svc.list_listings()
        assert exc_info.value.status_code == 502

    def test_get_listing(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.return_value = {
            "listing": {"id": "lst_1", "title": "Test"}
        }
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.get_listing("lst_1")
        assert result["id"] == "lst_1"

    def test_get_listing_api_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.side_effect = WhatnotApiError("timeout")
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ListingServiceError) as exc_info:
            svc.get_listing("lst_1")
        assert exc_info.value.status_code == 502

    def test_update_listing(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.return_value = {
            "listing": {"id": "lst_1", "title": "Updated"},
        }
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.update_listing("lst_1", {"title": "Updated"})
        mock_whatnot_client.execute_mutation.assert_called_once()

    def test_update_listing_user_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.side_effect = WhatnotUserError("Invalid title")
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ListingServiceError) as exc_info:
            svc.update_listing("lst_1", {"title": ""})
        assert exc_info.value.status_code == 422

    def test_update_listing_api_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.side_effect = WhatnotApiError("server error")
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ListingServiceError) as exc_info:
            svc.update_listing("lst_1", {"title": "X"})
        assert exc_info.value.status_code == 502

    def test_publish_listing(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.return_value = {
            "listing": {"id": "lst_1", "status": "PUBLISHED"},
        }
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        svc.publish("lst_1")
        mock_whatnot_client.execute_mutation.assert_called_once()

    def test_publish_user_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.side_effect = WhatnotUserError("Cannot publish")
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ListingServiceError) as exc_info:
            svc.publish("lst_1")
        assert exc_info.value.status_code == 422

    def test_publish_api_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.side_effect = WhatnotApiError("down")
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ListingServiceError) as exc_info:
            svc.publish("lst_1")
        assert exc_info.value.status_code == 502

    def test_unpublish_listing(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.return_value = {
            "listing": {"id": "lst_1", "status": "DRAFT"},
        }
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        svc.unpublish("lst_1")
        mock_whatnot_client.execute_mutation.assert_called_once()

    def test_unpublish_user_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.side_effect = WhatnotUserError("Already draft")
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ListingServiceError) as exc_info:
            svc.unpublish("lst_1")
        assert exc_info.value.status_code == 422

    def test_unpublish_api_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.side_effect = WhatnotApiError("fail")
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ListingServiceError) as exc_info:
            svc.unpublish("lst_1")
        assert exc_info.value.status_code == 502

    def test_delete_listing(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.return_value = {
            "deletedListingId": "lst_1",
        }
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.delete_listing("lst_1")
        assert result["deleted_listing_id"] == "lst_1"
        mock_whatnot_client.execute_mutation.assert_called_once()

    def test_delete_user_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.side_effect = WhatnotUserError("Cannot delete")
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ListingServiceError) as exc_info:
            svc.delete_listing("lst_1")
        assert exc_info.value.status_code == 422

    def test_delete_api_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.side_effect = WhatnotApiError("timeout")
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ListingServiceError) as exc_info:
            svc.delete_listing("lst_1")
        assert exc_info.value.status_code == 502

    def test_assign_to_livestream(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.return_value = {
            "listing": {"id": "lst_1", "livestreamId": "live_1"}
        }
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.assign_to_livestream("lst_1", "live_1")
        assert result["id"] == "lst_1"

    def test_assign_to_livestream_user_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.side_effect = WhatnotUserError("Invalid livestream")
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ListingServiceError) as exc_info:
            svc.assign_to_livestream("lst_1", "bad_live")
        assert exc_info.value.status_code == 422

    def test_assign_to_livestream_api_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.side_effect = WhatnotApiError("fail")
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ListingServiceError) as exc_info:
            svc.assign_to_livestream("lst_1", "live_1")
        assert exc_info.value.status_code == 502

    def test_remove_from_livestream(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.return_value = {
            "listing": {"id": "lst_1"}
        }
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.remove_from_livestream("lst_1", "live_1")
        assert result["id"] == "lst_1"

    def test_remove_from_livestream_user_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.side_effect = WhatnotUserError("Not assigned")
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ListingServiceError) as exc_info:
            svc.remove_from_livestream("lst_1", "live_1")
        assert exc_info.value.status_code == 422

    def test_remove_from_livestream_api_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.side_effect = WhatnotApiError("fail")
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ListingServiceError) as exc_info:
            svc.remove_from_livestream("lst_1", "live_1")
        assert exc_info.value.status_code == 502

    def test_adjust_quantity(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.return_value = {
            "listing": {"id": "lst_1", "quantity": 10}
        }
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.adjust_quantity("lst_1", 5)
        assert result["quantity"] == 10

    def test_adjust_quantity_user_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.side_effect = WhatnotUserError("Below minimum")
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ListingServiceError) as exc_info:
            svc.adjust_quantity("lst_1", -999)
        assert exc_info.value.status_code == 422

    def test_adjust_quantity_api_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute_mutation.side_effect = WhatnotApiError("fail")
        svc = ListingService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(ListingServiceError) as exc_info:
            svc.adjust_quantity("lst_1", 1)
        assert exc_info.value.status_code == 502
