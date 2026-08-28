import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.chat import session_store

client = TestClient(app)


def test_studio_rest_endpoint():
    print("\n--- Testing Studio REST Endpoint: POST /api/v1/studio/generate ---")
    response = client.post(
        "/api/v1/studio/generate",
        json={"topic": "Rotational Dynamics", "proficiency_level": "JEE Advanced"}
    )
    print("Status code:", response.status_code)
    print("Response JSON:", response.json())
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "Formula sheet generated" in response.json()["artifact"]
    print("✅ Studio REST endpoint test passed!")


def test_mentor_websocket_progression():
    print("\n--- Testing Mentor WebSocket: /ws/mentor/{session_id} ---")
    session_id = "test-session-123"

    with client.websocket_connect(f"/ws/mentor/{session_id}") as ws:
        # 1. Connection confirmation
        initial_msg = ws.receive_json()
        print("1. Received:", initial_msg)
        assert initial_msg["type"] == "connected"

        # 2. Send initial doubt
        doubt_text = "A solid sphere rolls without slipping down an inclined plane. Find acceleration."
        ws.send_text(doubt_text)
        tier1_resp = ws.receive_json()
        print("2. Received after doubt submission (Tier 1):", tier1_resp)
        assert tier1_resp["type"] == "hint_update"
        assert tier1_resp["hint_level"] == 1
        assert "Tier 1" in tier1_resp["tier_name"]
        assert session_store[session_id]["current_hint_level"] == 1
        # Check that master solution was not leaked in response
        assert "master_solution" not in tier1_resp
        print("   -> Tier 1 Conceptual Nudge received. Master solution safely cached.")

        # 3. Request next hint (Tier 2)
        ws.send_text("I need more help")
        tier2_resp = ws.receive_json()
        print("3. Received on 'I need more help' (Tier 2):", tier2_resp)
        assert tier2_resp["hint_level"] == 2
        assert session_store[session_id]["current_hint_level"] == 2
        print("   -> Tier 2 Structural Strategy received.")

        # 4. Request next hint (Tier 3)
        ws.send_text("next hint")
        tier3_resp = ws.receive_json()
        print("4. Received on 'next hint' (Tier 3):", tier3_resp)
        assert tier3_resp["hint_level"] == 3
        assert session_store[session_id]["current_hint_level"] == 3
        print("   -> Tier 3 Detailed Walkthrough received.")

        # 5. Request next hint (Master Solution)
        ws.send_text("next hint")
        solution_resp = ws.receive_json()
        print("5. Received on final request (Master Solution):", solution_resp)
        assert solution_resp["type"] == "master_solution"
        assert solution_resp["hint_level"] == 4
        assert session_store[session_id]["current_hint_level"] == 4
        print("   -> Master Solution revealed upon Level 3 completion.")

    print("✅ WebSocket Progressive Hint flow test passed with full isolation!")


if __name__ == "__main__":
    test_studio_rest_endpoint()
    test_mentor_websocket_progression()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
