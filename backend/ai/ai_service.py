import asyncio
import datetime
import json
import os
from typing import Optional, Dict, Any, List, Callable
from dotenv import load_dotenv
from .model_client import ModelClientFactory, BaseModelClient, ModelCallResult, classify_api_error
from ..core.roles import (
    ROLES,
    get_game_description,
    get_team_description,
    get_decision_guidance,
    get_role_description,
)
from ..core.constants import VOTE_RULES
from ..core.log_manager import LogManager

# 加载环境变量
load_dotenv()


class AIService:
    def __init__(self, log_manager: LogManager = None, player_count: int = 5):
        self.ai_provider = os.getenv("AI_PROVIDER", "zhipu").lower()
        self.timeout = int(os.getenv("AI_RESPONSE_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("AI_MAX_RETRIES", "0"))
        self.fallback_enabled = os.getenv("AI_FALLBACK_ENABLED", "true").lower() == "true"
        self.log_manager = log_manager
        self.player_count = player_count

        # 使用工厂创建模型客户端
        try:
            self.model_client = ModelClientFactory.create_client(self.ai_provider)
            if self.log_manager and self.model_client:
                self.log_manager.set_model(self.model_client.model)
        except Exception as e:
            print(f"初始化AI服务失败: {e}")
            self.model_client = None

    def _log_player_llm_call(
        self,
        player_name: str,
        request_log: Dict[str, Any],
        response_log: Dict[str, Any],
        request_at: datetime.datetime,
        response_at: datetime.datetime,
    ) -> None:
        if self.log_manager:
            self.log_manager.log_player_interaction(
                player_name, request_log, response_log, request_at, response_at
            )

    def _build_response_log(self, result: ModelCallResult, **fields) -> Dict[str, Any]:
        response_log: Dict[str, Any] = {"success": result.success}
        response_log.update(fields)

        if result.success:
            if result.content is not None:
                if "content" not in response_log and "speech" not in response_log:
                    response_log["content"] = result.content
            else:
                response_log["success"] = False
                response_log["error"] = {
                    "type": "empty_response",
                    "message": "模型返回空内容",
                }
        elif result.error:
            response_log["error"] = result.error

        return response_log

    async def _call_model(
        self,
        player_name: str,
        request_log: Dict[str, Any],
        messages: List[Dict[str, str]],
        finalize_response: Optional[Callable[[ModelCallResult, Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> ModelCallResult:
        request_at = datetime.datetime.now()

        if not self.model_client:
            response_at = datetime.datetime.now()
            response_log = {
                "success": False,
                "error": {
                    "type": "service_unavailable",
                    "message": "AI模型客户端未初始化",
                },
            }
            self._log_player_llm_call(player_name, request_log, response_log, request_at, response_at)
            return ModelCallResult(success=False, error=response_log["error"])

        try:
            result = await self.model_client.chat_completion(messages)
            response_at = datetime.datetime.now()
            response_log = self._build_response_log(result)
            if finalize_response:
                response_log = finalize_response(result, response_log)
            self._log_player_llm_call(player_name, request_log, response_log, request_at, response_at)
            return result
        except Exception as e:
            response_at = datetime.datetime.now()
            error = classify_api_error(
                e,
                timeout_seconds=self.timeout,
                max_retries=self.max_retries,
            )
            response_log = {
                "success": False,
                "error": error,
            }
            self._log_player_llm_call(player_name, request_log, response_log, request_at, response_at)
            print(f"AI {player_name} 模型调用异常: {e}")
            return ModelCallResult(success=False, error=error)

    async def get_ai_speech(self, player_name: str, role: str, game_context: Dict[str, Any]) -> Optional[str]:
        """获取AI玩家的发言"""
        try:
            prompt = self._build_speech_prompt(player_name, role, game_context)

            # 根据当前玩家数量生成游戏说明
            game_description = get_game_description(self.player_count)

            # 生成角色信息和阵营说明
            players = game_context.get('players', [])
            role_description = get_role_description(role, player_name, players)
            team_description = get_team_description(role)

            # 构建详细的system prompt
            system_content = f"{game_description}\n\n{team_description}\n\n{role_description}"

            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ]

            request_log = {
                "action": "speech",
                "player_name": player_name,
                "role": role,
                "game_context": game_context,
                "messages": messages
            }

            def finalize_speech(result: ModelCallResult, response_log: Dict[str, Any]) -> Dict[str, Any]:
                if result.success and result.content:
                    response_log["speech"] = result.content
                return response_log

            result = await self._call_model(
                player_name, request_log, messages, finalize_response=finalize_speech
            )
            if result.success and result.content:
                print(f"AI {player_name} 获得发言: {result.content}")
                return result.content

        except Exception as e:
            print(f"AI {player_name} 发言获取失败: {e}")

        return None

    async def get_ai_team_selection(
        self,
        player_name: str,
        role: str,
        game_context: Dict[str, Any],
        available_players: List[str],
        team_size: int,
        current_team: Optional[List[str]] = None,
    ) -> Optional[List[str]]:
        """获取AI玩家的队伍选择；传入 current_team 时进入讨论后改队流程。"""
        is_revision = current_team is not None
        try:
            players = game_context.get('players', [])
            context = self._build_role_decision_context(role, player_name, players)
            if is_revision:
                task_prompt = self._build_team_revision_prompt(
                    player_name, role, game_context, available_players, team_size, current_team
                )
                system_content = (
                    "你是阿瓦隆游戏中的AI玩家。你已提议一支队伍并完成讨论，"
                    "请根据你的角色确认是否维持或调整队伍。"
                    "只返回JSON格式的增序排列的玩家名称列表。"
                )
                action = "team_revision"
            else:
                task_prompt = self._build_team_selection_prompt(
                    player_name, role, game_context, available_players, team_size
                )
                system_content = (
                    "你是阿瓦隆游戏中的AI玩家。请根据你的角色选择任务队伍。"
                    "只返回JSON格式的增序排列的玩家名称列表。"
                )
                action = "team_selection"

            user_content = f"{context}\n\n{task_prompt}"

            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ]

            request_log = {
                "action": action,
                "player_name": player_name,
                "role": role,
                "game_context": game_context,
                "available_players": available_players,
                "team_size": team_size,
                "messages": messages,
            }
            if is_revision:
                request_log["current_team"] = current_team

            def finalize_team(result: ModelCallResult, response_log: Dict[str, Any]) -> Dict[str, Any]:
                if not result.success or not result.content:
                    return response_log

                content = result.content
                response_log["content"] = content
                try:
                    team = json.loads(content)
                    if isinstance(team, list) and len(team) == team_size:
                        response_log["team"] = team
                except json.JSONDecodeError:
                    team = self._extract_player_names(content, available_players, team_size)
                    if team:
                        response_log["team"] = team
                        response_log["parse_method"] = "extract"
                return response_log

            result = await self._call_model(
                player_name, request_log, messages, finalize_response=finalize_team
            )
            content = result.content if result.success else None

            team = None
            if content:
                try:
                    team = json.loads(content)
                    if not (isinstance(team, list) and len(team) == team_size):
                        team = None
                except json.JSONDecodeError:
                    team = self._extract_player_names(content, available_players, team_size)

                if team:
                    print(f"AI {player_name} 选择队伍: {team}")

            return team
        except Exception as e:
            print(f"AI {player_name} 队伍选择失败: {e}")
            return None

    async def get_ai_vote_decision(self, player_name: str, role: str, game_context: Dict[str, Any],
                                 vote_type: str) -> Optional[str]:
        """获取AI玩家的投票决策"""
        try:
            players = game_context.get('players', [])
            context = self._build_role_decision_context(role, player_name, players)
            task_prompt = self._build_vote_prompt(player_name, role, game_context, vote_type)
            user_content = f"{context}\n\n{task_prompt}"

            vote_type_label = "队伍" if vote_type == "team" else "任务"
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"你是阿瓦隆游戏中的AI玩家。请根据你的角色进行{vote_type_label}投票。"
                        "只返回 'approve'/'reject' 或 'success'/'fail'。"
                    ),
                },
                {"role": "user", "content": user_content},
            ]

            request_log = {
                "action": "vote_decision",
                "player_name": player_name,
                "role": role,
                "game_context": game_context,
                "vote_type": vote_type,
                "messages": messages
            }

            def finalize_vote(result: ModelCallResult, response_log: Dict[str, Any]) -> Dict[str, Any]:
                if not result.success or not result.content:
                    return response_log

                raw_content = result.content
                content = raw_content.strip().lower()
                response_log["content"] = raw_content

                vote = None
                if vote_type == "team":
                    if "approve" in content or "赞成" in content:
                        vote = "approve"
                    elif "reject" in content or "反对" in content:
                        vote = "reject"
                elif vote_type == "mission":
                    if "fail" in content:
                        vote = "fail"
                    elif "success" in content:
                        vote = "success"

                response_log["vote"] = vote
                if vote is None:
                    response_log["parse_error"] = "无法从模型回复中解析投票结果"
                return response_log

            result = await self._call_model(
                player_name, request_log, messages, finalize_response=finalize_vote
            )

            vote = None
            if result.success and result.content:
                content = result.content.strip().lower()
                if vote_type == "team":
                    if "approve" in content or "赞成" in content:
                        vote = "approve"
                    elif "reject" in content or "反对" in content:
                        vote = "reject"
                elif vote_type == "mission":
                    if "fail" in content:
                        vote = "fail"
                    elif "success" in content:
                        vote = "success"
                print(f"AI {player_name} 投票决策: {result.content}")

            return vote
        except Exception as e:
            print(f"AI {player_name} 投票决策失败: {e}")
            return None

    # 以下是辅助方法
    def _build_role_decision_context(
        self,
        role: str,
        player_name: str,
        players: List[Dict[str, Any]],
    ) -> str:
        """拼装游戏背景、阵营策略与角色信息（与发言阶段一致，供投票/刺杀决策使用）。"""
        game_description = get_game_description(self.player_count)
        decision_guidance = get_decision_guidance(role)
        role_description = get_role_description(role, player_name, players)
        return f"{game_description}\n\n{decision_guidance}\n\n{role_description}"

    def _build_speech_prompt(self, player_name: str, role: str, game_context: Dict[str, Any]) -> str:
        phase = game_context.get('phase', '未知')
        current_mission = game_context.get('current_mission', 1)
        current_team = game_context.get('current_team', [])
        vote_context = game_context.get('vote_context', '')
        messages_history = game_context.get('messages_history', [])

        # 添加对话历史
        history_info = ""
        if messages_history:
            history_lines = []
            for msg in messages_history:
                history_lines.append(f"{msg['player']}说: {msg['content']}")
            history_info = "\n\n对话历史:\n" + '\n'.join(history_lines)

        context_info = ""
        if vote_context == "team_vote":
            context_info = f"当前需要对队伍 {current_team} 进行投票。"
        elif vote_context == "mission_vote":
            context_info = "你在任务队伍中，需要决定任务的成败。"
        elif vote_context == "assassination_discussion":
            discussion_round = game_context.get('assassination_discussion_round', 1)
            max_rounds = game_context.get('max_assassination_discussion_rounds', 3)
            context_info = (
                f"好人已获得 3 次任务成功，进入刺杀阶段。"
                f"当前是坏人阵营第 {discussion_round}/{max_rounds} 轮秘密讨论，"
                f"请与同伴交流你对梅林身份的推断，帮助刺客做出最终决定。"
                f"这是坏人之间的私下商议，可以坦诚分享你的判断。"
            )

        prompt = f"""
{history_info}
当前游戏状态：
- 阶段：{phase}
- 当前任务：第{current_mission}个
- 当前队伍：{current_team if current_team else '未选择'}
{context_info}
"""
        return prompt

    def _build_team_selection_prompt(self, player_name: str, role: str, game_context: Dict[str, Any],
                                   available_players: List[str], team_size: int) -> str:
        messages_history = game_context.get('messages_history', [])
        mission_results = game_context.get('mission_results', [])

        role_info = ROLES.get(role, {'name': role, 'team': 'unknown'})

        # 任务历史
        mission_info = ""
        if mission_results:
            mission_lines = [
                (
                    f"第{r['mission']}轮任务{'成功' if r['success'] else '失败'}，"
                    f"队伍 {r['team']}，"
                    f"{r.get('success_count', 0)}票成功 / {r.get('fail_count', 0)}票失败"
                )
                for r in mission_results
            ]
            mission_info = "\n\n任务历史:\n" + '\n'.join(mission_lines)

        # 添加对话历史
        history_info = ""
        if messages_history:
            history_lines = []
            for msg in messages_history:
                history_lines.append(f"{msg['player']}说: {msg['content']}")
            history_info = "\n\n对话历史:\n" + '\n'.join(history_lines)

        # 根据角色阵营生成策略建议
        if role_info['team'] == 'good':
            team_strategy = "尽量选择可信的玩家，避免选择可疑的玩家"
        elif role_info['team'] == 'evil':
            team_strategy = "考虑是否要破坏任务，选择有利于己方的玩家"
        else:
            team_strategy = "根据情况选择合适的玩家"

        prompt = f"""【选择队伍】
你作为队长，需要选出执行本次任务的队伍。
可选玩家：{available_players}
需要选择 {team_size} 名玩家组成任务队伍。
{mission_info}
请根据你的角色、阵营策略与对局信息选择队伍成员：
- {team_strategy}
{history_info}

返回JSON格式的增序排列的玩家座位号列表，例如：["1", "2"]
"""
        return prompt

    def _build_team_revision_prompt(
        self,
        player_name: str,
        role: str,
        game_context: Dict[str, Any],
        available_players: List[str],
        team_size: int,
        current_team: List[str],
    ) -> str:
        messages_history = game_context.get('messages_history', [])
        mission_results = game_context.get('mission_results', [])
        role_info = ROLES.get(role, {'name': role, 'team': 'unknown'})

        mission_info = ""
        if mission_results:
            mission_lines = [
                (
                    f"第{r['mission']}轮任务{'成功' if r['success'] else '失败'}，"
                    f"队伍 {r['team']}，"
                    f"{r.get('success_count', 0)}票成功 / {r.get('fail_count', 0)}票失败"
                )
                for r in mission_results
            ]
            mission_info = "\n\n任务历史:\n" + '\n'.join(mission_lines)

        history_info = ""
        if messages_history:
            history_lines = [
                f"{msg['player']}说: {msg['content']}"
                for msg in messages_history
            ]
            history_info = "\n\n讨论发言（含你对当前队伍的提议及众人意见）:\n" + '\n'.join(history_lines)

        if role_info['team'] == 'good':
            team_strategy = "尽量选择可信的玩家，避免选择可疑的玩家"
        elif role_info['team'] == 'evil':
            team_strategy = "考虑是否要破坏任务，选择有利于己方的玩家"
        else:
            team_strategy = "根据情况选择合适的玩家"

        return f"""【讨论后确认或调整队伍】
你作为队长，已提议当前任务队伍：{current_team}
全队刚完成针对该队伍的讨论发言，尚未正式投票。
可选玩家：{available_players}
需要 {team_size} 名玩家组成任务队伍。
{mission_info}

请根据讨论内容决定最终队伍：
- 若讨论中无人明确反对当前队伍，也没有令人信服的理由要求换人，应维持原队伍不变（返回与当前队伍相同的成员列表）
- 仅当有人提出有理有据的反对、或推荐了更合适的替代人选时，才调整队伍成员
- {team_strategy}
{history_info}

返回JSON格式的增序排列的玩家座位号列表。维持原队时返回与当前提议相同的列表，例如：{json.dumps(current_team)}
"""

    def _build_vote_prompt(self, player_name: str, role: str, game_context: Dict[str, Any], vote_type: str) -> str:
        current_team = game_context.get('current_team', [])
        messages_history = game_context.get('messages_history', [])
        role_info = ROLES.get(role, {'name': role, 'team': 'unknown'})

        history_info = ""
        if messages_history:
            history_lines = [
                f"{msg['player']}说: {msg['content']}"
                for msg in messages_history
            ]
            history_info = "\n\n对话历史:\n" + '\n'.join(history_lines)

        mission_summary = ""
        mission_results = game_context.get('mission_results', [])
        if mission_results:
            result_lines = []
            for result in mission_results:
                status = '成功' if result.get('success') else '失败'
                result_lines.append(
                    f"第{result.get('mission')}轮任务{status}，队伍 {result.get('team')}"
                )
            mission_summary = "\n\n任务历史:\n" + '\n'.join(result_lines)

        vote_info = VOTE_RULES.get(vote_type, {})

        if vote_type == "team":
            if role_info['team'] == 'good':
                vote_strategy = "支持可信的队伍，反对可疑的队伍"
            elif role_info['team'] == 'evil':
                vote_strategy = "根据策略需要决定支持或反对"
            else:
                vote_strategy = "根据情况决定投票"

            prompt = f"""【队伍投票】
当前提议的任务队伍：{current_team}

请根据你的角色、阵营策略与对局信息对这个队伍进行投票：
- {vote_strategy}
{mission_summary}
{history_info}

如果赞成（{vote_info.get('approve', '赞成')}），回答 "approve"
如果反对（{vote_info.get('reject', '反对')}），回答 "reject"
"""
        else:
            if role_info['team'] == 'good':
                vote_strategy = "总是投票成功，帮助队伍完成任务"
            elif role_info['team'] == 'evil':
                vote_strategy = "根据策略需要决定是否破坏任务"
            else:
                vote_strategy = "根据情况决定投票"

            prompt = f"""【任务投票】
你在任务队伍 {current_team} 中，需要对任务进行秘密投票：
- {vote_strategy}
{mission_summary}
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

    def _build_assassination_prompt(
        self,
        assassin_name: str,
        good_players: List[str],
        game_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        messages_history = (game_context or {}).get('messages_history', [])
        mission_results = (game_context or {}).get('mission_results', [])

        history_info = ""
        if messages_history:
            history_lines = [
                f"{msg['player']}说: {msg['content']}"
                for msg in messages_history
            ]
            history_info = "\n\n对话历史:\n" + '\n'.join(history_lines)

        mission_info = ""
        if mission_results:
            mission_lines = [
                (
                    f"第{r['mission']}轮任务{'成功' if r['success'] else '失败'}，"
                    f"队伍 {r['team']}"
                )
                for r in mission_results
            ]
            mission_info = "\n\n任务历史:\n" + '\n'.join(mission_lines)

        return f"""【刺杀阶段】
可刺杀的好人玩家：{good_players}
{mission_info}
请根据整场对局的发言与任务记录，选择一个你认为最可能是梅林的玩家进行刺杀。
{history_info}

只返回玩家座位号，例如：3
"""

    def _build_assassination_decision_prompt(
        self,
        assassin_name: str,
        good_players: List[str],
        game_context: Dict[str, Any],
        discussion_round: int,
        max_rounds: int,
    ) -> str:
        messages_history = game_context.get('messages_history', [])
        assassination_phase = game_context.get('phase', '刺杀阶段')

        discussion_lines = [
            f"{msg['player']}说: {msg['content']}"
            for msg in messages_history
            if msg.get('phase') == assassination_phase
        ]
        discussion_info = ""
        if discussion_lines:
            discussion_info = "\n\n本轮坏人阵营讨论:\n" + '\n'.join(discussion_lines)

        remaining_rounds = max_rounds - discussion_round
        if remaining_rounds > 0:
            continue_hint = (
                f"你还可以选择继续讨论（剩余 {remaining_rounds} 轮讨论机会），"
                f"或现在就选定刺杀目标。"
            )
        else:
            continue_hint = "这是最后一轮讨论，讨论结束后你必须立即选定刺杀目标。"

        return f"""【刺客决策】
你是刺客 {assassin_name}，刚完成第 {discussion_round}/{max_rounds} 轮坏人阵营讨论。
可刺杀的好人玩家：{good_players}
{discussion_info}

{continue_hint}

请做出决策：
- 若需要继续讨论，只回答 continue
- 若决定行刺，只回答 assassinate:玩家座位号（例如 assassinate:3）
"""

    async def get_ai_assassination_decision(
        self,
        assassin_name: str,
        role: str,
        good_players: List[str],
        game_context: Dict[str, Any],
        discussion_round: int,
        max_rounds: int,
    ) -> Optional[str]:
        """获取刺客决策：continue 或 assassinate:目标"""
        try:
            players = game_context.get('players', [])
            context = self._build_role_decision_context(role, assassin_name, players)
            task_prompt = self._build_assassination_decision_prompt(
                assassin_name, good_players, game_context, discussion_round, max_rounds
            )
            user_content = f"{context}\n\n{task_prompt}"

            messages = [
                {
                    "role": "system",
                    "content": (
                        "你是阿瓦隆游戏中的刺客。"
                        "根据坏人阵营讨论，决定继续讨论或立即行刺。"
                        "只回答 continue 或 assassinate:玩家座位号。"
                    ),
                },
                {"role": "user", "content": user_content},
            ]

            request_log = {
                "action": "assassination_decision",
                "player_name": assassin_name,
                "role": role,
                "discussion_round": discussion_round,
                "good_players": good_players,
                "game_context": game_context,
                "messages": messages,
            }

            def finalize_decision(result: ModelCallResult, response_log: Dict[str, Any]) -> Dict[str, Any]:
                if not result.success or not result.content:
                    return response_log

                raw = result.content.strip()
                response_log["content"] = raw
                normalized = raw.lower().replace('：', ':').strip()

                if normalized == 'continue':
                    response_log["decision"] = 'continue'
                elif normalized.startswith('assassinate:'):
                    target = normalized.split(':', 1)[1].strip()
                    response_log["decision"] = 'assassinate'
                    response_log["target"] = target
                elif normalized in good_players:
                    response_log["decision"] = 'assassinate'
                    response_log["target"] = normalized
                return response_log

            result = await self._call_model(
                assassin_name, request_log, messages, finalize_response=finalize_decision
            )

            if not result.success or not result.content:
                return None

            normalized = result.content.strip().lower().replace('：', ':')
            if normalized == 'continue':
                return 'continue'

            if normalized.startswith('assassinate:'):
                target = normalized.split(':', 1)[1].strip()
                if target in good_players:
                    return target

            if result.content.strip() in good_players:
                return result.content.strip()

        except Exception as e:
            print(f"AI {assassin_name} 刺杀决策失败: {e}")

        return None

    async def get_ai_assassination_target(
        self,
        assassin_name: str,
        role: str,
        good_players: List[str],
        game_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """获取AI刺客的刺杀目标"""
        try:
            players = (game_context or {}).get('players', [])
            context = self._build_role_decision_context(role, assassin_name, players)
            task_prompt = self._build_assassination_prompt(assassin_name, good_players, game_context)
            user_content = f"{context}\n\n{task_prompt}"

            messages = [
                {"role": "system", "content": "你是阿瓦隆游戏中的刺客。请选择刺杀目标，只返回玩家座位号。"},
                {"role": "user", "content": user_content},
            ]

            request_log = {
                "action": "assassination",
                "player_name": assassin_name,
                "role": role,
                "good_players": good_players,
                "game_context": game_context,
                "messages": messages,
            }

            def finalize_assassination(result: ModelCallResult, response_log: Dict[str, Any]) -> Dict[str, Any]:
                if not result.success or not result.content:
                    return response_log

                target = result.content.strip()
                response_log["content"] = result.content
                if target in good_players:
                    response_log["target"] = target
                else:
                    response_log["parse_error"] = f"模型返回的目标不在可选列表中: {target}"
                return response_log

            result = await self._call_model(
                assassin_name, request_log, messages, finalize_response=finalize_assassination
            )

            if result.success and result.content and result.content.strip() in good_players:
                return result.content.strip()

        except Exception as e:
            print(f"AI {assassin_name} 刺杀目标选择失败: {e}")

        return None


# 全局AI服务实例（延迟初始化LogManager）
ai_service = AIService(log_manager=None)

# 注意：实际使用时，应在游戏开始时创建新的LogManager实例并传递给AIService
# 这样可以避免在启动后端时就创建空的日志目录
