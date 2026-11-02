"""No live database, credentials or personal data are used by these tests."""
from collections import defaultdict, deque

from fastapi.testclient import TestClient

from fullstack.backend import beta, beta_admin
from fullstack.backend.main import app

client = TestClient(app)
ADMIN_TOKEN = "unit-testing-admin-token-at-least-32-characters-long"
HEADERS = {"Authorization": "Bearer " + ADMIN_TOKEN}


def setup_database(monkeypatch):
    monkeypatch.setenv("BETA_SUPABASE_URL", "https://dedicated-test.supabase.co")
    monkeypatch.setenv("BETA_SUPABASE_SECRET_KEY", "sb_secret_testonly")
    monkeypatch.setenv("BETA_PRIVACY_READY", "true")
    monkeypatch.setenv("BETA_ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setattr(beta, "_recent", defaultdict(deque))


def test_admin_denied_when_disabled_or_unauthorized(monkeypatch):
    monkeypatch.delenv("BETA_ADMIN_TOKEN", raising=False)
    r = client.get("/api/admin/submissions")
    assert r.status_code == 503
    setup_database(monkeypatch)
    assert client.get("/api/admin/submissions").status_code == 401
    assert client.get("/api/admin/submissions",
                      headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_authenticated_list_is_private_and_not_cached(monkeypatch):
    setup_database(monkeypatch)
    seen=[]
    def fake_db(table, **kwargs):
        seen.append((table, kwargs))
        return [{"id":"test-row","email":"test@example.invalid"}]
    monkeypatch.setattr(beta_admin,"db_call",fake_db)
    r=client.get("/api/admin/submissions?kind=waitlist&limit=5",headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["items"][0]["email"]=="test@example.invalid"
    assert r.headers.get("cache-control")=="no-store"
    assert seen[0][0]=="beta_waitlist"
    assert client.get("/api/admin/submissions?kind=unknown",headers=HEADERS).status_code==422


def test_withdrawal_request_is_queued_never_publicly_deleted(monkeypatch):
    setup_database(monkeypatch)
    seen=[]
    monkeypatch.setattr(beta_admin,"db_call",
                        lambda table,**kwargs: seen.append((table,kwargs)) or None)
    body={"email":"test@example.invalid","confirmation":True}
    r=client.post("/api/beta/withdrawal-request",json=body)
    assert r.status_code==202
    assert r.json()=={"received":True,"next_step":"verify_email_with_support"}
    assert len(seen)==1
    assert seen[0][0]=="beta_withdrawal_requests"
    assert seen[0][1]["method"]=="POST"
    assert seen[0][1]["payload"]["status"]=="pending"
    assert "DELETE" not in str(seen)
    assert client.post("/api/beta/withdrawal-request",
                       json={**body,"confirmation":False}).status_code==422


def test_admin_cannot_delete_without_verified_email(monkeypatch):
    setup_database(monkeypatch)
    uid="123e4567-e89b-12d3-a456-426614174000"
    calls=[]
    monkeypatch.setattr(beta_admin,"db_call",
                        lambda table,**kw: calls.append((table,kw)) or [])
    unverified=client.post("/api/admin/withdrawals/"+uid+"/complete",
                           headers=HEADERS,json={
                               "verification_method":"reply-from-subscribed-email",
                               "confirmed_by_operator":False
                           })
    assert unverified.status_code==422
    assert calls==[]
    assert client.post("/api/admin/withdrawals/"+uid+"/complete",
                       json={"verification_method":"reply-from-subscribed-email",
                             "confirmed_by_operator":True}).status_code==401


def test_verified_manual_withdrawal_removes_only_waitlist(monkeypatch):
    setup_database(monkeypatch)
    uid="123e4567-e89b-12d3-a456-426614174000"
    calls=[]
    def mock_db(table,**kwargs):
        calls.append((table,kwargs))
        if table=="beta_withdrawal_requests" and kwargs.get("method","GET")=="GET":
            return [{"email":"test@example.invalid","status":"pending"}]
        return [{"id":"deleted-or-completed"}]
    monkeypatch.setattr(beta_admin,"db_call",mock_db)
    r=client.post("/api/admin/withdrawals/"+uid+"/complete",headers=HEADERS,
                  json={"verification_method":"reply-from-subscribed-email",
                        "confirmed_by_operator":True})
    assert r.status_code==200 and r.json()=={"completed":True}
    assert [x[0] for x in calls]==[
        "beta_withdrawal_requests","beta_waitlist","beta_withdrawal_requests"]
    assert calls[1][1]["method"]=="DELETE"
    assert calls[1][1]["filters"]=={"email":"test@example.invalid"}
    assert calls[2][1]["method"]=="PATCH"
    assert calls[2][1]["payload"]["status"]=="completed"
    assert r.headers["cache-control"]=="no-store"


def test_admin_feedback_erasure_requires_token_and_uuid(monkeypatch):
    setup_database(monkeypatch)
    uid="123e4567-e89b-12d3-a456-426614174000"
    calls=[]
    monkeypatch.setattr(beta_admin,"db_call",
                        lambda table,**kwargs: calls.append((table,kwargs)) or [])
    assert client.delete("/api/admin/feedback/"+uid).status_code==401
    r=client.delete("/api/admin/feedback/"+uid,headers=HEADERS)
    assert r.status_code==200
    assert calls[0][0]=="beta_feedback"
    assert calls[0][1]["filters"]=={"id":uid}
    assert client.delete("/api/admin/feedback/not-a-uuid",headers=HEADERS).status_code==422


def test_supabase_secret_key_is_not_sent_as_a_jwt(monkeypatch):
    setup_database(monkeypatch)
    class Response:
        status=200
        def __enter__(self): return self
        def __exit__(self,*args): return None
        def read(self,*args): return b"[]"
    checked=[]
    def fake_urlopen(req,timeout):
        checked.append(req)
        return Response()
    monkeypatch.setattr(beta_admin,"urlopen",fake_urlopen)
    assert beta_admin.db_call("beta_waitlist",limit=1)==[]
    req=checked[0]
    assert req.get_header("Apikey")=="sb_secret_testonly"
    assert req.get_header("Authorization") is None
    assert req.full_url.startswith("https://dedicated-test.supabase.co/rest/v1/")
    assert "sb_secret_" not in req.full_url
