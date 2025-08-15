import os
import asyncio
import json
import time
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from .game_rules import get_complete_rules_for_player
import sys
sys.path.append('..')
from config import AI_CONFIG
from .ai_logger import ai_logger
from .service_logger import service_logger

# 加载环境变量
load_dotenv()

class AIService:
    def __init__(self):
        self.ai_provider = os.getenv("AI_PROVIDER", "zhipu").lower()
        self.default_model = os.getenv("AI_MODEL", "glm-4.5-flash")
        self.timeout = int(os.getenv("AI_RESPONSE_TIMEOUT", "30"))
        self.fallback_enabled = os.getenv("AI_FALLBACK_ENABLED", "true").lower() == "true"
        
        # 初始化对应的AI客户端
        self.client = None
        self.initialization_error = None
        
        if self.ai_provider == "zhipu":
            self._init_zhipu_client()
        elif self.ai_provider == "openai":
            self._init_openai_client()
        elif self.ai_provider == "anthropic":
            self._init_anthropic_client()
        else:
            error_msg = f"不支持的AI提供商: {self.ai_provider}"
            print(f"警告: {error_msg}")
            service_logger.logger.warning(error_msg)
        
        # 记录初始化结果
        if self.client:
            service_logger.logger.info(f"AI服务初始化成功 - 提供商: {self.ai_provider}, 模型: {self.default_model}")
        else:
            service_logger.logger.warning(f"AI服务初始化失败 - 提供商: {self.ai_provider}, 将使用备用逻辑")

    def _init_zhipu_client(self):
        """初始化智谱AI客户端"""
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key or api_key == "your_zhipu_api_key_here":
            error_msg = "未找到有效的 ZHIPU_API_KEY 环境变量"
            print(f"警告: {error_msg}")
            service_logger.logger.warning(error_msg)
            self.initialization_error = error_msg
            return
            
        try:
            from zai import ZhipuAiClient
            self.client = ZhipuAiClient(api_key=api_key)
            print("✅ 智谱AI客户端初始化成功")
            service_logger.logger.info("智谱AI客户端初始化成功")
        except ImportError:
            error_msg = "zai 包未安装，请运行: pip install zai"
            print(f"错误: {error_msg}")
            service_logger.logger.error(error_msg)
            self.initialization_error = error_msg
        except Exception as e:
            error_msg = f"智谱AI客户端初始化失败: {e}"
            print(f"错误: {error_msg}")
            service_logger.logger.error(error_msg)
            self.initialization_error = error_msg

    def _init_openai_client(self):
        """初始化OpenAI客户端"""
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        if not api_key or api_key == "your_openai_api_key_here":
            error_msg = "未找到有效的 OPENAI_API_KEY 环境变量"
            print(f"警告: {error_msg}")
            service_logger.logger.warning(error_msg)
            self.initialization_error = error_msg
            return
            
        try:
            from openai import AsyncOpenAI
            import httpx
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=httpx.Timeout(self.timeout)
            )
            print("✅ OpenAI客户端初始化成功")
            service_logger.logger.info("OpenAI客户端初始化成功")
        except ImportError:
            error_msg = "openai 包未安装，请运行: pip install openai"
            print(f"错误: {error_msg}")
            service_logger.logger.error(error_msg)
            self.initialization_error = error_msg
        except Exception as e:
            error_msg = f"OpenAI客户端初始化失败: {e}"
            print(f"错误: {error_msg}")
            service_logger.logger.error(error_msg)
            self.initialization_error = error_msg

    def _init_anthropic_client(self):
        """初始化Anthropic客户端"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key or api_key == "your_anthropic_api_key_here":
            error_msg = "未找到有效的 ANTHROPIC_API_KEY 环境变量"
            print(f"警告: {error_msg}")
            service_logger.logger.warning(error_msg)
            self.initialization_error = error_msg
            return
            
        try:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=api_key)
            print("✅ Anthropic客户端初始化成功")
            service_logger.logger.info("Anthropic客户端初始化成功")
        except ImportError:
            error_msg = "anthropic 包未安装，请运行: pip install anthropic"
            print(f"错误: {error_msg}")
            service_logger.logger.error(error_msg)
            self.initialization_error = error_msg
        except Exception as e:
            error_msg = f"Anthropic客户端初始化失败: {e}"
            print(f"错误: {error_msg}")
            service_logger.logger.error(error_msg)
            self.initialization_error = error_msg

    def _get_model_config(self, engine_name: str) -> Optional[Dict[str, Any]]:
        """获取模型配置"""
        if engine_name in AI_CONFIG:
            return AI_CONFIG[engine_name]
        return None

    def _get_actual_model(self, engine_name: str) -> str:
        """获取实际使用的模型名称"""
        model_config = self._get_model_config(engine_name)
        if model_config:
            return model_config['model']
        return self.default_model

    async def get_ai_speech(self, player_name: str, role: str, game_context: Dict[str, Any], engine_name: str = None) -> Optional[str]:
        """获取AI玩家的发言"""
        if not self.client:
            error_msg = f"AI服务未初始化，{player_name} 使用默认发言"
            print(f"警告: {error_msg}")
            service_logger.log_warning(error_msg, f"AI服务初始化错误: {self.initialization_error}")
            
            # 提供简单的备用发言
            backup_speeches = [
                f"作为{player_name}，我认为我们应该谨慎行事。",
                f"我是{player_name}，我相信团队合作的重要性。",
                f"作为{player_name}，我会尽力为团队做出贡献。",
                f"我是{player_name}，让我们共同努力完成任务。",
                f"作为{player_name}，我支持当前的决定。"
            ]
            import random
            return random.choice(backup_speeches)
        
        # 确定使用的模型
        if engine_name:
            actual_model = self._get_actual_model(engine_name)
        else:
            actual_model = self.default_model
            
        service_logger.log_ai_request_start(player_name, "speech", actual_model)
        start_time = time.time()
        
        try:
            prompt = self._build_speech_prompt(player_name, role, game_context)
            messages = [
                {"role": "system", "content": "你是一个阿瓦隆游戏中的AI玩家。请根据你的角色和当前游戏情况，给出有利于你的身份的发言，为了游戏胜利，你可以选择隐瞒自己的身份，或者伪装成别的身份，以欺骗对手。（发言控制在 200 字以内）"},
                {"role": "user", "content": prompt}
            ]
            
            # 使用超时控制
            if self.ai_provider == "zhipu":
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.chat.completions.create,
                        model=actual_model,
                        messages=messages,
                    ),
                    timeout=self.timeout
                )
                speech = response.choices[0].message.content.strip()
            elif self.ai_provider == "openai":
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=actual_model,
                        messages=messages,
                        max_tokens=100,
                        temperature=0.8
                    ),
                    timeout=self.timeout
                )
                speech = response.choices[0].message.content.strip()
            elif self.ai_provider == "anthropic":
                response = await asyncio.wait_for(
                    self.client.messages.create(
                        model=actual_model,
                        max_tokens=100,
                        messages=messages
                    ),
                    timeout=self.timeout
                )
                speech = response.content[0].text.strip()
            else:
                return None
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 记录成功日志
            service_logger.log_ai_request_end(player_name, "speech", True, duration)
            
            # 记录AI日志
            ai_logger.log_speech_request(
                model_name=actual_model,
                messages=messages,
                player_id=player_name,
                response=speech,
                start_time=start_time,
                end_time=end_time
            )
            
            print(f"AI {player_name} 获得发言: {speech}")
            return speech
            
        except asyncio.TimeoutError:
            end_time = time.time()
            duration = end_time - start_time
            error_msg = f"AI请求超时 ({self.timeout}s)"
            print(f"AI {player_name} 发言获取超时: {error_msg}")
            
            # 记录超时日志
            service_logger.log_timeout(f"AI发言请求 - {player_name}", self.timeout)
            service_logger.log_ai_request_end(player_name, "speech", False, duration, error_msg)
            
            # 记录错误日志
            ai_logger.log_speech_request(
                model_name=actual_model,
                messages=messages,
                player_id=player_name,
                error=error_msg,
                start_time=start_time,
                end_time=end_time
            )
            
            return None
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            error_msg = str(e)
            print(f"AI {player_name} 发言获取失败: {error_msg}")
            
            # 记录错误日志
            service_logger.log_ai_request_end(player_name, "speech", False, duration, error_msg)
            ai_logger.log_speech_request(
                model_name=actual_model,
                messages=messages,
                player_id=player_name,
                error=error_msg,
                start_time=start_time,
                end_time=end_time
            )
            
            return None

    async def get_ai_team_selection(self, player_name: str, role: str, game_context: Dict[str, Any], 
                                  available_players: List[str], team_size: int, engine_name: str = None) -> Optional[List[str]]:
        """获取AI玩家的队伍选择"""
        if not self.client:
            print(f"AI服务未初始化，{player_name} 使用默认队伍选择")
            return None
        
        # 确定使用的模型
        if engine_name:
            actual_model = self._get_actual_model(engine_name)
        else:
            actual_model = self.default_model
            
        try:
            prompt = self._build_team_selection_prompt(player_name, role, game_context, available_players, team_size)
            messages = [
                {"role": "system", "content": "你是一个阿瓦隆游戏中的AI玩家。请根据你的角色和当前游戏情况，选择最有利于你的身份的队伍成员。请只返回玩家名字，用逗号分隔，不要其他内容。"},
                {"role": "user", "content": prompt}
            ]
            
            start_time = time.time()
            
            if self.ai_provider == "zhipu":
                response = self.client.chat.completions.create(
                    model=actual_model,
                    messages=messages,
                )
                content = response.choices[0].message.content.strip()
            elif self.ai_provider == "openai":
                response = await self.client.chat.completions.create(
                    model=actual_model,
                    messages=messages,
                    max_tokens=50,
                    temperature=0.3
                )
                content = response.choices[0].message.content.strip()
            elif self.ai_provider == "anthropic":
                response = await self.client.messages.create(
                    model=actual_model,
                    max_tokens=50,
                    messages=messages
                )
                content = response.content[0].text.strip()
            else:
                return None
            
            end_time = time.time()
            
            # 记录日志
            ai_logger.log_team_selection_request(
                model_name=actual_model,
                messages=messages,
                player_id=player_name,
                response=content,
                start_time=start_time,
                end_time=end_time
            )
            
            # 解析选择的玩家
            selected_team = self._extract_player_names(content, available_players, team_size)
            if selected_team:
                print(f"AI {player_name} 选择队伍: {selected_team}")
                return selected_team
            else:
                print(f"AI {player_name} 队伍选择解析失败，使用备用逻辑")
                return None
                
        except Exception as e:
            end_time = time.time()
            error_msg = str(e)
            print(f"AI {player_name} 队伍选择获取失败: {error_msg}")
            
            # 记录错误日志
            ai_logger.log_team_selection_request(
                model_name=actual_model,
                messages=messages,
                player_id=player_name,
                error=error_msg,
                start_time=start_time,
                end_time=end_time
            )
            
            return None

    async def get_ai_vote_decision(self, player_name: str, role: str, game_context: Dict[str, Any], 
                                 vote_type: str, engine_name: str = None) -> Optional[str]:
        """获取AI玩家的投票决定"""
        if not self.client:
            print(f"AI服务未初始化，{player_name} 使用默认投票")
            return None
        
        # 确定使用的模型
        if engine_name:
            actual_model = self._get_actual_model(engine_name)
        else:
            actual_model = self.default_model
            
        try:
            prompt = self._build_vote_prompt(player_name, role, game_context, vote_type)
            messages = [
                {"role": "system", "content": "你是一个阿瓦隆游戏中的AI玩家。请根据你的角色和当前游戏情况，做出最有利于你的身份的投票决定。请只返回 'approve' 或 'reject'，不要其他内容。"},
                {"role": "user", "content": prompt}
            ]
            
            start_time = time.time()
            
            if self.ai_provider == "zhipu":
                response = self.client.chat.completions.create(
                    model=actual_model,
                    messages=messages,
                )
                content = response.choices[0].message.content.strip().lower()
            elif self.ai_provider == "openai":
                response = await self.client.chat.completions.create(
                    model=actual_model,
                    messages=messages,
                    max_tokens=10,
                    temperature=0.3
                )
                content = response.choices[0].message.content.strip().lower()
            elif self.ai_provider == "anthropic":
                response = await self.client.messages.create(
                    model=actual_model,
                    max_tokens=10,
                    messages=messages
                )
                content = response.content[0].text.strip().lower()
            else:
                return None
            
            end_time = time.time()
            
            # 记录日志
            ai_logger.log_vote_request(
                model_name=actual_model,
                messages=messages,
                player_id=player_name,
                vote_type=vote_type,
                response=content,
                start_time=start_time,
                end_time=end_time
            )
            
            # 解析投票决定
            if 'approve' in content:
                vote = 'approve'
            elif 'reject' in content:
                vote = 'reject'
            else:
                print(f"AI {player_name} 投票解析失败，使用默认投票")
                vote = 'approve'  # 默认同意
            
            print(f"AI {player_name} 投票决定: {vote}")
            return vote
            
        except Exception as e:
            end_time = time.time()
            error_msg = str(e)
            print(f"AI {player_name} 投票获取失败: {error_msg}")
            
            # 记录错误日志
            ai_logger.log_vote_request(
                model_name=actual_model,
                messages=messages,
                player_id=player_name,
                vote_type=vote_type,
                error=error_msg,
                start_time=start_time,
                end_time=end_time
            )
            
            return None

    async def get_ai_assassination_target(self, assassin_name: str, role: str, good_players: List[str], engine_name: str = None) -> Optional[str]:
        """获取AI刺客的刺杀目标"""
        if not self.client:
            print(f"AI服务未初始化，{assassin_name} 使用默认刺杀目标")
            return None
        
        # 确定使用的模型
        if engine_name:
            actual_model = self._get_actual_model(engine_name)
        else:
            actual_model = self.default_model
            
        try:
            prompt = f"""
            你是阿瓦隆游戏中的刺客 {assassin_name}，你的角色是 {role}。
            
            当前游戏中的好人玩家有: {', '.join(good_players)}
            
            请根据游戏中的信息，选择最可能是梅林的玩家进行刺杀。请只返回玩家名字，不要其他内容。
            """
            
            messages = [
                {"role": "system", "content": "你是一个阿瓦隆游戏中的AI刺客。请根据游戏中的信息，选择最可能是梅林的玩家进行刺杀。请只返回玩家名字，不要其他内容。"},
                {"role": "user", "content": prompt}
            ]
            
            start_time = time.time()
            
            if self.ai_provider == "zhipu":
                response = self.client.chat.completions.create(
                    model=actual_model,
                    messages=messages,
                )
                content = response.choices[0].message.content.strip()
            elif self.ai_provider == "openai":
                response = await self.client.chat.completions.create(
                    model=actual_model,
                    messages=messages,
                    max_tokens=20,
                    temperature=0.3
                )
                content = response.choices[0].message.content.strip()
            elif self.ai_provider == "anthropic":
                response = await self.client.messages.create(
                    model=actual_model,
                    max_tokens=20,
                    messages=messages
                )
                content = response.content[0].text.strip()
            else:
                return None
            
            end_time = time.time()
            
            # 记录日志
            ai_logger.log_assassination_request(
                model_name=actual_model,
                messages=messages,
                player_id=assassin_name,
                response=content,
                start_time=start_time,
                end_time=end_time
            )
            
            # 验证目标是否在好人列表中
            target = content.strip()
            if target in good_players:
                print(f"AI刺客 {assassin_name} 选择目标: {target}")
                return target
            else:
                print(f"AI刺客 {assassin_name} 选择的目标 {target} 不在好人列表中，随机选择")
                import random
                return random.choice(good_players)
                
        except Exception as e:
            end_time = time.time()
            error_msg = str(e)
            print(f"AI刺客 {assassin_name} 刺杀目标获取失败: {error_msg}")
            
            # 记录错误日志
            ai_logger.log_assassination_request(
                model_name=actual_model,
                messages=messages,
                player_id=assassin_name,
                error=error_msg,
                start_time=start_time,
                end_time=end_time
            )
            
            return None

    def _build_speech_prompt(self, player_name: str, role: str, game_context: Dict[str, Any]) -> str:
        """构建发言提示"""
        prompt = f"""
        你是阿瓦隆游戏中的玩家 {player_name}，你的角色是 {role}。

        当前游戏情况：
        - 游戏阶段: {game_context.get('phase', 'unknown')}
        - 当前任务: {game_context.get('current_mission', 'unknown')}
        - 任务结果: {game_context.get('mission_results', [])}
        - 投票结果: {game_context.get('vote_results', [])}
        - 其他玩家: {', '.join(game_context.get('other_players', []))}

        请根据你的角色和当前游戏情况，给出有利于你的身份的发言。为了游戏胜利，你可以选择隐瞒自己的身份，或者伪装成别的身份，以欺骗对手。发言控制在200字以内。
        """
        return prompt.strip()

    def _build_team_selection_prompt(self, player_name: str, role: str, game_context: Dict[str, Any], 
                                   available_players: List[str], team_size: int) -> str:
        """构建队伍选择提示"""
        prompt = f"""
        你是阿瓦隆游戏中的玩家 {player_name}，你的角色是 {role}。

        当前游戏情况：
        - 游戏阶段: {game_context.get('phase', 'unknown')}
        - 当前任务: {game_context.get('current_mission', 'unknown')}
        - 任务结果: {game_context.get('mission_results', [])}
        - 投票结果: {game_context.get('vote_results', [])}

        可选择的玩家: {', '.join(available_players)}
        需要选择的队伍大小: {team_size}

        请根据你的角色和当前游戏情况，选择最有利于你的身份的 {team_size} 个玩家组成队伍。请只返回玩家名字，用逗号分隔，不要其他内容。
        """
        return prompt.strip()

    def _build_vote_prompt(self, player_name: str, role: str, game_context: Dict[str, Any], vote_type: str) -> str:
        """构建投票提示"""
        prompt = f"""
        你是阿瓦隆游戏中的玩家 {player_name}，你的角色是 {role}。

        当前游戏情况：
        - 游戏阶段: {game_context.get('phase', 'unknown')}
        - 投票类型: {vote_type}
        - 当前任务: {game_context.get('current_mission', 'unknown')}
        - 任务结果: {game_context.get('mission_results', [])}
        - 投票结果: {game_context.get('vote_results', [])}

        请根据你的角色和当前游戏情况，对当前提议的队伍进行投票。请只返回 'approve' 或 'reject'，不要其他内容。
        """
        return prompt.strip()

    def _extract_player_names(self, content: str, available_players: List[str], team_size: int) -> Optional[List[str]]:
        """从AI回复中提取玩家名字"""
        try:
            # 清理内容
            content = content.strip().lower()
            
            # 尝试直接匹配玩家名字
            selected_players = []
            for player in available_players:
                if player.lower() in content:
                    selected_players.append(player)
            
            # 如果找到的玩家数量正确，返回结果
            if len(selected_players) == team_size:
                return selected_players
            
            # 如果数量不对，尝试其他解析方法
            # 移除常见的无关词汇
            content = content.replace('选择', '').replace('玩家', '').replace('队伍', '').replace('成员', '')
            
            # 按逗号分割
            parts = [p.strip() for p in content.split(',')]
            
            selected_players = []
            for part in parts:
                for player in available_players:
                    if player.lower() in part.lower():
                        selected_players.append(player)
                        break
            
            if len(selected_players) == team_size:
                return selected_players
            
            return None
            
        except Exception as e:
            print(f"解析玩家名字失败: {e}")
            return None

# 全局AI服务实例
ai_service = AIService() 