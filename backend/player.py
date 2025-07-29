import random
from typing import List, Dict, Any, Optional
from .constants import ROLES
import sys
sys.path.append('..')
from config import AI_CONFIG

class Player:
    def __init__(self, name: str, role: Optional[str] = None):
        self.name = name
        self.role = role
        self.is_ai = False
        self.is_leader = False
        self.is_on_mission = False
        self.vote_history = []
        self.messages = []

    def receive_message(self, message: str):
        """玩家收到信息"""
        self.messages.append(message)
        print(f"{self.name} 收到消息: {message}")

    def set_role(self, role: str):
        """设置玩家角色"""
        self.role = role

    def get_role_info(self) -> Dict[str, Any]:
        """获取角色信息"""
        if self.role:
            return ROLES.get(self.role, {})
        return {}

    def can_see_player(self, other_player: 'Player') -> bool:
        """判断是否能看到其他玩家的身份"""
        if not self.role or not other_player.role:
            return False
        
        # 梅林能看到除了莫德雷德之外的所有坏人
        if self.role == 'merlin':
            if other_player.role in ['morgana', 'assassin', 'oberon', 'minion']:
                return True
            return False
        
        # 派西维尔能看到梅林和莫甘娜
        if self.role == 'percival':
            if other_player.role in ['merlin', 'morgana']:
                return True
            return False
        
        # 坏人能看到其他坏人（除了奥伯伦）
        if ROLES[self.role]['team'] == 'evil':
            if other_player.role in ['morgana', 'assassin', 'mordred', 'minion']:
                return True
            return False
        
        return False

class AIPlayer(Player):
    def __init__(self, name: str, ai_engine: str = 'gpt-3.5', role: Optional[str] = None):
        super().__init__(name, role)
        self.is_ai = True
        self.ai_engine = ai_engine
        self.knowledge_base = []
        
        # 验证AI引擎是否有效
        if ai_engine not in AI_CONFIG:
            print(f"警告: 不支持的AI引擎 '{ai_engine}'，使用默认引擎 'gpt-3.5'")
            self.ai_engine = 'gpt-3.5'

    def get_ai_engine_info(self) -> Dict[str, Any]:
        """获取AI引擎信息"""
        return AI_CONFIG.get(self.ai_engine, {})

    def decide(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """AI 玩家决策逻辑"""
        # 根据游戏状态和角色做出决策
        decision = {
            'action': 'pass',
            'reason': 'AI决策'
        }
        
        if game_state.get('phase') == 'team_selection':
            decision = self._decide_team_selection(game_state)
        elif game_state.get('phase') == 'team_vote':
            decision = self._decide_team_vote(game_state)
        elif game_state.get('phase') == 'mission_vote':
            decision = self._decide_mission_vote(game_state)
        elif game_state.get('phase') == 'assassination':
            decision = self._decide_assassination(game_state)
        
        return decision

    def _decide_team_selection(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """决定队伍选择"""
        # 简单的AI逻辑：随机选择玩家
        available_players = game_state.get('available_players', [])
        mission_size = game_state.get('mission_size', 2)
        
        if len(available_players) >= mission_size:
            selected = random.sample(available_players, mission_size)
            return {
                'action': 'select_team',
                'players': selected,
                'reason': f'选择了 {", ".join(selected)} 参加任务'
            }
        
        return {'action': 'pass', 'reason': '无法选择足够玩家'}

    def _decide_team_vote(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """决定队伍投票"""
        # 根据角色和游戏状态投票
        if self.role in ['merlin', 'percival', 'loyal_servant']:
            # 好人倾向于支持看起来安全的队伍
            return {'action': 'approve', 'reason': '好人支持'}
        else:
            # 坏人可能反对或支持
            return {'action': random.choice(['approve', 'reject']), 'reason': '坏人投票'}

    def _decide_mission_vote(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """决定任务投票"""
        if ROLES.get(self.role, {}).get('team') == 'evil':
            # 坏人投票失败
            return {'action': 'fail', 'reason': '坏人破坏任务'}
        else:
            # 好人投票成功
            return {'action': 'success', 'reason': '好人完成任务'}

    def _decide_assassination(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """决定刺杀目标"""
        if self.role == 'assassin':
            # 刺客尝试刺杀梅林
            good_players = [p for p in game_state.get('players', []) 
                          if ROLES.get(p.role, {}).get('team') == 'good']
            if good_players:
                target = random.choice(good_players)
                return {'action': 'assassinate', 'target': target.name, 'reason': '尝试刺杀梅林'}
        
        return {'action': 'pass', 'reason': '不是刺客'}

    def add_knowledge(self, knowledge: str):
        """添加知识到AI的知识库"""
        self.knowledge_base.append(knowledge)

class God:
    def __init__(self):
        self.role_assignments = {}
        self.secret_messages = {}

    def assign_roles(self, players: List[Player]) -> Dict[str, str]:
        """分配身份信息"""
        if len(players) < 5 or len(players) > 10:
            raise ValueError("玩家数量必须在5-10人之间")
        
        # 根据玩家数量确定角色配置
        role_config = self._get_role_config(len(players))
        
        # 随机分配角色
        available_roles = role_config.copy()
        random.shuffle(available_roles)
        
        assignments = {}
        for i, player in enumerate(players):
            role = available_roles[i]
            player.set_role(role)
            assignments[player.name] = role
        
        self.role_assignments = assignments
        return assignments

    def _get_role_config(self, player_count: int) -> List[str]:
        """根据玩家数量获取角色配置"""
        if player_count == 5:
            return ['merlin', 'percival', 'loyal_servant', 'morgana', 'assassin']
        elif player_count == 6:
            return ['merlin', 'percival', 'loyal_servant', 'loyal_servant', 'morgana', 'assassin']
        elif player_count == 7:
            return ['merlin', 'percival', 'loyal_servant', 'loyal_servant', 'morgana', 'assassin', 'oberon']
        elif player_count == 8:
            return ['merlin', 'percival', 'loyal_servant', 'loyal_servant', 'morgana', 'assassin', 'mordred', 'minion']
        elif player_count == 9:
            return ['merlin', 'percival', 'loyal_servant', 'loyal_servant', 'loyal_servant', 'morgana', 'assassin', 'mordred', 'minion']
        elif player_count == 10:
            return ['merlin', 'percival', 'loyal_servant', 'loyal_servant', 'loyal_servant', 'morgana', 'assassin', 'mordred', 'minion', 'minion']
        
        return []

    def send_secret_info(self, player: Player) -> str:
        """给玩家发送秘密信息"""
        if not player.role:
            return "你还没有被分配角色"
        
        role_info = ROLES.get(player.role, {})
        message = f"你的角色是：{role_info.get('name', '未知')}\n"
        message += f"描述：{role_info.get('description', '无描述')}\n"
        
        # 根据角色发送特殊信息
        if player.role == 'merlin':
            evil_players = [name for name, role in self.role_assignments.items() 
                          if role in ['morgana', 'assassin', 'oberon', 'minion']]
            message += f"坏人玩家：{', '.join(evil_players)}"
        
        elif player.role == 'percival':
            merlin_morgana = [name for name, role in self.role_assignments.items() 
                             if role in ['merlin', 'morgana']]
            message += f"梅林或莫甘娜：{', '.join(merlin_morgana)}"
        
        elif ROLES.get(player.role, {}).get('team') == 'evil':
            evil_players = [name for name, role in self.role_assignments.items() 
                          if role in ['morgana', 'assassin', 'mordred', 'minion'] and name != player.name]
            message += f"其他坏人：{', '.join(evil_players)}"
        
        return message 