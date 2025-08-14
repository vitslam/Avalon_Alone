import asyncio
import json
import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from .model_client import ModelClientFactory, BaseModelClient
from .common_constants import ROLES, VOTE_RULES, GAME_RULES
from .log_manager import LogManager

# 加载环境变量
load_dotenv()

class AIService:
    def __init__(self, log_manager: LogManager = None):
        self.ai_provider = os.getenv("AI_PROVIDER", "zhipu").lower()
        self.timeout = int(os.getenv("AI_RESPONSE_TIMEOUT", "30"))
        self.fallback_enabled = os.getenv("AI_FALLBACK_ENABLED", "true").lower() == "true"
        self.log_manager = log_manager if log_manager else LogManager()
        
        # 使用工厂创建模型客户端
        try:
            self.model_client = ModelClientFactory.create_client(self.ai_provider)
        except Exception as e:
            print(f"初始化AI服务失败: {e}")
            self.model_client = None

    async def get_ai_speech(self, player_name: str, role: str, game_context: Dict[str, Any]) -> Optional[str]:
        """获取AI玩家的发言"""
        if not self.model_client:
            print(f"AI服务未初始化，{player_name} 使用默认发言")
            return None
            
        try:
            prompt = self._build_speech_prompt(player_name, role, game_context)
            
            messages = [
                {"role": "system", "content": "你是一个阿瓦隆游戏中的AI玩家。请根据你的角色和当前游戏情况，给出简短的发言（不超过50字）。"},
                {"role": "user", "content": prompt}
            ]
            
            request_log = {
                "player_name": player_name,
                "role": role,
                "game_context": game_context,
                "messages": messages
            }
            
            speech = await self.model_client.chat_completion(messages)
            
            response_log = {
                "speech": speech
            }
            
            # 记录日志
            if self.log_manager:
                self.log_manager.log_player_interaction(player_name, request_log, response_log)
            
            if speech:
                print(f"AI {player_name} 获得发言: {speech}")
                return speech
            
        except Exception as e:
            print(f"AI {player_name} 发言获取失败: {e}")
            return None

    async def get_ai_team_selection(self, player_name: str, role: str, game_context: Dict[str, Any], 
                                  available_players: List[str], team_size: int) -> Optional[List[str]]:
        """获取AI玩家的队伍选择"""
        if not self.model_client:
            return None
            
        try:
            prompt = self._build_team_selection_prompt(player_name, role, game_context, available_players, team_size)
            
            messages = [
                {"role": "system", "content": "你是阿瓦隆游戏中的AI玩家。请根据你的角色选择任务队伍。只返回JSON格式的玩家名称列表。"},
                {"role": "user", "content": prompt}
            ]
            
            request_log = {
                "player_name": player_name,
                "role": role,
                "game_context": game_context,
                "available_players": available_players,
                "team_size": team_size,
                "messages": messages
            }
            
            content = await self.model_client.chat_completion(messages)
            
            response_log = {
                "content": content
            }
            
            team = None
            if content:
                # 尝试解析JSON
                try:
                    team = json.loads(content)
                    if isinstance(team, list) and len(team) == team_size:
                        print(f"AI {player_name} 选择队伍: {team}")
                        response_log["team"] = team
                except json.JSONDecodeError:
                    # 如果不是JSON，尝试提取玩家名称
                    team = self._extract_player_names(content, available_players, team_size)
                    if team:
                        print(f"AI {player_name} 选择队伍(提取): {team}")
                        response_log["team"] = team
            
            # 记录日志
            if self.log_manager:
                self.log_manager.log_player_interaction(player_name, request_log, response_log)
            
            return team
        except Exception as e:
            print(f"AI {player_name} 队伍选择失败: {e}")
            return None

    async def get_ai_vote_decision(self, player_name: str, role: str, game_context: Dict[str, Any], 
                                 vote_type: str) -> Optional[str]:
        """获取AI玩家的投票决策"""
        if not self.model_client:
            return None
            
        try:
            prompt = self._build_vote_prompt(player_name, role, game_context, vote_type)
            
            messages = [
                {"role": "system", "content": f"你是阿瓦隆游戏中的AI玩家。请根据你的角色进行{vote_type}投票。只返回 'approve'/'reject' 或 'success'/'fail'。"},
                {"role": "user", "content": prompt}
            ]
            
            request_log = {
                "player_name": player_name,
                "role": role,
                "game_context": game_context,
                "vote_type": vote_type,
                "messages": messages
            }
            
            content = await self.model_client.chat_completion(messages)
            
            vote = None
            if content:
                content = content.strip().lower()
                
                if vote_type == "team":
                    if "approve" in content or "赞成" in content:
                        vote = "approve"
                    elif "reject" in content or "反对" in content:
                        vote = "reject"
                elif vote_type == "mission":
                    if "success" in content or "成功" in content:
                        vote = "success"
                    elif "fail" in content or "失败" in content:
                        vote = "fail"
                    
                print(f"AI {player_name} 投票决策: {content}")
            
            response_log = {
                "content": content,
                "vote": vote
            }
            
            # 记录日志
            if self.log_manager:
                self.log_manager.log_player_interaction(player_name, request_log, response_log)
            
            return vote
        except Exception as e:
            print(f"AI {player_name} 投票决策失败: {e}")
            return None

    # 以下是辅助方法
    def _build_speech_prompt(self, player_name: str, role: str, game_context: Dict[str, Any]) -> str:
        phase = game_context.get('phase', '未知')
        current_mission = game_context.get('current_mission', 1)
        current_team = game_context.get('current_team', [])
        vote_context = game_context.get('vote_context', '')
        players = game_context.get('players', [])
        messages_history = game_context.get('messages_history', [])
        
        # 从配置中获取角色信息
        role_info = ROLES.get(role, {'name': role, 'description': role, 'strategy_tips': []})
        role_display = role_info['name']
        strategy_tips = ','.join(role_info['strategy_tips'])
        
        # 根据角色添加视野信息
        vision_info = ""
        if role == 'merlin':
            evil_players = [p['name'] for p in players if p['role'] in ['morgana', 'assassin', 'oberon', 'minion']]
            vision_info = f"你能看到这些坏人: {', '.join(evil_players)}"
        elif role == 'percival':
            merlin_players = [p['name'] for p in players if p['role'] == 'merlin']
            morgana_players = [p['name'] for p in players if p['role'] == 'morgana']
            vision_info = f"你能看到梅林: {', '.join(merlin_players)} 和 莫甘娜: {', '.join(morgana_players)}"
        elif role_info.get('team') == 'evil':
            evil_players = [p['name'] for p in players if p['role'] in ['morgana', 'assassin', 'mordred', 'minion']]
            vision_info = f"你能看到这些坏人同伴: {', '.join(evil_players)}"
        
        # 添加对话历史
        history_info = ""
        if messages_history:
            history_lines = []
            for msg in messages_history:  # 取所有消息
                history_lines.append(f"{msg['player']}说: {msg['content']}")
            history_info = "\n\n对话历史:\n" + '\n'.join(history_lines)
        
        context_info = ""
        if vote_context == "team_vote":
            context_info = f"当前需要对队伍 {current_team} 进行投票。"
        elif vote_context == "mission_vote":
            context_info = "你在任务队伍中，需要决定任务的成败。"
        
        prompt = f"""
你是阿瓦隆游戏中的玩家 {player_name}，你的角色是 {role_display}。
{role_info['description']}
{vision_info}
策略提示：{strategy_tips}

当前游戏状态：
- 阶段：{phase}
- 当前任务：第{current_mission}个
- 当前队伍：{current_team if current_team else '未选择'}
{context_info}
{history_info}

请根据你的角色和当前情况发言，要简洁有趣（不超过100字）。体现你的角色特点和策略思考。
"""
        return prompt

    def _build_team_selection_prompt(self, player_name: str, role: str, game_context: Dict[str, Any], 
                                   available_players: List[str], team_size: int) -> str:
        players = game_context.get('players', [])
        messages_history = game_context.get('messages_history', [])
        
        # 从配置中获取角色信息
        role_info = ROLES.get(role, {'name': role, 'description': role, 'team': 'unknown', 'strategy_tips': []})
        strategy_tips = ','.join(role_info['strategy_tips'])
        
        # 根据角色添加视野信息
        vision_info = ""
        if role == 'merlin':
            evil_players = [p['name'] for p in players if p['role'] in ['morgana', 'assassin', 'oberon', 'minion'] and p['name'] in available_players]
            vision_info = f"你能看到这些坏人: {', '.join(evil_players)}"
        elif role == 'percival':
            merlin_players = [p['name'] for p in players if p['role'] == 'merlin' and p['name'] in available_players]
            morgana_players = [p['name'] for p in players if p['role'] == 'morgana' and p['name'] in available_players]
            vision_info = f"你能看到梅林: {', '.join(merlin_players)} 和 莫甘娜: {', '.join(morgana_players)}"
        elif role_info.get('team') == 'evil':
            evil_players = [p['name'] for p in players if p['role'] in ['morgana', 'assassin', 'mordred', 'minion'] and p['name'] in available_players]
            vision_info = f"你能看到这些坏人同伴: {', '.join(evil_players)}"
        
        # 添加对话历史
        history_info = ""
        if messages_history:
            history_lines = []
            for msg in messages_history[-5:]:  # 只取最近5条消息
                history_lines.append(f"{msg['player']}说: {msg['content']}")
            history_info = "\n\n对话历史:\n" + '\n'.join(history_lines)
        
        # 根据角色阵营生成策略建议
        if role_info['team'] == 'good':
            team_strategy = "尽量选择可信的玩家，避免选择可疑的玩家"
        elif role_info['team'] == 'evil':
            team_strategy = "考虑是否要破坏任务，选择有利于己方的玩家"
        else:
            team_strategy = "根据情况选择合适的玩家"
        
        prompt = f"""
你是阿瓦隆游戏中的玩家 {player_name}，你的角色是 {role_info['name']}。
{role_info['description']}
{vision_info}
策略提示：{strategy_tips}

可选玩家：{available_players}
需要选择 {team_size} 名玩家组成任务队伍。

请根据你的角色特点和策略选择队伍成员：
- {team_strategy}
{history_info}

返回JSON格式的玩家名称列表，例如：["玩家1", "玩家2"]
"""
        return prompt

    def _build_vote_prompt(self, player_name: str, role: str, game_context: Dict[str, Any], vote_type: str) -> str:
        current_team = game_context.get('current_team', [])
        players = game_context.get('players', [])
        messages_history = game_context.get('messages_history', [])
        
        # 从配置中获取角色信息
        role_info = ROLES.get(role, {'name': role, 'description': role, 'team': 'unknown', 'strategy_tips': []})
        strategy_tips = ','.join(role_info['strategy_tips'])
        
        # 根据角色添加视野信息
        vision_info = ""
        if role == 'merlin':
            evil_players = [p['name'] for p in players if p['role'] in ['morgana', 'assassin', 'oberon', 'minion']]
            vision_info = f"你能看到这些坏人: {', '.join(evil_players)}"
        elif role == 'percival':
            merlin_players = [p['name'] for p in players if p['role'] == 'merlin']
            morgana_players = [p['name'] for p in players if p['role'] == 'morgana']
            vision_info = f"你能看到梅林: {', '.join(merlin_players)} 和 莫甘娜: {', '.join(morgana_players)}"
        elif role_info.get('team') == 'evil':
            evil_players = [p['name'] for p in players if p['role'] in ['morgana', 'assassin', 'mordred', 'minion']]
            vision_info = f"你能看到这些坏人同伴: {', '.join(evil_players)}"
        
        # 添加对话历史
        history_info = ""
        if messages_history:
            history_lines = []
            for msg in messages_history[-5:]:  # 只取最近5条消息
                history_lines.append(f"{msg['player']}说: {msg['content']}")
            history_info = "\n\n对话历史:\n" + '\n'.join(history_lines)
        
        # 获取投票规则信息
        vote_info = VOTE_RULES.get(vote_type, {})
        
        if vote_type == "team":
            # 根据角色阵营生成投票建议
            if role_info['team'] == 'good':
                vote_strategy = "支持可信的队伍，反对可疑的队伍"
            elif role_info['team'] == 'evil':
                vote_strategy = "根据策略需要决定支持或反对"
            else:
                vote_strategy = "根据情况决定投票"
            
            prompt = f"""
你是阿瓦隆游戏中的玩家 {player_name}，你的角色是 {role_info['name']}。
{role_info['description']}
{vision_info}
策略提示：{strategy_tips}

当前提议的任务队伍：{current_team}

请根据你的角色对这个队伍进行投票：
- {vote_strategy}
{history_info}

如果赞成（{vote_info.get('approve', '赞成')}），回答 "approve"
如果反对（{vote_info.get('reject', '反对')}），回答 "reject"
"""
        else:  # mission
            # 根据角色阵营生成投票建议
            if role_info['team'] == 'good':
                vote_strategy = "总是投票成功，帮助队伍完成任务"
            elif role_info['team'] == 'evil':
                vote_strategy = "根据策略需要决定是否破坏任务"
            else:
                vote_strategy = "根据情况决定投票"
            
            prompt = f"""
你是阿瓦隆游戏中的玩家 {player_name}，你的角色是 {role_info['name']}。
{role_info['description']}
{vision_info}
策略提示：{strategy_tips}

你在任务队伍中，需要对任务进行投票：
- {vote_strategy}
{history_info}

如果希望任务成功（{vote_info.get('success', '成功')}），回答 "success"  
如果希望任务失败（{vote_info.get('fail', '失败')}），回答 "fail"
"""
        
        return prompt

    def _extract_player_names(self, content: str, available_players: List[str], team_size: int) -> Optional[List[str]]:
        """从文本中提取玩家名称"""
        selected = []
        for player in available_players:
            if player in content and len(selected) < team_size:
                selected.append(player)
        
        return selected if len(selected) == team_size else None

    async def get_ai_assassination_target(self, assassin_name: str, role: str, good_players: List[str]) -> Optional[str]:
        """获取AI刺客的刺杀目标"""
        if not self.model_client:
            return None
            
        try:
            # 从配置中获取刺客角色信息
            role_info = ROLES.get(role, {'name': role, 'description': role, 'strategy_tips': []})
            strategy_tips = ','.join(role_info['strategy_tips'])
            
            prompt = f"""
你是阿瓦隆游戏中的刺客 {assassin_name}。
{role_info['description']}
策略提示：{strategy_tips}

可刺杀的好人玩家：{good_players}

请选择一个你认为最可能是梅林的玩家进行刺杀。只返回玩家名称。
"""
            
            messages = [
                {"role": "system", "content": "你是阿瓦隆游戏中的刺客。请选择刺杀目标。"},
                {"role": "user", "content": prompt}
            ]
            
            request_log = {
                "player_name": assassin_name,
                "role": role,
                "good_players": good_players,
                "messages": messages
            }
            
            target = await self.model_client.chat_completion(messages)
            
            response_log = {
                "content": target
            }
            
            if target and target.strip() in good_players:
                response_log["target"] = target.strip()
                # 记录日志
                if self.log_manager:
                    self.log_manager.log_player_interaction(assassin_name, request_log, response_log)
                return target.strip()
            
            # 记录日志
            if self.log_manager:
                self.log_manager.log_player_interaction(assassin_name, request_log, response_log)
                
        except Exception as e:
            print(f"AI {assassin_name} 刺杀目标选择失败: {e}")
            
        return None

# 全局AI服务实例
ai_service = AIService()

# 设置默认日志管理器
# 实际使用时，应在游戏开始时创建新的LogManager实例并传递给AIService