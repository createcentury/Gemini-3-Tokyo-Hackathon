#!/usr/bin/env python3
"""
Test script for the multi-agent system
"""
import requests
import time

BASE_URL = "http://localhost:8766"

def test_game_start():
    """Test starting a game with custom prompts"""
    print("🧪 Testing game start with agent prompts...")

    prompts = [
        "あなたは偵察兵です。敵の動きを観察してください。",
        "あなたは攻撃兵です。積極的に敵陣に進軍してください。",
        "あなたは防御兵です。味方の領地を守ってください。",
    ] * 4  # 12 prompts, only first 10 will be used

    response = requests.post(
        f"{BASE_URL}/game/start",
        json={"player_prompts": prompts[:10]}
    )

    if response.status_code != 200:
        print(f"❌ Failed to start game: {response.status_code}")
        print(response.text)
        return None

    data = response.json()
    session_id = data.get("session_id")
    print(f"✅ Game started! Session ID: {session_id}")
    print(f"   Player start: {data.get('player_start')}")
    print(f"   AI start: {data.get('ai_start')}")

    return session_id


def test_agent_state(session_id):
    """Test getting agent states"""
    print("\n🧪 Testing agent state retrieval...")

    response = requests.get(f"{BASE_URL}/game/agents/{session_id}")

    if response.status_code != 200:
        print(f"❌ Failed to get agents: {response.status_code}")
        return

    data = response.json()
    agents = data.get("agents", {})

    print(f"✅ Got {len(agents)} agents:")
    for agent_id, agent in list(agents.items())[:3]:  # Show first 3
        print(f"   {agent_id}:")
        print(f"     Position: ({agent['lat']:.4f}, {agent['lng']:.4f})")
        print(f"     State: {agent['state']}")
        print(f"     Target: {agent.get('target_ward', 'None')}")


def test_agent_movement(session_id):
    """Test agent movement over time"""
    print("\n🧪 Testing agent movement (10 seconds)...")

    # Get initial positions
    response = requests.get(f"{BASE_URL}/game/agents/{session_id}")
    initial = response.json()["agents"]

    print("⏳ Waiting 10 seconds...")
    time.sleep(10)

    # Get final positions
    response = requests.get(f"{BASE_URL}/game/agents/{session_id}")
    final = response.json()["agents"]

    # Compare positions
    moved_count = 0
    for agent_id in initial.keys():
        init_pos = (initial[agent_id]["lat"], initial[agent_id]["lng"])
        final_pos = (final[agent_id]["lat"], final[agent_id]["lng"])

        if init_pos != final_pos:
            moved_count += 1
            distance = ((init_pos[0] - final_pos[0])**2 +
                       (init_pos[1] - final_pos[1])**2)**0.5
            print(f"   {agent_id} moved {distance:.6f} degrees")

    print(f"✅ {moved_count}/{len(initial)} agents moved")


def main():
    print("=" * 60)
    print("Tokyo Risk - Multi-Agent System Test")
    print("=" * 60)

    # Test 1: Start game
    session_id = test_game_start()
    if not session_id:
        return

    # Test 2: Get agent states
    test_agent_state(session_id)

    # Test 3: Check movement
    test_agent_movement(session_id)

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
    print(f"\nView the game at: {BASE_URL}")


if __name__ == "__main__":
    main()
