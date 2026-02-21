#!/usr/bin/env python3
"""
エージェントの動作確認スクリプト
ブラウザで http://localhost:8766 を開いてゲームを開始した後に実行してください
"""
import requests
import time

def main():
    print("=" * 60)
    print("Tokyo Risk - エージェント動作確認")
    print("=" * 60)

    # セッションIDを入力
    print("\nブラウザでゲームを開始してください")
    print("http://localhost:8766")
    print("\nゲーム開始後、ブラウザのコンソール (F12) で以下を実行:")
    print("  console.log(sessionId)")
    print()

    session_id = input("Session ID を入力してください: ").strip()

    if not session_id:
        print("❌ Session ID が入力されませんでした")
        return

    print(f"\nSession: {session_id}")
    print("=" * 60)

    try:
        # 初期位置を取得
        response = requests.get(f"http://localhost:8766/game/agents/{session_id}")
        if response.status_code != 200:
            print(f"❌ エラー: {response.status_code}")
            print(response.text)
            return

        initial = response.json()["agents"]

        print(f"\n✅ エージェント数: {len(initial)}")
        print("\n📍 初期位置（サンプル4体）:")
        for aid in ['player_001', 'player_004', 'ai_001', 'ai_004']:
            a = initial[aid]
            print(f"  {aid}: ({a['lat']:.6f}, {a['lng']:.6f}) - {a['state']}")
            if a.get('destination'):
                dest = a['destination']
                print(f"    → 目的地: {dest.get('ward', 'Unknown')}")

        # 移動状態をカウント
        moving_count = sum(1 for a in initial.values() if a['state'] == 'moving')
        print("\n📊 状態:")
        print(f"  Moving: {moving_count}/20")
        print(f"  Idle: {20-moving_count}/20")

        # 10秒待機
        print("\n⏳ 10秒間の移動を観察中...")
        for i in range(10, 0, -1):
            print(f"  {i}秒...", end='\r', flush=True)
            time.sleep(1)
        print()

        # 最終位置を取得
        response = requests.get(f"http://localhost:8766/game/agents/{session_id}")
        final = response.json()["agents"]

        print("\n📍 最終位置:")
        total_distance = 0
        for aid in ['player_001', 'player_004', 'ai_001', 'ai_004']:
            i_agent = initial[aid]
            f_agent = final[aid]

            distance = ((f_agent['lat'] - i_agent['lat'])**2 +
                       (f_agent['lng'] - i_agent['lng'])**2)**0.5
            total_distance += distance

            distance_km = distance * 111  # 緯度1度 ≈ 111km

            print(f"  {aid}: ({f_agent['lat']:.6f}, {f_agent['lng']:.6f})")
            print(f"    移動距離: {distance:.6f}度 ({distance_km:.2f}km)")

        avg_distance = total_distance / 4
        avg_km = avg_distance * 111

        print("\n📊 結果:")
        print(f"  平均移動距離: {avg_distance:.6f}度 ({avg_km:.2f}km)")
        print(f"  平均速度: {avg_km/10:.3f}km/s ({avg_km/10*3.6:.1f}km/h)")

        if avg_distance > 0.001:
            print("\n✅ エージェントは正常に動いています！")
            print("   地図上で視覚的に確認できる速度です。")
        elif avg_distance > 0.0001:
            print("\n⚠️ エージェントは動いていますが、遅すぎます")
            print("   game_engine.py の Agent.speed を増やしてください")
        else:
            print("\n❌ エージェントがほとんど動いていません")
            print("   サーバーログを確認してください: tail -f server_agent.log")

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
