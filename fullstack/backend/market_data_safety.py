"""Fail-closed controls for public market-price redistribution.

The application has no verified public-display licence for its current
unofficial provider. Keep these endpoints disabled unless the operator has
actually obtained applicable rights and completed regulatory review.

Reversal requires both independent server-only approvals, never query inputs.
This does not itself verify that a licence is valid.
"""
from __future__ import annotations

import os

from fastapi import HTTPException

_PUBLIC_PRICE_NOTICE = (
    "Public stock-price charts and stock-specific scenarios are temporarily "
    "unavailable while market-data rights and regulatory requirements are "
    "reviewed. You can still use the upload-based scanner and user-entered "
    "paper-risk tools. No live quotes or real orders are provided."
)


def public_market_data_enabled() -> bool:
    """Default to OFF. Two explicit operator-controlled server flags required."""
    return (
        os.environ.get("IML_PUBLIC_PRICE_DATA_ENABLED", "").strip().lower() == "true"
        and os.environ.get("IML_MARKET_DATA_LICENSE_APPROVED", "").strip().lower() == "true"
    )


def public_market_data_safety_mode() -> bool:
    return not public_market_data_enabled()


def require_public_market_data() -> None:
    """Call at the API boundary, before any cache or price provider access."""
    if public_market_data_safety_mode():
        raise HTTPException(status_code=503, detail=_PUBLIC_PRICE_NOTICE)


def market_data_status() -> dict:
    """Non-sensitive public capability status. Never exposes env var contents."""
    blocked = public_market_data_safety_mode()
    return {
        "market_data_safety_mode": blocked,
        "public_price_data_available": not blocked,
        "note": _PUBLIC_PRICE_NOTICE if blocked else
                "Historical price endpoints available only under operator-approved market-data rights.",
        "safe_tools": ["synthetic-scanner-demo", "manual-risk", "manual-derivatives", "paper-journal"],
        "real_orders": False,
    }
