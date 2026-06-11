// 入口文件：初始化、事件监听、全局绑定
import { addPlayer, removePlayer, updateStartButton, initializeDefaultPlayers } from './players.js';
import { startGame, resetGame } from './game.js';
import { connectWebSocket } from './websocket.js';
import { loadTTSModule, initializeVoiceControl, testVoice } from './voice.js';
import { loadClientConfig } from './config.js';

document.addEventListener('DOMContentLoaded', async function() {
    await loadClientConfig();
    initializeEventListeners();
    initializeDefaultPlayers();
    await loadTTSModule();
    connectWebSocket();
});

window.addPlayer = addPlayer;
window.removePlayer = removePlayer;
window.startGame = startGame;
window.resetGame = resetGame;
window.testVoice = testVoice;

function initializeEventListeners() {
    document.getElementById('playerName').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            addPlayer();
        }
    });

    initializeVoiceControl();
}
