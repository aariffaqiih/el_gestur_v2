from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request

from snippet_commands import SnippetCommandService


def create_snippet_blueprint(snippet_commands: SnippetCommandService) -> Blueprint:
    """Create HTTP routes for local quick templates."""
    blueprint = Blueprint("snippets", __name__, url_prefix="/snippets")

    @blueprint.before_request
    def restrict_snippet_access_to_local_dashboard():
        if not _is_loopback_host(request.remote_addr):
            return jsonify({
                "status": "error",
                "message": "Template cepat hanya tersedia dari laptop lokal.",
            }), 403

        origin = request.headers.get("Origin")
        if origin and not _is_trusted_local_origin(origin):
            return jsonify({
                "status": "error",
                "message": "Origin dashboard tidak diizinkan mengakses template lokal.",
            }), 403
        return None

    @blueprint.get("")
    def list_snippets():
        payload = snippet_commands.list(query=request.args.get("query"))
        status_code = 200 if payload.get("status") == "success" else 500
        return jsonify(payload), status_code

    @blueprint.post("")
    def create_snippet():
        payload = snippet_commands.create(request.get_json(silent=True) or {})
        status_code = 201 if payload.get("status") == "success" else 400
        return jsonify(payload), status_code

    @blueprint.put("/<snippet_id>")
    def update_snippet(snippet_id: str):
        payload = snippet_commands.update(snippet_id, request.get_json(silent=True) or {})
        if payload.get("status") == "success":
            return jsonify(payload)
        status_code = 404 if "tidak ditemukan" in payload.get("message", "").casefold() else 400
        return jsonify(payload), status_code

    @blueprint.delete("/<snippet_id>")
    def delete_snippet(snippet_id: str):
        payload = snippet_commands.delete(snippet_id)
        if payload.get("status") == "success":
            return jsonify(payload)
        status_code = 404 if "tidak ditemukan" in payload.get("message", "").casefold() else 400
        return jsonify(payload), status_code

    @blueprint.post("/insert")
    def insert_snippet():
        data = request.get_json(silent=True) or {}
        payload = snippet_commands.insert(
            snippet_id=data.get("snippet_id"),
            query=data.get("query"),
        )
        if payload.get("status") == "success":
            return jsonify(payload)
        status_code = 400
        if "tidak ditemukan" in payload.get("message", "").casefold():
            status_code = 404
        return jsonify(payload), status_code

    return blueprint


def _is_trusted_local_origin(origin: str) -> bool:
    if origin == "null":
        return True
    return _is_loopback_host(urlparse(origin).hostname)


def _is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    if host.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False
