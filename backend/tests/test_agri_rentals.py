import os
import uuid

import requests


BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def test_tools_seed_and_filters():
    response = requests.get(f"{BASE_URL}/api/tools", timeout=15)
    assert response.status_code == 200
    tools = response.json()
    assert len(tools) >= 4
    assert all("id" in tool and "hourly_rate" in tool and "daily_rate" in tool for tool in tools)
    filtered = requests.get(f"{BASE_URL}/api/tools", params={"category": "Tractors", "available": "true"}, timeout=15)
    assert filtered.status_code == 200
    assert all(tool["category"] == "Tractors" and tool["available"] for tool in filtered.json())


def test_rental_create_and_history():
    tool_response = requests.get(f"{BASE_URL}/api/tools", timeout=15)
    tool = next(tool for tool in tool_response.json() if tool["available"])
    payload = {"tool_id": tool["id"], "renter_name": f"TEST_{uuid.uuid4().hex}", "duration": 2, "unit": "hour"}
    created = requests.post(f"{BASE_URL}/api/rentals", json=payload, timeout=15)
    assert created.status_code == 200
    rental = created.json()
    assert rental["tool_id"] == tool["id"]
    assert rental["total"] == tool["hourly_rate"] * 2
    history = requests.get(f"{BASE_URL}/api/rentals", timeout=15)
    assert history.status_code == 200
    assert any(item["id"] == rental["id"] for item in history.json())


def test_rental_rejects_unavailable_tool():
    tools = requests.get(f"{BASE_URL}/api/tools", timeout=15).json()
    unavailable = next(tool for tool in tools if not tool["available"])
    response = requests.post(f"{BASE_URL}/api/rentals", json={"tool_id": unavailable["id"]}, timeout=15)
    assert response.status_code == 400
    assert "unavailable" in response.json()["detail"].lower()