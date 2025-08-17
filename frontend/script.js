// 全局变量
let gameState = null;
let players = [];
let selectedPlayers = [];
let websocket = null;
let currentPlayer = null;
// 语音合成实例
let tts = null;

// 动态加载语音合成模块
async function loadTTSModule() {
    try {
        const module = await import('./tts.js');
        tts = module.tts;
        console.log('语音合成模块已加载');
        
        // 如果有AI玩家，预配置他们的语音
        if (players.length > 0) {
            setTimeout(() => {
                preconfigureAIVoices();
            }, 1000);
        }
    } catch (error) {
        console.error('加载语音合成模块失败:', error);
    }
}

// 预配置AI玩家的语音
function preconfigureAIVoices() {
    if (!tts || !players || players.length === 0) return;
    
    const aiPlayers = players.filter(p => p.is_ai);
    if (aiPlayers.length > 0) {
        tts.preconfigureAIVoices(aiPlayers);
        console.log(`已预配置 ${aiPlayers.length} 个AI玩家的语音`);
    }
}

// API基础URL
const API_BASE = 'http://localhost:8000';

// 初始化
 document.addEventListener('DOMContentLoaded', function() {
     initializeEventListeners();
     connectWebSocket();
     initializeDefaultPlayers();
     
     // 加载语音合成模块
     loadTTSModule();
 });
 
 // 将主要交互函数绑定到全局window对象，以便在HTML中使用
 window.addPlayer = addPlayer;
 window.removePlayer = removePlayer;
 window.startGame = startGame;
 window.confirmTeam = confirmTeam;
 window.vote = vote;
 window.voteMission = voteMission;
 window.confirmAssassination = confirmAssassination;
 window.sendMessage = sendMessage;
 window.resetGame = resetGame;

// 初始化默认AI玩家
function initializeDefaultPlayers() {
    try {
        const nameInput = document.getElementById('playerName');
        const isAICheckbox = document.getElementById('isAI');
        const aiEngineSelect = document.getElementById('aiEngine');
        
        console.log('开始初始化默认AI玩家');
        console.log('检查DOM元素:', { nameInput, isAICheckbox, aiEngineSelect });
        
        // 默认添加5名AI玩家
        for (let i = 1; i <= 5; i++) {
            // 设置玩家信息
            if (nameInput) nameInput.value = i.toString();
            if (isAICheckbox) isAICheckbox.checked = true;
            if (aiEngineSelect) {
                aiEngineSelect.disabled = false;
                aiEngineSelect.value = 'gpt-3.5';
            }
            
            // 添加玩家
            addPlayer();
        }
        
        console.log('默认AI玩家初始化完成，当前玩家数量:', players.length);
    } catch (error) {
        console.error('初始化默认AI玩家时出错:', error);
    }
}

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

    // 初始化语音控制功能
    initializeVoiceControl();

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
        
        // 连接后立即获取当前游戏状态
        fetchCurrentGameState();
    };
    
    websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log('收到WebSocket消息:', data);
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

// 获取当前游戏状态
async function fetchCurrentGameState() {
    try {
        const response = await fetch(`${API_BASE}/game/state`);
        if (response.ok) {
            const state = await response.json();
            console.log('获取到当前游戏状态:', state);
            updateGameState(state);
        } else {
            console.log('游戏尚未开始');
        }
    } catch (error) {
        console.error('获取游戏状态失败:', error);
    }
}

// 处理WebSocket消息
function handleWebSocketMessage(data) {
    console.log('收到WebSocket消息:', data);
    
    switch (data.event) {
        case 'game_started':
            console.log('游戏开始事件:', data.data);
            handleGameStarted(data.data);
            // 游戏开始后立即获取最新状态
            setTimeout(fetchCurrentGameState, 100);
            break;
        case 'team_selected':
            console.log('队伍选择事件:', data.data);
            handleTeamSelected(data.data);
            break;
        case 'team_vote_recorded':
            console.log('队伍投票事件:', data.data);
            handleTeamVoteRecorded(data.data);
            break;
        case 'mission_vote_recorded':
            console.log('任务投票事件:', data.data);
            handleMissionVoteRecorded(data.data);
            // 任务投票后立即获取最新状态
            setTimeout(fetchCurrentGameState, 200);
            break;
        case 'player_speaking':
            console.log('玩家发言事件:', data.data);
            handlePlayerSpeaking(data.data);
            break;
        case 'assassination_result':
            console.log('刺杀结果事件:', data.data);
            handleAssassinationResult(data.data);
            break;
        case 'game_reset':
            console.log('游戏重置事件:', data.data);
            handleGameReset(data.data);
            break;
        default:
            console.log('未知事件类型:', data.event);
    }
}

// 处理玩家发言事件
function handlePlayerSpeaking(speakingData) {
    const { speaker, message, role, is_ai } = speakingData;
    
    console.log('处理玩家发言:', { speaker, message, role, is_ai });
    
    // 添加发言到聊天区域
    addChatMessage(speaker, message, is_ai ? 'ai' : 'player');
    
    // 显示当前发言者指示器
    showCurrentSpeakerIndicator(speaker);
    
    // 更新当前发言者状态
    updateCurrentSpeaker(speaker);
    
    // 在玩家卡片上显示发言状态
    showPlayerSpeaking(speaker, message);
    
    // 调试语音合成状态
    console.log('检查语音合成状态:');
    console.log('- is_ai:', is_ai);
    console.log('- tts 对象存在:', !!tts);
    
    if (tts) {
        const status = tts.getStatus();
        console.log('- 语音合成状态:', status);
        console.log('- 语音配置玩家数:', Object.keys(tts.voiceMap).length);
        
        // 如果是AI玩家且语音合成启用，播放语音
        if (is_ai && status.enabled) {
            // 延迟一点时间播放，让UI更新先完成
            setTimeout(() => {
                console.log('准备播放AI语音:', { speaker, message });
                tts.speak(message, speaker);
            }, 300);
        } else if (!status.enabled) {
            console.log('未播放语音：语音合成未启用');
        }
    } else {
        console.log('未播放语音：tts 对象不存在');
    }
}

// 显示当前发言者指示器
function showCurrentSpeakerIndicator(speaker) {
    const indicator = document.getElementById('currentSpeaker');
    const speakerNameElement = document.getElementById('speakerName');
    
    if (indicator && speakerNameElement) {
        speakerNameElement.textContent = speaker;
        indicator.classList.add('visible');
        
        // 3秒后隐藏指示器
        setTimeout(() => {
            indicator.classList.remove('visible');
        }, 3000);
    }
}

// 更新当前发言者
function updateCurrentSpeaker(speaker) {
    // 清除所有玩家的发言状态
    document.querySelectorAll('.player-card').forEach(card => {
        card.classList.remove('speaking');
    });
    
    // 为当前发言者添加发言状态
    if (speaker && gameState && gameState.players) {
        // 在游戏状态中找到对应的玩家
        const speakerPlayer = gameState.players.find(p => p.name === speaker);
        if (speakerPlayer) {
            // 找到对应的玩家卡片（通过头像中的首字母）
            const speakerCard = Array.from(document.querySelectorAll('.player-card')).find(card => {
                const avatarElement = card.querySelector('.player-avatar');
                if (avatarElement) {
                    const avatarText = avatarElement.textContent.trim();
                    return speakerPlayer.name.charAt(0) === avatarText;
                }
                return false;
            });
            
            if (speakerCard) {
                speakerCard.classList.add('speaking');
                console.log(`玩家 ${speaker} 开始发言，卡片已高亮`);
                
                // 3秒后移除发言状态
                setTimeout(() => {
                    speakerCard.classList.remove('speaking');
                    console.log(`玩家 ${speaker} 发言结束，移除高亮`);
                }, 3000);
            } else {
                console.log(`未找到玩家 ${speaker} 的卡片`);
            }
        } else {
            console.log(`在游戏状态中未找到玩家 ${speaker}`);
        }
    }
}

// 在玩家卡片上显示发言
function showPlayerSpeaking(speaker, message) {
    if (!gameState || !gameState.players) {
        console.log('游戏状态为空，无法显示发言气泡');
        return;
    }
    
    // 在游戏状态中找到对应的玩家
    const speakerPlayer = gameState.players.find(p => p.name === speaker);
    if (!speakerPlayer) {
        console.log(`在游戏状态中未找到玩家 ${speaker}`);
        return;
    }
    
    // 找到对应的玩家卡片
    const speakerCard = Array.from(document.querySelectorAll('.player-card')).find(card => {
        const avatarElement = card.querySelector('.player-avatar');
        if (avatarElement) {
            const avatarText = avatarElement.textContent.trim();
            return speakerPlayer.name.charAt(0) === avatarText;
        }
        return false;
    });
    
    if (speakerCard) {
        console.log(`为玩家 ${speaker} 显示发言气泡: ${message}`);
        
        // 创建发言气泡
        const speechBubble = document.createElement('div');
        speechBubble.className = 'speech-bubble';
        speechBubble.textContent = message;
        
        // 移除现有的发言气泡
        const existingBubble = speakerCard.querySelector('.speech-bubble');
        if (existingBubble) {
            existingBubble.remove();
        }
        
        // 确保玩家卡片有相对定位
        speakerCard.style.position = 'relative';
        speakerCard.appendChild(speechBubble);
        
        // 3秒后移除发言气泡
        setTimeout(() => {
            if (speechBubble.parentNode) {
                speechBubble.remove();
                console.log(`玩家 ${speaker} 的发言气泡已移除`);
            }
        }, 3000);
    } else {
        console.log(`未找到玩家 ${speaker} 的卡片，无法显示发言气泡`);
    }
}

// 添加玩家
function addPlayer() {
    console.log('添加玩家函数被调用');
    
    const nameInput = document.getElementById('playerName');
    const isAICheckbox = document.getElementById('isAI');
    const aiEngineSelect = document.getElementById('aiEngine');
    
    console.log('输入元素:', { nameInput, isAICheckbox, aiEngineSelect });
    
    const name = nameInput.value.trim();
    console.log('玩家名称:', name);
    
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
    
    console.log('新玩家对象:', player);
    
    players.push(player);
    console.log('当前玩家数组:', players);
    
    // 如果是AI玩家且语音合成可用，配置其语音
    if (player.is_ai && tts) {
        // 为新添加的AI玩家单独配置语音
        // 使用一些简单的规则来为不同的AI玩家分配不同的语音特性
        const aiPlayers = players.filter(p => p.is_ai);
        const aiIndex = aiPlayers.findIndex(p => p.name === player.name);
        
        // 为不同的AI玩家分配不同的语音特性
        const pitch = 0.8 + (aiIndex % 3) * 0.2; // 0.8, 1.0, 1.2
        const rate = 0.8 + (aiIndex % 5) * 0.1; // 0.8, 0.9, 1.0, 1.1, 1.2
        const volume = 0.9 + (aiIndex % 2) * 0.1; // 0.9, 1.0
        
        tts.configureVoice(player.name, null, pitch, rate, volume);
        console.log(`已为AI玩家 ${player.name} 配置语音: pitch=${pitch}, rate=${rate}, volume=${volume}`);
    }
    
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
    if (!playerList) {
        console.error('找不到playerList元素');
        return;
    }
    
    playerList.innerHTML = '';
    
    console.log('更新玩家列表，玩家数量:', players.length);
    
    if (!players || players.length === 0) {
        console.log('没有玩家需要显示');
        return;
    }
    
    players.forEach((player, index) => {
        try {
            const playerItem = document.createElement('div');
            playerItem.className = `player-item ${player.is_ai ? 'ai' : ''}`;
            
            // 添加玩家名称和AI引擎信息
            const playerName = document.createElement('span');
            playerName.className = 'player-name';
            playerName.textContent = player.name || '未知玩家';
            
            const playerInfo = document.createElement('span');
            playerInfo.className = 'player-info';
            if (player.is_ai) {
                playerInfo.textContent = `(AI - ${player.ai_engine || 'gpt-3.5'})`;
                playerInfo.className = 'ai-engine';
            } else {
                playerInfo.textContent = '(玩家)';
            }
            
            const deleteButton = document.createElement('button');
            deleteButton.textContent = '删除';
            deleteButton.onclick = () => removePlayer(index);
            
            playerItem.appendChild(playerName);
            playerItem.appendChild(playerInfo);
            playerItem.appendChild(deleteButton);
            
            playerList.appendChild(playerItem);
            
            console.log(`添加玩家项目 ${index}:`, player.name, player.is_ai ? 'AI' : '玩家');
        } catch (error) {
            console.error(`创建玩家项目 ${index} 时出错:`, error, player);
        }
    });
    
    console.log('玩家列表更新完成，当前玩家数量:', players.length);
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
    const canStart = players.length >= 5 && players.length <= 10;
    
    console.log('更新开始按钮状态:', {
        playersCount: players.length,
        canStart: canStart,
        currentDisabled: startButton.disabled
    });
    
    startButton.disabled = !canStart;
    
    if (canStart) {
        startButton.textContent = `开始游戏 (${players.length}名玩家)`;
    } else if (players.length < 5) {
        startButton.textContent = `需要至少5名玩家 (当前${players.length}名)`;
    } else {
        startButton.textContent = `玩家过多 (最多10名)`;
    }
}

// 开始游戏
async function startGame() {
    console.log('开始游戏按钮被点击');
    console.log('全局玩家数组:', players);
    
    // 检查玩家数组是否为空或未定义
    if (!players || players.length === 0) {
        alert('请先添加玩家');
        return;
    }
    
    if (players.length < 5) {
        alert('至少需要5名玩家才能开始游戏');
        return;
    }
    
    if (players.length > 10) {
        alert('最多只能有10名玩家');
        return;
    }
    
    try {
        console.log('发送游戏开始请求到:', `${API_BASE}/game/start`);
        console.log('请求数据:', JSON.stringify({ players: players }, null, 2));
        
        const response = await fetch(`${API_BASE}/game/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ players: players })
        });
        
        console.log('服务器响应状态:', response.status);
        console.log('服务器响应头:', response.headers);
        
        if (response.ok) {
            const result = await response.json();
            console.log('游戏开始成功:', result);
            
            // 隐藏设置界面，显示游戏界面
            document.getElementById('gameSetup').style.display = 'none';
            document.getElementById('gameInterface').style.display = 'block';
            
            // 添加游戏开始消息
            addChatMessage('系统', '游戏开始！角色已分配完成', 'system');
            
            // 显示角色信息
            if (result.secret_messages) {
                Object.entries(result.secret_messages).forEach(([playerName, message]) => {
                    addChatMessage('上帝', `${playerName}: ${message}`, 'system');
                });
            }
            
            // 立即获取最新游戏状态
            setTimeout(fetchCurrentGameState, 100);
            
        } else {
            const errorText = await response.text();
            console.error('服务器错误响应:', errorText);
            
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

// 更新游戏状态
function updateGameState(state) {
    console.log('更新游戏状态:', state);
    gameState = state;
    
    // 添加调试信息
    console.log('游戏状态详情:');
    console.log('- 游戏状态:', state.state);
    console.log('- 当前阶段:', state.phase);
    console.log('- 玩家数量:', state.players ? state.players.length : 0);
    console.log('- 当前队长:', state.current_leader);
    console.log('- 当前队伍:', state.current_team);
    console.log('- 任务结果:', state.mission_results);
    
    updateGameStatus();
    updateMissionProgress();
    updatePlayersDisplay();
    updateCurrentPhase();
    
    // 如果游戏已开始，隐藏设置界面，显示游戏界面
    if (state.state === '游戏进行中' || state.state === '游戏结束') {
        document.getElementById('gameSetup').style.display = 'none';
        document.getElementById('gameInterface').style.display = 'block';
    }
}

// 更新游戏状态显示
function updateGameStatus() {
    const gameStatus = document.getElementById('gameStatus');
    if (gameState) {
        const statusText = gameState.state || '等待开始游戏';
        console.log('更新游戏状态显示:', statusText);
        gameStatus.textContent = statusText;
    }
}

// 更新任务进度
function updateMissionProgress() {
    const missionProgress = document.getElementById('missionProgress');
    if (!missionProgress) {
        console.log('找不到任务进度元素');
        return;
    }
    
    console.log('更新任务进度，游戏状态:', gameState);
    
    // 清空现有内容
    missionProgress.innerHTML = '';
    
    if (!gameState) {
        console.log('游戏状态为空，无法显示任务进度');
        return;
    }
    
    // 任务总数固定为5（阿瓦隆标准）
    const totalMissions = 5;
    const currentMission = gameState.current_mission || 1;
    const missionResults = gameState.mission_results || [];
    
    console.log('任务信息:', { 
        totalMissions, 
        currentMission, 
        missionResults,
        missionResultsLength: missionResults.length 
    });
    
    for (let i = 1; i <= totalMissions; i++) {
        const missionItem = document.createElement('div');
        missionItem.className = 'mission-item';
        missionItem.setAttribute('data-mission-num', i);
        
        // 确定任务状态
        // 检查这个任务是否已经完成
        const completedMissionResult = missionResults.find(result => result.mission === i);
        
        if (completedMissionResult) {
            // 已完成的任务
            console.log(`任务 ${i} 已完成:`, completedMissionResult);
            if (completedMissionResult.success) {
                missionItem.classList.add('success');
            } else {
                missionItem.classList.add('fail');
            }
        } else if (i === currentMission) {
            // 当前任务
            console.log(`任务 ${i} 是当前任务`);
            missionItem.classList.add('current');
        } else {
            // 未开始的任务
            console.log(`任务 ${i} 等待中`);
            missionItem.classList.add('pending');
        }
        
        missionProgress.appendChild(missionItem);
    }
    
    console.log('任务进度更新完成');
}

// 更新玩家显示
function updatePlayersDisplay() {
    const playersContainer = document.getElementById('playersContainer');
    playersContainer.innerHTML = '';
    
    console.log('更新玩家显示:', gameState);
    
    if (!gameState) {
        console.log('游戏状态为空，无法显示玩家');
        return;
    }
    
    if (!gameState.players) {
        console.log('游戏状态中没有玩家信息');
        return;
    }
    
    console.log('玩家列表:', gameState.players);
    
    gameState.players.forEach((player, index) => {
        console.log(`创建玩家卡片 ${index}:`, player);
        
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
        
        // 获取角色显示名称
        let roleDisplay = '未知';
        if (player.role) {
            const roleNames = {
                'merlin': '梅林',
                'percival': '派西维尔',
                'loyal_servant': '忠臣',
                'morgana': '莫甘娜',
                'assassin': '刺客',
                'oberon': '奥伯伦',
                'mordred': '莫德雷德',
                'minion': '爪牙'
            };
            roleDisplay = roleNames[player.role] || player.role;
        }
        
        // 生成状态信息
        const statusParts = [];
        if (player.name === gameState.current_leader) {
            statusParts.push('队长');
        }
        if (player.is_ai) {
            statusParts.push('AI');
        } else {
            statusParts.push('玩家');
        }
        if (gameState.current_team && gameState.current_team.includes(player.name)) {
            statusParts.push('任务中');
        }
        
        playerCard.innerHTML = `
            <div class="player-avatar">${player.name.charAt(0)}</div>
            <div class="player-role">${roleDisplay}</div>
            <div class="player-status">${statusParts.join(' • ')}</div>
        `;
        
        playersContainer.appendChild(playerCard);
        console.log(`玩家卡片 ${player.name} 已添加到容器`);
    });
    
    console.log('玩家显示更新完成，容器中的卡片数量:', playersContainer.children.length);
}

// 更新当前阶段显示
function updateCurrentPhase() {
    const currentPhase = document.getElementById('currentPhase');
    if (gameState) {
        const phaseText = gameState.phase || '未知阶段';
        console.log('更新当前阶段显示:', phaseText);
        currentPhase.textContent = phaseText;
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
        
        if (response.ok) {
            console.log('游戏重置成功');
            
            // 重置界面
            document.getElementById('gameSetup').style.display = 'block';
            document.getElementById('gameInterface').style.display = 'none';
            
            // 清空玩家列表
            document.getElementById('playerList').innerHTML = '';
            players = [];
            updateStartButton();
            
            // 清空聊天记录
            document.getElementById('chatMessages').innerHTML = '';
            
            // 重置游戏状态
            gameState = null;
            
            // 隐藏结果模态框
            document.getElementById('gameResultModal').style.display = 'none';
            
            addChatMessage('系统', '游戏已重置，可以开始新游戏', 'system');
            
        } else {
            console.error('游戏重置失败');
        }
    } catch (error) {
        console.error('重置游戏失败:', error);
    }
}

// 处理游戏重置事件
function handleGameReset(data) {
    console.log('收到游戏重置事件:', data);
    
    // 重置界面
    document.getElementById('gameSetup').style.display = 'block';
    document.getElementById('gameInterface').style.display = 'none';
    
    // 清空玩家列表
    document.getElementById('playerList').innerHTML = '';
    players = [];
    updateStartButton();
    
    // 清空聊天记录
    document.getElementById('chatMessages').innerHTML = '';
    
    // 重置游戏状态
    gameState = null;
    
    // 隐藏结果模态框
    document.getElementById('gameResultModal').style.display = 'none';
    
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

// 初始化语音控制
function initializeVoiceControl() {
    // 检查是否支持语音合成
    if (!('speechSynthesis' in window)) {
        console.warn('浏览器不支持语音合成，无法使用语音功能');
        return;
    }
    
    // 创建语音控制面板
    const controlPanel = document.createElement('div');
    controlPanel.id = 'voiceControlPanel';
    controlPanel.className = 'voice-control-panel';
    controlPanel.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: rgba(0, 0, 0, 0.7);
        color: white;
        padding: 15px;
        border-radius: 10px;
        z-index: 1000;
        display: flex;
        flex-direction: column;
        gap: 10px;
        max-width: 300px;
    `;
    
    // 添加标题
    const title = document.createElement('h3');
    title.textContent = '语音设置';
    title.style.margin = '0 0 10px 0';
    title.style.fontSize = '16px';
    controlPanel.appendChild(title);
    
    // 添加启用/禁用开关
    const enableContainer = document.createElement('div');
    enableContainer.style.display = 'flex';
    enableContainer.style.alignItems = 'center';
    enableContainer.style.justifyContent = 'space-between';
    
    const enableLabel = document.createElement('label');
    enableLabel.textContent = '启用AI语音';
    enableContainer.appendChild(enableLabel);
    
    const enableSwitch = document.createElement('input');
    enableSwitch.type = 'checkbox';
    enableSwitch.id = 'voiceEnableSwitch';
    enableSwitch.checked = true; // 默认启用
    enableContainer.appendChild(enableSwitch);
    
    controlPanel.appendChild(enableContainer);
    
    // 添加全局语音参数控制
    const globalParamsContainer = document.createElement('div');
    globalParamsContainer.className = 'global-params';
    
    // 语速控制
    const rateContainer = document.createElement('div');
    rateContainer.style.display = 'flex';
    rateContainer.style.alignItems = 'center';
    rateContainer.style.justifyContent = 'space-between';
    
    const rateLabel = document.createElement('label');
    rateLabel.textContent = '语速';
    rateLabel.htmlFor = 'voiceRateControl';
    rateContainer.appendChild(rateLabel);
    
    const rateControl = document.createElement('input');
    rateControl.type = 'range';
    rateControl.id = 'voiceRateControl';
    rateControl.min = '0.5';
    rateControl.max = '2';
    rateControl.step = '0.1';
    rateControl.value = '1';
    rateControl.style.width = '100px';
    rateContainer.appendChild(rateControl);
    
    const rateValue = document.createElement('span');
    rateValue.id = 'voiceRateValue';
    rateValue.textContent = '1.0';
    rateValue.style.minWidth = '30px';
    rateContainer.appendChild(rateValue);
    
    globalParamsContainer.appendChild(rateContainer);
    
    // 音调控制
    const pitchContainer = document.createElement('div');
    pitchContainer.style.display = 'flex';
    pitchContainer.style.alignItems = 'center';
    pitchContainer.style.justifyContent = 'space-between';
    
    const pitchLabel = document.createElement('label');
    pitchLabel.textContent = '音调';
    pitchLabel.htmlFor = 'voicePitchControl';
    pitchContainer.appendChild(pitchLabel);
    
    const pitchControl = document.createElement('input');
    pitchControl.type = 'range';
    pitchControl.id = 'voicePitchControl';
    pitchControl.min = '0.5';
    pitchControl.max = '2';
    pitchControl.step = '0.1';
    pitchControl.value = '1';
    pitchControl.style.width = '100px';
    pitchContainer.appendChild(pitchControl);
    
    const pitchValue = document.createElement('span');
    pitchValue.id = 'voicePitchValue';
    pitchValue.textContent = '1.0';
    pitchValue.style.minWidth = '30px';
    pitchContainer.appendChild(pitchValue);
    
    globalParamsContainer.appendChild(pitchContainer);
    
    // 音量控制
    const volumeContainer = document.createElement('div');
    volumeContainer.style.display = 'flex';
    volumeContainer.style.alignItems = 'center';
    volumeContainer.style.justifyContent = 'space-between';
    
    const volumeLabel = document.createElement('label');
    volumeLabel.textContent = '音量';
    volumeLabel.htmlFor = 'voiceVolumeControl';
    volumeContainer.appendChild(volumeLabel);
    
    const volumeControl = document.createElement('input');
    volumeControl.type = 'range';
    volumeControl.id = 'voiceVolumeControl';
    volumeControl.min = '0';
    volumeControl.max = '1';
    volumeControl.step = '0.1';
    volumeControl.value = '1';
    volumeControl.style.width = '100px';
    volumeContainer.appendChild(volumeControl);
    
    const volumeValue = document.createElement('span');
    volumeValue.id = 'voiceVolumeValue';
    volumeValue.textContent = '1.0';
    volumeValue.style.minWidth = '30px';
    volumeContainer.appendChild(volumeValue);
    
    globalParamsContainer.appendChild(volumeContainer);
    
    controlPanel.appendChild(globalParamsContainer);
    
    // 测试按钮
    const testButton = document.createElement('button');
    testButton.textContent = '测试语音';
    testButton.onclick = testVoice;
    controlPanel.appendChild(testButton);
    
    // 添加到文档中
    document.body.appendChild(controlPanel);
    
    // 添加事件监听器
    enableSwitch.addEventListener('change', function() {
        if (tts) {
            tts.enable(this.checked);
            console.log(`语音合成已${this.checked ? '启用' : '禁用'}`);
        }
    });
    
    rateControl.addEventListener('input', function() {
        rateValue.textContent = this.value;
    });
    
    pitchControl.addEventListener('input', function() {
        pitchValue.textContent = this.value;
    });
    
    volumeControl.addEventListener('input', function() {
        volumeValue.textContent = this.value;
    });
}

// 测试语音功能
function testVoice() {
    // 添加更详细的调试信息
    console.log('测试语音功能调用');
    console.log('tts 对象:', tts);
    
    // 直接检查window.speechSynthesis
    if (!('speechSynthesis' in window)) {
        console.error('window.speechSynthesis 不存在');
        alert('您的浏览器不支持Web Speech API，无法使用语音合成功能');
        return;
    }
    
    console.log('window.speechSynthesis 存在:', window.speechSynthesis);
    
    if (!tts) {
        console.error('tts 实例未加载');
        alert('语音合成模块未加载成功，请刷新页面重试');
        return;
    }
    
    const status = tts.getStatus();
    console.log('语音合成状态:', status);
    
    if (!status.supported) {
        console.error('tts.getStatus().supported 返回 false');
        alert('语音合成功能不被支持，请刷新页面重试或使用其他浏览器');
        return;
    }
    
    const rate = parseFloat(document.getElementById('voiceRateControl')?.value || '1');
    const pitch = parseFloat(document.getElementById('voicePitchControl')?.value || '1');
    const volume = parseFloat(document.getElementById('voiceVolumeControl')?.value || '1');
    
    // 保存当前语音配置
    const currentVoiceSettings = tts.getStatus();
    
    // 临时配置测试语音
    tts.configureVoice('测试语音', null, pitch, rate, volume);
    
    // 播放测试文本
    tts.speak('这是一段测试语音，您可以通过上方的滑块调整语速、音调和音量。', '测试语音');
    
    // 添加测试消息到聊天区域
    addChatMessage('测试语音', '这是一段测试语音，您可以通过上方的滑块调整语速、音调和音量。', 'system');
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
window.testVoice = testVoice;