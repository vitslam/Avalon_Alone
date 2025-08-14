"""
阿瓦隆游戏整合常量定义
"""

# 游戏基本规则
GAME_RULES = {
    "mission_count": 5,  # 总任务数
    "required_players": 5,  # 最小玩家数
    "max_players": 10,  # 最大玩家数
    "success_threshold": 3,  # 获胜所需成功任务数
    "fail_threshold": 3,  # 失败所需失败任务数
    "team_vote_limit": 5,  # 队伍投票上限
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

# 游戏角色
ROLES = {
    # 好人阵营
    "merlin": {
        "name": "梅林",
        "team": "good",
        "description": "能看到除了莫德雷德之外的所有坏人",
        "abilities": ["知道坏人身份(除莫德雷德)"],
        "strategy_tips": [
            "隐藏自己的身份，不要太明显地暗示坏人是谁",
            "通过间接方式引导好人识别坏人"
        ]
    },
    "percival": {
        "name": "派西维尔",
        "team": "good",
        "description": "能看到梅林和莫甘娜",
        "abilities": ["识别梅林和莫甘娜"],
        "strategy_tips": [
            "观察梅林和莫甘娜的行为差异",
            "尝试保护疑似梅林的玩家"
        ]
    },
    "loyal_servant": {
        "name": "忠臣",
        "team": "good",
        "description": "普通的好人",
        "abilities": [],
        "strategy_tips": [
            "仔细观察其他玩家的发言和行为",
            "跟随可信玩家的建议"
        ]
    },

    # 坏人阵营
    "morgana": {
        "name": "莫甘娜",
        "team": "evil",
        "description": "坏人，派西维尔会看到你",
        "abilities": ["伪装成梅林"],
        "strategy_tips": [
            "模仿梅林的行为，但不要太完美",
            "误导派西维尔让他相信你是梅林"
        ]
    },
    "assassin": {
        "name": "刺客",
        "team": "evil",
        "description": "坏人，游戏结束后可以刺杀梅林",
        "abilities": ["刺杀梅林"],
        "strategy_tips": [
            "观察谁可能是梅林",
            "在游戏后期选择合适的时机刺杀"
        ]
    },
    "mordred": {
        "name": "莫德雷德",
        "team": "evil",
        "description": "坏人，梅林看不到你",
        "abilities": ["对梅林隐身"],
        "strategy_tips": [
            "利用自己对梅林隐身的优势",
            "大胆地参与游戏，因为梅林无法识别你"
        ]
    },
    "minion": {
        "name": "爪牙",
        "team": "evil",
        "description": "普通坏人",
        "abilities": ["知道其他坏人身份(除奥伯伦)"],
        "strategy_tips": [
            "支持其他坏人的行动",
            "尝试伪装成好人"
        ]
    },
    "oberon": {
        "name": "奥伯伦",
        "team": "evil",
        "description": "坏人，但其他坏人不知道你的身份",
        "abilities": [],
        "strategy_tips": [
            "破坏任务但不暴露自己",
            "尝试识别其他坏人"
        ]
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

# 游戏状态
GAME_STATES = {
    'waiting': '等待开始',
    'playing': '游戏进行中',
    'finished': '游戏结束'
}

# 角色分配规则（根据玩家数量）
ROLE_ASSIGNMENT = {
    5: ["merlin", "percival", "loyal_servant", "morgana", "assassin"],
    6: ["merlin", "percival", "loyal_servant", "morgana", "assassin", "minion"],
    7: ["merlin", "percival", "loyal_servant", "morgana", "assassin", "mordred", "minion"],
    8: ["merlin", "percival", "loyal_servant", "loyal_servant", "morgana", "assassin", "mordred", "minion"],
    9: ["merlin", "percival", "loyal_servant", "loyal_servant", "morgana", "assassin", "mordred", "minion", "oberon"],
    10: ["merlin", "percival", "loyal_servant", "loyal_servant", "loyal_servant", "morgana", "assassin", "mordred", "minion", "oberon"]
}

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