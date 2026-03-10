"""Tests for livestream service."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from services.whatnot.services.livestream_service import LivestreamService, LivestreamServiceError


class TestLivestreamService:
    def test_pull_livestreams_empty(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.return_value = {
            "livestreams": {"edges": [], "pageInfo": {"hasNextPage": False}}
        }

        svc = LivestreamService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.pull_livestreams()

        assert result["created"] == 0
        assert result["updated"] == 0

    def test_pull_livestreams_creates_shows(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.return_value = {
            "livestreams": {
                "edges": [
                    {
                        "node": {
                            "id": "ls_1",
                            "title": "Test Livestream",
                            "status": "UPCOMING",
                            "scheduledStartTime": "2026-04-01T19:00:00Z",
                        },
                        "cursor": "cursor_1",
                    }
                ],
                "pageInfo": {"hasNextPage": False},
            }
        }

        svc = LivestreamService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.pull_livestreams()

        assert result["synced"] == 1
