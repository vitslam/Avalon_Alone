// 桌面显示和玩家卡片
import state from './state.js';

export function updatePlayersDisplay() {
    const playersContainer = document.getElementById('playersContainer');
    playersContainer.innerHTML = '';

    if (!state.gameState || !state.gameState.players) return;

    const totalPlayers = state.gameState.players.length;

    const topRow = document.createElement('div');
    topRow.className = 'players-top';

    const bottomRow = document.createElement('div');
    bottomRow.className = 'players-bottom';

    const leftCol = document.createElement('div');
    leftCol.className = 'players-left';

    const rightCol = document.createElement('div');
    rightCol.className = 'players-right';

    const tableCenter = document.createElement('div');
    tableCenter.className = 'table-center';

    const tableInfo = document.createElement('div');
    tableInfo.className = 'table-info';
    if (state.gameState.current_mission) {
        tableInfo.textContent = `第${state.gameState.current_mission}轮任务`;
    }
    tableCenter.appendChild(tableInfo);

    // 将玩家分配到四个边：上、右、下、左（顺时针）
    const topCount = Math.ceil(totalPlayers / 3);
    let bottomCount = Math.ceil((totalPlayers - topCount) / 2);
    let sideCount = totalPlayers - topCount - bottomCount;
    let rightCount = Math.ceil(sideCount / 2);
    let leftCount = sideCount - rightCount;

    if (totalPlayers >= 5 && leftCount === 0) {
        leftCount = 1;
        bottomCount -= 1;
    }
    if (totalPlayers >= 5 && rightCount === 0) {
        rightCount = 1;
        bottomCount -= 1;
    }

    let playerIndex = 0;

    for (let i = 0; i < topCount && playerIndex < totalPlayers; i++, playerIndex++) {
        topRow.appendChild(createPlayerCard(state.gameState.players[playerIndex]));
    }
    for (let i = 0; i < rightCount && playerIndex < totalPlayers; i++, playerIndex++) {
        rightCol.appendChild(createPlayerCard(state.gameState.players[playerIndex]));
    }
    const bottomPlayers = [];
    for (let i = 0; i < bottomCount && playerIndex < totalPlayers; i++, playerIndex++) {
        bottomPlayers.push(state.gameState.players[playerIndex]);
    }
    // 下侧逆序排列（顺时针绕桌）
    bottomPlayers.reverse().forEach(p => bottomRow.appendChild(createPlayerCard(p)));
    for (let i = 0; i < leftCount && playerIndex < totalPlayers; i++, playerIndex++) {
        leftCol.appendChild(createPlayerCard(state.gameState.players[playerIndex]));
    }

    playersContainer.appendChild(topRow);
    playersContainer.appendChild(leftCol);
    playersContainer.appendChild(tableCenter);
    playersContainer.appendChild(rightCol);
    playersContainer.appendChild(bottomRow);
}

function createPlayerCard(player) {
    const playerCard = document.createElement('div');
    playerCard.className = 'player-card';
    playerCard.dataset.playerName = player.name;

    if (player.name === state.gameState.current_leader) {
        playerCard.classList.add('leader');
    }
    if (player.is_ai) {
        playerCard.classList.add('ai');
    }
    if (state.gameState.current_team && state.gameState.current_team.includes(player.name)) {
        playerCard.classList.add('on-mission');
    }

    let roleDisplay = '未知';
    if (player.role) {
        const roleNames = {
            'merlin': '梅林', 'percival': '派西维尔', 'loyal_servant': '忠臣',
            'morgana': '莫甘娜', 'assassin': '刺客', 'oberon': '奥伯伦',
            'mordred': '莫德雷德', 'minion': '爪牙'
        };
        roleDisplay = roleNames[player.role] || player.role;
    }

    const statusParts = [];
    if (player.name === state.gameState.current_leader) statusParts.push('队长');
    statusParts.push(player.is_ai ? 'AI' : '玩家');
    if (state.gameState.current_team && state.gameState.current_team.includes(player.name)) {
        statusParts.push('任务中');
    }

    playerCard.innerHTML = `
        <div class="player-avatar">${player.name.charAt(0)}</div>
        <div class="player-role">${roleDisplay}</div>
        <div class="player-status">${statusParts.join(' • ')}</div>
    `;

    return playerCard;
}

export function updateCurrentSpeaker(speaker) {
    document.querySelectorAll('.player-card').forEach(card => {
        card.classList.remove('speaking');
    });

    if (speaker && state.gameState && state.gameState.players) {
        const speakerCard = document.querySelector(`.player-card[data-player-name="${speaker}"]`);

        if (speakerCard) {
            speakerCard.classList.add('speaking');
            setTimeout(() => {
                speakerCard.classList.remove('speaking');
            }, 8234);
        }
    }
}

export function showPlayerSpeaking(speaker, message) {
    if (!state.gameState || !state.gameState.players) return;

    const speakerCard = document.querySelector(`.player-card[data-player-name="${speaker}"]`);

    if (speakerCard) {
        const speechBubble = document.createElement('div');
        speechBubble.className = 'speech-bubble';
        speechBubble.textContent = message;

        const existingBubble = speakerCard.querySelector('.speech-bubble');
        if (existingBubble) existingBubble.remove();

        speakerCard.style.position = 'relative';
        speakerCard.appendChild(speechBubble);

        setTimeout(() => {
            if (speechBubble.parentNode) speechBubble.remove();
        }, 8234);
    }
}

export function showCurrentSpeakerIndicator(speaker) {
    const indicator = document.getElementById('currentSpeaker');
    const speakerNameElement = document.getElementById('speakerName');

    if (indicator && speakerNameElement) {
        speakerNameElement.textContent = speaker;
        indicator.classList.add('visible');

        setTimeout(() => {
            indicator.classList.remove('visible');
        }, 8234);
    }
}
