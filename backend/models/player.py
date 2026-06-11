import random
from typing import List, Dict, Any, Optional
from ..core.roles import ROLES


class Player:
    def __init__(self, name: str, role: Optional[str] = None):
        self.name = name
        self.role = role
        self.is_ai = False
        self.is_leader = False
        self.is_on_mission = False
        self.vote_history = []

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

    def decide(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """AI 玩家决策逻辑"""
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
        if self.role in ['merlin', 'percival', 'loyal_servant']:
            return {'action': 'approve', 'reason': '好人支持'}
        else:
            return {'action': random.choice(['approve', 'reject']), 'reason': '坏人投票'}

    def _decide_mission_vote(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """决定任务投票"""
        if ROLES.get(self.role, {}).get('team') == 'evil':
            return {'action': 'fail', 'reason': '坏人破坏任务'}
        else:
            return {'action': 'success', 'reason': '好人完成任务'}

    def _decide_assassination(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """决定刺杀目标"""
        if self.role == 'assassin':
            good_players = [p for p in game_state.get('players', [])
                          if ROLES.get(p.role, {}).get('team') == 'good']
            if good_players:
                target = random.choice(good_players)
                return {'action': 'assassinate', 'target': target.name, 'reason': '尝试刺杀梅林'}

        return {'action': 'pass', 'reason': '不是刺客'}

    def add_knowledge(self, knowledge: str):
        """添加知识到AI的知识库"""
        self.knowledge_base.append(knowledge)
