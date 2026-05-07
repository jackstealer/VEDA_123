"""
VEDA — End-to-End Test
Tests the full audit workflow with a real public GitHub repo.

Usage:
    python tests/test_e2e.py

Make sure the VEDA API is running first:
    uvicorn api.main:app --port 8080 --reload
"""

import time
import httpx
import websockets
import asyncio
import json

BASE_URL = "http://localhost:8080"
WS_URL   = "ws://localhost:8080"

# ── Test with a real public GitHub repo ──────────────────────────────────────
TEST_PAYLOAD = {
    "company_name":    "FastAPI Framework",
    "github_repo_url": "https://github.com/tiangolo/fastapi",
    "industry":        "saas",
    "description":     "Modern web framework for building APIs with Python",
    "schedule_kickoff_meeting": False,
    "attendee_email":  "",
}


def test_health():
    print("\n── Test 1: Health Check ──")
    resp = httpx.get(f"{BASE_URL}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    print(f"  ✅ Health: {data['service']}")


def test_start_audit():
    print("\n── Test 2: Start Audit ──")
    resp = httpx.post(f"{BASE_URL}/audit", json=TEST_PAYLOAD, timeout=30)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "PENDING"
    print(f"  ✅ Audit started: job_id = {data['job_id']}")
    print(f"  ✅ WebSocket URL: {data['websocket_url']}")
    return data["job_id"]


async def test_websocket(job_id: str):
    print(f"\n── Test 3: WebSocket Live Progress ──")
    uri = f"{WS_URL}/ws/{job_id}"
    print(f"  Connecting to {uri}")

    try:
        async with websockets.connect(uri) as ws:
            print("  ✅ WebSocket connected")
            events_received = 0
            start = time.time()

            while True:
                try:
                    # Wait up to 3 mins for the full audit
                    message = await asyncio.wait_for(ws.recv(), timeout=180)
                    event = json.loads(message)
                    events_received += 1

                    status = event.get("status")
                    agent  = event.get("agent")
                    msg    = event.get("message")
                    pct    = event.get("progress_pct", 0)

                    print(f"  [{pct:3d}%] {agent}: {msg}")

                    if status in ("COMPLETED", "FAILED"):
                        elapsed = round(time.time() - start, 1)
                        print(f"\n  ✅ Audit finished in {elapsed}s")
                        print(f"  ✅ Events received: {events_received}")
                        if status == "COMPLETED":
                            data = event.get("data", {})
                            print(f"  📊 Risk Score:    {data.get('overall_risk_score')}")
                            print(f"  📋 Recommendation: {data.get('recommendation')}")
                            print(f"  ⭐ Rating:        {data.get('overall_rating')}")
                            print(f"  💬 Verdict:       {data.get('one_line_verdict')}")
                        break

                except asyncio.TimeoutError:
                    print("  ⚠️  Timeout waiting for events")
                    break

    except Exception as e:
        print(f"  ⚠️  WebSocket error: {e}")


def test_poll_status(job_id: str):
    print(f"\n── Test 4: Poll Status ──")
    resp = httpx.get(f"{BASE_URL}/status/{job_id}", timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    print(f"  ✅ Status: {data['status']}")
    print(f"  ✅ Message: {data['message']}")
    return data["status"]


def test_get_report(job_id: str):
    print(f"\n── Test 5: Get Report ──")
    # Poll until completed (max 5 mins)
    for i in range(60):
        status = test_poll_status(job_id)
        if status == "COMPLETED":
            resp = httpx.get(f"{BASE_URL}/report/{job_id}", timeout=10)
            assert resp.status_code == 200
            report = resp.json()
            print(f"  ✅ Report retrieved!")
            print(f"  📊 Overall Risk Score:  {report.get('overall_risk_score')}")
            print(f"  🏢 Company:             {report.get('company_name')}")
            exec_s = report.get("executive_summary", {})
            print(f"  📋 Recommendation:      {exec_s.get('recommendation')}")
            print(f"  ⭐ Rating:              {exec_s.get('overall_rating')}")
            print(f"  💬 Verdict:             {exec_s.get('one_line_verdict')}")
            return report
        elif status == "FAILED":
            print(f"  ❌ Audit failed!")
            return None
        print(f"  ⏳ Waiting... ({i+1}/60)")
        time.sleep(5)

    print("  ⚠️  Timed out waiting for completion")
    return None


def test_list_jobs():
    print(f"\n── Test 6: List Jobs ──")
    resp = httpx.get(f"{BASE_URL}/jobs", timeout=10)
    assert resp.status_code == 200
    jobs = resp.json()
    print(f"  ✅ Jobs in database: {len(jobs)}")
    for j in jobs[:3]:
        print(f"     - {j.get('company_name')} [{j.get('status')}]")


# ── Run all tests ─────────────────────────────────────────────────────────────

async def main():
    print("🔷 VEDA — End-to-End Test Suite")
    print(f"   API: {BASE_URL}\n")

    try:
        # Test 1: Health
        test_health()

        # Test 2: Start audit
        job_id = test_start_audit()

        # Test 3: WebSocket (runs while audit is processing)
        await test_websocket(job_id)

        # Test 4 & 5: Status + Report
        test_get_report(job_id)

        # Test 6: List jobs
        test_list_jobs()

        print("\n✅ All tests passed! VEDA is working end-to-end.\n")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except httpx.ConnectError:
        print(f"\n❌ Cannot connect to {BASE_URL}")
        print("   Make sure VEDA API is running:")
        print("   uvicorn api.main:app --port 8080 --reload")


if __name__ == "__main__":
    asyncio.run(main())