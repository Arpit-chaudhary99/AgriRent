import os
import uuid

import pytest
import requests


BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def test_approval_payment_order_and_signature_guards():
    tools = requests.get(f"{BASE_URL}/api/tools", timeout=15).json()
    tool = next(item for item in tools if item["available"])
    created = requests.post(
        f"{BASE_URL}/api/rentals",
        json={"tool_id": tool["id"], "renter_name": f"TEST_{uuid.uuid4().hex}", "duration": 1, "unit": "day"},
        timeout=15,
    )
    assert created.status_code == 200
    rental = created.json()
    assert rental["status"] == "Requested"
    assert rental["payment_status"] == "unpaid"

    blocked = requests.post(f"{BASE_URL}/api/payments/order", params={"rental_id": rental["id"]}, timeout=15)
    assert blocked.status_code == 400
    assert "approved" in blocked.json()["detail"].lower()

    approved = requests.patch(f"{BASE_URL}/api/rentals/{rental['id']}/approve", timeout=15)
    assert approved.status_code == 200
    assert approved.json()["status"] == "Approved"

    order = requests.post(f"{BASE_URL}/api/payments/order", params={"rental_id": rental["id"]}, timeout=30)
    if order.status_code == 200:
        order_data = order.json()
        assert order_data["amount"] == int(tool["daily_rate"] * 100)
        assert order_data["currency"] == "INR"
        assert order_data["key_id"]
        assert "secret" not in order_data
        mismatch = requests.post(
            f"{BASE_URL}/api/payments/verify",
            json={
                "rental_id": rental["id"],
                "razorpay_payment_id": "pay_TEST_invalid",
                "razorpay_order_id": "order_TEST_wrong",
                "razorpay_signature": "invalid",
            },
            timeout=15,
        )
        assert mismatch.status_code == 400
        assert "match" in mismatch.json()["detail"].lower()
    else:
        pytest.fail(f"Configured Razorpay test order creation failed: {order.status_code} {order.text}")