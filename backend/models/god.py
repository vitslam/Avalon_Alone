import random
from typing import List, Dict
from ..core.roles import ROLES
from ..core.constants import ROLE_ASSIGNMENT
from .player import Player


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
        """根据玩家数量获取阿瓦隆标准角色配置（含刺客）"""
        return ROLE_ASSIGNMENT.get(player_count, [])

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
