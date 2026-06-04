// 入口文件：初始化、事件监听、全局绑定
import state from './state.js';
import { addPlayer, removePlayer, updateStartButton, initializeDefaultPlayers } from './players.js';
import { startGame, resetGame, setCurrentPlayer } from './game.js';
import { confirmTeam, vote, voteMission, confirmAssassination } from './controls.js';
import { sendMessage } from './chat.js';
import { connectWebSocket } from './websocket.js';
import { loadTTSModule, initializeVoiceControl, testVoice } from './voice.js';

document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    connectWebSocket();
    initializeDefaultPlayers();
    loadTTSModule();
});

// 绑定到全局 window 对象供 HTML onclick 调用
window.addPlayer = addPlayer;
window.removePlayer = removePlayer;
window.startGame = startGame;
window.confirmTeam = confirmTeam;
window.vote = vote;
window.voteMission = voteMission;
window.confirmAssassination = confirmAssassination;
window.sendMessage = sendMessage;
window.resetGame = resetGame;
window.setCurrentPlayer = setCurrentPlayer;
window.testVoice = testVoice;

function initializeEventListeners() {
    document.getElementById('isAI').addEventListener('change', function() {
        const aiEngineSelect = document.getElementById('aiEngine');
        aiEngineSelect.disabled = !this.checked;
    });

    document.getElementById('playerName').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            addPlayer();
        }
    });

    initializeVoiceControl();

    document.getElementById('chatInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
}
