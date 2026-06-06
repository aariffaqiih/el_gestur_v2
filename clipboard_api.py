# ============================================================
# EL PRESENTASI v2.0 — CLIPBOARD HTTP API
# Endpoint REST untuk mengakses Clipboard History dari dashboard
# ============================================================

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request

from clipboard_commands import ClipboardCommandService
from clipboard_ring import ClipboardItemNotFoundError, ClipboardRingError


def create_clipboard_blueprint(
    clipboard_commands: ClipboardCommandService,
) -> Blueprint:
    """Create HTTP routes for clipboard history without coupling them to the main app."""
    blueprint = Blueprint("clipboard", __name__, url_prefix="/clipboard")

    @blueprint.before_request
    def restrict_clipboard_access_to_local_dashboard():
        if not _is_loopback_host(request.remote_addr):
            return jsonify({
                "status": "error",
                "message": "Riwayat clipboard hanya tersedia dari laptop lokal.",
            }), 403

        origin = request.headers.get("Origin")
        if origin and not _is_trusted_local_origin(origin):
            return jsonify({
                "status": "error",
                "message": "Origin dashboard tidak diizinkan mengakses clipboard.",
            }), 403
        return None

    @blueprint.get("")
    def list_clipboard():
        """Ambil seluruh riwayat clipboard ring (item terbaru di posisi 1)."""
        payload = clipboard_commands.list_items()
        return jsonify(payload)

    @blueprint.post("/paste")
    def paste_clipboard_item():
        """Tempel item clipboard berdasarkan posisi (1 = terbaru)."""
        data = request.get_json(silent=True) or {}
        try:
            position = int(data.get("position", 1))
        except (TypeError, ValueError):
            return jsonify({
                "status": "error",
                "message": "Posisi harus berupa angka.",
            }), 400

        payload = clipboard_commands.paste_at(position)
        if payload.get("status") == "success":
            return jsonify(payload)
        status_code = 404 if "tidak ada" in payload.get("message", "").casefold() else 400
        return jsonify(payload), status_code

    @blueprint.delete("")
    def clear_clipboard():
        """Kosongkan seluruh riwayat clipboard."""
        payload = clipboard_commands.clear_ring()
        return jsonify(payload)

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
