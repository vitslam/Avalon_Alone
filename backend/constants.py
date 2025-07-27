"""
阿瓦隆游戏常量定义
"""

# 游戏角色
ROLES = {
    'merlin': {
        'name': '梅林',
        'team': 'good',
        'description': '能看到除了莫德雷德之外的所有坏人'
    },
    'percival': {
        'name': '派西维尔',
        'team': 'good',
        'description': '能看到梅林和莫甘娜'
    },
    'loyal_servant': {
        'name': '忠臣',
        'team': 'good',
        'description': '普通的好人'
    },
    'morgana': {
        'name': '莫甘娜',
        'team': 'evil',
        'description': '坏人，派西维尔会看到你'
    },
    'assassin': {
        'name': '刺客',
        'team': 'evil',
        'description': '坏人，游戏结束后可以刺杀梅林'
    },
    'oberon': {
        'name': '奥伯伦',
        'team': 'evil',
        'description': '坏人，但其他坏人不知道你的身份'
    },
    'mordred': {
        'name': '莫德雷德',
        'team': 'evil',
        'description': '坏人，梅林看不到你'
    },
    'minion': {
        'name': '爪牙',
        'team': 'evil',
        'description': '普通坏人'
    }
}

# 游戏阶段
GAME_PHASES = {
    'init': '初始化',
    'role_assignment': '分配角色',
    'secret_info': '传递秘密信息',
    'team_selection': '选择队伍',
    'team_vote': '队伍投票',
    'mission_vote': '任务投票',
    'mission_result': '任务结果',
    'assassination': '刺杀阶段',
    'game_end': '游戏结束'
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

# 游戏状态
GAME_STATES = {
    'waiting': '等待开始',
    'playing': '游戏进行中',
    'finished': '游戏结束'
} 