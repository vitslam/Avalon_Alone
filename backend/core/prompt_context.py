"""
Prompt 上下文构建：结构化局势摘要、分层对话历史。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .constants import GAME_PHASES

_ASSASSINATION_PHASES = frozenset({
    GAME_PHASES.get('assassination', '刺杀阶段'),
    'assassination',
    '刺杀阶段',
})


def _player_sort_key(name: str):
    return int(name) if str(name).isdigit() else name


def resolve_message_missions(messages: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], int]]:
    """为每条消息解析所属任务轮次（无 mission 字段时按 system 任务结果回溯推断）。"""
    resolved: List[Tuple[Dict[str, Any], int]] = []
    current_mission = 1

    for msg in messages:
        if msg.get('phase') in _ASSASSINATION_PHASES:
            continue

        if 'mission' in msg and msg['mission'] is not None:
            mission = int(msg['mission'])
        else:
            mission = current_mission

        resolved.append((msg, mission))

        if msg.get('player') == 'system':
            match = re.search(r'第(\d+)轮任务', msg.get('content', ''))
            if match:
                current_mission = int(match.group(1)) + 1

    return resolved


def _sorted_player_names(names: List[str]) -> List[str]:
    return sorted(names, key=_player_sort_key)


def _format_vote_side(players: List[str]) -> str:
    return ', '.join(players) if players else '无'


def _format_team_vote_record_line(record: Dict[str, Any]) -> str:
    mission = record.get('mission')
    attempt = record.get('attempt', 1)
    team = record.get('team', [])
    approve = _sorted_player_names(record.get('approve', []))
    reject = _sorted_player_names(record.get('reject', []))
    outcome = '通过' if record.get('approved') else '否决'
    attempt_label = f"第{mission}轮第{attempt}次" if attempt > 1 else f"第{mission}轮"
    return (
        f"  {attempt_label} 队伍 {team}："
        f"赞成 {_format_vote_side(approve)} / 反对 {_format_vote_side(reject)}（{outcome}）"
    )


def _build_player_mission_board(
    mission_results: List[Dict[str, Any]],
    player_names: List[str],
) -> Dict[str, List[int]]:
    board: Dict[str, List[int]] = {name: [] for name in player_names}
    for result in mission_results:
        mission_num = result.get('mission')
        for name in result.get('team', []):
            if name in board and mission_num is not None:
                board[name].append(mission_num)
    return board


def build_situation_summary(
    game_context: Dict[str, Any],
    player_name: Optional[str] = None,
) -> str:
    """生成结构化局势摘要，供插入对话历史之后。"""
    mission_results = game_context.get('mission_results', [])
    players = game_context.get('players', [])
    player_names = sorted([p['name'] for p in players], key=_player_sort_key)

    lines = ["\n\n【局势摘要】（以投票和任务结果为准，比发言更可靠）"]

    if mission_results:
        lines.append("- 任务记录：")
        for result in mission_results:
            status = '成功' if result.get('success') else '失败'
            team = result.get('team', [])
            lines.append(
                f"  第{result.get('mission')}轮 {status}，队伍 {team}，"
                f"{result.get('success_count', 0)}票成功 / {result.get('fail_count', 0)}票失败"
            )
    else:
        lines.append("- 任务记录：暂无")

    team_vote_history = game_context.get('team_vote_history', [])
    if team_vote_history:
        lines.append("- 队伍投票记录：")
        for record in team_vote_history:
            lines.append(_format_team_vote_record_line(record))

    good_wins = sum(1 for r in mission_results if r.get('success'))
    evil_wins = len(mission_results) - good_wins
    lines.append(f"- 比分：好人 {good_wins} 胜 / 坏人 {evil_wins} 败")

    board = _build_player_mission_board(mission_results, player_names)
    if player_names:
        board_parts = [
            f"{name}→第{','.join(map(str, board[name]))}轮" if board[name] else f"{name}→未上车"
            for name in player_names
        ]
        lines.append(f"- 各玩家上车记录：{'；'.join(board_parts)}")

    current_team = game_context.get('current_team') or []
    current_leader = game_context.get('current_leader')
    current_mission = game_context.get('current_mission')
    failed_team_votes = game_context.get('failed_team_votes', 0)

    if current_mission:
        lines.append(
            f"- 当前：第{current_mission}轮任务，队长 {current_leader or '未知'}，"
            f"提名队伍 {current_team or '未选择'}，连续否决 {failed_team_votes} 次"
        )

    team_votes = game_context.get('team_votes', [])
    phase = game_context.get('phase', '')
    if team_votes and current_team and phase == GAME_PHASES.get('team_vote', '队伍投票'):
        approve = _sorted_player_names([v['player'] for v in team_votes if v.get('vote') == 'approve'])
        reject = _sorted_player_names([v['player'] for v in team_votes if v.get('vote') == 'reject'])
        lines.append(
            f"- 当前队伍投票（进行中）队伍 {current_team}："
            f"赞成 {_format_vote_side(approve)} / 反对 {_format_vote_side(reject)}"
        )

    if player_name:
        my_missions = board.get(player_name, [])
        if my_missions:
            lines.append(f"- 你（{player_name}）曾参与第 {', '.join(map(str, my_missions))} 轮任务")
        else:
            lines.append(f"- 你（{player_name}）尚未参与任何任务")

    return '\n'.join(lines)


def build_dialogue_history_lines(game_context: Dict[str, Any]) -> List[str]:
    """
    组装对话历史行：
    - 更早轮次：使用压缩摘要；
    - 上一轮 + 当前轮：保留完整发言；
    - 刺杀阶段讨论：始终保留完整发言。
    """
    messages = game_context.get('messages_history', [])
    if not messages:
        return []

    current_mission = int(game_context.get('current_mission') or 1)
    prev_mission = max(1, current_mission - 1)
    summaries: Dict[int, str] = game_context.get('round_discussion_summaries', {})

    resolved = resolve_message_missions(messages)
    lines: List[str] = []

    for mission_num in range(1, prev_mission):
        if mission_num in summaries:
            lines.append(f"【第{mission_num}轮讨论摘要】{summaries[mission_num]}")
        else:
            mission_msgs = [msg for msg, m in resolved if m == mission_num]
            if mission_msgs:
                lines.append(f"【第{mission_num}轮讨论摘要】（摘要生成中，暂略）")

    for msg, mission_num in resolved:
        if mission_num in (prev_mission, current_mission):
            lines.append(f"{msg['player']}说: {msg['content']}")

    phase = game_context.get('phase', '')
    if phase in _ASSASSINATION_PHASES:
        for msg in messages:
            if msg.get('phase') in _ASSASSINATION_PHASES:
                lines.append(f"{msg['player']}说: {msg['content']}")

    return lines


def format_dialogue_history_block(
    game_context: Dict[str, Any],
    label: str = "对话历史",
    player_name: Optional[str] = None,
) -> str:
    """对话历史块 + 局势摘要（摘要紧跟在历史之后）。"""
    history_lines = build_dialogue_history_lines(game_context)
    history_part = ""
    if history_lines:
        history_part = f"\n\n{label}:\n" + '\n'.join(history_lines)

    return history_part + build_situation_summary(game_context, player_name)


def collect_round_messages(
    messages: List[Dict[str, Any]],
    mission_number: int,
) -> List[Dict[str, Any]]:
    """收集指定任务轮次的全部发言（不含刺杀阶段）。"""
    resolved = resolve_message_missions(messages)
    return [msg for msg, m in resolved if m == mission_number]
