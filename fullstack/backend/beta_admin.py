"""Private beta administration, server-side database client and manual verified withdrawal.

Never expose BETA_ADMIN_TOKEN or BETA_SUPABASE_SECRET_KEY to a browser.
An email address alone is NOT sufficient proof of ownership for deletion.
"""
from __future__ import annotations

import json
import os
import secrets
import uuid
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as URLRequest, urlopen

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

admin_router = APIRouter(prefix="/api/admin", tags=["Beta administration"])
_TABLES = frozenset(("beta_waitlist", "beta_feedback", "beta_withdrawal_requests"))
_COLUMNS = frozenset(("id", "email", "status"))
_METHODS = frozenset(("GET", "POST", "PATCH", "DELETE"))


def db_call(table: str, *, method: str = "GET", filters: dict[str, str] | None = None,
            payload: dict | None = None, select: str = "*",
            limit: int | None = None, offset: int | None = None,
            prefer: str = "return=representation") -> object:
    """Restricted PostgREST operations; never accepts user-generated tables/URLs."""
    from fullstack.backend.beta import storage_config
    creds = storage_config()
    if creds is None:
        raise HTTPException(503, "Dedicated beta database is not configured.")
    if table not in _TABLES or method not in _METHODS:
        raise ValueError("Unsupported data operation")
    if select not in ("*", "id", "email,status", "id,email,status,requested_at"):
        raise ValueError("Unsupported column projection")
    if filters and any(col not in _COLUMNS for col in filters):
        raise ValueError("Unsupported database filter")
    url, key = creds
    query = {}
    if method == "GET":
        query["select"] = select
        if limit is not None:
            query["limit"] = str(max(1, min(int(limit), 50)))
        if offset is not None:
            query["offset"] = str(max(0, int(offset)))
    elif method in ("PATCH", "DELETE"):
        query["select"] = select
    if filters:
        query.update({k: "eq." + str(v) for k, v in filters.items()})
    endpoint = url + "/rest/v1/" + table
    if query:
        endpoint += "?" + urlencode(query)
    headers = {
        "apikey": key,  # new sb_secret_ keys are opaque, not bearer JWTs
        "Accept": "application/json",
        "User-Agent": "IndianMarketLabBetaAdmin/1.0",
        "Cache-Control": "no-store",
    }
    if method in ("POST", "PATCH", "DELETE"):
        headers["Prefer"] = prefer
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = URLRequest(endpoint, method=method,
                     data=json.dumps(payload).encode("utf-8") if payload is not None else None,
                     headers=headers)
    try:
        with urlopen(req, timeout=8) as response:
            raw = response.read(100000)
            if not raw:
                return None
            return json.loads(raw)
    except HTTPError:
        # Never return provider response bodies; those may contain protected values.
        raise HTTPException(503, "Secure beta storage request failed.") from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise HTTPException(503, "Secure beta storage is temporarily unavailable.") from None


def require_admin(request: Request) -> None:
    secret = os.environ.get("BETA_ADMIN_TOKEN", "")
    if len(secret) < 32:
        raise HTTPException(503, "Private administration is not configured.")
    header = request.headers.get("authorization", "")
    provided = header[7:] if header.startswith("Bearer ") else ""
    if not secrets.compare_digest(provided, secret):
        raise HTTPException(401, "Administrator access required.",
                            headers={"WWW-Authenticate": "Bearer"})


def no_store(data: object, status_code: int = 200) -> JSONResponse:
    return JSONResponse(data, status_code=status_code,
                        headers={"Cache-Control": "no-store", "Pragma": "no-cache",
                                 "X-Content-Type-Options": "nosniff"})


@admin_router.get("/submissions")
def submissions(request: Request,
                kind: Literal["waitlist", "feedback", "withdrawals"] = "withdrawals",
                limit: int = Query(30, ge=1, le=50),
                offset: int = Query(0, ge=0, le=10000)):
    require_admin(request)
    table = {"waitlist": "beta_waitlist", "feedback": "beta_feedback",
             "withdrawals": "beta_withdrawal_requests"}[kind]
    rows = db_call(table, limit=limit, offset=offset)
    if not isinstance(rows, list):
        raise HTTPException(503, "Unable to read beta submissions.")
    return no_store({"kind": kind, "items": rows, "limit": limit, "offset": offset})


class Completion(BaseModel):
    verification_method: Literal["reply-from-subscribed-email", "verified-offline"]
    confirmed_by_operator: bool = Field(description="Human administrator verified email ownership")


def validated_uuid(raw: str) -> str:
    try:
        return str(uuid.UUID(raw))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(422, "Invalid request identifier.") from None


@admin_router.post("/withdrawals/{request_id}/complete")
def complete_withdrawal(request: Request, request_id: str, form: Completion):
    """The operator must verify ownership out-of-band before this endpoint is used.

    A pending request submitted with only an email address never deletes data.
    """
    require_admin(request)
    uid = validated_uuid(request_id)
    if not form.confirmed_by_operator:
        raise HTTPException(422, "Verify email ownership before completing erasure.")
    records = db_call("beta_withdrawal_requests",
                      filters={"id": uid}, select="email,status", limit=1)
    if not isinstance(records, list) or not records:
        raise HTTPException(404, "Withdrawal request not found.")
    item = records[0]
    if item.get("status") != "pending":
        raise HTTPException(409, "Withdrawal request is not pending.")
    email = item.get("email", "")
    if not isinstance(email, str) or not email:
        raise HTTPException(503, "Withdrawal request cannot be verified.")
    # Delete the waitlist entry AND the request containing the same email.
    # Keeping a completed erasure request would otherwise retain the address.
    # Retrying after a partial network failure is safe while the pending queue exists.
    db_call("beta_waitlist", method="DELETE", filters={"email": email},
            select="id")
    db_call("beta_withdrawal_requests", method="DELETE",
            filters={"id": uid}, select="id")
    return no_store({"completed": True, "email_removed_from_queue": True})


@admin_router.delete("/feedback/{feedback_id}")
def delete_feedback(request: Request, feedback_id: str):
    require_admin(request)
    uid = validated_uuid(feedback_id)
    db_call("beta_feedback", method="DELETE", filters={"id": uid}, select="id")
    return no_store({"deleted": True})
