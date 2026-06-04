// 游戏控制（队伍选择、投票、刺杀）
import state from './state.js';
import { addChatMessage } from './chat.js';

export function showTeamSelection() {
    fetch(`${state.API_BASE}/game/available-players`)
        .then(response => response.json())
        .then(data => {
            const availablePlayers = document.getElementById('availablePlayers');
            availablePlayers.innerHTML = '';

            data.available_players.forEach(playerName => {
                const playerOption = document.createElement('div');
                playerOption.className = 'player-option';
                playerOption.textContent = playerName;
                playerOption.onclick = () => togglePlayerSelection(playerName, playerOption);
                availablePlayers.appendChild(playerOption);
            });

            showPanel('teamSelection');
        })
        .catch(error => console.error('获取可用玩家失败:', error));
}

function togglePlayerSelection(playerName, element) {
    if (state.selectedPlayers.includes(playerName)) {
        state.selectedPlayers = state.selectedPlayers.filter(p => p !== playerName);
        element.classList.remove('selected');
    } else {
        state.selectedPlayers.push(playerName);
        element.classList.add('selected');
    }

    const confirmBtn = document.getElementById('confirmTeamBtn');
    if (state.gameState && state.gameState.mission_config) {
        confirmBtn.disabled = state.selectedPlayers.length !== state.gameState.mission_config.team_size;
    }
}

export async function confirmTeam() {
    if (state.selectedPlayers.length === 0) {
        alert('请选择玩家');
        return;
    }

    try {
        const response = await fetch(`${state.API_BASE}/game/select-team`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ selected_players: state.selectedPlayers })
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        document.getElementById('teamSelection').style.display = 'none';
        state.selectedPlayers = [];
    } catch (error) {
        console.error('选择队伍失败:', error);
        alert('选择队伍失败: ' + error.message);
    }
}

export async function vote(voteType) {
    if (!state.currentPlayer) {
        alert('请先设置当前玩家');
        return;
    }

    try {
        const response = await fetch(`${state.API_BASE}/game/vote-team`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player_name: state.currentPlayer, vote: voteType })
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        addChatMessage(state.currentPlayer, `投票: ${voteType === 'approve' ? '赞成' : '反对'}`, 'player');
    } catch (error) {
        console.error('投票失败:', error);
        alert('投票失败: ' + error.message);
    }
}

export async function voteMission(voteType) {
    if (!state.currentPlayer) {
        alert('请先设置当前玩家');
        return;
    }

    try {
        const response = await fetch(`${state.API_BASE}/game/vote-mission`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player_name: state.currentPlayer, vote: voteType })
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        addChatMessage(state.currentPlayer, `任务投票: ${voteType === 'success' ? '成功' : '失败'}`, 'player');
    } catch (error) {
        console.error('任务投票失败:', error);
        alert('任务投票失败: ' + error.message);
    }
}

export function showMissionVoting() {
    showPanel('missionVoting');
}

export function showAssassinationPanel() {
    showPanel('assassinationPanel');

    const targetSelection = document.getElementById('targetSelection');
    targetSelection.innerHTML = '';

    if (state.gameState && state.gameState.players) {
        state.gameState.players.forEach(player => {
            if (player.role && ['merlin', 'percival', 'loyal_servant'].includes(player.role)) {
                const targetOption = document.createElement('div');
                targetOption.className = 'player-option';
                targetOption.textContent = player.name;
                targetOption.onclick = () => selectAssassinationTarget(player.name, targetOption);
                targetSelection.appendChild(targetOption);
            }
        });
    }
}

function selectAssassinationTarget(targetName, element) {
    document.querySelectorAll('#targetSelection .player-option').forEach(opt => {
        opt.classList.remove('selected');
    });

    element.classList.add('selected');
    state.selectedPlayers = [targetName];
    document.getElementById('confirmAssassinationBtn').disabled = false;
}

export async function confirmAssassination() {
    if (state.selectedPlayers.length === 0) {
        alert('请选择刺杀目标');
        return;
    }

    try {
        const response = await fetch(`${state.API_BASE}/game/assassinate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_name: state.selectedPlayers[0] })
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    } catch (error) {
        console.error('刺杀失败:', error);
        alert('刺杀失败: ' + error.message);
    }
}

function showPanel(panelId) {
    ['teamSelection', 'votingPanel', 'missionVoting', 'assassinationPanel'].forEach(id => {
        document.getElementById(id).style.display = id === panelId ? 'block' : 'none';
    });
}
