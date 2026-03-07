#!/usr/bin/env python
"""
WebSocket Chat Test Script
===========================
Simulates two users connecting to the same chatroom and exchanging messages.

Requirements:
    pip install websockets httpx

Usage:
    python scripts/test_chat_ws.py

Configure the variables below or set environment variables:
    CHAT_API_URL, USER1_EMAIL, USER1_PASSWORD, USER2_EMAIL, USER2_PASSWORD, CHATROOM_ID
"""

import asyncio
import json
import os
import sys

try:
    import httpx
    import websockets
except ImportError:
    print("Install dependencies first:\n  pip install websockets httpx")
    sys.exit(1)

# ── Configuration ──────────────────────────────────────────────────────
API_URL = os.getenv("CHAT_API_URL", "http://localhost:8000")
WS_URL = API_URL.replace("http://", "ws://").replace("https://", "wss://")

USER1_EMAIL = os.getenv("USER1_EMAIL", "user1@example.com")
USER1_PASSWORD = os.getenv("USER1_PASSWORD", "password123")
USER2_EMAIL = os.getenv("USER2_EMAIL", "user2@example.com")
USER2_PASSWORD = os.getenv("USER2_PASSWORD", "password123")
CHATROOM_ID = os.getenv("CHATROOM_ID", "")  # Required — set this


# ── Helpers ────────────────────────────────────────────────────────────
def login(email: str, password: str) -> str:
    """Login and return JWT access token."""
    with httpx.Client() as client:
        res = client.post(
            f"{API_URL}/api/v1/auth/login/",
            json={"email": email, "password": password},
        )
        res.raise_for_status()
        data = res.json()
        token = data["data"]["tokens"]["access"]
        print(f"  ✓ Logged in as {email} (token: {token[:20]}...)")
        return token


async def chat_client(label: str, token: str, chatroom_id: str, messages_to_send: list[str], delay: float = 1.0):
    """Connect to chatroom, send messages, and print received messages."""
    url = f"{WS_URL}/ws/chat/{chatroom_id}/?token={token}"
    print(f"[{label}] Connecting to {url}")

    async with websockets.connect(url) as ws:
        print(f"[{label}] ✓ Connected")

        async def receiver():
            try:
                async for raw in ws:
                    msg = json.loads(raw)
                    if "error" in msg:
                        print(f"[{label}] ✗ Error: {msg['error']}")
                    else:
                        sender_name = msg.get("sender", {}).get("full_name", "Unknown")
                        text = msg.get("text", "[file]")
                        print(f"[{label}] ← {sender_name}: {text}")
            except websockets.ConnectionClosed as e:
                print(f"[{label}] Connection closed: {e.code} {e.reason}")

        async def sender():
            for text in messages_to_send:
                await asyncio.sleep(delay)
                payload = json.dumps({"message_type": "text", "text": text})
                await ws.send(payload)
                print(f"[{label}] → Sent: {text}")
            # Keep alive for a bit to receive replies
            await asyncio.sleep(delay * 3)
            await ws.close()

        await asyncio.gather(receiver(), sender())


# ── Main ───────────────────────────────────────────────────────────────
async def main():
    if not CHATROOM_ID:
        print("ERROR: Set CHATROOM_ID env var or edit it in the script.")
        print("\nTo find a chatroom ID:")
        print(f"  curl {API_URL}/api/v1/chatrooms/ -H 'Authorization: Bearer <token>'")
        sys.exit(1)

    print("=" * 60)
    print("Chat WebSocket Test")
    print("=" * 60)

    # Step 1: Login both users
    print("\n1. Logging in users...")
    token1 = login(USER1_EMAIL, USER1_PASSWORD)
    token2 = login(USER2_EMAIL, USER2_PASSWORD)

    # Step 2: List chatrooms for user 1
    print(f"\n2. Listing chatrooms for {USER1_EMAIL}...")
    with httpx.Client() as client:
        res = client.get(
            f"{API_URL}/api/v1/chatrooms/",
            headers={"Authorization": f"Bearer {token1}"},
        )
        if res.status_code == 200:
            rooms = res.json()["data"].get("results", [])
            print(f"  Found {len(rooms)} chatroom(s)")
            for r in rooms[:5]:
                print(f"    - {r['id']} (active={r.get('is_active', '?')})")
        else:
            print(f"  ✗ Failed to list: {res.status_code}")

    # Step 3: Connect and chat
    print(f"\n3. Starting WebSocket chat in room {CHATROOM_ID}...")
    print("-" * 60)

    user1_msgs = [
        "Hey! This is User 1 speaking.",
        "How are you doing?",
        "Testing message #3 from User 1",
    ]
    user2_msgs = [
        "Hello User 1! This is User 2.",
        "I'm great, thanks for asking!",
        "Looks like WebSocket chat is working!",
    ]

    await asyncio.gather(
        chat_client("User1", token1, CHATROOM_ID, user1_msgs, delay=1.5),
        chat_client("User2", token2, CHATROOM_ID, user2_msgs, delay=2.0),
    )

    print("-" * 60)
    print("✓ Test complete")


if __name__ == "__main__":
    asyncio.run(main())
