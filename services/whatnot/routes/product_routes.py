"""Product sync routes — pull/push products, taxonomy browsing."""

import uuid

from flask import Blueprint, request
from flask_jwt_extended import get_jwt, jwt_required

from services.shared.database import get_db
from services.shared.errors import error_response, success_response
from services.whatnot.services.oauth_service import OAuthService, OAuthServiceError
from services.whatnot.services.product_service import ProductService, ProductServiceError
from services.whatnot.graphql.client import WhatnotClient

product_bp = Blueprint("whatnot_products", __name__)


def _get_account_id() -> uuid.UUID:
    return uuid.UUID(get_jwt()["account_id"])


def _get_whatnot_client(account_id: uuid.UUID) -> WhatnotClient:
    db = get_db()
    oauth_svc = OAuthService(db)
    access_token = oauth_svc.get_access_token(account_id)
    return WhatnotClient(access_token)


@product_bp.route("/products/pull", methods=["POST"])
@jwt_required()
def pull_products():  # type: ignore[no-untyped-def]
    """Pull products from Whatnot into local inventory."""
    account_id = _get_account_id()
    db = get_db()

    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = ProductService(db, account_id, client)
    try:
        result = svc.pull_products()
    except ProductServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@product_bp.route("/products/push", methods=["POST"])
@jwt_required()
def push_product():  # type: ignore[no-untyped-def]
    """Push a local inventory item to Whatnot as a new product."""
    account_id = _get_account_id()
    data = request.get_json(force=True)
    item_id = data.get("item_id")
    if not item_id:
        return error_response("validation_error", "item_id is required", status_code=422)

    db = get_db()
    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = ProductService(db, account_id, client)
    try:
        result = svc.push_product(uuid.UUID(item_id))
    except ProductServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result, status_code=201)


@product_bp.route("/products/<item_id>/sync", methods=["POST"])
@jwt_required()
def sync_product(item_id: str):  # type: ignore[no-untyped-def]
    """Push updates for a local item to its linked Whatnot product."""
    account_id = _get_account_id()
    db = get_db()

    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = ProductService(db, account_id, client)
    try:
        result = svc.update_product(uuid.UUID(item_id))
    except ProductServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@product_bp.route("/products/<item_id>/unlink", methods=["POST"])
@jwt_required()
def delete_product(item_id: str):  # type: ignore[no-untyped-def]
    """Delete a product from Whatnot and unlink the local item."""
    account_id = _get_account_id()
    db = get_db()

    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = ProductService(db, account_id, client)
    try:
        result = svc.delete_product(uuid.UUID(item_id))
    except ProductServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@product_bp.route("/taxonomy", methods=["GET"])
@jwt_required()
def get_taxonomy():  # type: ignore[no-untyped-def]
    """Browse the Whatnot product taxonomy tree."""
    account_id = _get_account_id()
    parent_id = request.args.get("parent_id")
    db = get_db()

    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = ProductService(db, account_id, client)
    nodes = svc.get_taxonomy(parent_id=parent_id)
    return success_response(nodes)


@product_bp.route("/taxonomy/<node_id>", methods=["GET"])
@jwt_required()
def get_taxonomy_node(node_id: str):  # type: ignore[no-untyped-def]
    """Get a specific taxonomy node."""
    account_id = _get_account_id()
    db = get_db()

    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = ProductService(db, account_id, client)
    node = svc.get_taxonomy_node(node_id)
    return success_response(node)


@product_bp.route("/taxonomy/<node_id>/attributes", methods=["GET"])
@jwt_required()
def get_taxonomy_attributes(node_id: str):  # type: ignore[no-untyped-def]
    """Get product attributes for a taxonomy category."""
    account_id = _get_account_id()
    db = get_db()

    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = ProductService(db, account_id, client)
    attributes = svc.get_taxonomy_attributes(node_id)
    return success_response(attributes)
