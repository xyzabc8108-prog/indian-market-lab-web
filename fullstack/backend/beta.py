"""Public beta intake. No PII is stored locally or written to transient Render disk.

Set BETA_SUPABASE_URL and BETA_SUPABASE_SECRET_KEY for a dedicated project.
Only the server accesses the secret; public endpoints never expose submissions.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import json
import os
import re
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request as URLRequest, urlopen

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

router = APIRouter(prefix="/api/beta", tags=["Beta"])
_EMAIL = re.compile(r"^[^@\s]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}$")
_FEATURES = {"charts", "scanner", "backtesting", "paper-trading", "news", "other"}
_rate_lock = threading.Lock()
_rate_condition = threading.Condition(_rate_lock)
_rate_cleaner_started = False
_recent: dict[str, deque[float]] = defaultdict(deque)


def _prune_rate_history(now: float) -> None:
    """Called with _rate_lock held. Remove expired IP keys, including idle keys."""
    for ident, history in list(_recent.items()):
        while history and now - history[0] >= 3600:
            history.popleft()
        if not history:
            _recent.pop(ident, None)


def _rate_expiry_worker() -> None:
    """One daemon per process; sleeps until the next rate-window expiry."""
    while True:
        with _rate_condition:
            now = time.monotonic()
            _prune_rate_history(now)
            earliest = min((h[0] + 3600 for h in _recent.values() if h),
                           default=None)
            if earliest is None:
                _rate_condition.wait()
            else:
                _rate_condition.wait(timeout=max(0.01, earliest - now))


def _start_rate_expiry_worker() -> None:
    """Called under _rate_condition to avoid spawning multiple cleanup threads."""
    global _rate_cleaner_started
    if not _rate_cleaner_started:
        threading.Thread(
            target=_rate_expiry_worker,
            name="beta-ephemeral-rate-expiry",
            daemon=True,
        ).start()
        _rate_cleaner_started = True


class Interest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    feature: str = Field(default="charts", max_length=32)
    consent: bool
    website: str = Field(default="", max_length=150)  # bot honeypot

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL.fullmatch(value) or ".." in value:
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("feature")
    @classmethod
    def validate_feature(cls, value: str) -> str:
        if value not in _FEATURES:
            raise ValueError("Choose an available feature.")
        return value


class Feedback(BaseModel):
    feature: str = Field(max_length=32)
    rating: int = Field(ge=1, le=5)
    message: str = Field(min_length=12, max_length=1200)
    website: str = Field(default="", max_length=150)

    @field_validator("feature")
    @classmethod
    def validate_feature(cls, value: str) -> str:
        if value not in _FEATURES:
            raise ValueError("Choose an available feature.")
        return value

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 12:
            raise ValueError("Describe your feedback in at least 12 characters.")
        if any(ord(char) < 32 and char not in "\n\t" for char in value):
            raise ValueError("Feedback contains invalid control characters.")
        if "<" in value or ">" in value:
            raise ValueError("Please write feedback as plain text without HTML tags.")
        return value


def public_contact_email() -> str | None:
    """Return the operator-designated public address published in the Privacy Notice."""
    contact = "rohanchhaya108@gmail.com"
    if not _EMAIL.fullmatch(contact) or ".." in contact:
        return None
    return contact


def storage_config() -> tuple[str, str] | None:
    """Server-only database access, even when public signups are closed."""
    url = os.environ.get("BETA_SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("BETA_SUPABASE_SECRET_KEY", "").strip()
    parsed = urlparse(url)
    if (parsed.scheme != "https" or not parsed.hostname or
        not parsed.hostname.endswith(".supabase.co") or
        parsed.port not in (None, 443) or
        parsed.username or parsed.password or
        parsed.path not in ("", "/") or parsed.query or parsed.fragment or
        not key.startswith("sb_secret_")):
        return None
    return url, key


def beta_config() -> tuple[str, str] | None:
    """Public intake needs verified storage plus an explicit privacy readiness flag."""
    if os.environ.get("BETA_PRIVACY_READY", "").strip().lower() != "true":
        return None
    if public_contact_email() is None:
        return None
    return storage_config()


def _remote(table: str, payload: dict | None = None) -> int:
    credentials = beta_config()
    if credentials is None:
        raise HTTPException(503, "Beta registration is not open yet.")
    url, key = credentials
    # Fixed table names, never user-controlled URLs or filters.
    if table not in ("beta_waitlist", "beta_feedback"):
        raise ValueError("Unsupported beta store")
    endpoint = f"{url}/rest/v1/{table}"
    if payload is None:
        endpoint += "?select=id&limit=0"
    headers = {
        "apikey": key,
        "Accept": "application/json",
        "User-Agent": "IndianMarketLabBeta/1.0",
    }
    if payload is not None:
        headers["Content-Type"] = "application/json"
        headers["Prefer"] = "return=minimal"
    req = URLRequest(
        endpoint, data=None if payload is None else json.dumps(payload).encode(),
        headers=headers, method="GET" if payload is None else "POST",
    )
    try:
        with urlopen(req, timeout=6) as response:
            return response.status
    except HTTPError as exc:
        # Unique email constraint: indistinguishable response from fresh signup.
        if payload is not None and table == "beta_waitlist" and exc.code == 409:
            return 409
        raise HTTPException(503, "Beta submissions are temporarily unavailable.") from None
    except (URLError, TimeoutError, OSError):
        raise HTTPException(503, "Beta submissions are temporarily unavailable.") from None


def _accept(request: Request, kind: str) -> None:
    # No cookies or analytics. Per-IP rate counters stay in memory, not a database.
    origin = request.headers.get("origin")
    if origin:
        parsed = urlparse(origin)
        expected = os.environ.get("BETA_PUBLIC_ORIGIN", "").rstrip("/")
        if expected and origin.rstrip("/") != expected:
            raise HTTPException(403, "Request origin not allowed.")
        if not expected and parsed.netloc.lower() != request.headers.get("host", "").lower():
            raise HTTPException(403, "Request origin not allowed.")
    ident = (request.client.host if request.client else "unknown") + ":" + kind
    now = time.monotonic()
    with _rate_condition:
        _prune_rate_history(now)
        history = _recent[ident]
        # One server process: a basic abuse brake, not distributed spam protection.
        if len(history) >= (3 if kind == "waitlist" else 12):
            raise HTTPException(429, "Too many submissions. Please try later.")
        history.append(now)
        _start_rate_expiry_worker()
        _rate_condition.notify()


_status_cache: tuple[float, bool, bool] | None = None


@router.get("/status")
def status():
    global _status_cache
    if beta_config() is None:
        return {"waitlist_open": False, "feedback_open": False,
                "message": "Early access registration is not open yet."}
    now = time.monotonic()
    if _status_cache and _status_cache[0] > now:
        return {"waitlist_open": _status_cache[1],
                "feedback_open": _status_cache[2]}
    def ready(table: str) -> bool:
        try:
            return _remote(table) in (200, 206)
        except HTTPException:
            return False
    waitlist, feedback = ready("beta_waitlist"), ready("beta_feedback")
    _status_cache = (now + 90, waitlist, feedback)
    return {"waitlist_open": waitlist, "feedback_open": feedback}


@router.post("/interest", status_code=202)
def interest(request: Request, form: Interest):
    if not form.consent:
        raise HTTPException(422, "Consent is required to join the waitlist.")
    if beta_config() is None:
        raise HTTPException(503, "Early access registration is not open yet.")
    _accept(request, "waitlist")
    if form.website:
        return {"received": True}
    _remote("beta_waitlist", {
        "email": form.email,
        "feature": form.feature,
        "consent_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"received": True}


@router.post("/feedback", status_code=202)
def feedback(request: Request, form: Feedback):
    if beta_config() is None:
        raise HTTPException(503, "Feedback submission is not open yet.")
    _accept(request, "feedback")
    if form.website:
        return {"received": True}
    _remote("beta_feedback", {
        "feature": form.feature, "rating": form.rating, "message": form.message,
    })
    return {"received": True}


class WaitlistSignup(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    feature_interest: str = Field(default="charts", max_length=32)
    consent_given: bool
    website: str = Field(default="", max_length=150)

    @field_validator("email")
    @classmethod
    def verify_email(cls, value: str) -> str:
        return Interest.validate_email(value)

    @field_validator("feature_interest")
    @classmethod
    def verify_interest(cls, value: str) -> str:
        return Interest.validate_feature(value)


@router.post("/waitlist", status_code=202)
def signup_waitlist(request: Request, form: WaitlistSignup):
    """New explicit-consent API, backed by the same existing beta_waitlist table."""
    return interest(request, Interest(
        email=form.email, feature=form.feature_interest,
        consent=form.consent_given, website=form.website,
    ))


class WithdrawalRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    confirmation: bool
    website: str = Field(default="", max_length=150)

    @field_validator("email")
    @classmethod
    def verify_email(cls, value: str) -> str:
        return Interest.validate_email(value)


@router.post("/withdrawal-request", status_code=202)
def withdrawal_request(request: Request, form: WithdrawalRequest):
    """Queue a request; actual erasure requires manual email-ownership verification."""
    if not form.confirmation:
        raise HTTPException(422, "Confirm that you are requesting withdrawal.")
    if storage_config() is None:
        raise HTTPException(503, "Data requests are unavailable. Please email rohanchhaya108@gmail.com.")
    _accept(request, "withdrawal")
    if form.website:
        return {"received": True, "next_step": "verify_email_with_support"}
    # This does not disclose whether the requested address appears in the waitlist.
    # It also never deletes records based solely on an unverified email address.
    from fullstack.backend.beta_admin import db_call
    db_call("beta_withdrawal_requests", method="POST",
            payload={"email": form.email, "status": "pending"},
            prefer="return=minimal")
    return {"received": True, "next_step": "verify_email_with_support"}
