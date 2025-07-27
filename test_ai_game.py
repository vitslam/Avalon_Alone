#!/usr/bin/env python3
"""
AI自动游戏测试脚本
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.game import AvalonGame
from backend.player import AIPlayer, God
from backend.ai_controller import AIController

async def test_ai_auto_game():
    """测试AI自动游戏"""
    print("=== 开始AI自动游戏测试 ===")
    
    # 创建全AI玩家
    players = [
        AIPlayer("Doubao", "gpt-3.5"),
        AIPlayer("GPT", "gpt-4"),
        AIPlayer("Gemini", "claude"),
        AIPlayer("Claude", "gpt-3.5"),
        AIPlayer("Qwen", "gpt-4"),
        AIPlayer("GLM", "claude")
    ]
    
    # 创建上帝和游戏实例
    god = God()
    game = AvalonGame(players, god)
    
    # 创建AI控制器
    ai_controller = AIController(game)
    
    print(f"创建了 {len(players)} 个AI玩家")
    print("开始游戏...")
    
    # 开始游戏
    result = game.start_game()
    print("游戏开始成功！")
    
    # 显示游戏状态
    print(f"游戏状态: {game.state}")
    print(f"游戏阶段: {game.phase}")
    
    # 显示角色分配
    print("\n角色分配:")
    for player in players:
        role_info = player.get_role_info()
        print(f"  {player.name}: {role_info.get('name', '未知')} ({role_info.get('team', '未知')})")
    
    # 启动AI自动游戏
    print("\n启动AI自动游戏...")
    print(f"游戏状态检查: state='{game.state}', is_running={ai_controller.is_running}")
    
    await ai_controller.start_auto_play()
    
    # 显示最终结果
    print("\n=== 游戏结束 ===")
    final_state = game.get_game_state()
    print(f"游戏状态: {final_state['state']}")
    print(f"获胜方: {final_state.get('winner', '未知')}")
    
    if final_state.get('mission_results'):
        print("\n任务结果:")
        for result in final_state['mission_results']:
            status = "成功" if result['success'] else "失败"
            print(f"  任务 {result['mission']}: {status}")

async def test_ai_controller():
    """测试AI控制器功能"""
    print("\n=== 测试AI控制器功能 ===")
    
    # 创建测试游戏
    players = [
        AIPlayer("AI1", "gpt-3.5"),
        AIPlayer("AI2", "gpt-4"),
        AIPlayer("AI3", "claude"),
        AIPlayer("AI4", "gpt-3.5"),
        AIPlayer("AI5", "gpt-4")
    ]
    
    god = God()
    game = AvalonGame(players, god)
    ai_controller = AIController(game)
    
    # 测试AI状态
    status = ai_controller.get_ai_status()
    print(f"AI控制器状态: {status}")
    
    # 测试队伍选择策略
    print("\n测试队伍选择策略:")
    game.start_game()
    current_leader = game.players[game.current_leader_index]
    available_players = game.get_available_players()
    mission_config = game.get_mission_config()
    
    print(f"当前队长: {current_leader.name} ({current_leader.role})")
    print(f"可用玩家: {available_players}")
    print(f"任务配置: {mission_config}")
    
    # 测试AI选择队伍
    selected_team = ai_controller.ai_select_team(current_leader, available_players, mission_config['team_size'])
    print(f"AI选择的队伍: {selected_team}")
    
    # 测试投票决策
    print("\n测试投票决策:")
    for player in players:
        team_vote = ai_controller.ai_decide_team_vote(player)
        mission_vote = ai_controller.ai_decide_mission_vote(player)
        print(f"  {player.name} ({player.role}): 队伍投票={team_vote}, 任务投票={mission_vote}")

async def main():
    """主函数"""
    print("开始AI自动游戏测试...\n")
    
    try:
        # 测试AI控制器功能
        await test_ai_controller()
        
        # 测试完整AI游戏
        await test_ai_auto_game()
        
        print("\n=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 