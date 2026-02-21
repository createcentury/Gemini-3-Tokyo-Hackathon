#!/usr/bin/env python3
"""
Final comprehensive test for agent movement
"""
import requests
import time

BASE_URL = "http://localhost:8766"

def main():
    print("=" * 60)
    print("Tokyo Risk - 最終移動テスト")
    print("=" * 60)

    # 1. Start game
    print("\n1. ゲーム開始...")
    response = requests.post(
        f"{BASE_URL}/game/start",
        json={"player_prompts": ["テスト"] * 10}
    )

    if response.status_code != 200:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)
        return

    data = response.json()
    session_id = data["session_id"]
    print(f"✅ Session: {session_id}")

    # 2. Wait for AI loop to start
    print("\n2. AIループ起動待機 (3秒)...")
    time.sleep(3)

    # 3. Get initial positions
    print("\n3. 初期位置取得...")
    response = requests.get(f"{BASE_URL}/game/agents/{session_id}")
    if response.status_code != 200:
        print(f"❌ Failed to get agents: {response.status_code}")
        return

    initial = response.json()["agents"]
    print(f"✅ {len(initial)} agents found")

    sample_ids = ['player_001', 'player_004', 'ai_001', 'ai_004']
    print("\n初期位置:")
    for aid in sample_ids:
        agent = initial[aid]
        print(f"  {aid}: ({agent['lat']:.6f}, {agent['lng']:.6f}) - {agent['state']}")

    # 4. Wait for agents to get destinations and move
    print("\n4. 移動待機 (20秒)...")
    time.sleep(20)

    # 5. Get final positions
    print("\n5. 最終位置取得...")
    response = requests.get(f"{BASE_URL}/game/agents/{session_id}")
    if response.status_code != 200:
        print(f"❌ Failed to get agents: {response.status_code}")
        return

    final = response.json()["agents"]

    print("\n最終位置:")
    for aid in sample_ids:
        agent = final[aid]
        print(f"  {aid}: ({agent['lat']:.6f}, {agent['lng']:.6f}) - {agent['state']}")

    # 6. Calculate movement
    print("\n6. 移動距離計算:")
    total_moved = 0
    for aid in sample_ids:
        lat_diff = final[aid]['lat'] - initial[aid]['lat']
        lng_diff = final[aid]['lng'] - initial[aid]['lng']
        dist = (lat_diff**2 + lng_diff**2)**0.5

        if dist > 0.0001:
            total_moved += 1
            print(f"  {aid}: {dist:.6f} ✅ 移動")
        else:
            print(f"  {aid}: {dist:.6f} ❌ 停止")

    # 7. Overall status
    print("\n7. 全体状態:")
    moving_count = sum(1 for a in final.values() if a['state'] == 'moving')
    print(f"  Moving状態: {moving_count}/20")

    if total_moved >= 2:
        print("\n✅ SUCCESS: エージェントは動いています！")
    else:
        print("\n❌ FAIL: エージェントが十分に動いていません")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
