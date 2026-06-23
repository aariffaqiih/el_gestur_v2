from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request

from .document_commands import DocumentCommandService
from .document_finder import DocumentFinderError, DocumentNotFoundError


def create_document_blueprint(document_commands: DocumentCommandService) -> Blueprint:
    """Create HTTP routes for local document search without coupling them to the main app."""
    blueprint = Blueprint("documents", __name__, url_prefix="/documents")

    @blueprint.before_request
    def restrict_document_access_to_local_dashboard():
        if not _is_loopback_host(request.remote_addr):
            return jsonify({
                "status": "error",
                "message": "Pencarian dokumen hanya tersedia dari laptop lokal.",
            }), 403

        origin = request.headers.get("Origin")
        if origin and not _is_trusted_local_origin(origin):
            return jsonify({
                "status": "error",
                "message": "Origin dashboard tidak diizinkan mengakses dokumen lokal.",
            }), 403
        return None

    @blueprint.post("/search")
    def search_documents():
        """Cari dokumen lokal pada folder yang telah dikonfigurasi."""
        data = request.get_json(silent=True) or {}
        try:
            payload = document_commands.search(
                data.get("query", ""),
                force_refresh=bool(data.get("force_refresh", False)),
            )
            return jsonify(payload)
        except ValueError as error:
            return jsonify({"status": "error", "message": str(error)}), 400

    @blueprint.post("/open")
    def open_document():
        """Buka dokumen hasil pencarian dengan aplikasi default sistem operasi."""
        data = request.get_json(silent=True) or {}
        try:
            position = data.get("position")
            if position is not None:
                position = int(position)
            payload = document_commands.open_result(
                result_id=data.get("result_id"),
                position=position,
            )
            return jsonify(payload)
        except (TypeError, ValueError) as error:
            return jsonify({"status": "error", "message": str(error)}), 400
        except DocumentNotFoundError as error:
            return jsonify({"status": "error", "message": str(error)}), 404
        except DocumentFinderError as error:
            return jsonify({"status": "error", "message": str(error)}), 500

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
