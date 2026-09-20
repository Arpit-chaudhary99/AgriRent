"""Backend tests for AgriRent Pro — auth, RBAC, rental flow, admin CRUD."""
import os
import subprocess
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://crop-tool-hub.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"


def _mongo_eval(script: str) -> str:
    result = subprocess.run(
        ["mongosh", "--quiet", "--eval", script],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout + result.stderr


def _bootstrap_user(email: str, role: str = "USER", blocked: bool = False):
    uid = f"test-{role.lower()}-{uuid.uuid4().hex[:8]}"
    token = f"testtok_{uuid.uuid4().hex}"
    script = f"""
    use('test_database');
    db.users.insertOne({{
      user_id: '{uid}',
      email: '{email}',
      name: 'Test {role}',
      picture: 'https://via.placeholder.com/150',
      role: '{role}',
      blocked: {str(blocked).lower()},
      created_at: new Date().toISOString()
    }});
    db.user_sessions.insertOne({{
      user_id: '{uid}',
      session_token: '{token}',
      expires_at: new Date(Date.now() + 7*24*60*60*1000),
      created_at: new Date()
    }});
    """
    _mongo_eval(script)
    return uid, token


def _cleanup_user(uid: str):
    _mongo_eval(f"""
    use('test_database');
    db.users.deleteOne({{user_id: '{uid}'}});
    db.user_sessions.deleteMany({{user_id: '{uid}'}});
    db.rentals.deleteMany({{user_id: '{uid}'}});
    db.payments.deleteMany({{user_id: '{uid}'}});
    """)


def _hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ------------------------ Fixtures ------------------------
@pytest.fixture(scope="module")
def user_a():
    uid, tok = _bootstrap_user(f"TEST_userA_{uuid.uuid4().hex[:6]}@example.com", "USER")
    yield {"uid": uid, "token": tok}
    _cleanup_user(uid)


@pytest.fixture(scope="module")
def user_b():
    uid, tok = _bootstrap_user(f"TEST_userB_{uuid.uuid4().hex[:6]}@example.com", "USER")
    yield {"uid": uid, "token": tok}
    _cleanup_user(uid)


@pytest.fixture(scope="module")
def admin_user():
    # Use a distinct admin email (not the primary ADMIN_EMAIL) so we don't collide,
    # but the role=ADMIN in DB is what current_admin checks.
    uid, tok = _bootstrap_user(f"TEST_admin_{uuid.uuid4().hex[:6]}@example.com", "ADMIN")
    yield {"uid": uid, "token": tok}
    _cleanup_user(uid)


@pytest.fixture(scope="module")
def blocked_user():
    uid, tok = _bootstrap_user(f"TEST_blocked_{uuid.uuid4().hex[:6]}@example.com", "USER", blocked=True)
    yield {"uid": uid, "token": tok}
    _cleanup_user(uid)


# ------------------------ Public routes ------------------------
class TestPublicRoutes:
    def test_get_tools_no_auth(self):
        r = requests.get(f"{API}/tools")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_tool_by_id_no_auth(self):
        tools = requests.get(f"{API}/tools").json()
        r = requests.get(f"{API}/tools/{tools[0]['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == tools[0]["id"]

    def test_payments_methods_no_auth(self):
        r = requests.get(f"{API}/payments/methods")
        assert r.status_code in (200, 502)  # 502 if Razorpay unreachable

    def test_webhook_no_auth_but_needs_signature(self):
        # Should not return 401/403 — should hit signature check instead (400 or 503)
        r = requests.post(f"{API}/payments/webhook", json={})
        assert r.status_code in (400, 503)


# ------------------------ Auth /me + logout ------------------------
class TestAuthMe:
    def test_me_no_token_401(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_me_bogus_token_401(self):
        r = requests.get(f"{API}/auth/me", headers=_hdr("nonexistent-token"))
        assert r.status_code == 401

    def test_me_valid_token_200(self, user_a):
        r = requests.get(f"{API}/auth/me", headers=_hdr(user_a["token"]))
        assert r.status_code == 200
        data = r.json()
        assert data["user_id"] == user_a["uid"]
        assert data["role"] == "USER"

    def test_logout_invalidates_session(self):
        uid, tok = _bootstrap_user(f"TEST_logout_{uuid.uuid4().hex[:6]}@example.com", "USER")
        try:
            r = requests.get(f"{API}/auth/me", headers=_hdr(tok))
            assert r.status_code == 200
            r = requests.post(f"{API}/auth/logout", headers=_hdr(tok))
            assert r.status_code == 200
            r = requests.get(f"{API}/auth/me", headers=_hdr(tok))
            assert r.status_code == 401
        finally:
            _cleanup_user(uid)


# ------------------------ RBAC gating ------------------------
class TestRoleGating:
    def test_user_forbidden_admin_stats(self, user_a):
        r = requests.get(f"{API}/admin/stats", headers=_hdr(user_a["token"]))
        assert r.status_code == 403

    def test_user_forbidden_admin_create_tool(self, user_a):
        r = requests.post(f"{API}/admin/tools", headers=_hdr(user_a["token"]),
                          json={"name": "x", "category": "y", "location": "z", "daily_rate": 100})
        assert r.status_code == 403

    def test_user_forbidden_admin_patch_tool(self, user_a):
        r = requests.patch(f"{API}/admin/tools/tool-001", headers=_hdr(user_a["token"]), json={"name": "x"})
        assert r.status_code == 403

    def test_user_forbidden_admin_delete_tool(self, user_a):
        r = requests.delete(f"{API}/admin/tools/tool-001", headers=_hdr(user_a["token"]))
        assert r.status_code == 403

    def test_user_forbidden_admin_list_users(self, user_a):
        r = requests.get(f"{API}/admin/users", headers=_hdr(user_a["token"]))
        assert r.status_code == 403

    def test_user_forbidden_admin_list_rentals(self, user_a):
        r = requests.get(f"{API}/admin/rentals", headers=_hdr(user_a["token"]))
        assert r.status_code == 403

    def test_user_forbidden_admin_list_payments(self, user_a):
        r = requests.get(f"{API}/admin/payments", headers=_hdr(user_a["token"]))
        assert r.status_code == 403

    def test_user_forbidden_admin_block_user(self, user_a, user_b):
        r = requests.patch(f"{API}/admin/users/{user_b['uid']}/block",
                           headers=_hdr(user_a["token"]), json={"blocked": True})
        assert r.status_code == 403

    def test_user_forbidden_admin_approve(self, user_a):
        r = requests.patch(f"{API}/admin/rentals/fakeid/approve", headers=_hdr(user_a["token"]))
        assert r.status_code == 403

    def test_admin_can_access_stats(self, admin_user):
        r = requests.get(f"{API}/admin/stats", headers=_hdr(admin_user["token"]))
        assert r.status_code == 200
        for k in ("total_tools", "available_tools", "total_users", "active_rentals",
                  "paid_rentals", "cancelled_rentals", "total_revenue"):
            assert k in r.json()


# ------------------------ Blocked user ------------------------
class TestBlockedUser:
    def test_blocked_user_gets_403(self, blocked_user):
        r = requests.get(f"{API}/auth/me", headers=_hdr(blocked_user["token"]))
        assert r.status_code == 403
        r = requests.get(f"{API}/rentals", headers=_hdr(blocked_user["token"]))
        assert r.status_code == 403


# ------------------------ Rental creation ------------------------
class TestRentalCreate:
    def test_create_rental_computes_days_and_total(self, user_a):
        tool = requests.get(f"{API}/tools").json()[0]
        payload = {"tool_id": tool["id"], "start_date": "2026-03-01", "end_date": "2026-03-05"}
        r = requests.post(f"{API}/rentals", headers=_hdr(user_a["token"]), json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["days"] == 5  # (5-1)+1
        assert data["total"] == 5 * tool["daily_rate"]
        assert data["user_id"] == user_a["uid"]
        assert data["status"] == "Requested"

    def test_create_rental_same_day(self, user_a):
        tool = requests.get(f"{API}/tools").json()[0]
        r = requests.post(f"{API}/rentals", headers=_hdr(user_a["token"]),
                          json={"tool_id": tool["id"], "start_date": "2026-04-01", "end_date": "2026-04-01"})
        assert r.status_code == 200
        assert r.json()["days"] == 1

    def test_create_rental_end_before_start_400(self, user_a):
        tool = requests.get(f"{API}/tools").json()[0]
        r = requests.post(f"{API}/rentals", headers=_hdr(user_a["token"]),
                          json={"tool_id": tool["id"], "start_date": "2026-05-10", "end_date": "2026-05-05"})
        assert r.status_code == 400

    def test_create_rental_unavailable_tool_400(self, user_a, admin_user):
        # Create a new tool and mark unavailable via admin
        c = requests.post(f"{API}/admin/tools", headers=_hdr(admin_user["token"]),
                          json={"name": "TEST_unavailable", "category": "T", "location": "L",
                                "daily_rate": 100, "available": False})
        assert c.status_code == 200
        tool_id = c.json()["id"]
        try:
            r = requests.post(f"{API}/rentals", headers=_hdr(user_a["token"]),
                              json={"tool_id": tool_id, "start_date": "2026-06-01", "end_date": "2026-06-02"})
            assert r.status_code == 400
        finally:
            requests.delete(f"{API}/admin/tools/{tool_id}", headers=_hdr(admin_user["token"]))

    def test_create_rental_no_auth_401(self):
        r = requests.post(f"{API}/rentals", json={"tool_id": "tool-001", "start_date": "2026-01-01", "end_date": "2026-01-02"})
        assert r.status_code == 401


# ------------------------ User isolation ------------------------
class TestUserIsolation:
    def test_user_a_only_sees_own_rentals(self, user_a, user_b):
        tool = requests.get(f"{API}/tools").json()[0]
        # user_b creates a rental
        rb = requests.post(f"{API}/rentals", headers=_hdr(user_b["token"]),
                           json={"tool_id": tool["id"], "start_date": "2026-07-01", "end_date": "2026-07-02"})
        assert rb.status_code == 200
        rental_b_id = rb.json()["id"]
        # user_a lists rentals - should not see user_b's rental
        ra = requests.get(f"{API}/rentals", headers=_hdr(user_a["token"]))
        assert ra.status_code == 200
        ids = [x["id"] for x in ra.json()]
        assert rental_b_id not in ids

    def test_user_cannot_cancel_others_rental(self, user_a, user_b):
        tool = requests.get(f"{API}/tools").json()[0]
        rb = requests.post(f"{API}/rentals", headers=_hdr(user_b["token"]),
                           json={"tool_id": tool["id"], "start_date": "2026-08-01", "end_date": "2026-08-02"}).json()
        r = requests.post(f"{API}/rentals/{rb['id']}/cancel", headers=_hdr(user_a["token"]))
        assert r.status_code == 403

    def test_user_cannot_pay_others_rental(self, user_a, user_b, admin_user):
        tool = requests.get(f"{API}/tools").json()[0]
        rb = requests.post(f"{API}/rentals", headers=_hdr(user_b["token"]),
                           json={"tool_id": tool["id"], "start_date": "2026-09-01", "end_date": "2026-09-02"}).json()
        # Approve it (still user A cannot pay)
        requests.patch(f"{API}/admin/rentals/{rb['id']}/approve", headers=_hdr(admin_user["token"]))
        r = requests.post(f"{API}/payments/order?rental_id={rb['id']}", headers=_hdr(user_a["token"]))
        assert r.status_code == 403


# ------------------------ Admin Tool CRUD ------------------------
class TestAdminToolCRUD:
    def test_full_crud(self, admin_user):
        r = requests.post(f"{API}/admin/tools", headers=_hdr(admin_user["token"]),
                          json={"name": "TEST_Plough", "category": "Tillage", "location": "TestCity",
                                "daily_rate": 500})
        assert r.status_code == 200
        tool = r.json()
        assert tool["id"].startswith("tool-")
        assert tool["daily_rate"] == 500
        tid = tool["id"]

        # PATCH
        p = requests.patch(f"{API}/admin/tools/{tid}", headers=_hdr(admin_user["token"]),
                           json={"daily_rate": 750, "name": "TEST_Plough_v2"})
        assert p.status_code == 200
        assert p.json()["daily_rate"] == 750
        assert p.json()["name"] == "TEST_Plough_v2"

        # Verify GET
        g = requests.get(f"{API}/tools/{tid}")
        assert g.status_code == 200
        assert g.json()["daily_rate"] == 750

        # DELETE
        d = requests.delete(f"{API}/admin/tools/{tid}", headers=_hdr(admin_user["token"]))
        assert d.status_code == 200
        # verify gone
        g2 = requests.get(f"{API}/tools/{tid}")
        assert g2.status_code == 404

    def test_delete_tool_with_active_rentals_400(self, admin_user, user_a):
        # Create tool
        t = requests.post(f"{API}/admin/tools", headers=_hdr(admin_user["token"]),
                          json={"name": "TEST_ActiveTool", "category": "X", "location": "Y", "daily_rate": 200}).json()
        # Create rental for it
        rr = requests.post(f"{API}/rentals", headers=_hdr(user_a["token"]),
                           json={"tool_id": t["id"], "start_date": "2026-10-01", "end_date": "2026-10-02"})
        assert rr.status_code == 200
        rental_id = rr.json()["id"]
        # Try delete
        d = requests.delete(f"{API}/admin/tools/{t['id']}", headers=_hdr(admin_user["token"]))
        assert d.status_code == 400
        # Cleanup: cancel rental then delete
        requests.post(f"{API}/rentals/{rental_id}/cancel", headers=_hdr(user_a["token"]))
        requests.delete(f"{API}/admin/tools/{t['id']}", headers=_hdr(admin_user["token"]))


# ------------------------ Admin approve rental ------------------------
class TestAdminApprove:
    def test_approve_flips_requested_to_approved(self, admin_user, user_a):
        tool = requests.get(f"{API}/tools").json()[0]
        rr = requests.post(f"{API}/rentals", headers=_hdr(user_a["token"]),
                           json={"tool_id": tool["id"], "start_date": "2026-11-01", "end_date": "2026-11-02"}).json()
        assert rr["status"] == "Requested"
        a = requests.patch(f"{API}/admin/rentals/{rr['id']}/approve", headers=_hdr(admin_user["token"]))
        assert a.status_code == 200
        assert a.json()["status"] == "Approved"


# ------------------------ Admin block user ------------------------
class TestAdminBlockUser:
    def test_block_user_then_denied(self, admin_user):
        uid, tok = _bootstrap_user(f"TEST_blocktarget_{uuid.uuid4().hex[:6]}@example.com", "USER")
        try:
            # Confirm access first
            r = requests.get(f"{API}/auth/me", headers=_hdr(tok))
            assert r.status_code == 200
            # Admin blocks
            b = requests.patch(f"{API}/admin/users/{uid}/block", headers=_hdr(admin_user["token"]),
                               json={"blocked": True})
            assert b.status_code == 200
            assert b.json()["blocked"] is True
            # Note: block wipes sessions, so this token no longer exists → 401
            # Recreate a session directly in DB to test that a fresh session is also denied
            new_tok = f"testtok_after_{uuid.uuid4().hex}"
            _mongo_eval(f"""
            use('test_database');
            db.user_sessions.insertOne({{
              user_id: '{uid}', session_token: '{new_tok}',
              expires_at: new Date(Date.now()+7*24*60*60*1000), created_at: new Date()
            }});
            """)
            r2 = requests.get(f"{API}/auth/me", headers=_hdr(new_tok))
            assert r2.status_code == 403
            r3 = requests.get(f"{API}/rentals", headers=_hdr(new_tok))
            assert r3.status_code == 403
        finally:
            _cleanup_user(uid)
