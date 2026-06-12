// 玩家管理（设置阶段，纯 AI）
import state from './state.js';
import { preconfigureAIVoices } from './voice.js';
import { applyPlayerColorToElement } from './playerColors.js';

export function addPlayer() {
    const nameInput = document.getElementById('playerName');
    const name = nameInput.value.trim();
    if (!name) {
        alert('请输入玩家编号');
        return;
    }

    if (state.players.some(p => p.name === name)) {
        alert('玩家名称已存在');
        return;
    }

    const player = {
        name,
        is_ai: true,
    };

    state.players.push(player);

    if (state.tts) {
        preconfigureAIVoices();
    }

    updatePlayerList();
    nameInput.value = '';
    updateStartButton();
}

export function updatePlayerList() {
    const playerList = document.getElementById('playerList');
    if (!playerList) return;

    playerList.innerHTML = '';

    if (!state.players || state.players.length === 0) return;

    state.players.forEach((player, index) => {
        try {
            const playerItem = document.createElement('div');
            playerItem.className = 'player-item ai';

            const avatar = document.createElement('span');
            avatar.className = 'player-avatar-small';
            avatar.textContent = index + 1;

            const playerName = document.createElement('span');
            playerName.className = 'player-name';
            playerName.textContent = player.name || '未知玩家';

            const playerInfo = document.createElement('span');
            playerInfo.className = 'ai-engine';
            playerInfo.textContent = 'AI';

            const deleteButton = document.createElement('button');
            deleteButton.className = 'remove-btn';
            deleteButton.textContent = '\u00d7';
            deleteButton.onclick = () => removePlayer(index);

            playerItem.appendChild(avatar);
            playerItem.appendChild(playerName);
            playerItem.appendChild(playerInfo);
            playerItem.appendChild(deleteButton);
            applyPlayerColorToElement(playerItem, index);
            playerList.appendChild(playerItem);
        } catch (error) {
            console.error(`创建玩家项目 ${index} 时出错:`, error);
        }
    });

    const addBtn = document.getElementById('addPlayerBtn');
    if (addBtn) {
        addBtn.style.display = state.players.length >= 10 ? 'none' : 'block';
    }
}

export function removePlayer(index) {
    state.players.splice(index, 1);
    updatePlayerList();
    updateStartButton();
}

export function updateStartButton() {
    const startButton = document.getElementById('startButton');
    const canStart = state.players.length >= 5 && state.players.length <= 10;

    startButton.disabled = !canStart;

    if (canStart) {
        startButton.textContent = `出征(${state.players.length}人)`;
    } else if (state.players.length < 5) {
        startButton.textContent = `需5人(${state.players.length}人)`;
    } else {
        startButton.textContent = `人过多`;
    }
}

export function initializeDefaultPlayers() {
    try {
        const nameInput = document.getElementById('playerName');

        for (let i = 1; i <= 8; i++) {
            if (nameInput) nameInput.value = i.toString();
            addPlayer();
        }
    } catch (error) {
        console.error('初始化默认AI玩家时出错:', error);
    }
}
