"""
游戏常量定义
"""

# 游戏阶段
GAME_PHASES = {
    'init': '初始化',
    'role_assignment': '分配角色',
    'team_selection': '选择队伍',
    'team_vote': '队伍投票',
    'mission_vote': '任务投票',
    'mission_result': '任务结果',
    'assassination': '刺杀阶段',
    'game_end': '游戏结束'
}

# 游戏状态
GAME_STATES = {
    'waiting': '等待开始',
    'playing': '游戏进行中',
    'finished': '游戏结束'
}

# 游戏基本规则
GAME_RULES = {
    "mission_count": 5,
    "required_players": 5,
    "max_players": 10,
    "success_threshold": 3,
    "fail_threshold": 3,
    "team_vote_limit": 5,
}

# 任务配置（根据玩家数量）
MISSION_CONFIGS = {
    5: {
        'missions': [2, 3, 2, 3, 3],
        'fails_needed': [1, 1, 1, 1, 1]
    },
    6: {
        'missions': [2, 3, 4, 3, 4],
        'fails_needed': [1, 1, 1, 1, 1]
    },
    7: {
        'missions': [2, 3, 3, 4, 4],
        'fails_needed': [1, 1, 1, 2, 1]
    },
    8: {
        'missions': [3, 4, 4, 5, 5],
        'fails_needed': [1, 1, 1, 2, 1]
    },
    9: {
        'missions': [3, 4, 4, 5, 5],
        'fails_needed': [1, 1, 1, 2, 1]
    },
    10: {
        'missions': [3, 4, 4, 5, 5],
        'fails_needed': [1, 1, 1, 2, 1]
    }
}

# 角色分配规则（根据玩家数量）
ROLE_ASSIGNMENT = {
    5: ["merlin", "percival", "loyal_servant", "morgana", "assassin"],
    6: ["merlin", "percival", "loyal_servant", "loyal_servant", "morgana", "assassin"],
    7: ["merlin", "percival", "loyal_servant", "loyal_servant", "morgana", "assassin", "oberon"],
    8: ["merlin", "percival", "loyal_servant", "loyal_servant", "loyal_servant", "morgana", "assassin", "minion"],
    9: ["merlin", "percival", "loyal_servant", "loyal_servant", "loyal_servant", "loyal_servant", "morgana", "assassin", "mordred"],
    10: ["merlin", "percival", "loyal_servant", "loyal_servant", "loyal_servant", "loyal_servant", "morgana", "assassin", "mordred", "oberon"]
}

# 坏人角色（刺杀讨论阶段按座位顺序发言）
EVIL_ROLES = frozenset(['morgana', 'assassin', 'minion', 'mordred', 'oberon'])

# 刺杀阶段坏人阵营最多讨论轮数
MAX_ASSASSINATION_DISCUSSION_ROUNDS = 3

# 投票规则
VOTE_RULES = {
    "team": {
        "approve": "赞成这个队伍执行任务",
        "reject": "反对这个队伍执行任务"
    },
    "mission": {
        "success": "让任务成功（好人应该总是选择这个）",
        "fail": "让任务失败（坏人可以选择这个）"
    }
}
