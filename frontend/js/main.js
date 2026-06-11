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

function initializeHeaderMenu() {
    const headerMenu = document.getElementById('headerMenu');
    const menuToggle = document.getElementById('menuToggle');
    const headerDropdown = document.getElementById('headerDropdown');
    const resetGameMenuItem = document.getElementById('resetGameMenuItem');

    if (!headerMenu || !menuToggle || !headerDropdown) return;

    function setMenuOpen(open) {
        headerMenu.classList.toggle('is-open', open);
        menuToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        headerDropdown.hidden = !open;
    }

    function closeMenu() {
        setMenuOpen(false);
    }

    menuToggle.addEventListener('click', (event) => {
        event.stopPropagation();
        setMenuOpen(headerDropdown.hidden);
    });

    resetGameMenuItem?.addEventListener('click', () => {
        closeMenu();
        resetGame();
    });

    document.addEventListener('click', (event) => {
        if (!headerMenu.contains(event.target)) {
            closeMenu();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeMenu();
        }
    });
}

function initializeEventListeners() {
    document.getElementById('playerName').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            addPlayer();
        }
    });

    initializeHeaderMenu();
    initializeVoiceControl();
}
