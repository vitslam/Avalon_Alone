import os
import json
import time
from typing import Dict, Any, List
import datetime

class LogManager:
    def __init__(self, game_id: str = None):
        self.root_log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        
        # 如果没有提供game_id，则创建一个包含时间戳的新game_id
        if game_id is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            self.game_id = f"game_{timestamp}"
        else:
            self.game_id = game_id

        # 创建游戏日志目录
        self.game_log_dir = os.path.join(self.root_log_dir, self.game_id)
        os.makedirs(self.game_log_dir, exist_ok=True)

        # 全局日志文件路径
        self.global_log_path = os.path.join(self.game_log_dir, 'global.log')
        
        # 记录已创建的玩家日志文件
        self.player_log_files = {}

    def log_global_event(self, event_type: str, data: Dict[str, Any]):
        """记录全局游戏事件"""
        log_entry = {
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'event_type': event_type,
            'data': data
        }

        with open(self.global_log_path, 'a') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    def log_player_speech(self, player_name: str, message: str, is_ai: bool = False, role: str = None):
        """记录玩家发言到全局日志"""
        log_entry = {
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'event_type': 'player_speech',
            'data': {
                'player_name': player_name,
                'message': message,
                'is_ai': is_ai,
                'role': role
            }
        }

        with open(self.global_log_path, 'a') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    def log_game_start_with_roles(self, role_assignments: Dict[str, str], secret_messages: Dict[str, str] = None):
        """记录游戏开始和身份信息到全局日志"""
        # 记录公开的角色分配信息（不包含秘密信息）
        log_entry = {
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'event_type': 'game_start',
            'data': {
                'role_assignments': role_assignments
            }
        }

        with open(self.global_log_path, 'a') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        # 如果有秘密信息，也记录下来
        if secret_messages:
            for player_name, message in secret_messages.items():
                secret_entry = {
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'event_type': 'secret_message',
                    'data': {
                        'player_name': player_name,
                        'message': message
                    }
                }
                f.write(json.dumps(secret_entry, ensure_ascii=False) + '\n')

    def log_player_interaction(self, player_name: str, request: Dict[str, Any], response: Dict[str, Any]):
        """记录玩家与AI模型的交互"""
        # 如果玩家日志文件不存在，则创建
        if player_name not in self.player_log_files:
            player_log_path = os.path.join(self.game_log_dir, f'{player_name}.jsonl')
            self.player_log_files[player_name] = player_log_path
        else:
            player_log_path = self.player_log_files[player_name]

        log_entry = {
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'request': request,
            'response': response
        }

        with open(player_log_path, 'a') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    def get_game_log_dir(self) -> str:
        """获取游戏日志目录路径"""
        return self.game_log_dir

    def get_game_id(self) -> str:
        """获取游戏ID"""
        return self.game_id