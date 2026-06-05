"""
AI控制器 - 负责AI玩家的自动决策和游戏流程控制
"""

import asyncio
import random
from typing import Dict, List, Optional, Callable, Any
from ..core.constants import GAME_PHASES, GAME_STATES
from .ai_service import ai_service
from ..core.log_manager import LogManager


class AIController:
    def __init__(self, game, websocket_notifier: Optional[Callable] = None):
        self.game = game
        self.websocket_notifier = websocket_notifier
        self.ai_players = [p for p in game.players if p.is_ai]
        self.is_running = False
        self.auto_delay = 2.0
        self.current_speaker = None
        self.log_manager = LogManager()
        # 更新AI服务的日志管理器
        global ai_service
        ai_service = ai_service.__class__(self.log_manager)

        # 语音播放状态控制
        self.waiting_for_voice = False
        self.voice_complete_event = asyncio.Event()

    async def start_auto_play(self):
        """开始AI自动游戏"""
        if not self.ai_players:
            print("没有AI玩家，退出自动游戏")
            return

        self.is_running = True
        print(f"AI控制器启动，管理 {len(self.ai_players)} 个AI玩家")

        # 检查游戏是否已经开始，如果没有则开始游戏
        if self.game.state == GAME_STATES['waiting']:
            print("开始新游戏")
            game_start_result = self.game.start_game()

            # 记录游戏开始和角色分配信息到全局日志
            if 'role_assignments' in game_start_result and 'secret_messages' in game_start_result:
                self.log_manager.log_game_start_with_roles(
                    role_assignments=game_start_result['role_assignments'],
                    secret_messages=game_start_result['secret_messages']
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
                    await self.notify_frontend("team_selected", result)
                else:
                    print(f"队伍选择失败: {result['error']}")

    async def handle_team_vote(self):
        """处理队伍投票阶段"""
        print("处理队伍投票阶段")

        if not hasattr(self, 'team_vote_started'):
            self.team_vote_started = False

        if not self.team_vote_started:
            team_vote_data = {
                "team": self.game.current_team,
                "mission_number": self.game.current_mission
            }
            self.log_manager.log_global_event("team_vote_start", team_vote_data)
            self.team_vote_started = True

        total_players = len(self.game.players)
        voted_players = len(self.game.team_votes)

        if voted_players > total_players:
            print(f"警告: 投票计数异常 ({voted_players}/{total_players})，重置投票状态")
            self.team_vote_started = False
            if self.game.phase == GAME_PHASES['team_vote']:
                self.game.phase = GAME_PHASES['team_selection']
                self.game.current_leader_index = (self.game.current_leader_index + 1) % len(self.game.players)
                print(f"队长已轮换为: {self.game.players[self.game.current_leader_index].name}")
            return

        print(f"投票进度: {voted_players}/{total_players}")

        for player in self.ai_players:
            if player.name not in [v['player'] for v in self.game.team_votes]:
                print(f"AI玩家 {player.name} 准备对队伍投票")

                thinking_speech = await self._get_ai_team_vote_speech(player)
                if thinking_speech:
                    await self.ai_speak(player, thinking_speech)

                vote = self._parse_vote_from_speech(thinking_speech, "team")

                if not vote:
                    vote = await self._ai_decide_team_vote_with_llm(player)

                if not vote:
                    print(f"AI API失败，使用备用逻辑为 {player.name}")
                    vote = self.ai_decide_team_vote(player)

                if vote:
                    print(f"AI玩家 {player.name} 投票: {vote}")

                    vote_data = {
                        "player": player.name,
                        "vote": vote,
                        "team": self.game.current_team
                    }
                    self.log_manager.log_global_event("team_vote", vote_data)

                    vote_speech = "我赞成这个队伍" if vote == "approve" else "我反对这个队伍"
                    await self.ai_speak(player, vote_speech)

                    result = self.game.vote_team(player.name, vote)
                    if 'error' not in result:
                        await self.notify_frontend("team_vote_recorded", result)

                    if result.get('status') in ['team_approved', 'team_rejected', 'evil_win']:
                        print(f"队伍投票完成，结果: {result.get('status')}")
                        self.team_vote_started = False
                        return
                    elif 'error' in result:
                        print(f"投票失败: {result['error']}")
                    else:
                        print(f"投票结果处理: {result.get('status', 'unknown')}")

                    await asyncio.sleep(0.5)

    async def handle_mission_vote(self):
        """处理任务投票阶段"""
        print("处理任务投票阶段")

        mission_vote_data = {
            "team": self.game.current_team,
            "mission_number": self.game.current_mission
        }
        self.log_manager.log_global_event("mission_vote_start", mission_vote_data)

        team_ai_players = [p for p in self.ai_players if p.name in self.game.current_team]

        total_team_members = len(self.game.current_team)
        voted_members = len(self.game.mission_votes)

        print(f"任务投票进度: {voted_members}/{total_team_members}")

        if voted_members >= total_team_members:
            print("所有队伍成员已完成任务投票，等待游戏状态更新...")
            return

        for player in team_ai_players:
            if player.name not in [v['player'] for v in self.game.mission_votes]:
                print(f"AI队伍成员 {player.name} 准备任务投票")

                vote = await self._ai_decide_mission_vote_with_llm(player)

                if not vote:
                    print(f"AI API失败，使用备用逻辑为 {player.name}")
                    vote = self.ai_decide_mission_vote(player)

                if vote:
                    print(f"AI队伍成员 {player.name} 任务投票: {vote}")

                    mission_vote_data = {
                        "player": player.name,
                        "vote": vote,
                        "mission_number": self.game.current_mission
                    }
                    self.log_manager.log_global_event("mission_vote", mission_vote_data)
                    result = self.game.vote_mission(player.name, vote)
                    if 'error' not in result:
                        await self.notify_frontend("mission_vote_recorded", result)

                        if result.get('status') in ['good_mission_win', 'evil_win', 'mission_completed']:
                            print(f"任务投票完成，结果: {result.get('status')}")
                            return
                    else:
                        print(f"任务投票失败: {result['error']}")

                    await asyncio.sleep(0.5)

    async def handle_assassination(self):
        """处理刺杀阶段"""
        print("处理刺杀阶段")

        assassination_data = {
            "mission_results": self.game.mission_results
        }
        self.log_manager.log_global_event("assassination_start", assassination_data)

        assassin = None
        for player in self.ai_players:
            if player.role == 'assassin':
                assassin = player
                break

        if assassin:
            print(f"AI刺客 {assassin.name} 准备选择刺杀目标")

            await self.ai_speak(assassin, "是时候展现真正的技术了...")

            good_players = [p.name for p in self.game.players if p.role in ['merlin', 'percival', 'loyal_servant']]

            if good_players:
                target = await self._ai_select_assassination_target_with_llm(assassin, good_players)

                if not target:
                    print(f"AI API失败，使用备用逻辑为 {assassin.name}")
                    target = self.ai_select_assassination_target(assassin, good_players)

                if target:
                    print(f"刺客 {assassin.name} 选择刺杀: {target}")

                    await self.ai_speak(assassin, f"我要刺杀 {target}！")

                    result = self.game.assassinate(target)
                    await self.notify_frontend("assassination_result", result)

    def _parse_vote_from_speech(self, speech: str, vote_type: str) -> Optional[str]:
        """从发言中解析投票决策，减少LLM调用。无法确定时返回None，走LLM兜底。"""
        if not speech:
            return None
        speech_lower = speech.lower()

        if vote_type == "team":
            approve_hit = any(kw in speech_lower for kw in ["赞同", "approve", "同意", "赞成", "支持"])
            reject_hit = any(kw in speech_lower for kw in ["反对", "reject", "不同意", "否决"])
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

    async def _ai_decide_team_vote_with_llm(self, player) -> Optional[str]:
        """使用LLM API决定队伍投票"""
        game_context = self.game.get_game_state()
        return await ai_service.get_ai_vote_decision(player.name, player.role, game_context, "team")

    async def _ai_decide_mission_vote_with_llm(self, player) -> Optional[str]:
        """使用LLM API决定任务投票"""
        game_context = self.game.get_game_state()
        return await ai_service.get_ai_vote_decision(player.name, player.role, game_context, "mission")

    async def _ai_select_assassination_target_with_llm(self, assassin, good_players: List[str]) -> Optional[str]:
        """使用LLM API选择刺杀目标"""
        return await ai_service.get_ai_assassination_target(assassin.name, assassin.role, good_players)

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

    async def ai_speak(self, player, message: str):
        """AI玩家发言"""
        print(f"[发言] {player.name}: {message}")

        self.current_speaker = player.name

        self.game.record_message(player.name, message)

        if self.log_manager:
            self.log_manager.log_player_speech(
                player_name=player.name,
                message=message,
                is_ai=player.is_ai,
                role=player.role
            )

        if self.websocket_notifier:
            self.waiting_for_voice = True
            self.voice_complete_event.clear()

            await self.websocket_notifier("player_speaking", {
                "speaker": player.name,
                "message": message,
                "role": player.role,
                "is_ai": player.is_ai
            })

            print(f"等待 {player.name} 的语音播放完成...")
            await self.voice_complete_event.wait()
            print(f"{player.name} 的语音播放已完成，继续游戏流程")

        self.current_speaker = None

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

        return team

    def select_evil_team(self, leader, available_players: List[str], team_size: int) -> List[str]:
        """坏人选择队伍策略"""
        team = [leader.name]
        remaining_players = [p for p in available_players if p != leader.name]

        while len(team) < team_size and remaining_players:
            selected = random.choice(remaining_players)
            team.append(selected)
            remaining_players.remove(selected)

        return team

    def ai_decide_team_vote(self, player) -> str:
        """AI队伍投票决策备用逻辑"""
        if player.role in ['morgana', 'assassin', 'minion', 'mordred']:
            evil_in_team = any(p.role in ['morgana', 'assassin', 'minion', 'mordred', 'oberon']
                             for p in self.game.players if p.name in self.game.current_team)
            return "approve" if evil_in_team else "reject"
        else:
            return random.choice(["approve", "reject"])

    def ai_decide_mission_vote(self, player) -> str:
        """AI任务投票决策备用逻辑"""
        if player.role in ['morgana', 'assassin', 'minion', 'mordred']:
            return random.choice(["success", "fail"])
        else:
            return "success"

    def ai_select_assassination_target(self, assassin, good_players: List[str]) -> str:
        """AI刺杀目标选择备用逻辑"""
        return random.choice(good_players) if good_players else None

    async def notify_frontend(self, event: str, data: Dict[str, Any]):
        """通知前端"""
        if self.websocket_notifier:
            await self.websocket_notifier(event, data)

    async def handle_voice_start(self, data: Dict[str, Any]):
        """处理前端发送的语音开始播放通知"""
        player_name = data.get('player_name')
        if player_name:
            print(f"语音开始播放: {player_name}")

    async def handle_voice_complete(self, data: Dict[str, Any]):
        """处理前端发送的语音播放完成通知"""
        player_name = data.get('player_name')
        if player_name:
            print(f"语音播放完成: {player_name}")
            self.waiting_for_voice = False
            self.voice_complete_event.set()

    def get_ai_status(self) -> Dict[str, Any]:
        """获取AI控制器状态"""
        return {
            'is_running': self.is_running,
            'ai_players_count': len(self.ai_players),
            'current_speaker': self.current_speaker,
            'auto_delay': self.auto_delay
        }
