import asyncio
import json
import sys
import websockets

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

async def verify_connection():
    uri = "ws://127.0.0.1:8000/ws/mentor/test-verification-session"
    print(f"Connecting to {uri}...")
    async with websockets.connect(uri) as ws:
        msg = await ws.recv()
        data = json.loads(msg)
        print("Received Server Message:", data)
        assert data.get("type") == "connected"
        print("[SUCCESS] WebSocket connection and immediate greeting verified successfully!")

if __name__ == "__main__":
    asyncio.run(verify_connection())
