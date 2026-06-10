// 游戏状态管理和事件处理
import state from './state.js';
import { addChatMessage } from './chat.js';
import {
    updatePlayersDisplay,
    showTeamVoteProgress,
    showTeamVoteResult,
    clearTeamVoteDisplay,
    isProposedTeamPhase,
    isMissionVotePhase,
    sortTeamNames,
} from './table.js';
import { clearSpeechQueue } from './speechPresenter.js';
import {
    showTeamSelection,
    showMissionVoting,
    showAssassinationDiscussionPanel,
} from './controls.js';
import { updatePlayerList, updateStartButton } from './players.js';
import { playMissionVideo, playAssassinationVideo, stopMissionVideo, setMissionResult } from './missionVideo.js';

export function updateGameState(newState) {
    state.gameState = newState;

    updateGameStatus();
    updateMissionProgress();
    updatePlayersDisplay();
    updateCurrentPhase();

    if (newState.state === 'playing' || newState.phase) {
        document.getElementById('gameSetup').style.display = 'none';
        document.getElementById('gameInterface').style.display = 'block';
    }
}

function updateGameStatus() {
    const gameStatus = document.getElementById('gameStatus');
    if (state.gameState) {
        const statusMap = {
            'waiting': '等待开始游戏',
            'playing': '游戏进行中',
            'finished': '游戏结束',
            '等待开始': '等待开始游戏',
            '游戏进行中': '游戏进行中',
            '游戏结束': '游戏结束'
        };
        gameStatus.textContent = statusMap[state.gameState.state] || state.gameState.state || '未知状态';
    }
}

function updateMissionProgress() {
    const missionProgress = document.getElementById('missionProgress');
    if (!missionProgress) return;

    missionProgress.innerHTML = '';

    if (!state.gameState) return;

    // 任务总数固定为5（阿瓦隆标准）
    const totalMissions = 5;
    const currentMission = state.gameState.current_mission || 1;
    const missionResults = state.gameState.mission_results || [];

    for (let i = 1; i <= totalMissions; i++) {
        const missionItem = document.createElement('div');
        missionItem.className = 'mission-item';
        missionItem.setAttribute('data-mission-num', i);

        // 检查这个任务是否已经完成
        const completedMissionResult = missionResults.find(result => result.mission === i);

        if (completedMissionResult) {
            if (completedMissionResult.success) {
                missionItem.classList.add('success');
            } else {
                missionItem.classList.add('fail');
            }
        } else if (i === currentMission) {
            missionItem.classList.add('current');
        } else {
            missionItem.classList.add('pending');
        }

        missionProgress.appendChild(missionItem);
    }
}

function updateCurrentPhase() {
    const currentPhase = document.getElementById('currentPhase');
    if (!currentPhase || !state.gameState) return;

    const phase = state.gameState.phase || '未知阶段';
    const mission = state.gameState.current_mission;
    const team = state.gameState.current_team;
    const missionPrefix = mission ? `第 ${mission} 轮任务` : '';

    if (team?.length && isProposedTeamPhase(phase)) {
        const chipsHtml = sortTeamNames(team)
            .map(name => `<span class="team-nominee-chip">${name}</span>`)
            .join('');
        currentPhase.innerHTML = `
            <div class="phase-situation-line">
                <span class="phase-situation-text">${missionPrefix} · 队伍提名</span>
                <span class="phase-situation-chips">${chipsHtml}</span>
            </div>
        `;
        return;
    }

    if (isMissionVotePhase(phase)) {
        currentPhase.textContent = missionPrefix
            ? `${missionPrefix} · 任务表决`
            : phase;
        return;
    }

    if (phase === '刺杀阶段' || phase === 'assassination') {
        const round = state.gameState.assassination_discussion_round || 0;
        const maxRounds = state.gameState.max_assassination_discussion_rounds || 3;
        if (round > 0) {
            currentPhase.textContent = `刺杀阶段 · 坏人讨论 第 ${round}/${maxRounds} 轮`;
        } else {
            currentPhase.textContent = '刺杀阶段 · 坏人讨论';
        }
        return;
    }

    if (missionPrefix) {
        currentPhase.textContent = `${missionPrefix} · ${phase}`;
        return;
    }

    currentPhase.textContent = phase;
}

export function handleGameStarted(data) {
    addChatMessage('系统', '游戏开始！角色已分配完成', 'system');

    if (data.secret_messages) {
        Object.entries(data.secret_messages).forEach(([playerName, message]) => {
            addChatMessage('上帝', `${playerName}: ${message}`, 'system');
        });
    }
}

export function handleTeamSelected(data) {
    addChatMessage('系统', `队伍已选择: ${data.team.join(', ')}`, 'system');

    if (state.gameState && data.team) {
        state.gameState.current_team = data.team;
        updatePlayersDisplay();
        updateCurrentPhase();
    }

    if (state.gameState && (state.gameState.phase === 'team_selection' || state.gameState.phase === '选择队伍')) {
        showTeamSelection();
    }
}

const TEAM_VOTE_RESULT_DURATION = 4000;

export function handleTeamVotePhaseStart(data) {
    showTeamVoteProgress(data.voted_count || 0, data.total_players || 0);
}

export function handleTeamVoteProgress(data) {
    showTeamVoteProgress(data.voted_count || 0, data.total_players || 0);
}

export function handleTeamVoteCompleted(data) {
    showTeamVoteResult(data);

    setTimeout(async () => {
        clearTeamVoteDisplay();

        if (data.status === 'team_approved') {
            showMissionVoting();
            triggerMissionVideo(data.team);
        } else if (data.status === 'team_rejected') {
            showTeamSelection();
        } else if (data.status === 'evil_win') {
            showGameResult('坏人获胜', data.reason);
        }

        const { fetchCurrentGameState } = await import('./websocket.js');
        fetchCurrentGameState();
    }, TEAM_VOTE_RESULT_DURATION);
}

export function handleTeamVoteRecorded(data) {
    if (data.status === 'vote_recorded') {
        handleTeamVoteProgress({
            voted_count: data.voted_count,
            total_players: data.total_players,
        });
        return;
    }

    if (['team_approved', 'team_rejected', 'evil_win'].includes(data.status)) {
        handleTeamVoteCompleted(data);
    }
}

async function triggerMissionVideo(teamFromEvent) {
    const { fetchCurrentGameState } = await import('./websocket.js');
    await fetchCurrentGameState();

    const team = teamFromEvent?.length
        ? teamFromEvent
        : state.gameState?.current_team;
    const players = state.gameState?.players;
    const mission = state.gameState?.current_mission;

    if (!team?.length || !players?.length) {
        console.warn('无法播放任务视频：缺少车队或玩家信息', { team, players });
        return;
    }

    playMissionVideo(team, players, mission);
}

export function handleMissionVoteRecorded(data) {
    // 任务结果出炉时，衔接播放成功/失败视频（执行视频结束后或等待画面后）
    if (typeof data.mission_result === 'boolean') {
        setMissionResult(data.mission_result);
    }

    if (data.status === 'good_mission_win') {
        addChatMessage('系统', '好人获得3次任务成功！坏人阵营进入秘密讨论', 'system');
        showAssassinationDiscussionPanel();
    } else if (data.status === 'evil_win') {
        showGameResult('坏人获胜', data.reason);
    } else if (data.status === 'mission_completed') {
        addChatMessage('系统', `任务完成，结果: ${data.mission_result ? '成功' : '失败'}`, 'system');
        showTeamSelection();
    }
}

export function handleAssassinationDiscussionStart(data) {
    if (state.gameState) {
        state.gameState.assassination_discussion_round = 0;
    }

    addChatMessage(
        '系统',
        `进入刺杀阶段，坏人从刺客起按座位顺序讨论（最多 ${data.max_rounds || 3} 轮）`,
        'system'
    );
    showAssassinationDiscussionPanel(data);
    updateCurrentPhase();
}

export function handleAssassinationRoundStart(data) {
    if (state.gameState) {
        state.gameState.assassination_discussion_round = data.round;
    }

    addChatMessage(
        '系统',
        `刺杀讨论第 ${data.round}/${data.max_rounds} 轮开始`,
        'system'
    );
    showAssassinationDiscussionPanel(data);
    updateCurrentPhase();
}

export function handleAssassinationResult(data) {
    const assassinationPanel = document.getElementById('assassinationPanel');
    if (assassinationPanel) {
        assassinationPanel.style.display = 'none';
    }

    const showResult = () => {
        if (data.status === 'evil_win') {
            showGameResult('坏人获胜', data.reason);
        } else if (data.status === 'good_win') {
            showGameResult('好人获胜', data.reason);
        }
    };

    if (data.status === 'evil_win' || data.status === 'good_win') {
        playAssassinationVideo(data.status === 'evil_win', showResult);
    }
}

export function showGameResult(title, message) {
    document.getElementById('resultTitle').textContent = title;
    document.getElementById('resultMessage').textContent = message;
    document.getElementById('gameResultModal').style.display = 'flex';
}

export async function resetGame() {
    try {
        const response = await fetch(`${state.API_BASE}/game/reset`, { method: 'POST' });

        if (response.ok) {
            clearSpeechQueue();
            clearTeamVoteDisplay();
            stopMissionVideo();
            document.getElementById('gameSetup').style.display = 'block';
            document.getElementById('gameInterface').style.display = 'none';
            document.getElementById('playerList').innerHTML = '';
            state.players = [];
            updateStartButton();
            document.getElementById('chatMessages').innerHTML = '';
            state.gameState = null;
            document.getElementById('gameResultModal').style.display = 'none';
            addChatMessage('系统', '游戏已重置，可以开始新游戏', 'system');
        }
    } catch (error) {
        console.error('重置游戏失败:', error);
    }
}

export function handleGameReset(data) {
    clearSpeechQueue();
    clearTeamVoteDisplay();
    stopMissionVideo();
    document.getElementById('gameSetup').style.display = 'block';
    document.getElementById('gameInterface').style.display = 'none';
    document.getElementById('playerList').innerHTML = '';
    state.players = [];
    updateStartButton();
    document.getElementById('chatMessages').innerHTML = '';
    state.gameState = null;
    document.getElementById('gameResultModal').style.display = 'none';
    addChatMessage('系统', '游戏已重置', 'system');
}

export async function startGame() {
    if (!state.players || state.players.length === 0) {
        alert('请先添加玩家');
        return;
    }
    if (state.players.length < 5) {
        alert('至少需要5名玩家才能开始游戏');
        return;
    }
    if (state.players.length > 10) {
        alert('最多只能有10名玩家');
        return;
    }

    try {
        const response = await fetch(`${state.API_BASE}/game/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ players: state.players })
        });

        if (response.ok) {
            const result = await response.json();

            document.getElementById('gameSetup').style.display = 'none';
            document.getElementById('gameInterface').style.display = 'block';

            addChatMessage('系统', '游戏开始！角色已分配完成', 'system');

            if (result.secret_messages) {
                Object.entries(result.secret_messages).forEach(([playerName, message]) => {
                    addChatMessage('上帝', `${playerName}: ${message}`, 'system');
                });
            }

            // 动态导入避免循环依赖
            const { fetchCurrentGameState } = await import('./websocket.js');
            setTimeout(fetchCurrentGameState, 100);
        } else {
            const errorText = await response.text();
            let errorMessage = '游戏开始失败';
            try {
                const errorData = JSON.parse(errorText);
                errorMessage = errorData.detail || errorMessage;
            } catch (e) {
                errorMessage = `HTTP ${response.status}: ${errorText}`;
            }
            alert(`游戏开始失败: ${errorMessage}`);
        }
    } catch (error) {
        console.error('开始游戏失败:', error);
        alert('开始游戏失败，请检查服务器连接: ' + error.message);
    }
}

export function setCurrentPlayer(playerName) {
    state.currentPlayer = playerName;
    addChatMessage('系统', `当前玩家设置为: ${playerName}`, 'system');
}
