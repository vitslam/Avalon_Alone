"""
AI控制器 - 负责AI玩家的自动决策和游戏流程控制
"""

import asyncio
import random
from typing import List, Dict, Any, Optional
from .player import AIPlayer
from .game import AvalonGame
from .constants import ROLES, GAME_STATES, GAME_PHASES

class AIController:
    """AI控制器，管理所有AI玩家的自动决策"""
    
    def __init__(self, game: AvalonGame, websocket_notifier=None):
        self.game = game
        self.ai_players = [p for p in game.players if p.is_ai]
        self.is_running = False
        self.auto_delay = 1.0  # AI操作间隔时间（秒）
        self.websocket_notifier = websocket_notifier  # WebSocket通知函数
    
    async def start_auto_play(self):
        """开始AI自动游戏"""
        if not self.ai_players:
            print("没有AI玩家，退出自动游戏")
            return
        
        self.is_running = True
        print(f"AI控制器启动，管理 {len(self.ai_players)} 个AI玩家")
        
        loop_count = 0
        # 持续处理游戏直到结束
        while self.is_running and self.game.state == GAME_STATES['playing']:
            loop_count += 1
            print(f"\n=== AI循环 {loop_count} ===")
            print(f"游戏状态: {self.game.state}")
            print(f"游戏阶段: {self.game.phase}")
            
            await self.process_current_phase()
            
            # 检查游戏是否结束
            if self.game.state == GAME_STATES['finished']:
                print("游戏结束！")
                break
            
            # 防止无限循环
            if loop_count > 50:
                print("达到最大循环次数，停止AI控制器")
                break
            
            await asyncio.sleep(self.auto_delay)
        
        print(f"AI控制器结束，总共执行了 {loop_count} 次循环")
    
    def stop_auto_play(self):
        """停止AI自动游戏"""
        self.is_running = False
        print("AI控制器已停止")
    
    async def process_current_phase(self):
        """处理当前游戏阶段"""
        phase = self.game.phase
        print(f"处理阶段: {phase}")
        
        if phase == GAME_PHASES['team_selection']:
            await self.handle_team_selection()
        elif phase == GAME_PHASES['team_vote']:
            await self.handle_team_vote()
        elif phase == GAME_PHASES['mission_vote']:
            await self.handle_mission_vote()
        elif phase == GAME_PHASES['assassination']:
            await self.handle_assassination()
        else:
            print(f"未知阶段: {phase}，等待...")
            await asyncio.sleep(1.0)
    
    async def handle_team_selection(self):
        """处理队伍选择阶段"""
        current_leader = self.game.players[self.game.current_leader_index]
        
        if not current_leader.is_ai:
            print(f"当前队长 {current_leader.name} 不是AI，跳过自动选择")
            return
        
        print(f"AI队长 {current_leader.name} 正在选择队伍...")
        
        # 获取任务配置
        mission_config = self.game.get_mission_config()
        if not mission_config:
            print("无法获取任务配置")
            return
        
        team_size = mission_config['team_size']
        available_players = self.game.get_available_players()
        
        print(f"任务大小: {team_size}, 可用玩家: {available_players}")
        
        # AI选择队伍的策略
        selected_players = self.ai_select_team(current_leader, available_players, team_size)
        
        if selected_players:
            # 执行队伍选择
            result = self.game.select_team(selected_players)
            print(f"AI队长 {current_leader.name} 选择了队伍: {selected_players}")
            print(f"选择结果: {result}")
            
            # 通知前端
            await self.notify_frontend("team_selected", result)
        else:
            print("AI无法选择队伍")
    
    def ai_select_team(self, leader: AIPlayer, available_players: List[str], team_size: int) -> List[str]:
        """AI选择队伍的策略"""
        if len(available_players) < team_size:
            return []
        
        # 根据角色制定选择策略
        if leader.role in ['merlin', 'percival', 'loyal_servant']:
            # 好人倾向于选择看起来安全的队伍
            return self.select_good_team(leader, available_players, team_size)
        else:
            # 坏人可能选择包含坏人的队伍
            return self.select_evil_team(leader, available_players, team_size)
    
    def select_good_team(self, leader: AIPlayer, available_players: List[str], team_size: int) -> List[str]:
        """好人选择队伍的策略"""
        # 优先选择自己和其他好人
        good_players = []
        for player_name in available_players:
            player = next(p for p in self.game.players if p.name == player_name)
            if player.role in ['merlin', 'percival', 'loyal_servant']:
                good_players.append(player_name)
        
        # 如果好人不够，随机补充
        selected = good_players[:team_size]
        if len(selected) < team_size:
            remaining = [p for p in available_players if p not in selected]
            selected.extend(random.sample(remaining, team_size - len(selected)))
        
        return selected[:team_size]
    
    def select_evil_team(self, leader: AIPlayer, available_players: List[str], team_size: int) -> List[str]:
        """坏人选择队伍的策略"""
        # 优先选择包含坏人的队伍
        evil_players = []
        for player_name in available_players:
            player = next(p for p in self.game.players if p.name == player_name)
            if ROLES.get(player.role, {}).get('team') == 'evil':
                evil_players.append(player_name)
        
        # 确保队伍包含坏人
        selected = []
        if evil_players:
            selected.append(random.choice(evil_players))
        
        # 随机补充其他玩家
        remaining = [p for p in available_players if p not in selected]
        if remaining:
            selected.extend(random.sample(remaining, min(team_size - len(selected), len(remaining))))
        
        return selected[:team_size]
    
    async def handle_team_vote(self):
        """处理队伍投票阶段"""
        # 检查哪些AI还没有投票
        voted_players = {vote['player'] for vote in self.game.team_votes}
        ai_players_to_vote = [p for p in self.ai_players if p.name not in voted_players]
        
        print(f"队伍投票阶段，AI玩家待投票: {[p.name for p in ai_players_to_vote]}")
        
        for ai_player in ai_players_to_vote:
            await asyncio.sleep(0.5)  # 稍微延迟，模拟思考时间
            
            vote = self.ai_decide_team_vote(ai_player)
            result = self.game.vote_team(ai_player.name, vote)
            
            print(f"AI玩家 {ai_player.name} 队伍投票: {vote}")
            print(f"投票结果: {result}")
            
            # 通知前端
            await self.notify_frontend("team_vote_recorded", result)
            
            # 检查投票是否完成
            if result.get('status') in ['team_approved', 'team_rejected', 'evil_win']:
                print(f"队伍投票完成: {result.get('status')}")
                break
    
    def ai_decide_team_vote(self, ai_player: AIPlayer) -> str:
        """AI决定队伍投票"""
        if ai_player.role in ['merlin', 'percival', 'loyal_servant']:
            # 好人倾向于支持看起来安全的队伍
            return 'approve'
        else:
            # 坏人可能反对或支持，有一定随机性
            return random.choice(['approve', 'reject'])
    
    async def handle_mission_vote(self):
        """处理任务投票阶段"""
        # 检查哪些AI还没有投票
        voted_players = {vote['player'] for vote in self.game.mission_votes}
        ai_players_to_vote = [p for p in self.ai_players if p.name in self.game.current_team and p.name not in voted_players]
        
        print(f"任务投票阶段，AI玩家待投票: {[p.name for p in ai_players_to_vote]}")
        
        for ai_player in ai_players_to_vote:
            await asyncio.sleep(0.5)  # 稍微延迟，模拟思考时间
            
            vote = self.ai_decide_mission_vote(ai_player)
            result = self.game.vote_mission(ai_player.name, vote)
            
            print(f"AI玩家 {ai_player.name} 任务投票: {vote}")
            print(f"投票结果: {result}")
            
            # 通知前端
            await self.notify_frontend("mission_vote_recorded", result)
            
            # 检查投票是否完成
            if result.get('status') in ['good_mission_win', 'evil_win', 'mission_completed']:
                print(f"任务投票完成: {result.get('status')}")
                break
    
    def ai_decide_mission_vote(self, ai_player: AIPlayer) -> str:
        """AI决定任务投票"""
        if ROLES.get(ai_player.role, {}).get('team') == 'evil':
            # 坏人投票失败
            return 'fail'
        else:
            # 好人投票成功
            return 'success'
    
    async def handle_assassination(self):
        """处理刺杀阶段"""
        # 找到刺客
        assassin = None
        for player in self.ai_players:
            if player.role == 'assassin':
                assassin = player
                break
        
        if not assassin:
            print("没有找到AI刺客")
            return
        
        print(f"AI刺客 {assassin.name} 开始选择刺杀目标...")
        await asyncio.sleep(1.0)  # 给刺客一些思考时间
        
        # AI刺客选择刺杀目标
        target = self.ai_select_assassination_target(assassin)
        
        if target:
            result = self.game.assassinate(target)
            print(f"AI刺客 {assassin.name} 选择刺杀目标: {target}")
            print(f"刺杀结果: {result}")
            
            # 通知前端
            await self.notify_frontend("assassination_result", result)
        else:
            print("AI刺客无法选择目标")
    
    def ai_select_assassination_target(self, assassin: AIPlayer) -> Optional[str]:
        """AI刺客选择刺杀目标"""
        # 获取所有好人玩家
        good_players = []
        for player in self.game.players:
            if ROLES.get(player.role, {}).get('team') == 'good':
                good_players.append(player.name)
        
        if good_players:
            # 随机选择一个好人作为目标
            return random.choice(good_players)
        
        return None
    
    async def notify_frontend(self, event: str, data: Dict[str, Any]):
        """通知前端"""
        print(f"AI事件: {event} - {data}")
        
        # 通过WebSocket通知前端
        if self.websocket_notifier:
            try:
                await self.websocket_notifier(event, data)
            except Exception as e:
                print(f"WebSocket通知失败: {e}")
    
    def get_ai_status(self) -> Dict[str, Any]:
        """获取AI控制器状态"""
        return {
            'is_running': self.is_running,
            'ai_players_count': len(self.ai_players),
            'current_phase': self.game.phase,
            'auto_delay': self.auto_delay
        } 