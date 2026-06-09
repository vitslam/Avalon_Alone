// WebSocket 连接和消息路由
import state from './state.js';
import { addChatMessage } from './chat.js';
import { enqueuePlayerSpeech } from './speechPresenter.js';
import {
    handleGameStarted, handleTeamSelected,
    handleTeamVotePhaseStart, handleTeamVoteProgress, handleTeamVoteCompleted, handleTeamVoteRecorded,
    handleMissionVoteRecorded, handleAssassinationResult, handleGameReset
} from './game.js';

export function connectWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    state.websocket = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);

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

    state.websocket.onopen = function() {
        console.log('WebSocket连接已建立');
        addChatMessage('系统', '已连接到游戏服务器', 'system');
        fetchCurrentGameState();
    };

    state.websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    state.websocket.onclose = function() {
        console.log('WebSocket连接已关闭');
        addChatMessage('系统', '与服务器连接已断开', 'system');
    };

    state.websocket.onerror = function(error) {
        console.error('WebSocket错误:', error);
        addChatMessage('系统', '连接错误', 'system');
    };
}

export async function fetchCurrentGameState() {
    try {
        const response = await fetch(`${state.API_BASE}/game/state`);
        if (response.ok) {
            const stateData = await response.json();
            // 动态导入避免循环依赖
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
            setTimeout(fetchCurrentGameState, 100);
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
        case 'assassination_result':
            handleAssassinationResult(data.data);
            break;
        case 'game_reset':
            handleGameReset(data.data);
            break;
        default:
            console.log('未知事件类型:', data.event);
    }
}

function handlePlayerSpeaking(speakingData) {
    const { speaker, message, is_ai } = speakingData;

    // 聊天区即时更新；气泡、呼吸灯、TTS 由展示队列串行同步
    addChatMessage(speaker, message, is_ai ? 'ai' : 'player');
    enqueuePlayerSpeech(speakingData);
}
