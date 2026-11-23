"""ClamAV INSTREAM scanning over TCP (clamd). Skipped when CLAMAV_HOST is unset."""

from __future__ import annotations

import logging
import socket
import struct
from typing import Literal

from app.core.config import get_settings

logger = logging.getLogger(__name__)

ScanResult = Literal["clean", "infected", "failed"]

_CHUNK = 8192


def scan_bytes(
    data: bytes, *, host: str | None = None, port: int | None = None
) -> ScanResult | None:
    """Return None when scanning is disabled (no host configured)."""
    settings = get_settings()
    target = host if host is not None else settings.clamav_host
    if not target:
        return None
    target_port = port if port is not None else settings.clamav_port
    try:
        with socket.create_connection((target, target_port), timeout=30.0) as sock:
            sock.settimeout(60.0)
            sock.sendall(b"zINSTREAM\0")
            offset = 0
            while offset < len(data):
                piece = data[offset : offset + _CHUNK]
                offset += len(piece)
                sock.sendall(struct.pack("!I", len(piece)) + piece)
            sock.sendall(struct.pack("!I", 0))
            response = bytearray()
            while True:
                part = sock.recv(4096)
                if not part:
                    break
                response.extend(part)
    except OSError:
        logger.warning("clamav_scan_failed host=%s", target, exc_info=True)
        return "failed"

    text = response.decode("utf-8", errors="replace").strip()
    if "FOUND" in text.upper():
        return "infected"
    if "OK" in text.upper():
        return "clean"
    logger.warning("clamav_unexpected_response response=%r", text[:200])
    return "failed"
