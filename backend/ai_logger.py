"""
AI日志记录器 - 记录所有AI请求到JSONL格式的日志文件
"""

import json
import time
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import sys
sys.path.append('..')
from config import AI_LOGGING_CONFIG

class AILogger:
    def __init__(self):
        self.enabled = AI_LOGGING_CONFIG['enabled']
        self.log_dir = AI_LOGGING_CONFIG.get('log_dir', 'ai_logs')
        self.include_system_prompt = AI_LOGGING_CONFIG['include_system_prompt']
        self.include_user_prompt = AI_LOGGING_CONFIG['include_user_prompt']
        self.include_response = AI_LOGGING_CONFIG['include_response']
        self.include_timing = AI_LOGGING_CONFIG['include_timing']
        
        # 确保日志目录存在
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        # 当前游戏的文件名
        self.current_game_file = None
    
    def start_new_game(self):
        """开始新游戏，创建新的日志文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_game_file = os.path.join(self.log_dir, f"game_{timestamp}.jsonl")
        print(f"开始新游戏日志: {self.current_game_file}")
    
    def log_request(self, 
                   model_name: str,
                   messages: List[Dict[str, str]],
                   player_id: Optional[str] = None,
                   request_type: str = "unknown",
                   response: Optional[str] = None,
                   start_time: Optional[float] = None,
                   end_time: Optional[float] = None,
                   error: Optional[str] = None) -> None:
        """
        记录AI请求到JSONL日志文件
        
        Args:
            model_name: 模型名称
            messages: 请求消息列表
            player_id: 玩家ID
            request_type: 请求类型（speech, team_selection, vote, assassination等）
            response: 模型回复
            start_time: 请求开始时间戳
            end_time: 请求结束时间戳
            error: 错误信息
        """
        if not self.enabled:
            return
        
        # 如果没有当前游戏文件，创建一个
        if not self.current_game_file:
            self.start_new_game()
        
        # 构建日志条目
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'model_name': model_name,
            'request_type': request_type,
            'player_id': player_id,
            'messages': messages if self.include_system_prompt and self.include_user_prompt else [],
            'system_prompt': self._extract_system_prompt(messages) if self.include_system_prompt else None,
            'user_prompt': self._extract_user_prompt(messages) if self.include_user_prompt else None,
            'response': response if self.include_response else None,
            'error': error
        }
        
        # 添加时间信息
        if self.include_timing and start_time and end_time:
            log_entry['request_duration'] = end_time - start_time
            log_entry['start_time'] = start_time
            log_entry['end_time'] = end_time
        
        # 写入JSONL文件
        try:
            with open(self.current_game_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"AI日志记录失败: {e}")
    
    def _extract_system_prompt(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """提取系统提示"""
        for message in messages:
            if message.get('role') == 'system':
                return message.get('content')
        return None
    
    def _extract_user_prompt(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """提取用户提示"""
        for message in messages:
            if message.get('role') == 'user':
                return message.get('content')
        return None
    
    def log_speech_request(self, 
                          model_name: str,
                          messages: List[Dict[str, str]],
                          player_id: str,
                          response: Optional[str] = None,
                          start_time: Optional[float] = None,
                          end_time: Optional[float] = None,
                          error: Optional[str] = None) -> None:
        """记录发言请求"""
        self.log_request(
            model_name=model_name,
            messages=messages,
            player_id=player_id,
            request_type="speech",
            response=response,
            start_time=start_time,
            end_time=end_time,
            error=error
        )
    
    def log_team_selection_request(self, 
                                 model_name: str,
                                 messages: List[Dict[str, str]],
                                 player_id: str,
                                 response: Optional[str] = None,
                                 start_time: Optional[float] = None,
                                 end_time: Optional[float] = None,
                                 error: Optional[str] = None) -> None:
        """记录队伍选择请求"""
        self.log_request(
            model_name=model_name,
            messages=messages,
            player_id=player_id,
            request_type="team_selection",
            response=response,
            start_time=start_time,
            end_time=end_time,
            error=error
        )
    
    def log_vote_request(self, 
                        model_name: str,
                        messages: List[Dict[str, str]],
                        player_id: str,
                        vote_type: str,
                        response: Optional[str] = None,
                        start_time: Optional[float] = None,
                        end_time: Optional[float] = None,
                        error: Optional[str] = None) -> None:
        """记录投票请求"""
        self.log_request(
            model_name=model_name,
            messages=messages,
            player_id=player_id,
            request_type=f"vote_{vote_type}",
            response=response,
            start_time=start_time,
            end_time=end_time,
            error=error
        )
    
    def log_assassination_request(self, 
                                model_name: str,
                                messages: List[Dict[str, str]],
                                player_id: str,
                                response: Optional[str] = None,
                                start_time: Optional[float] = None,
                                end_time: Optional[float] = None,
                                error: Optional[str] = None) -> None:
        """记录刺杀请求"""
        self.log_request(
            model_name=model_name,
            messages=messages,
            player_id=player_id,
            request_type="assassination",
            response=response,
            start_time=start_time,
            end_time=end_time,
            error=error
        )

# 全局AI日志记录器实例
ai_logger = AILogger() 