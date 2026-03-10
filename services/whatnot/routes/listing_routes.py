"""Listing management routes — CRUD, publish, unpublish, livestream assignment."""

import uuid

from flask import Blueprint, request
from flask_jwt_extended import get_jwt, jwt_required

from services.shared.database import get_db
from services.shared.errors import error_response, success_response
from services.whatnot.graphql.client import WhatnotClient
from services.whatnot.services.listing_service import ListingService, ListingServiceError
from services.whatnot.services.oauth_service import OAuthService, OAuthServiceError

listing_bp = Blueprint("whatnot_listings", __name__)


def _get_account_id() -> uuid.UUID:
    return uuid.UUID(get_jwt()["account_id"])


def _get_whatnot_client(account_id: uuid.UUID) -> WhatnotClient:
    db = get_db()
    oauth_svc = OAuthService(db)
    access_token = oauth_svc.get_access_token(account_id)
    return WhatnotClient(access_token)


@listing_bp.route("", methods=["GET"])
@jwt_required()
def list_listings():  # type: ignore[no-untyped-def]
    """List Whatnot listings with optional filtering."""
    account_id = _get_account_id()
    first = request.args.get("limit", 50, type=int)
    after = request.args.get("cursor")
    status = request.args.get("status")
    db = get_db()

    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = ListingService(db, account_id, client)
    try:
        result = svc.list_listings(first=first, after=after, status=status)
    except ListingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@listing_bp.route("/<listing_id>", methods=["GET"])
@jwt_required()
def get_listing(listing_id: str):  # type: ignore[no-untyped-def]
    """Get a single Whatnot listing."""
    account_id = _get_account_id()
    db = get_db()

    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = ListingService(db, account_id, client)
    try:
        result = svc.get_listing(listing_id)
    except ListingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@listing_bp.route("/<listing_id>", methods=["PUT"])
@jwt_required()
def update_listing(listing_id: str):  # type: ignore[no-untyped-def]
    """Update a Whatnot listing."""
    account_id = _get_account_id()
    data = request.get_json(force=True)
    db = get_db()

    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = ListingService(db, account_id, client)
    try:
        result = svc.update_listing(listing_id, data)
    except ListingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@listing_bp.route("/<listing_id>", methods=["DELETE"])
@jwt_required()
def delete_listing(listing_id: str):  # type: ignore[no-untyped-def]
    """Delete a Whatnot listing."""
    account_id = _get_account_id()
    db = get_db()

    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = ListingService(db, account_id, client)
    try:
        result = svc.delete_listing(listing_id)
    except ListingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@listing_bp.route("/<listing_id>/publish", methods=["POST"])
@jwt_required()
def publish_listing(listing_id: str):  # type: ignore[no-untyped-def]
    """Publish a listing on Whatnot."""
    account_id = _get_account_id()
    db = get_db()

    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = ListingService(db, account_id, client)
    try:
        result = svc.publish(listing_id)
    except ListingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@listing_bp.route("/<listing_id>/unpublish", methods=["POST"])
@jwt_required()
def unpublish_listing(listing_id: str):  # type: ignore[no-untyped-def]
    """Unpublish a listing on Whatnot."""
    account_id = _get_account_id()
    db = get_db()

    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = ListingService(db, account_id, client)
    try:
        result = svc.unpublish(listing_id)
    except ListingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@listing_bp.route("/<listing_id>/assign-livestream", methods=["POST"])
@jwt_required()
def assign_to_livestream(listing_id: str):  # type: ignore[no-untyped-def]
    """Assign a listing to a livestream."""
    account_id = _get_account_id()
    data = request.get_json(force=True)
    livestream_id = data.get("livestream_id")
    if not livestream_id:
        return error_response("validation_error", "livestream_id is required", status_code=422)

    db = get_db()
    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = ListingService(db, account_id, client)
    try:
        result = svc.assign_to_livestream(listing_id, livestream_id)
    except ListingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@listing_bp.route("/<listing_id>/remove-livestream", methods=["POST"])
@jwt_required()
def remove_from_livestream(listing_id: str):  # type: ignore[no-untyped-def]
    """Remove a listing from a livestream."""
    account_id = _get_account_id()
    data = request.get_json(force=True)
    livestream_id = data.get("livestream_id")
    if not livestream_id:
        return error_response("validation_error", "livestream_id is required", status_code=422)

    db = get_db()
    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = ListingService(db, account_id, client)
    try:
        result = svc.remove_from_livestream(listing_id, livestream_id)
    except ListingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@listing_bp.route("/<listing_id>/adjust-quantity", methods=["POST"])
@jwt_required()
def adjust_quantity(listing_id: str):  # type: ignore[no-untyped-def]
    """Adjust the quantity of a listing."""
    account_id = _get_account_id()
    data = request.get_json(force=True)
    quantity_delta = data.get("quantity_delta")
    if quantity_delta is None:
        return error_response("validation_error", "quantity_delta is required", status_code=422)

    db = get_db()
    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = ListingService(db, account_id, client)
    try:
        result = svc.adjust_quantity(listing_id, int(quantity_delta))
    except ListingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)
