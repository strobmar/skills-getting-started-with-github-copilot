import asyncio
import copy

import pytest
from httpx import ASGITransport, AsyncClient

from src import app as app_module


BASE_ACTIVITIES = copy.deepcopy(app_module.activities)


@pytest.fixture(autouse=True)
def reset_activities():
    app_module.activities = copy.deepcopy(BASE_ACTIVITIES)


def send_request(method: str, path: str, **kwargs):
    async def _request():
        transport = ASGITransport(app=app_module.app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            request = getattr(client, method.lower())
            return await request(path, **kwargs)

    return asyncio.run(_request())


def test_get_activities_returns_seed_data():
    response = send_request("GET", "/activities")

    assert response.status_code == 200
    data = response.json()
    assert "Chess Club" in data
    assert data["Chess Club"]["participants"][0] == "michael@mergington.edu"


def test_signup_adds_participant():
    activity_name = "Chess Club"
    email = "new.student@mergington.edu"

    response = send_request(
        "POST",
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )

    assert response.status_code == 200
    assert response.json()["message"] == f"Signed up {email} for {activity_name}"

    activities_response = send_request("GET", "/activities")
    assert email in activities_response.json()[activity_name]["participants"]


def test_duplicate_signup_is_rejected():
    activity_name = "Chess Club"
    email = "michael@mergington.edu"

    response = send_request(
        "POST",
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"


def test_unregister_participant_removes_from_activity():
    activity_name = "Chess Club"
    email = "new.student@mergington.edu"

    signup_response = send_request(
        "POST",
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )
    assert signup_response.status_code == 200

    delete_response = send_request(
        "DELETE",
        f"/activities/{activity_name}/participants",
        params={"email": email},
    )
    assert delete_response.status_code == 200

    activities_response = send_request("GET", "/activities")
    assert activities_response.status_code == 200

    activity = activities_response.json()[activity_name]
    assert email not in activity["participants"]
