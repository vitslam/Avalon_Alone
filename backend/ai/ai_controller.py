"""
AI控制器 - 负责AI玩家的自动决策和游戏流程控制
"""

import asyncio
import os
import random
from typing import Dict, List, Optional, Callable, Any, Awaitable
from ..core.constants import GAME_PHASES, GAME_STATES, MAX_ASSASSINATION_DISCUSSION_ROUNDS
from ..core.roles import ROLES
from .ai_service import ai_service
from ..core.log_manager import LogManager

try:
    from config import GAME_CONFIG
except ImportError:
    GAME_CONFIG = {}


class AIController:
    def __init__(self, game, websocket_notifier: Optional[Callable] = None):
        self.game = game
        self.websocket_notifier = websocket_notifier
        self.ai_players = [p for p in game.players if p.is_ai]
        self.is_running = False
        self.auto_delay = 0.1
        self.current_speaker = None
        self.log_manager = LogManager()
        # 更新AI服务的日志管理器
        global ai_service
        ai_service = ai_service.__class__(self.log_manager, player_count=len(self.game.players))

        # 发言节奏控制：后端按估算的朗读时长自行推进，不再阻塞等待前端语音回调
        # 这样多个观众可以各自用本地 TTS 播放，互不影响，刷新/关闭页面也不会卡死后端
        self.base_speech_seconds = 0.8
        self.per_char_seconds = 0.18
        self.min_speech_seconds = 2.0
        self.team_vote_result_pause = 4.0
        self.speech_prefetch_size = max(
            0,
            int(GAME_CONFIG.get(
                'speech_prefetch_size',
                os.getenv('AVALON_SPEECH_PREFETCH_SIZE', '1'),
            )),
        )
    async def start_auto_play(self):
        """开始AI自动游戏"""
        if not self.ai_players:
            print("没有AI玩家，退出自动游戏")
            return

        self.is_running = True
        print(f"AI控制器启动，管理 {len(self.ai_players)} 个AI玩家，发言预取深度={self.speech_prefetch_size}")

        # 检查游戏是否已经开始，如果没有则开始游戏
        if self.game.state == GAME_STATES['waiting']:
            print("开始新游戏")
            game_start_result = self.game.start_game()

            for entry in self.game.get_chat_log():
                await self.notify_frontend('chat_log_entry', entry)

            # 记录游戏开始和角色分配信息到全局日志
            if 'role_assignments' in game_start_result:
                self.log_manager.log_game_start_with_roles(
                    role_assignments=game_start_result['role_assignments']
                )
                print(f"游戏角色分配已记录到全局日志")

        # 记录游戏开始事件
        game_start_data = {
            "players": [p.name for p in self.game.players],
            "ai_players": [p.name for p in self.ai_players],
            "game_id": self.log_manager.get_game_id()
        }
        self.log_manager.log_global_event("game_start", game_start_data)
        print(f"游戏日志将保存到: {self.log_manager.get_game_log_dir()}")

        loop_count = 0
        while self.is_running and self.game.state == GAME_STATES['playing']:
            loop_count += 1
            print(f"\n=== AI循环 {loop_count} ===")
            print(f"游戏状态: {self.game.state}")
            print(f"游戏阶段: {self.game.phase}")

            game_state_data = {
                "state": self.game.state,
                "phase": self.game.phase,
                "round": self.game.current_round,
                "mission": self.game.current_mission
            }
            self.log_manager.log_global_event("game_state", game_state_data)

            await self.process_current_phase()

            if self.game.state == GAME_STATES['finished']:
                print("游戏结束！")
                break

            if loop_count > 200:
                print("达到最大循环次数，停止AI控制器")
                break

            await asyncio.sleep(self.auto_delay)

        game_end_data = {
            "loop_count": loop_count,
            "state": self.game.state
        }
        self.log_manager.log_global_event("game_end", game_end_data)
        print(f"AI控制器结束，总共执行了 {loop_count} 次循环")
        print(f"游戏日志已保存到: {self.log_manager.get_game_log_dir()}")

    async def stop_auto_play(self):
        """停止AI自动游戏"""
        self.is_running = False
        print("AI控制器已停止")

    async def process_current_phase(self):
        """处理当前游戏阶段"""
        phase = self.game.phase
        print(f"处理阶段: {phase}")

        if phase == GAME_PHASES['team_selection']:
            await self.handle_team_selection()
        elif phase == GAME_PHASES['team_vote']:
            await self.handle_team_vote()
        elif phase == GAME_PHASES['mission_vote']:
            await self.handle_mission_vote()
        elif phase == GAME_PHASES['assassination']:
            await self.handle_assassination()
        else:
            print(f"未知阶段: {phase}，等待...")
            await asyncio.sleep(1)

    async def handle_team_selection(self):
        """处理队伍选择阶段"""
        current_leader = self.game.players[self.game.current_leader_index]

        team_selection_data = {
            "leader": current_leader.name,
            "mission_number": self.game.current_mission
        }
        self.log_manager.log_global_event("team_selection_start", team_selection_data)

        if current_leader.is_ai:
            print(f"AI队长 {current_leader.name} 开始选择队伍")

            await self.ai_speak(current_leader, "我来选择这次任务的队伍成员...")

            mission_config = self.game.get_mission_config()
            if not mission_config:
                print("无法获取任务配置")
                return

            team_size = mission_config['team_size']
            available_players = self.game.get_available_players()

            selected_team = await self._ai_select_team_with_llm(current_leader, available_players, team_size)

            if not selected_team:
                print(f"AI API失败，使用备用逻辑为 {current_leader.name}")
                selected_team = self.ai_select_team(current_leader, available_players, team_size)

            if selected_team:
                print(f"队长 {current_leader.name} 选择队伍: {selected_team}")

                team_selected_data = {
                    "leader": current_leader.name,
                    "team": selected_team
                }
                self.log_manager.log_global_event("team_selected", team_selected_data)

                team_announcement = f"我选择的队伍成员是：{', '.join(selected_team)}"
                await self.ai_speak(current_leader, team_announcement)

                result = self.game.select_team(selected_team)
                if 'error' not in result:
                    await self._publish_chat(
                        '系统',
                        f"队伍已选择: {', '.join(result['team'])}",
                        'system',
                    )
                    await self.notify_frontend("team_selected", result)
                else:
                    print(f"队伍选择失败: {result['error']}")

    async def handle_team_vote(self):
        """处理队伍投票阶段：①依次发言讨论 ②队长二次确认/修改队伍 ③全员统一投票"""
        print("处理队伍投票阶段")

        self.log_manager.log_global_event("team_vote_start", {
            "team": self.game.current_team,
            "mission_number": self.game.current_mission
        })

        n = len(self.game.players)
        start = self.game.current_leader_index

        # 阶段1：从队长开始依次发言（仅讨论，不投票），支持预取后续玩家发言
        print("队伍投票-阶段1：依次发言讨论")
        discussion_players = [
            self.game.players[(start + i) % n]
            for i in range(n)
            if self.game.players[(start + i) % n].is_ai
        ]
        await self._run_prefetched_speeches(
            discussion_players,
            self._get_ai_team_vote_speech,
        )

        # 阶段2：队长根据讨论二次确认或修改队伍
        print("队伍投票-阶段2：队长二次确认/修改队伍")
        await self._leader_revise_team()

        # 阶段3：全员并行投票（官方规则：同时表决，不发言）
        print("队伍投票-阶段3：全员并行投票")
        total_players = len(self.game.players)
        voted_names = {v['player'] for v in self.game.team_votes}
        ai_pending = [
            p for p in self.game.players
            if p.is_ai and p.name not in voted_names
        ]

        self.log_manager.log_global_event("team_vote_phase_start", {
            "team": self.game.current_team,
            "mission_number": self.game.current_mission,
            "total_players": total_players,
            "voted_count": len(self.game.team_votes),
        })
        await self.notify_frontend("team_vote_phase_start", {
            "team": self.game.current_team,
            "mission_number": self.game.current_mission,
            "total_players": total_players,
            "voted_count": len(self.game.team_votes),
        })

        if not ai_pending:
            return

        async def fetch_team_vote(player):
            vote = await self._ai_decide_team_vote_with_llm(player)
            if not vote:
                print(f"AI API失败，使用发言解析/兜底逻辑为 {player.name}")
                vote = self.ai_decide_team_vote(player)
            return player, vote

        tasks = [asyncio.create_task(fetch_team_vote(p)) for p in ai_pending]
        final_result = None

        for task in asyncio.as_completed(tasks):
            player, vote = await task
            if not vote:
                continue

            print(f"AI玩家 {player.name} 投票: {vote}")
            self.log_manager.log_global_event("team_vote", {
                "player": player.name,
                "vote": vote,
                "team": self.game.current_team
            })

            result = self.game.vote_team(player.name, vote)
            if 'error' in result:
                print(f"投票失败: {result['error']}")
                continue

            await self.notify_frontend("team_vote_progress", {
                "voted_count": result.get('voted_count', len(self.game.team_votes)),
                "total_players": total_players,
            })

            if result.get('status') in ['team_approved', 'team_rejected', 'evil_win']:
                final_result = result

        if final_result:
            print(f"队伍投票完成，结果: {final_result.get('status')}")
            await self._notify_team_vote_completed(final_result)
            await asyncio.sleep(self.team_vote_result_pause)

    async def _leader_revise_team(self):
        """队长在讨论后二次确认或修改队伍成员"""
        current_leader = self.game.players[self.game.current_leader_index]
        if not current_leader.is_ai:
            return

        mission_config = self.game.get_mission_config()
        if not mission_config:
            return

        team_size = mission_config['team_size']
        available_players = self.game.get_available_players()
        original_team = list(self.game.current_team)

        revised_team = await self._ai_revise_team_with_llm(
            current_leader, available_players, team_size, original_team
        )
        if not revised_team:
            revised_team = self.ai_select_team(current_leader, available_players, team_size)

        # 维持原队伍
        if not revised_team or set(revised_team) == set(original_team):
            await self.ai_speak(
                current_leader,
                f"听完大家的发言，我决定维持原队伍不变：{', '.join(original_team)}，现在开始投票。"
            )
            return

        # 修改队伍
        result = self.game.revise_team(revised_team)
        if 'error' in result:
            print(f"队伍修改失败: {result['error']}，维持原队伍")
            await self.ai_speak(
                current_leader,
                f"我维持原队伍：{', '.join(original_team)}，现在开始投票。"
            )
            return

        self.log_manager.log_global_event("team_revised", {
            "leader": current_leader.name,
            "old_team": original_team,
            "new_team": revised_team
        })
        await self.ai_speak(
            current_leader,
            f"听完大家的发言，我决定调整队伍为：{', '.join(revised_team)}，现在开始投票。"
        )
        await self._publish_chat(
            '系统',
            f"队伍已选择: {', '.join(result['team'])}",
            'system',
        )
        await self.notify_frontend("team_selected", result)

    async def handle_mission_vote(self):
        """处理任务投票阶段：好人固定 success，坏人并行 LLM 决策（秘密表决，不发言）"""
        print("处理任务投票阶段")

        total_team_members = len(self.game.current_team)
        voted_names = {v['player'] for v in self.game.mission_votes}
        voted_members = len(self.game.mission_votes)

        print(f"任务投票进度: {voted_members}/{total_team_members}")

        if voted_members >= total_team_members:
            print("所有队伍成员已完成任务投票，等待游戏状态更新...")
            return

        mission_vote_data = {
            "team": self.game.current_team,
            "mission_number": self.game.current_mission,
            "total_team_members": total_team_members,
            "voted_count": voted_members,
        }
        self.log_manager.log_global_event("mission_vote_start", mission_vote_data)

        ai_pending = [
            p for p in self.ai_players
            if p.name in self.game.current_team and p.name not in voted_names
        ]

        if not ai_pending:
            return

        async def fetch_mission_vote(player):
            vote = await self._decide_mission_vote_for_player(player)
            return player, vote

        tasks = [asyncio.create_task(fetch_mission_vote(p)) for p in ai_pending]
        final_result = None

        for task in asyncio.as_completed(tasks):
            player, vote = await task
            if not vote:
                continue

            print(f"AI队伍成员 {player.name} 任务投票: {vote}")
            self.log_manager.log_global_event("mission_vote", {
                "player": player.name,
                "vote": vote,
                "mission_number": self.game.current_mission,
            })

            result = self.game.vote_mission(player.name, vote)
            if 'error' in result:
                print(f"任务投票失败: {result['error']}")
                continue

            await self.notify_frontend("mission_vote_recorded", result)

            if result.get('status') in ['good_mission_win', 'evil_win', 'mission_completed']:
                final_result = result
                if result.get('status') in ('mission_completed', 'good_mission_win'):
                    self._schedule_round_discussion_compress()

        if final_result:
            print(f"任务投票完成，结果: {final_result.get('status')}")
            await self._publish_mission_vote_chat(final_result)

    async def handle_assassination(self):
        """处理刺杀阶段：坏人阵营多轮讨论后由刺客决定行刺或继续讨论。"""
        print("处理刺杀阶段")

        assassination_data = {
            "mission_results": self.game.mission_results,
            "max_rounds": MAX_ASSASSINATION_DISCUSSION_ROUNDS,
        }
        self.log_manager.log_global_event("assassination_start", assassination_data)

        assassin = self.game.get_assassin()
        if not assassin:
            print("未找到刺客，跳过刺杀阶段")
            return

        good_players = [
            p.name for p in self.game.players
            if p.role in ['merlin', 'percival', 'loyal_servant']
        ]
        if not good_players:
            print("没有可刺杀的好人玩家")
            return

        evil_players = self.game.get_evil_players_from_assassin()
        print(
            f"刺杀讨论开始，刺客 {assassin.name}，"
            f"坏人发言顺序: {[p.name for p in evil_players]}"
        )

        await self._publish_chat(
            '系统',
            f"进入刺杀阶段，坏人从刺客起按座位顺序讨论（最多 {MAX_ASSASSINATION_DISCUSSION_ROUNDS} 轮）",
            'system',
        )
        await self.notify_frontend("assassination_discussion_start", {
            "assassin": assassin.name,
            "evil_players": [p.name for p in evil_players],
            "max_rounds": MAX_ASSASSINATION_DISCUSSION_ROUNDS,
        })

        for round_num in range(1, MAX_ASSASSINATION_DISCUSSION_ROUNDS + 1):
            self.game.assassination_discussion_round = round_num

            await self._publish_chat(
                '系统',
                f"刺杀讨论第 {round_num}/{MAX_ASSASSINATION_DISCUSSION_ROUNDS} 轮开始",
                'system',
            )
            await self.notify_frontend("assassination_round_start", {
                "round": round_num,
                "max_rounds": MAX_ASSASSINATION_DISCUSSION_ROUNDS,
                "evil_players": [p.name for p in evil_players],
            })

            await self._run_prefetched_speeches(
                evil_players,
                self._get_ai_assassination_discussion_speech,
            )

            must_assassinate = round_num >= MAX_ASSASSINATION_DISCUSSION_ROUNDS
            if must_assassinate:
                target = await self._resolve_assassination_target(assassin, good_players)
                if target:
                    await self._execute_assassination(assassin, target)
                return

            decision = await self._ai_assassination_decision_with_llm(
                assassin, good_players, round_num
            )
            if decision == 'continue':
                print(f"刺客 {assassin.name} 选择继续第 {round_num + 1} 轮讨论")
                continue

            target = decision if decision in good_players else None
            if not target:
                target = await self._resolve_assassination_target(assassin, good_players)
            if target:
                await self._execute_assassination(assassin, target)
            return

    def _schedule_round_discussion_compress(self) -> None:
        """任务轮次结束后异步压缩刚结束轮次的讨论。"""
        if not self.game.mission_results:
            return

        completed_mission = self.game.mission_results[-1].get('mission')
        if not completed_mission:
            return

        asyncio.create_task(
            ai_service.compress_round_discussion(self.game, int(completed_mission))
        )

    async def _resolve_assassination_target(self, assassin, good_players: List[str]) -> Optional[str]:
        """综合 LLM 与备用逻辑确定刺杀目标。"""
        target = await self._ai_select_assassination_target_with_llm(assassin, good_players)
        if not target:
            print(f"AI API失败，使用备用逻辑为 {assassin.name}")
            target = self.ai_select_assassination_target(assassin, good_players)
        return target

    async def _execute_assassination(self, assassin, target: str) -> None:
        print(f"刺客 {assassin.name} 选择刺杀: {target}")
        await self.ai_speak(assassin, f"我要刺杀 {target}！")
        result = self.game.assassinate(target)
        await self._publish_assassination_result_chat(result)
        await self.notify_frontend("assassination_result", result)

    def _get_player_last_speech(self, player_name: str, phase: Optional[str] = None) -> Optional[str]:
        """获取玩家在指定阶段最近一条发言（从后往前找）。"""
        for msg in reversed(self.game.messages_history):
            if msg.get('player') != player_name:
                continue
            if phase and msg.get('phase') != phase:
                continue
            return msg.get('content')
        return None

    def _parse_vote_from_speech(self, speech: str, vote_type: str) -> Optional[str]:
        """从发言中解析投票决策，减少LLM调用。无法确定时返回None，走LLM兜底。"""
        if not speech:
            return None
        speech_lower = speech.lower()

        if vote_type == "team":
            approve_hit = any(kw in speech_lower for kw in ["赞同", "approve", "同意", "赞成", "支持"])
            reject_hit = any(kw in speech_lower for kw in ["不赞成", "不赞同", "不支持", "反对", "reject", "不同意", "否决"])
            if approve_hit and not reject_hit:
                return "approve"
            if reject_hit and not approve_hit:
                return "reject"

        elif vote_type == "mission":
            success_hit = any(kw in speech_lower for kw in ["成功", "success", "赞成"])
            fail_hit = any(kw in speech_lower for kw in ["失败", "fail", "破坏"])
            if success_hit and not fail_hit:
                return "success"
            if fail_hit and not success_hit:
                return "fail"

        return None

    # LLM API调用方法
    async def _ai_select_team_with_llm(self, leader, available_players: List[str], team_size: int) -> Optional[List[str]]:
        """使用LLM API选择队伍"""
        game_context = self.game.get_game_state()
        return await ai_service.get_ai_team_selection(leader.name, leader.role, game_context, available_players, team_size)

    async def _ai_revise_team_with_llm(
        self, leader, available_players: List[str], team_size: int, current_team: List[str]
    ) -> Optional[List[str]]:
        """使用LLM API在讨论后确认或调整队伍"""
        game_context = self.game.get_game_state()
        return await ai_service.get_ai_team_selection(
            leader.name, leader.role, game_context, available_players, team_size,
            current_team=current_team,
        )

    async def _ai_decide_team_vote_with_llm(self, player) -> Optional[str]:
        """使用LLM API决定队伍投票"""
        game_context = self.game.get_game_state()
        return await ai_service.get_ai_vote_decision(player.name, player.role, game_context, "team")

    async def _decide_mission_vote_for_player(self, player) -> Optional[str]:
        """任务投票：好人按规则固定 success，仅坏人调用 LLM。"""
        if ROLES.get(player.role, {}).get('team') == 'good':
            print(f"AI好人 {player.name} 任务投票: success（规则固定）")
            return 'success'

        vote = await self._ai_decide_mission_vote_with_llm(player)
        if not vote:
            print(f"AI API失败，使用发言解析/兜底逻辑为 {player.name}")
            vote = self.ai_decide_mission_vote(player)
        return vote

    async def _ai_decide_mission_vote_with_llm(self, player) -> Optional[str]:
        """使用LLM API决定任务投票"""
        game_context = self.game.get_game_state()
        return await ai_service.get_ai_vote_decision(player.name, player.role, game_context, "mission")

    async def _ai_select_assassination_target_with_llm(self, assassin, good_players: List[str]) -> Optional[str]:
        """使用LLM API选择刺杀目标"""
        game_context = self.game.get_game_state()
        return await ai_service.get_ai_assassination_target(
            assassin.name, assassin.role, good_players, game_context
        )

    async def _ai_assassination_decision_with_llm(
        self, assassin, good_players: List[str], discussion_round: int
    ) -> Optional[str]:
        """使用 LLM 决定继续讨论或立即行刺。"""
        game_context = self.game.get_game_state()
        return await ai_service.get_ai_assassination_decision(
            assassin.name,
            assassin.role,
            good_players,
            game_context,
            discussion_round,
            MAX_ASSASSINATION_DISCUSSION_ROUNDS,
        )

    async def _get_ai_assassination_discussion_speech(self, player) -> Optional[str]:
        """获取刺杀阶段坏人阵营讨论发言。"""
        game_context = self.game.get_game_state()
        game_context['vote_context'] = 'assassination_discussion'
        return await ai_service.get_ai_speech(player.name, player.role, game_context)

    async def _get_ai_team_vote_speech(self, player) -> Optional[str]:
        """获取AI队伍投票时的发言"""
        game_context = self.game.get_game_state()
        game_context['vote_context'] = "team_vote"
        return await ai_service.get_ai_speech(player.name, player.role, game_context)

    async def _get_ai_mission_vote_speech(self, player) -> Optional[str]:
        """获取AI任务投票时的发言"""
        game_context = self.game.get_game_state()
        game_context['vote_context'] = "mission_vote"
        return await ai_service.get_ai_speech(player.name, player.role, game_context)

    async def _run_prefetched_speeches(
        self,
        players: List[Any],
        fetch_speech: Callable[[Any], Awaitable[Optional[str]]],
    ) -> None:
        """按顺序播报发言，同时预取队列中后续玩家的 LLM 发言。"""
        if not players:
            return

        prefetch_size = self.speech_prefetch_size
        if prefetch_size == 0:
            for player in players:
                speech = await fetch_speech(player)
                if speech:
                    await self.ai_speak(player, speech)
            return

        tasks: Dict[int, asyncio.Task] = {}

        def start_prefetch(index: int) -> None:
            if index < len(players) and index not in tasks:
                tasks[index] = asyncio.create_task(fetch_speech(players[index]))

        for index in range(min(prefetch_size, len(players))):
            start_prefetch(index)

        for index, player in enumerate(players):
            if index not in tasks:
                start_prefetch(index)
            speech = await tasks.pop(index)
            # 在 ai_speak 等待期间并行拉取后续玩家发言，而非等朗读结束后再预取
            start_prefetch(index + prefetch_size)
            if speech:
                await self.ai_speak(player, speech)

    async def ai_speak(self, player, message: str):
        """AI玩家发言"""
        print(f"[发言] {player.name}: {message}")

        self.current_speaker = player.name

        self.game.record_message(player.name, message)

        msg_type = 'ai' if player.is_ai else 'player'
        await self._publish_chat(player.name, message, msg_type, player=player)

        if self.log_manager:
            self.log_manager.log_player_speech(
                player_name=player.name,
                message=message,
                is_ai=player.is_ai,
                role=player.role
            )

        if self.websocket_notifier:
            await self.websocket_notifier("player_speaking", {
                "speaker": player.name,
                "message": message,
                "role": player.role,
                "is_ai": player.is_ai
            })

            # 按发言长度估算朗读时长进行节奏控制，不依赖任何前端的播放完成回调
            delay = self._estimate_speech_duration(message)
            print(f"{player.name} 发言已广播，按估算时长 {delay:.1f}s 后继续")
            await asyncio.sleep(delay)

        self.current_speaker = None

    def _estimate_speech_duration(self, message: str) -> float:
        """根据发言长度估算朗读时长（秒），用于控制后端广播节奏"""
        if not message:
            return self.min_speech_seconds
        seconds = self.base_speech_seconds + len(message) * self.per_char_seconds
        return max(self.min_speech_seconds, seconds)

    # 备用逻辑方法（原有的简单AI逻辑）
    def ai_select_team(self, leader, available_players: List[str], team_size: int) -> List[str]:
        """AI选择队伍的备用逻辑"""
        if leader.role in ['morgana', 'assassin', 'minion', 'mordred', 'oberon']:
            return self.select_evil_team(leader, available_players, team_size)
        else:
            return self.select_good_team(leader, available_players, team_size)

    def select_good_team(self, leader, available_players: List[str], team_size: int) -> List[str]:
        """好人选择队伍策略"""
        team = [leader.name]
        remaining_players = [p for p in available_players if p != leader.name]

        while len(team) < team_size and remaining_players:
            selected = random.choice(remaining_players)
            team.append(selected)
            remaining_players.remove(selected)

        return sorted(team, key=lambda n: int(n) if n.isdigit() else n)

    def select_evil_team(self, leader, available_players: List[str], team_size: int) -> List[str]:
        """坏人选择队伍策略"""
        team = [leader.name]
        remaining_players = [p for p in available_players if p != leader.name]

        while len(team) < team_size and remaining_players:
            selected = random.choice(remaining_players)
            team.append(selected)
            remaining_players.remove(selected)

        return sorted(team, key=lambda n: int(n) if n.isdigit() else n)

    def ai_decide_team_vote(self, player) -> str:
        """AI队伍投票决策备用逻辑：解析本队讨论发言，无法解析时默认赞成"""
        speech = self._get_player_last_speech(player.name, GAME_PHASES['team_vote'])
        vote = self._parse_vote_from_speech(speech, "team")
        if vote:
            return vote
        return "approve"

    def ai_decide_mission_vote(self, player) -> str:
        """AI任务投票决策备用逻辑（仅坏人）：解析讨论发言，无法解析时投 fail"""
        if ROLES.get(player.role, {}).get('team') == 'good':
            return "success"

        speech = self._get_player_last_speech(player.name, GAME_PHASES['team_vote'])
        vote = self._parse_vote_from_speech(speech, "mission")
        if vote:
            return vote
        return "fail"

    def ai_select_assassination_target(self, assassin, good_players: List[str]) -> str:
        """AI刺杀目标选择备用逻辑"""
        return random.choice(good_players) if good_players else None

    async def notify_frontend(self, event: str, data: Dict[str, Any]):
        """通知前端"""
        if self.websocket_notifier:
            await self.websocket_notifier(event, data)

    async def _publish_chat(
        self,
        sender: str,
        message: str,
        msg_type: str = 'system',
        role: Optional[str] = None,
        player: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """写入战报并通过 WebSocket 推送"""
        meta: Dict[str, Any] = {}
        if player is not None:
            for index, p in enumerate(self.game.players):
                if p.name == player.name:
                    role_info = ROLES.get(p.role or '', {})
                    meta = {
                        'seat': index + 1,
                        'role': p.role,
                        'role_name': role_info.get('name'),
                        'is_ai': p.is_ai,
                    }
                    break
        elif sender != '系统':
            meta = self.game.get_player_chat_meta(sender)
            if role and 'role' not in meta:
                meta['role'] = role
                meta['role_name'] = ROLES.get(role, {}).get('name')

        entry = self.game.append_chat_log(
            sender,
            message,
            msg_type,
            role=meta.get('role') or role,
            role_name=meta.get('role_name'),
            seat=meta.get('seat'),
            is_ai=meta.get('is_ai'),
        )
        await self.notify_frontend('chat_log_entry', entry)
        return entry

    async def _publish_mission_vote_chat(self, result: Dict[str, Any]) -> None:
        status = result.get('status')
        if status == 'good_mission_win':
            await self._publish_chat(
                '系统',
                '好人获得3次任务成功！坏人阵营进入秘密讨论',
                'system',
            )
        elif status == 'mission_completed':
            success = result.get('mission_result')
            await self._publish_chat(
                '系统',
                f"任务完成，结果: {'成功' if success else '失败'}",
                'system',
            )
        elif status == 'evil_win':
            await self._publish_chat(
                '系统',
                result.get('reason', '坏人获胜'),
                'system',
            )

    async def _publish_assassination_result_chat(self, result: Dict[str, Any]) -> None:
        status = result.get('status')
        if status == 'evil_win':
            await self._publish_chat(
                '系统',
                result.get('reason', '坏人获胜'),
                'system',
            )
        elif status == 'good_win':
            await self._publish_chat(
                '系统',
                result.get('reason', '好人获胜'),
                'system',
            )

    def _build_team_vote_hint(self, result: Dict[str, Any]) -> str:
        status = result.get('status')
        approve = result.get('approve_count', 0)
        reject = result.get('reject_count', 0)
        if status == 'team_approved':
            return f"表决通过（{approve} 赞成 / {reject} 反对），远征队即将出发执行任务…"
        if status == 'team_rejected':
            leader = result.get('next_leader', '')
            return f"表决未通过（{approve} 赞成 / {reject} 反对），队长移交给 {leader}，重新组队…"
        if status == 'evil_win':
            return result.get('reason', '坏人获胜')
        return ''

    async def _notify_team_vote_completed(self, result: Dict[str, Any]):
        hint = self._build_team_vote_hint(result)
        if hint:
            await self._publish_chat('系统', hint, 'system')
        await self.notify_frontend("team_vote_completed", {
            **result,
            "hint": hint,
        })

    async def handle_voice_start(self, data: Dict[str, Any]):
        """处理前端发送的语音开始播放通知（仅记录，节奏已由后端自行控制）"""
        player_name = data.get('player_name')
        if player_name:
            print(f"语音开始播放: {player_name}")

    async def handle_voice_complete(self, data: Dict[str, Any]):
        """处理前端发送的语音播放完成通知（仅记录，后端不再依赖此回调推进）"""
        player_name = data.get('player_name')
        if player_name:
            print(f"语音播放完成: {player_name}")

    def get_ai_status(self) -> Dict[str, Any]:
        """获取AI控制器状态"""
        return {
            'is_running': self.is_running,
            'ai_players_count': len(self.ai_players),
            'current_speaker': self.current_speaker,
            'auto_delay': self.auto_delay,
            'speech_prefetch_size': self.speech_prefetch_size,
        }
