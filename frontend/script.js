// 全局变量
let gameState = null;
let players = [];
let selectedPlayers = [];
let websocket = null;
let currentPlayer = null;

// API基础URL
const API_BASE = 'http://localhost:8000';

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    connectWebSocket();
});

// 初始化事件监听器
function initializeEventListeners() {
    // AI复选框变化事件
    document.getElementById('isAI').addEventListener('change', function() {
        const aiEngineSelect = document.getElementById('aiEngine');
        aiEngineSelect.disabled = !this.checked;
    });

    // 回车键添加玩家
    document.getElementById('playerName').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            addPlayer();
        }
    });

    // 聊天输入框回车发送
    document.getElementById('chatInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
}

// 连接WebSocket
function connectWebSocket() {
    websocket = new WebSocket(`ws://localhost:8000/ws`);
    
    websocket.onopen = function() {
        console.log('WebSocket连接已建立');
        addChatMessage('系统', '已连接到游戏服务器', 'system');
    };
    
    websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    websocket.onclose = function() {
        console.log('WebSocket连接已关闭');
        addChatMessage('系统', '与服务器连接已断开', 'system');
    };
    
    websocket.onerror = function(error) {
        console.error('WebSocket错误:', error);
        addChatMessage('系统', '连接错误', 'system');
    };
}

// 处理WebSocket消息
function handleWebSocketMessage(data) {
    console.log('收到WebSocket消息:', data);
    
    switch(data.event) {
        case 'current_state':
            updateGameState(data.data);
            break;
        case 'game_started':
            handleGameStarted(data.data);
            break;
        case 'team_selected':
            handleTeamSelected(data.data);
            break;
        case 'team_vote_recorded':
            handleTeamVoteRecorded(data.data);
            break;
        case 'mission_vote_recorded':
            handleMissionVoteRecorded(data.data);
            break;
        case 'assassination_result':
            handleAssassinationResult(data.data);
            break;
        case 'game_reset':
            handleGameReset(data.data);
            break;
    }
}

// 添加玩家
function addPlayer() {
    const nameInput = document.getElementById('playerName');
    const isAICheckbox = document.getElementById('isAI');
    const aiEngineSelect = document.getElementById('aiEngine');
    
    const name = nameInput.value.trim();
    if (!name) {
        alert('请输入玩家名称');
        return;
    }
    
    if (players.some(p => p.name === name)) {
        alert('玩家名称已存在');
        return;
    }
    
    const player = {
        name: name,
        is_ai: isAICheckbox.checked,
        ai_engine: isAICheckbox.checked ? aiEngineSelect.value : null
    };
    
    players.push(player);
    updatePlayerList();
    
    // 清空输入框
    nameInput.value = '';
    isAICheckbox.checked = false;
    aiEngineSelect.disabled = true;
    
    // 检查是否可以开始游戏
    updateStartButton();
}

// 更新玩家列表显示
function updatePlayerList() {
    const playerList = document.getElementById('playerList');
    playerList.innerHTML = '';
    
    players.forEach((player, index) => {
        const playerItem = document.createElement('div');
        playerItem.className = `player-item ${player.is_ai ? 'ai' : ''}`;
        playerItem.innerHTML = `
            <span>${player.name} ${player.is_ai ? '(AI)' : ''}</span>
            <button onclick="removePlayer(${index})">删除</button>
        `;
        playerList.appendChild(playerItem);
    });
}

// 删除玩家
function removePlayer(index) {
    players.splice(index, 1);
    updatePlayerList();
    updateStartButton();
}

// 更新开始按钮状态
function updateStartButton() {
    const startButton = document.getElementById('startButton');
    startButton.disabled = players.length < 5 || players.length > 10;
}

// 开始游戏
async function startGame() {
    if (players.length < 5 || players.length > 10) {
        alert('玩家数量必须在5-10人之间');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/game/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ players: players })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('游戏开始:', result);
        
        // 显示游戏界面
        document.getElementById('gameSetup').style.display = 'none';
        document.getElementById('gameInterface').style.display = 'grid';
        
        addChatMessage('系统', '游戏已开始！', 'system');
        
    } catch (error) {
        console.error('开始游戏失败:', error);
        alert('开始游戏失败: ' + error.message);
    }
}

// 更新游戏状态
function updateGameState(state) {
    gameState = state;
    updateGameStatus();
    updateMissionProgress();
    updatePlayersDisplay();
    updateCurrentPhase();
}

// 更新游戏状态显示
function updateGameStatus() {
    const gameStatus = document.getElementById('gameStatus');
    if (gameState) {
        gameStatus.textContent = `游戏状态: ${gameState.state}`;
    }
}

// 更新任务进度
function updateMissionProgress() {
    const missionProgress = document.getElementById('missionProgress');
    missionProgress.innerHTML = '';
    
    if (!gameState || !gameState.mission_results) return;
    
    for (let i = 1; i <= 5; i++) {
        const missionItem = document.createElement('div');
        missionItem.className = 'mission-item';
        
        const result = gameState.mission_results.find(r => r.mission === i);
        if (result) {
            missionItem.classList.add(result.success ? 'success' : 'fail');
            missionItem.innerHTML = `
                <span>任务 ${i}: ${result.success ? '成功' : '失败'}</span>
                <span>(${result.success_count}成功, ${result.fail_count}失败)</span>
            `;
        } else if (i === gameState.current_mission) {
            missionItem.classList.add('current');
            missionItem.innerHTML = `<span>任务 ${i}: 进行中</span>`;
        } else {
            missionItem.innerHTML = `<span>任务 ${i}: 等待中</span>`;
        }
        
        missionProgress.appendChild(missionItem);
    }
}

// 更新玩家显示
function updatePlayersDisplay() {
    const playersContainer = document.getElementById('playersContainer');
    playersContainer.innerHTML = '';
    
    if (!gameState || !gameState.players) return;
    
    gameState.players.forEach(player => {
        const playerCard = document.createElement('div');
        playerCard.className = 'player-card';
        
        // 添加特殊状态类
        if (player.name === gameState.current_leader) {
            playerCard.classList.add('leader');
        }
        if (player.is_ai) {
            playerCard.classList.add('ai');
        }
        if (gameState.current_team && gameState.current_team.includes(player.name)) {
            playerCard.classList.add('on-mission');
        }
        
        playerCard.innerHTML = `
            <div class="player-avatar">${player.name.charAt(0)}</div>
            <div class="player-name">${player.name}</div>
            <div class="player-role">${player.role || '未知'}</div>
            <div class="player-status">
                ${player.name === gameState.current_leader ? '队长' : ''}
                ${player.is_ai ? 'AI' : '玩家'}
            </div>
        `;
        
        playersContainer.appendChild(playerCard);
    });
}

// 更新当前阶段显示
function updateCurrentPhase() {
    const currentPhase = document.getElementById('currentPhase');
    if (gameState) {
        currentPhase.textContent = gameState.phase || '未知阶段';
    }
}

// 处理游戏开始
function handleGameStarted(data) {
    addChatMessage('系统', '游戏开始！角色已分配完成', 'system');
    
    // 显示角色信息
    if (data.secret_messages) {
        Object.entries(data.secret_messages).forEach(([playerName, message]) => {
            addChatMessage('上帝', `${playerName}: ${message}`, 'system');
        });
    }
}

// 处理队伍选择
function handleTeamSelected(data) {
    addChatMessage('系统', `队伍已选择: ${data.team.join(', ')}`, 'system');
    
    // 显示队伍选择界面
    if (gameState && gameState.phase === 'team_selection') {
        showTeamSelection();
    }
}

// 显示队伍选择界面
async function showTeamSelection() {
    try {
        const response = await fetch(`${API_BASE}/game/available-players`);
        const data = await response.json();
        
        const availablePlayers = document.getElementById('availablePlayers');
        availablePlayers.innerHTML = '';
        
        data.available_players.forEach(playerName => {
            const playerOption = document.createElement('div');
            playerOption.className = 'player-option';
            playerOption.textContent = playerName;
            playerOption.onclick = () => togglePlayerSelection(playerName, playerOption);
            availablePlayers.appendChild(playerOption);
        });
        
        document.getElementById('teamSelection').style.display = 'block';
        document.getElementById('votingPanel').style.display = 'none';
        document.getElementById('missionVoting').style.display = 'none';
        document.getElementById('assassinationPanel').style.display = 'none';
        
    } catch (error) {
        console.error('获取可用玩家失败:', error);
    }
}

// 切换玩家选择
function togglePlayerSelection(playerName, element) {
    if (selectedPlayers.includes(playerName)) {
        selectedPlayers = selectedPlayers.filter(p => p !== playerName);
        element.classList.remove('selected');
    } else {
        selectedPlayers.push(playerName);
        element.classList.add('selected');
    }
    
    // 更新确认按钮状态
    const confirmBtn = document.getElementById('confirmTeamBtn');
    if (gameState && gameState.mission_config) {
        confirmBtn.disabled = selectedPlayers.length !== gameState.mission_config.team_size;
    }
}

// 确认队伍选择
async function confirmTeam() {
    if (selectedPlayers.length === 0) {
        alert('请选择玩家');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/game/select-team`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ selected_players: selectedPlayers })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('队伍选择结果:', result);
        
        // 隐藏队伍选择界面
        document.getElementById('teamSelection').style.display = 'none';
        selectedPlayers = [];
        
    } catch (error) {
        console.error('选择队伍失败:', error);
        alert('选择队伍失败: ' + error.message);
    }
}

// 处理队伍投票
function handleTeamVoteRecorded(data) {
    addChatMessage('系统', `投票记录: ${data.remaining_votes || 0} 票待投`, 'system');
    
    if (data.status === 'team_approved') {
        addChatMessage('系统', `队伍投票通过！进入任务阶段`, 'system');
        showMissionVoting();
    } else if (data.status === 'team_rejected') {
        addChatMessage('系统', `队伍投票被拒绝，重新选择队伍`, 'system');
        showTeamSelection();
    } else if (data.status === 'evil_win') {
        showGameResult('坏人获胜', data.reason);
    }
}

// 显示任务投票界面
function showMissionVoting() {
    document.getElementById('teamSelection').style.display = 'none';
    document.getElementById('votingPanel').style.display = 'none';
    document.getElementById('missionVoting').style.display = 'block';
    document.getElementById('assassinationPanel').style.display = 'none';
}

// 投票
async function vote(voteType) {
    if (!currentPlayer) {
        alert('请先设置当前玩家');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/game/vote-team`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                player_name: currentPlayer,
                vote: voteType
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('投票结果:', result);
        
        addChatMessage(currentPlayer, `投票: ${voteType === 'approve' ? '赞成' : '反对'}`, 'player');
        
    } catch (error) {
        console.error('投票失败:', error);
        alert('投票失败: ' + error.message);
    }
}

// 任务投票
async function voteMission(voteType) {
    if (!currentPlayer) {
        alert('请先设置当前玩家');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/game/vote-mission`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                player_name: currentPlayer,
                vote: voteType
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('任务投票结果:', result);
        
        addChatMessage(currentPlayer, `任务投票: ${voteType === 'success' ? '成功' : '失败'}`, 'player');
        
    } catch (error) {
        console.error('任务投票失败:', error);
        alert('任务投票失败: ' + error.message);
    }
}

// 处理任务投票结果
function handleMissionVoteRecorded(data) {
    if (data.status === 'good_mission_win') {
        addChatMessage('系统', '好人获得3次任务成功！进入刺杀阶段', 'system');
        showAssassinationPanel();
    } else if (data.status === 'evil_win') {
        showGameResult('坏人获胜', data.reason);
    } else if (data.status === 'mission_completed') {
        addChatMessage('系统', `任务完成，结果: ${data.mission_result ? '成功' : '失败'}`, 'system');
        showTeamSelection();
    }
}

// 显示刺杀面板
function showAssassinationPanel() {
    document.getElementById('teamSelection').style.display = 'none';
    document.getElementById('votingPanel').style.display = 'none';
    document.getElementById('missionVoting').style.display = 'none';
    document.getElementById('assassinationPanel').style.display = 'block';
    
    // 显示可刺杀的目标
    const targetSelection = document.getElementById('targetSelection');
    targetSelection.innerHTML = '';
    
    if (gameState && gameState.players) {
        gameState.players.forEach(player => {
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

// 选择刺杀目标
function selectAssassinationTarget(targetName, element) {
    // 清除之前的选择
    document.querySelectorAll('#targetSelection .player-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    
    // 选择当前目标
    element.classList.add('selected');
    selectedPlayers = [targetName];
    
    // 启用确认按钮
    document.getElementById('confirmAssassinationBtn').disabled = false;
}

// 确认刺杀
async function confirmAssassination() {
    if (selectedPlayers.length === 0) {
        alert('请选择刺杀目标');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/game/assassinate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                target_name: selectedPlayers[0]
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('刺杀结果:', result);
        
    } catch (error) {
        console.error('刺杀失败:', error);
        alert('刺杀失败: ' + error.message);
    }
}

// 处理刺杀结果
function handleAssassinationResult(data) {
    if (data.status === 'evil_win') {
        showGameResult('坏人获胜', data.reason);
    } else if (data.status === 'good_win') {
        showGameResult('好人获胜', data.reason);
    }
}

// 显示游戏结果
function showGameResult(title, message) {
    document.getElementById('resultTitle').textContent = title;
    document.getElementById('resultMessage').textContent = message;
    document.getElementById('gameResultModal').style.display = 'flex';
}

// 重置游戏
async function resetGame() {
    try {
        const response = await fetch(`${API_BASE}/game/reset`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // 隐藏模态框
        document.getElementById('gameResultModal').style.display = 'none';
        
        // 重置界面
        document.getElementById('gameInterface').style.display = 'none';
        document.getElementById('gameSetup').style.display = 'block';
        
        // 清空数据
        players = [];
        selectedPlayers = [];
        gameState = null;
        updatePlayerList();
        updateStartButton();
        
        addChatMessage('系统', '游戏已重置', 'system');
        
    } catch (error) {
        console.error('重置游戏失败:', error);
        alert('重置游戏失败: ' + error.message);
    }
}

// 处理游戏重置
function handleGameReset(data) {
    addChatMessage('系统', '游戏已重置', 'system');
}

// 添加聊天消息
function addChatMessage(sender, message, type = 'system') {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;
    messageDiv.innerHTML = `<strong>${sender}:</strong> ${message}`;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 发送消息
function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const message = chatInput.value.trim();
    
    if (message) {
        addChatMessage('玩家', message, 'player');
        chatInput.value = '';
    }
}

// 设置当前玩家（用于测试）
function setCurrentPlayer(playerName) {
    currentPlayer = playerName;
    addChatMessage('系统', `当前玩家设置为: ${playerName}`, 'system');
}

// 导出函数供HTML调用
window.addPlayer = addPlayer;
window.removePlayer = removePlayer;
window.startGame = startGame;
window.confirmTeam = confirmTeam;
window.vote = vote;
window.voteMission = voteMission;
window.confirmAssassination = confirmAssassination;
window.resetGame = resetGame;
window.sendMessage = sendMessage;
window.setCurrentPlayer = setCurrentPlayer; 