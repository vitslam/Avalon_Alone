import random
from typing import List, Dict, Any, Optional
from .constants import GAME_PHASES, MISSION_CONFIGS, GAME_STATES, ROLES
from .player import Player, AIPlayer, God

class AvalonGame:
    def __init__(self, players: List[Player], god: God):
        self.players = players
        self.god = god
        self.current_round = 1
        self.current_mission = 1
        self.mission_results = []
        self.state = GAME_STATES['waiting']
        self.phase = GAME_PHASES['init']
        self.current_leader_index = 0
        self.current_team = []
        self.team_votes = []
        self.mission_votes = []
        self.failed_team_votes = 0
        self.game_history = []
        
        # 根据玩家数量设置任务配置
        player_count = len(players)
        if player_count in MISSION_CONFIGS:
            self.mission_config = MISSION_CONFIGS[player_count]
        else:
            raise ValueError(f"不支持的玩家数量: {player_count}")

    def start_game(self) -> Dict[str, Any]:
        """开始游戏"""
        if len(self.players) < 5 or len(self.players) > 10:
            raise ValueError("玩家数量必须在5-10人之间")
        
        self.state = GAME_STATES['playing']
        self.phase = GAME_PHASES['role_assignment']
        
        # 分配角色
        role_assignments = self.god.assign_roles(self.players)
        
        # 发送秘密信息
        self.phase = GAME_PHASES['secret_info']
        secret_messages = {}
        for player in self.players:
            message = self.god.send_secret_info(player)
            player.receive_message(message)
            secret_messages[player.name] = message
        
        # 开始第一轮
        self.phase = GAME_PHASES['team_selection']
        self.current_leader_index = 0
        
        return {
            'status': 'started',
            'role_assignments': role_assignments,
            'secret_messages': secret_messages,
            'current_leader': self.players[self.current_leader_index].name
        }

    def select_team(self, selected_players: List[str]) -> Dict[str, Any]:
        """选择任务队伍"""
        if self.phase != GAME_PHASES['team_selection']:
            return {'error': '当前不是选择队伍阶段'}
        
        # 验证选择的玩家
        available_players = [p.name for p in self.players]
        mission_size = self.mission_config['missions'][self.current_mission - 1]
        
        if len(selected_players) != mission_size:
            return {'error': f'需要选择 {mission_size} 名玩家'}
        
        if not all(player in available_players for player in selected_players):
            return {'error': '选择的玩家不存在'}
        
        self.current_team = selected_players
        self.phase = GAME_PHASES['team_vote']
        
        return {
            'status': 'team_selected',
            'team': self.current_team,
            'next_phase': 'team_vote'
        }

    def vote_team(self, player_name: str, vote: str) -> Dict[str, Any]:
        """队伍投票"""
        if self.phase != GAME_PHASES['team_vote']:
            return {'error': '当前不是队伍投票阶段'}
        
        if vote not in ['approve', 'reject']:
            return {'error': '投票必须是 approve 或 reject'}
        
        # 记录投票
        self.team_votes.append({
            'player': player_name,
            'vote': vote
        })
        
        # 检查是否所有玩家都投票了
        if len(self.team_votes) == len(self.players):
            approve_count = sum(1 for v in self.team_votes if v['vote'] == 'approve')
            
            if approve_count > len(self.players) / 2:
                # 队伍通过，进入任务投票
                self.phase = GAME_PHASES['mission_vote']
                return {
                    'status': 'team_approved',
                    'approve_count': approve_count,
                    'next_phase': 'mission_vote'
                }
            else:
                # 队伍被拒绝
                self.failed_team_votes += 1
                self.current_leader_index = (self.current_leader_index + 1) % len(self.players)
                
                if self.failed_team_votes >= 5:
                    # 5次拒绝，坏人获胜
                    self.end_game('evil')
                    return {'status': 'evil_win', 'reason': '队伍被拒绝5次'}
                
                # 重新选择队伍
                self.phase = GAME_PHASES['team_selection']
                return {
                    'status': 'team_rejected',
                    'failed_votes': self.failed_team_votes,
                    'next_leader': self.players[self.current_leader_index].name,
                    'next_phase': 'team_selection'
                }
        
        return {'status': 'vote_recorded', 'remaining_votes': len(self.players) - len(self.team_votes)}

    def vote_mission(self, player_name: str, vote: str) -> Dict[str, Any]:
        """任务投票"""
        if self.phase != GAME_PHASES['mission_vote']:
            return {'error': '当前不是任务投票阶段'}
        
        if vote not in ['success', 'fail']:
            return {'error': '投票必须是 success 或 fail'}
        
        # 只有队伍中的玩家才能投票
        if player_name not in self.current_team:
            return {'error': '只有队伍中的玩家才能投票'}
        
        # 记录投票
        self.mission_votes.append({
            'player': player_name,
            'vote': vote
        })
        
        # 检查是否所有队伍成员都投票了
        if len(self.mission_votes) == len(self.current_team):
            fail_count = sum(1 for v in self.mission_votes if v['vote'] == 'fail')
            success_count = len(self.mission_votes) - fail_count
            
            # 判断任务成功或失败
            fails_needed = self.mission_config['fails_needed'][self.current_mission - 1]
            mission_success = fail_count < fails_needed
            
            self.mission_results.append({
                'mission': self.current_mission,
                'team': self.current_team,
                'votes': self.mission_votes,
                'success': mission_success,
                'fail_count': fail_count,
                'success_count': success_count
            })
            
            # 检查游戏是否结束
            good_wins = sum(1 for r in self.mission_results if r['success'])
            evil_wins = len(self.mission_results) - good_wins
            
            if good_wins >= 3:
                # 好人获得3次成功，进入刺杀阶段
                self.phase = GAME_PHASES['assassination']
                return {
                    'status': 'good_mission_win',
                    'mission_result': mission_success,
                    'good_wins': good_wins,
                    'evil_wins': evil_wins,
                    'next_phase': 'assassination'
                }
            elif evil_wins >= 3:
                # 坏人获得3次成功，坏人获胜
                self.end_game('evil')
                return {
                    'status': 'evil_win',
                    'mission_result': mission_success,
                    'good_wins': good_wins,
                    'evil_wins': evil_wins,
                    'reason': '坏人获得3次任务成功'
                }
            else:
                # 继续下一轮
                self.next_round()
                return {
                    'status': 'mission_completed',
                    'mission_result': mission_success,
                    'good_wins': good_wins,
                    'evil_wins': evil_wins,
                    'next_round': self.current_round,
                    'next_mission': self.current_mission
                }
        
        return {'status': 'vote_recorded', 'remaining_votes': len(self.current_team) - len(self.mission_votes)}

    def assassinate(self, target_name: str) -> Dict[str, Any]:
        """刺客刺杀"""
        if self.phase != GAME_PHASES['assassination']:
            return {'error': '当前不是刺杀阶段'}
        
        # 找到目标玩家
        target_player = None
        for player in self.players:
            if player.name == target_name:
                target_player = player
                break
        
        if not target_player:
            return {'error': '目标玩家不存在'}
        
        # 检查刺杀结果
        if target_player.role == 'merlin':
            # 刺杀梅林成功，坏人获胜
            self.end_game('evil')
            return {
                'status': 'evil_win',
                'target': target_name,
                'reason': '刺客成功刺杀梅林'
            }
        else:
            # 刺杀失败，好人获胜
            self.end_game('good')
            return {
                'status': 'good_win',
                'target': target_name,
                'reason': '刺客刺杀失败，好人获胜'
            }

    def next_round(self):
        """进入下一轮"""
        self.current_round += 1
        self.current_mission += 1
        self.current_leader_index = (self.current_leader_index + 1) % len(self.players)
        self.current_team = []
        self.team_votes = []
        self.mission_votes = []
        self.failed_team_votes = 0
        self.phase = GAME_PHASES['team_selection']

    def end_game(self, winner: str):
        """结束游戏"""
        self.state = GAME_STATES['finished']
        self.phase = GAME_PHASES['game_end']
        self.winner = winner

    def get_game_state(self) -> Dict[str, Any]:
        """返回当前游戏状态信息"""
        return {
            'state': self.state,
            'phase': self.phase,
            'current_round': self.current_round,
            'current_mission': self.current_mission,
            'mission_results': self.mission_results,
            'current_leader': self.players[self.current_leader_index].name if self.players else None,
            'current_team': self.current_team,
            'team_votes': self.team_votes,
            'mission_votes': self.mission_votes,
            'failed_team_votes': self.failed_team_votes,
            'players': [{'name': p.name, 'role': p.role, 'is_ai': p.is_ai} for p in self.players],
            'winner': getattr(self, 'winner', None)
        }

    def get_mission_config(self) -> Dict[str, Any]:
        """获取当前任务配置"""
        if self.current_mission <= len(self.mission_config['missions']):
            return {
                'mission_number': self.current_mission,
                'team_size': self.mission_config['missions'][self.current_mission - 1],
                'fails_needed': self.mission_config['fails_needed'][self.current_mission - 1]
            }
        return {}

    def get_available_players(self) -> List[str]:
        """获取可选择的玩家列表"""
        return [p.name for p in self.players]

    def get_mission_players(self) -> List[str]:
        """获取当前任务中的玩家列表"""
        return self.current_team 