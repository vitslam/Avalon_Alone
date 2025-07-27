import os
import asyncio
import json
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class AIService:
    def __init__(self):
        self.ai_provider = os.getenv("AI_PROVIDER", "zhipu").lower()
        self.timeout = int(os.getenv("AI_RESPONSE_TIMEOUT", "30"))
        self.fallback_enabled = os.getenv("AI_FALLBACK_ENABLED", "true").lower() == "true"
        
        # 初始化对应的AI客户端
        self.client = None
        if self.ai_provider == "zhipu":
            self._init_zhipu_client()
        elif self.ai_provider == "openai":
            self._init_openai_client()
        else:
            print(f"警告: 不支持的AI提供商: {self.ai_provider}")

    def _init_zhipu_client(self):
        """初始化智谱AI客户端"""
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            print("警告: 未找到 ZHIPU_API_KEY 环境变量")
            return
            
        try:
            from zhipuai import ZhipuAI
            self.client = ZhipuAI(api_key=api_key)
            print("✅ 智谱AI客户端初始化成功")
        except ImportError:
            print("错误: zhipuai 包未安装，请运行: pip install zhipuai")
        except Exception as e:
            print(f"智谱AI客户端初始化失败: {e}")

    def _init_openai_client(self):
        """初始化OpenAI客户端"""
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        if not api_key:
            print("警告: 未找到 OPENAI_API_KEY 环境变量")
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
        except ImportError:
            print("错误: openai 包未安装，请运行: pip install openai")
        except Exception as e:
            print(f"OpenAI客户端初始化失败: {e}")

    async def get_ai_speech(self, player_name: str, role: str, game_context: Dict[str, Any]) -> Optional[str]:
        """获取AI玩家的发言"""
        if not self.client:
            print(f"AI服务未初始化，{player_name} 使用默认发言")
            return None
            
        try:
            prompt = self._build_speech_prompt(player_name, role, game_context)
            
            if self.ai_provider == "zhipu":
                response = self.client.chat.completions.create(
                    model="glm-4-flash",
                    messages=[
                        {"role": "system", "content": "你是一个阿瓦隆游戏中的AI玩家。请根据你的角色和当前游戏情况，给出简短的发言（不超过50字）。"},
                        {"role": "user", "content": prompt}
                    ],
                )
            elif self.ai_provider == "openai":
                response = await self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "你是一个阿瓦隆游戏中的AI玩家。请根据你的角色和当前游戏情况，给出简短的发言（不超过50字）。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=100,
                    temperature=0.8
                )
            else:
                return None
            
            speech = response.choices[0].message.content.strip()
            print(f"AI {player_name} 获得发言: {speech}")
            return speech
            
        except Exception as e:
            print(f"AI {player_name} 发言获取失败: {e}")
            return None

    async def get_ai_team_selection(self, player_name: str, role: str, game_context: Dict[str, Any], 
                                  available_players: List[str], team_size: int) -> Optional[List[str]]:
        """获取AI玩家的队伍选择"""
        if not self.client:
            return None
            
        try:
            prompt = self._build_team_selection_prompt(player_name, role, game_context, available_players, team_size)
            
            if self.ai_provider == "zhipu":
                response = self.client.chat.completions.create(
                    model="glm-4-flash",
                    messages=[
                        {"role": "system", "content": "你是阿瓦隆游戏中的AI玩家。请根据你的角色选择任务队伍。只返回JSON格式的玩家名称列表。"},
                        {"role": "user", "content": prompt}
                    ],
                )
            elif self.ai_provider == "openai":
                response = await self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "你是阿瓦隆游戏中的AI玩家。请根据你的角色选择任务队伍。只返回JSON格式的玩家名称列表。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200,
                    temperature=0.7
                )
            else:
                return None
            
            content = response.choices[0].message.content.strip()
            # 尝试解析JSON
            try:
                team = json.loads(content)
                if isinstance(team, list) and len(team) == team_size:
                    print(f"AI {player_name} 选择队伍: {team}")
                    return team
            except json.JSONDecodeError:
                # 如果不是JSON，尝试提取玩家名称
                team = self._extract_player_names(content, available_players, team_size)
                if team:
                    print(f"AI {player_name} 选择队伍(提取): {team}")
                    return team
                    
        except Exception as e:
            print(f"AI {player_name} 队伍选择失败: {e}")
            
        return None

    async def get_ai_vote_decision(self, player_name: str, role: str, game_context: Dict[str, Any], 
                                 vote_type: str) -> Optional[str]:
        """获取AI玩家的投票决策"""
        if not self.client:
            return None
            
        try:
            prompt = self._build_vote_prompt(player_name, role, game_context, vote_type)
            
            if self.ai_provider == "zhipu":
                response = self.client.chat.completions.create(
                    model="glm-4-flash",
                    messages=[
                        {"role": "system", "content": f"你是阿瓦隆游戏中的AI玩家。请根据你的角色进行{vote_type}投票。只返回 'approve'/'reject' 或 'success'/'fail'。"},
                        {"role": "user", "content": prompt}
                    ],
                )
            elif self.ai_provider == "openai":
                response = await self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": f"你是阿瓦隆游戏中的AI玩家。请根据你的角色进行{vote_type}投票。只返回 'approve'/'reject' 或 'success'/'fail'。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=50,
                    temperature=0.5
                )
            else:
                return None
            
            content = response.choices[0].message.content.strip().lower()
            
            if vote_type == "team":
                if "approve" in content or "赞成" in content:
                    return "approve"
                elif "reject" in content or "反对" in content:
                    return "reject"
            elif vote_type == "mission":
                if "success" in content or "成功" in content:
                    return "success"
                elif "fail" in content or "失败" in content:
                    return "fail"
                    
            print(f"AI {player_name} 投票决策: {content}")
            
        except Exception as e:
            print(f"AI {player_name} 投票决策失败: {e}")
            
        return None

    async def get_ai_assassination_target(self, assassin_name: str, role: str, good_players: List[str]) -> Optional[str]:
        """获取AI刺客的刺杀目标"""
        if not self.client:
            return None
            
        try:
            prompt = f"""
你是阿瓦隆游戏中的刺客 {assassin_name}。

可刺杀的好人玩家：{good_players}

请选择一个你认为最可能是梅林的玩家进行刺杀。只返回玩家名称。
"""
            
            if self.ai_provider == "zhipu":
                response = self.client.chat.completions.create(
                    model="glm-4-flash",
                    messages=[
                        {"role": "system", "content": "你是阿瓦隆游戏中的刺客。请选择刺杀目标。"},
                        {"role": "user", "content": prompt}
                    ],
                )
            elif self.ai_provider == "openai":
                response = await self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "你是阿瓦隆游戏中的刺客。请选择刺杀目标。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=50,
                    temperature=0.5
                )
            else:
                return None
            
            target = response.choices[0].message.content.strip()
            if target in good_players:
                return target
                
        except Exception as e:
            print(f"AI {assassin_name} 刺杀目标选择失败: {e}")
            
        return None

    def _build_speech_prompt(self, player_name: str, role: str, game_context: Dict[str, Any]) -> str:
        """构建发言提示词"""
        phase = game_context.get('phase', '未知')
        current_mission = game_context.get('current_mission', 1)
        current_team = game_context.get('current_team', [])
        vote_context = game_context.get('vote_context', '')
        
        role_names = {
            'merlin': '梅林',
            'percival': '派西维尔', 
            'loyal_servant': '忠臣',
            'morgana': '莫甘娜',
            'assassin': '刺客',
            'oberon': '奥伯伦',
            'mordred': '莫德雷德',
            'minion': '爪牙'
        }
        
        role_display = role_names.get(role, role)
        
        context_info = ""
        if vote_context == "team_vote":
            context_info = f"当前需要对队伍 {current_team} 进行投票。"
        elif vote_context == "mission_vote":
            context_info = "你在任务队伍中，需要决定任务的成败。"
        
        prompt = f"""
你是阿瓦隆游戏中的玩家 {player_name}，你的角色是 {role_display}。

当前游戏状态：
- 阶段：{phase}
- 当前任务：第{current_mission}个
- 当前队伍：{current_team if current_team else '未选择'}
{context_info}

请根据你的角色和当前情况发言，要简洁有趣（不超过30字）。体现你的角色特点和策略思考。
"""
        return prompt

    def _build_team_selection_prompt(self, player_name: str, role: str, game_context: Dict[str, Any], 
                                   available_players: List[str], team_size: int) -> str:
        """构建队伍选择提示词"""
        role_names = {
            'merlin': '梅林（好人领袖，知道坏人身份但不能暴露）',
            'percival': '派西维尔（好人，知道梅林和莫甘娜但不知道谁是谁）',
            'loyal_servant': '忠臣（普通好人）',
            'morgana': '莫甘娜（坏人，伪装成梅林）',
            'assassin': '刺客（坏人，负责最后刺杀梅林）',
            'oberon': '奥伯伦（独立坏人，不知道其他坏人身份）',
            'mordred': '莫德雷德（坏人，对梅林隐身）',
            'minion': '爪牙（普通坏人）'
        }
        
        role_desc = role_names.get(role, role)
        
        prompt = f"""
你是阿瓦隆游戏中的玩家 {player_name}，你的角色是 {role_desc}。

可选玩家：{available_players}
需要选择 {team_size} 名玩家组成任务队伍。

请根据你的角色特点和策略选择队伍成员：
- 如果你是好人，尽量选择可信的玩家
- 如果你是坏人，考虑是否要破坏任务

返回JSON格式的玩家名称列表，例如：["玩家1", "玩家2"]
"""
        return prompt

    def _build_vote_prompt(self, player_name: str, role: str, game_context: Dict[str, Any], vote_type: str) -> str:
        """构建投票提示词"""
        current_team = game_context.get('current_team', [])
        
        role_names = {
            'merlin': '梅林（好人领袖）',
            'percival': '派西维尔（好人）', 
            'loyal_servant': '忠臣（好人）',
            'morgana': '莫甘娜（坏人）',
            'assassin': '刺客（坏人）',
            'oberon': '奥伯伦（坏人）',
            'mordred': '莫德雷德（坏人）',
            'minion': '爪牙（坏人）'
        }
        
        role_desc = role_names.get(role, role)
        
        if vote_type == "team":
            prompt = f"""
你是阿瓦隆游戏中的玩家 {player_name}，你的角色是 {role_desc}。

当前提议的任务队伍：{current_team}

请根据你的角色对这个队伍进行投票：
- 好人角色：支持可信的队伍，反对可疑的队伍
- 坏人角色：根据策略需要决定支持或反对

如果赞成，回答 "approve"
如果反对，回答 "reject"
"""
        else:  # mission
            prompt = f"""
你是阿瓦隆游戏中的玩家 {player_name}，你的角色是 {role_desc}。

你在任务队伍中，需要对任务进行投票：
- 好人角色：总是投票成功
- 坏人角色：可以选择破坏任务

如果希望任务成功，回答 "success"  
如果希望任务失败，回答 "fail"
"""
        
        return prompt

    def _extract_player_names(self, content: str, available_players: List[str], team_size: int) -> Optional[List[str]]:
        """从文本中提取玩家名称"""
        selected = []
        for player in available_players:
            if player in content and len(selected) < team_size:
                selected.append(player)
        
        return selected if len(selected) == team_size else None

# 全局AI服务实例
ai_service = AIService() 