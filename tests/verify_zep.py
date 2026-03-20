import asyncio
import uuid
import os
import sys

# Add backend to path so we can import engine
sys.path.append(os.path.join(os.getcwd(), "backend"))

from engine.agent import add_agent_memory, get_agent_memory, zep_client


async def test_persistence():
    if not zep_client:
        print("❌ Zep Client not initialized. Check your ZEP_API_KEY.")
        return

    test_id = f"test_persona_{uuid.uuid4().hex[:8]}"
    test_user_msg = "Hello, I am testing Zep persistence."
    test_assistant_msg = "Confirmed. I will remember this."

    print(f"🚀 Testing with Session ID: {test_id}")

    # 1. Add Memory
    print("📥 Adding memory...")
    await add_agent_memory(test_id, test_user_msg, test_assistant_msg)

    # Give Zep a second to index
    await asyncio.sleep(2)

    # 2. Fetch Memory
    print("📤 Fetching memory...")
    history = await get_agent_memory(test_id)

    print(f"DEBUG: Retrieved History: {history}")

    if test_assistant_msg in history:
        print("✅ SUCCESS: Memory persisted and retrieved!")
    else:
        print("❌ FAILURE: Memory not found in retrieval.")


if __name__ == "__main__":
    asyncio.run(test_persistence())
