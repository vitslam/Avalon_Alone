#!/usr/bin/env python3
"""
阿瓦隆游戏测试脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.game import AvalonGame
from backend.player import Player, AIPlayer, God

def test_game_creation():
    """测试游戏创建"""
    print("=== 测试游戏创建 ===")
    
    # 创建玩家
    players = [
        Player("玩家1"),
        AIPlayer("AI1", "gpt-3.5"),
        AIPlayer("AI2", "gpt-4"),
        AIPlayer("AI3", "claude"),
        AIPlayer("AI4", "gpt-3.5"),
        AIPlayer("AI5", "gpt-3.5")
    ]
    
    # 创建上帝
    god = God()
    
    # 创建游戏
    game = AvalonGame(players, god)
    
    print(f"游戏创建成功，玩家数量: {len(players)}")
    print(f"游戏状态: {game.state}")
    print(f"当前阶段: {game.phase}")
    
    return game

def test_role_assignment(game):
    """测试角色分配"""
    print("\n=== 测试角色分配 ===")
    
    # 开始游戏
    result = game.start_game()
    
    print("角色分配结果:")
    for player in game.players:
        role_info = player.get_role_info()
        print(f"  {player.name}: {role_info.get('name', '未知')} ({role_info.get('team', '未知')})")
    
    print(f"\n游戏状态: {game.state}")
    print(f"当前阶段: {game.phase}")
    print(f"当前队长: {game.players[game.current_leader_index].name}")

def test_team_selection(game):
    """测试队伍选择"""
    print("\n=== 测试队伍选择 ===")
    
    # 获取任务配置
    mission_config = game.get_mission_config()
    print(f"当前任务: {mission_config['mission_number']}")
    print(f"队伍大小: {mission_config['team_size']}")
    print(f"需要失败票数: {mission_config['fails_needed']}")
    
    # 选择队伍
    available_players = game.get_available_players()
    selected_players = available_players[:mission_config['team_size']]
    
    result = game.select_team(selected_players)
    print(f"队伍选择结果: {result}")
    
    if 'error' not in result:
        print(f"选择的队伍: {game.current_team}")

def test_voting(game):
    """测试投票"""
    print("\n=== 测试投票 ===")
    
    # 队伍投票
    for player in game.players:
        vote = 'approve' if player.role in ['merlin', 'percival', 'loyal_servant'] else 'reject'
        result = game.vote_team(player.name, vote)
        print(f"{player.name} 队伍投票: {vote} -> {result.get('status', 'error')}")
        
        if result.get('status') == 'team_approved':
            break
    
    # 任务投票
    if game.phase == 'mission_vote':
        print("\n开始任务投票:")
        for player_name in game.current_team:
            player = next(p for p in game.players if p.name == player_name)
            vote = 'success' if player.role in ['merlin', 'percival', 'loyal_servant'] else 'fail'
            result = game.vote_mission(player_name, vote)
            print(f"{player_name} 任务投票: {vote} -> {result.get('status', 'error')}")

def test_game_state(game):
    """测试游戏状态"""
    print("\n=== 测试游戏状态 ===")
    
    state = game.get_game_state()
    print("游戏状态:")
    for key, value in state.items():
        if key != 'mission_results':
            print(f"  {key}: {value}")
    
    print("\n任务结果:")
    for result in state.get('mission_results', []):
        print(f"  任务 {result['mission']}: {'成功' if result['success'] else '失败'}")

def main():
    """主测试函数"""
    print("开始阿瓦隆游戏测试...\n")
    
    try:
        # 测试游戏创建
        game = test_game_creation()
        
        # 测试角色分配
        test_role_assignment(game)
        
        # 测试队伍选择
        test_team_selection(game)
        
        # 测试投票
        test_voting(game)
        
        # 测试游戏状态
        test_game_state(game)
        
        print("\n=== 测试完成 ===")
        print("所有测试通过！")
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 