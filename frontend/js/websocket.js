// WebSocket 连接和消息路由
import state from './state.js';
import { addChatMessage, appendChatLogEntry, renderChatLog } from './chat.js';
import { enqueuePlayerSpeech, pauseForBackground, resumeSpeechQueue } from './speechPresenter.js';
import { unlockSpeechAudio } from './voice.js';
import {
    handleGameStarted, handleTeamSelected,
    handleTeamVotePhaseStart, handleTeamVoteProgress, handleTeamVoteCompleted, handleTeamVoteRecorded,
    handleMissionVoteRecorded,
    handleAssassinationDiscussionStart,
    handleAssassinationRoundStart,
    handleAssassinationResult,
    handleGameReset,
} from './game.js';

const MAX_RECONNECT_DELAY_MS = 30000;
let reconnectTimer = null;
let reconnectAttempts = 0;
let intentionalClose = false;
let disconnectNotified = false;
let lifecycleListenersBound = false;

function getReconnectDelay() {
    return Math.min(1000 * Math.pow(2, reconnectAttempts), MAX_RECONNECT_DELAY_MS);
}

function clearReconnectTimer() {
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }
}

function scheduleReconnect() {
    if (intentionalClose || reconnectTimer) return;

    const delay = getReconnectDelay();
    reconnectAttempts += 1;
    console.log(`WebSocket 将在 ${delay}ms 后重连（第 ${reconnectAttempts} 次）`);

    reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connectWebSocketInternal(true);
    }, delay);
}

function notifyDisconnectedOnce() {
    if (disconnectNotified) return;
    disconnectNotified = true;
    addChatMessage('系统', '与服务器连接已断开，正在尝试重连…', 'system');
}

function onSocketOpen(isReconnect) {
    reconnectAttempts = 0;
    clearReconnectTimer();
    disconnectNotified = false;

    console.log(isReconnect ? 'WebSocket 已重新连接' : 'WebSocket连接已建立');
    if (isReconnect) {
        addChatMessage('系统', '已重新连接到游戏服务器', 'system');
    } else {
        addChatMessage('系统', '已连接到游戏服务器', 'system');
    }

    fetchChatHistory().then(() => fetchCurrentGameState());
}

function connectWebSocketInternal(isReconnect = false) {
    if (
        state.websocket &&
        (state.websocket.readyState === WebSocket.OPEN ||
            state.websocket.readyState === WebSocket.CONNECTING)
    ) {
        return;
    }

    if (state.websocket) {
        state.websocket.onopen = null;
        state.websocket.onmessage = null;
        state.websocket.onclose = null;
        state.websocket.onerror = null;
        try {
            state.websocket.close();
        } catch (_) {
            // 忽略旧连接关闭异常
        }
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    state.websocket = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);

    state.websocket.onopen = function() {
        onSocketOpen(isReconnect);
    };

    state.websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    state.websocket.onclose = function() {
        console.log('WebSocket连接已关闭');
        if (!intentionalClose) {
            notifyDisconnectedOnce();
            scheduleReconnect();
        }
    };

    state.websocket.onerror = function(error) {
        // Safari 切后台时常同时触发 error + close，避免重复刷战报
        console.error('WebSocket错误:', error);
    };
}

function resumeAfterForeground() {
    unlockSpeechAudio();
    resumeSpeechQueue();

    reconnectAttempts = 0;
    clearReconnectTimer();

    if (!state.websocket || state.websocket.readyState !== WebSocket.OPEN) {
        connectWebSocketInternal(true);
    }

    fetchChatHistory().then(() => fetchCurrentGameState());
}

function bindLifecycleListeners() {
    if (lifecycleListenersBound) return;
    lifecycleListenersBound = true;

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            pauseForBackground();
            return;
        }
        resumeAfterForeground();
    });

    window.addEventListener('online', () => {
        resumeAfterForeground();
    });

    window.addEventListener('pageshow', (event) => {
        if (event.persisted) {
            resumeAfterForeground();
        }
    });
}

export function connectWebSocket() {
    bindLifecycleListeners();
    intentionalClose = false;
    disconnectNotified = false;
    connectWebSocketInternal(false);
}

window.onVoiceStart = function(playerName, text) {
    if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
        state.websocket.send(JSON.stringify({
            event: 'voice_start',
            data: { player_name: playerName, text: text }
        }));
    }
};

window.onVoiceEnd = function(playerName, text) {
    if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
        state.websocket.send(JSON.stringify({
            event: 'voice_complete',
            data: { player_name: playerName, text: text }
        }));
    }
};

export async function fetchChatHistory() {
    try {
        const response = await fetch(`${state.API_BASE}/game/chat-history`);
        if (!response.ok) return;

        const data = await response.json();
        if (data.status === 'ok' && data.entries?.length) {
            renderChatLog(data.entries);
        }
    } catch (error) {
        console.error('获取战报历史失败:', error);
    }
}

export async function fetchCurrentGameState() {
    try {
        const response = await fetch(`${state.API_BASE}/game/state`);
        if (response.ok) {
            const stateData = await response.json();
            const { updateGameState } = await import('./game.js');
            updateGameState(stateData);
        }
    } catch (error) {
        console.error('获取游戏状态失败:', error);
    }
}

function handleWebSocketMessage(data) {
    switch (data.event) {
        case 'game_started':
            handleGameStarted(data.data);
            fetchChatHistory().then(() => setTimeout(fetchCurrentGameState, 100));
            break;
        case 'chat_log_entry':
            appendChatLogEntry(data.data);
            break;
        case 'team_selected':
            handleTeamSelected(data.data);
            break;
        case 'team_vote_phase_start':
            handleTeamVotePhaseStart(data.data);
            break;
        case 'team_vote_progress':
            handleTeamVoteProgress(data.data);
            break;
        case 'team_vote_completed':
            handleTeamVoteCompleted(data.data);
            break;
        case 'team_vote_recorded':
            handleTeamVoteRecorded(data.data);
            break;
        case 'mission_vote_recorded':
            handleMissionVoteRecorded(data.data);
            setTimeout(fetchCurrentGameState, 200);
            break;
        case 'player_speaking':
            handlePlayerSpeaking(data.data);
            break;
        case 'voice_complete':
            setTimeout(fetchCurrentGameState, 100);
            break;
        case 'assassination_discussion_start':
            handleAssassinationDiscussionStart(data.data);
            setTimeout(fetchCurrentGameState, 100);
            break;
        case 'assassination_round_start':
            handleAssassinationRoundStart(data.data);
            setTimeout(fetchCurrentGameState, 100);
            break;
        case 'assassination_result':
            handleAssassinationResult(data.data);
            setTimeout(fetchCurrentGameState, 100);
            break;
        case 'game_reset':
            handleGameReset(data.data);
            break;
        case 'current_state':
            import('./game.js').then(({ updateGameState }) => updateGameState(data.data));
            break;
        default:
            console.log('未知事件类型:', data.event);
    }
}

function handlePlayerSpeaking(speakingData) {
    enqueuePlayerSpeech(speakingData);
}
