"""Beta launch tests: no external service or actual email addresses are used."""
from collections import defaultdict, deque

from fastapi.testclient import TestClient

from fullstack.backend import beta
from fullstack.backend.main import app

client = TestClient(app)


def test_beta_page_and_assets():
    page = client.get("/beta")
    assert page.status_code == 200
    assert "PUBLIC BETA" in page.text
    assert "No real orders" in page.text
    assert client.get("/beta.js").status_code == 200
    assert client.get("/beta.css").status_code == 200


def test_closed_beta_never_claims_to_store(monkeypatch):
    monkeypatch.delenv("BETA_SUPABASE_URL", raising=False)
    monkeypatch.delenv("BETA_SUPABASE_SECRET_KEY", raising=False)
    r = client.get("/api/beta/status")
    assert r.status_code == 200
    assert r.json()["waitlist_open"] is False
    assert r.json()["feedback_open"] is False
    r = client.post("/api/beta/interest", json={
        "email": "test@example.invalid", "feature": "charts", "consent": True,
    })
    assert r.status_code == 503
    r = client.post("/api/beta/feedback", json={
        "feature": "charts", "rating": 4, "message": "Great chart experience!",
    })
    assert r.status_code == 503


def test_invalid_email_consent_feature_and_feedback():
    assert client.post("/api/beta/interest", json={
        "email": "invalid", "feature": "charts", "consent": True,
    }).status_code == 422
    assert client.post("/api/beta/interest", json={
        "email": "test@example.invalid", "feature": "charts", "consent": False,
    }).status_code == 422
    assert client.post("/api/beta/interest", json={
        "email": "test@example.invalid", "feature": "secret-plan", "consent": True,
    }).status_code == 422
    assert client.post("/api/beta/feedback", json={
        "feature": "charts", "rating": 9, "message": "A long and interesting message.",
    }).status_code == 422
    assert client.post("/api/beta/feedback", json={
        "feature": "charts", "rating": 4, "message": "Too short",
    }).status_code == 422


def test_ready_endpoints_have_no_public_pii(monkeypatch):
    monkeypatch.setenv("BETA_SUPABASE_URL", "https://dedicated-test.supabase.co")
    monkeypatch.setenv("BETA_SUPABASE_SECRET_KEY", "sb_secret_placeholder")
    monkeypatch.setenv("BETA_PRIVACY_READY", "true")
    monkeypatch.setattr(beta, "_recent", defaultdict(deque))
    monkeypatch.setattr(beta, "_status_cache", None)
    requests = []

    def fake_remote(table, payload=None):
        requests.append((table, payload))
        return 200 if payload is None else 201

    monkeypatch.setattr(beta, "_remote", fake_remote)
    status = client.get("/api/beta/status").json()
    assert status == {"waitlist_open": True, "feedback_open": True}
    assert "email" not in status
    lead = client.post("/api/beta/interest", json={
        "email": "  Test@Example.invalid ", "feature": "charts", "consent": True,
    })
    assert lead.status_code == 202 and lead.json() == {"received": True}
    feedback = client.post("/api/beta/feedback", json={
        "feature": "scanner", "rating": 3,
        "message": "The scanner needs a clearer guide.",
    })
    assert feedback.status_code == 202
    assert requests[2][1]["email"] == "test@example.invalid"
    assert requests[2][1]["feature"] == "charts"
    assert requests[3][1]["rating"] == 3
    assert "email" not in requests[3][1]


def test_public_form_origin_restriction_and_bot_trap(monkeypatch):
    monkeypatch.setenv("BETA_SUPABASE_URL", "https://dedicated-test.supabase.co")
    monkeypatch.setenv("BETA_SUPABASE_SECRET_KEY", "sb_secret_placeholder")
    monkeypatch.setenv("BETA_PRIVACY_READY", "true")
    monkeypatch.setenv("BETA_PUBLIC_ORIGIN", "https://example.test")
    monkeypatch.setattr(beta, "_recent", defaultdict(deque))
    calls = []
    monkeypatch.setattr(beta, "_remote", lambda table, payload=None: calls.append(payload) or 201)
    payload = {"email": "test@example.invalid", "feature": "charts", "consent": True}
    blocked = client.post("/api/beta/interest", headers={"Origin": "https://other.test"}, json=payload)
    assert blocked.status_code == 403
    trapped = client.post("/api/beta/interest", headers={"Origin": "https://example.test"},
                          json={**payload, "website": "spam.example"})
    assert trapped.status_code == 202
    assert calls == []


def test_rate_limiter(monkeypatch):
    monkeypatch.setenv("BETA_SUPABASE_URL", "https://dedicated-test.supabase.co")
    monkeypatch.setenv("BETA_SUPABASE_SECRET_KEY", "sb_secret_placeholder")
    monkeypatch.setenv("BETA_PRIVACY_READY", "true")
    monkeypatch.delenv("BETA_PUBLIC_ORIGIN", raising=False)
    monkeypatch.setattr(beta, "_recent", defaultdict(deque))
    monkeypatch.setattr(beta, "_remote", lambda table, payload=None: 201)
    payload = {"email": "test@example.invalid", "feature": "charts", "consent": True}
    for _ in range(3):
        assert client.post("/api/beta/interest", json=payload).status_code == 202
    assert client.post("/api/beta/interest", json=payload).status_code == 429


def test_credentials_alone_do_not_open_beta(monkeypatch):
    monkeypatch.setenv("BETA_SUPABASE_URL", "https://dedicated-test.supabase.co")
    monkeypatch.setenv("BETA_SUPABASE_SECRET_KEY", "sb_secret_placeholder")
    monkeypatch.delenv("BETA_PRIVACY_READY", raising=False)
    r=client.get("/api/beta/status")
    assert r.status_code==200
    assert r.json()["waitlist_open"] is False
    assert r.json()["feedback_open"] is False


def test_published_email_does_not_open_waitlist_by_itself(monkeypatch):
    assert beta.public_contact_email() == "rohanchhaya108@gmail.com"
    monkeypatch.delenv("BETA_SUPABASE_URL", raising=False)
    monkeypatch.delenv("BETA_SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.delenv("BETA_PRIVACY_READY", raising=False)
    monkeypatch.setattr(beta, "_status_cache", None)
    assert beta.beta_config() is None
    r = client.get("/api/beta/status")
    assert r.status_code == 200
    assert r.json()["waitlist_open"] is False
    assert r.json()["feedback_open"] is False



def test_new_waitlist_alias_requires_explicit_consent(monkeypatch):
    monkeypatch.setenv("BETA_SUPABASE_URL", "https://dedicated-test.supabase.co")
    monkeypatch.setenv("BETA_SUPABASE_SECRET_KEY", "sb_secret_placeholder")
    monkeypatch.setenv("BETA_PRIVACY_READY", "true")
    monkeypatch.setattr(beta, "_recent", defaultdict(deque))
    submitted = []
    monkeypatch.setattr(beta, "_remote", lambda table, payload=None: submitted.append(payload) or 201)
    invalid = client.post("/api/beta/waitlist", json={
        "email": "test@example.invalid", "feature_interest": "scanner",
        "consent_given": False,
    })
    assert invalid.status_code == 422
    valid = client.post("/api/beta/waitlist", json={
        "email": "test@example.invalid", "feature_interest": "scanner",
        "consent_given": True,
    })
    assert valid.status_code == 202
    assert submitted[0]["email"] == "test@example.invalid"
    assert submitted[0]["feature"] == "scanner"
    assert "consent_at" in submitted[0]


def test_feedback_rejects_html_and_control_chars():
    for text in ("Hello <script>alert(1)</script>", "Hello\nworld\x01 test feedback"):
        r=client.post("/api/beta/feedback", json={
            "feature": "other", "rating": 4, "message": text,
        })
        assert r.status_code == 422
