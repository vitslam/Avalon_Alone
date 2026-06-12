// 桌面显示和玩家卡片
import state from './state.js';
import { stripMarkdownQuotes } from './chat.js';
import { isMobileLayout, onLayoutChange, fitTableScale } from './layout.js';
import { applyPlayerColorToElement, getPlayerSeatIndex } from './playerColors.js';

onLayoutChange(() => {
    if (state.gameState?.players?.length) {
        updatePlayersDisplay();
    }
});

window.addEventListener('table-layout-fitted', () => {
    refreshActiveSpeechBubble();
});

let speechBubbleLayer = 10;

const PROPOSED_TEAM_PHASES = new Set(['选择队伍', '队伍投票', 'team_selection', 'team_vote']);
const MISSION_VOTE_PHASES = new Set(['任务投票', 'mission_vote']);

export function isProposedTeamPhase(phase) {
    return PROPOSED_TEAM_PHASES.has(phase);
}

export function isMissionVotePhase(phase) {
    return MISSION_VOTE_PHASES.has(phase);
}

export function sortTeamNames(names) {
    return [...names].sort((a, b) => {
        const na = parseInt(a, 10);
        const nb = parseInt(b, 10);
        if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
        return String(a).localeCompare(String(b));
    });
}

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

    const tableCenter = createTableCenter();

    const { top: topCount, right: rightCount, bottom: bottomCount, left: leftCount } =
        getSeatLayout(totalPlayers);

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
    // 下侧、左侧逆序排列（顺时针绕桌：底行从右到左，左列从下到上）
    bottomPlayers.reverse().forEach(p => bottomRow.appendChild(createPlayerCard(p)));
    const leftPlayers = [];
    for (let i = 0; i < leftCount && playerIndex < totalPlayers; i++, playerIndex++) {
        leftPlayers.push(state.gameState.players[playerIndex]);
    }
    leftPlayers.reverse().forEach(p => leftCol.appendChild(createPlayerCard(p)));

    playersContainer.appendChild(topRow);
    playersContainer.appendChild(leftCol);
    playersContainer.appendChild(tableCenter);
    playersContainer.appendChild(rightCol);
    playersContainer.appendChild(bottomRow);

    requestAnimationFrame(() => {
        fitTableScale();
        refreshActiveSpeechBubble();
    });
}

function refreshActiveSpeechBubble() {
    const overlay = document.getElementById('speechBubbleOverlay');
    const bubble = overlay?.querySelector('.speech-bubble');
    if (!bubble) return;

    const speaker = bubble.dataset.speaker;
    if (!speaker) return;

    const speakerCard = document.querySelector(`.player-card[data-player-name="${speaker}"]`);
    if (!speakerCard) return;

    speakerCard.classList.add('speech-active');
    positionSpeechBubble(bubble, speakerCard);
}

function getMobileSeatLayout(totalPlayers) {
    // 尽量少占上下行，把玩家分到左右两侧，降低纵向高度
    const layouts = {
        5: { top: 1, right: 2, bottom: 1, left: 1 },
        6: { top: 1, right: 2, bottom: 1, left: 2 },
        7: { top: 1, right: 3, bottom: 1, left: 2 },
        8: { top: 1, right: 3, bottom: 1, left: 3 },
        9: { top: 1, right: 4, bottom: 1, left: 3 },
        10: { top: 1, right: 4, bottom: 1, left: 4 },
    };
    return layouts[totalPlayers] || { top: 1, right: 2, bottom: 1, left: 1 };
}

function getSeatLayout(totalPlayers) {
    if (isMobileLayout()) {
        return getMobileSeatLayout(totalPlayers);
    }

    const overrides = {
        9: { top: 3, right: 1, bottom: 4, left: 1 },
        10: { top: 4, right: 1, bottom: 4, left: 1 },
    };
    if (overrides[totalPlayers]) {
        return overrides[totalPlayers];
    }

    // 默认：上、右、下、左（顺时针）
    let top = Math.ceil(totalPlayers / 3);
    let bottom = Math.ceil((totalPlayers - top) / 2);
    let side = totalPlayers - top - bottom;
    let right = Math.ceil(side / 2);
    let left = side - right;

    if (totalPlayers >= 5 && left === 0) {
        left = 1;
        bottom -= 1;
    }
    if (totalPlayers >= 5 && right === 0) {
        right = 1;
        bottom -= 1;
    }

    return { top, right, bottom, left };
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
    const phase = state.gameState.phase;
    const onTeam = state.gameState.current_team?.includes(player.name);
    if (onTeam && isProposedTeamPhase(phase)) {
        playerCard.classList.add('on-proposed-team');
    }
    if (onTeam && isMissionVotePhase(phase)) {
        playerCard.classList.add('on-mission');
    }

    let playerVote = null;
    if (state.teamVoteDisplay?.phase === 'result' && state.teamVoteDisplay.votes) {
        playerVote = state.teamVoteDisplay.votes.find(v => v.player === player.name);
        if (playerVote) {
            playerCard.classList.add(playerVote.vote === 'approve' ? 'vote-approve' : 'vote-reject');
        }
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
    if (onTeam && isProposedTeamPhase(phase)) {
        statusParts.push('远征队');
    }
    if (onTeam && isMissionVotePhase(phase)) {
        statusParts.push('任务中');
    }

    const avatarText = player.name.slice(0, 2);
    const avatarClass = avatarText.length >= 2 ? 'player-avatar avatar-dual' : 'player-avatar';

    playerCard.innerHTML = `
        <div class="${avatarClass}">${avatarText}</div>
        <div class="player-role">${roleDisplay}</div>
        <div class="player-status">${statusParts.join(' • ')}</div>
    `;

    if (playerVote) {
        const voteBubble = document.createElement('div');
        voteBubble.className = 'vote-bubble';
        voteBubble.textContent = playerVote.vote === 'approve' ? '赞成' : '反对';
        playerCard.appendChild(voteBubble);
    }

    applyPlayerColorToElement(playerCard, getPlayerSeatIndex(player.name, state.gameState.players));

    return playerCard;
}

function createTableCenter() {
    const tableCenter = document.createElement('div');
    tableCenter.className = 'table-center';

    const tableInfo = document.createElement('div');
    tableInfo.className = 'table-info';
    if (state.gameState?.current_mission) {
        tableInfo.textContent = `第${state.gameState.current_mission}轮任务`;
    }
    tableCenter.appendChild(tableInfo);

    const overlay = document.createElement('div');
    overlay.className = 'table-vote-overlay';
    overlay.id = 'tableVoteOverlay';

    if (state.teamVoteDisplay) {
        if (state.teamVoteDisplay.phase === 'progress') {
            overlay.innerHTML = `
                <div class="table-vote-progress">投票中 ${state.teamVoteDisplay.votedCount}/${state.teamVoteDisplay.totalPlayers}</div>
            `;
        } else if (state.teamVoteDisplay.phase === 'result') {
            const { approveCount, rejectCount, hint } = state.teamVoteDisplay;
            overlay.innerHTML = `
                <div class="table-vote-result">
                    <div class="vote-counts">
                        <span class="vote-count-approve">赞成 ${approveCount}</span>
                        <span class="vote-count-sep">·</span>
                        <span class="vote-count-reject">反对 ${rejectCount}</span>
                    </div>
                    <div class="vote-hint">${hint || ''}</div>
                </div>
            `;
        }
    }

    tableCenter.appendChild(overlay);
    return tableCenter;
}

export function showTeamVoteProgress(votedCount, totalPlayers) {
    state.teamVoteDisplay = { phase: 'progress', votedCount, totalPlayers, votes: null };
    updatePlayersDisplay();
}

export function showTeamVoteResult(data) {
    state.teamVoteDisplay = {
        phase: 'result',
        votedCount: data.votes?.length || 0,
        totalPlayers: data.votes?.length || 0,
        votes: data.votes || [],
        approveCount: data.approve_count || 0,
        rejectCount: data.reject_count || 0,
        hint: data.hint || '',
    };
    updatePlayersDisplay();
}

export function clearTeamVoteDisplay() {
    state.teamVoteDisplay = null;
    updatePlayersDisplay();
}

export function updateCurrentSpeaker(speaker) {
    document.querySelectorAll('.player-card').forEach(card => {
        card.classList.remove('speaking');
    });

    if (speaker && state.gameState && state.gameState.players) {
        const speakerCard = document.querySelector(`.player-card[data-player-name="${speaker}"]`);
        if (speakerCard) {
            speakerCard.classList.add('speaking');
        }
    }
}

export function showPlayerSpeaking(speaker, message) {
    const overlay = document.getElementById('speechBubbleOverlay');
    if (overlay) {
        overlay.querySelectorAll('.speech-bubble').forEach((b) => b.remove());
    }
    document.querySelectorAll('.player-card.speech-active').forEach((card) => {
        card.classList.remove('speech-active');
        card.style.zIndex = '';
    });

    if (!state.gameState || !state.gameState.players) return;

    const speakerCard = document.querySelector(`.player-card[data-player-name="${speaker}"]`);
    if (!speakerCard || !overlay) return;

    const speechBubble = document.createElement('div');
    speechBubble.className = 'speech-bubble';
    speechBubble.dataset.speaker = speaker;

    let bubbleText = stripMarkdownQuotes(message);
    if (isMobileLayout() && bubbleText.length > 150) {
        bubbleText = bubbleText.slice(0, 150) + '...';
    }
    speechBubble.textContent = bubbleText;
    applyPlayerColorToElement(speechBubble, getPlayerSeatIndex(speaker, state.gameState.players));

    speechBubbleLayer += 1;
    speechBubble.style.zIndex = String(1500 + speechBubbleLayer);
    speakerCard.classList.add('speech-active');
    speakerCard.style.zIndex = String(speechBubbleLayer);

    overlay.appendChild(speechBubble);
    positionSpeechBubble(speechBubble, speakerCard);
}

function positionSpeechBubble(bubble, speakerCard) {
    const cardRect = speakerCard.getBoundingClientRect();
    const bubbleRect = bubble.getBoundingClientRect();
    const margin = 10;
    const viewportPadding = 12;

    let anchorX = cardRect.left + cardRect.width / 2;
    let anchorY = cardRect.top - margin;

    // 上方空间不足时改显示在卡片下方
    if (anchorY - bubbleRect.height < viewportPadding) {
        anchorY = cardRect.bottom + margin;
        bubble.classList.add('speech-bubble--below');
        bubble.style.transform = 'translate(-50%, 0)';
    } else {
        bubble.classList.remove('speech-bubble--below');
        bubble.style.transform = 'translate(-50%, -100%)';
    }

    let left = anchorX;
    const halfWidth = bubbleRect.width / 2;
    left = Math.max(viewportPadding + halfWidth, Math.min(window.innerWidth - viewportPadding - halfWidth, left));

    bubble.style.left = `${left}px`;
    bubble.style.top = `${anchorY}px`;
}

export function showCurrentSpeakerIndicator(speaker) {
    // 手机版不显示右上角"正在发言"弹窗
    if (isMobileLayout()) return;

    const indicator = document.getElementById('currentSpeaker');
    const speakerNameElement = document.getElementById('speakerName');

    if (indicator && speakerNameElement) {
        speakerNameElement.textContent = speaker;
        indicator.classList.add('visible');
    }
}

/** 语音播完或无 TTS 时估算结束后，由 speechPresenter 调用以收起发言 UI */
export function hideSpeechPresentation(speaker) {
    document.querySelectorAll('.player-card').forEach(card => {
        card.classList.remove('speaking');
    });

    const overlay = document.getElementById('speechBubbleOverlay');
    if (overlay) {
        overlay.querySelectorAll('.speech-bubble').forEach((b) => b.remove());
    }
    document.querySelectorAll('.player-card.speech-active').forEach((card) => {
        card.classList.remove('speech-active');
        card.style.zIndex = '';
    });

    const indicator = document.getElementById('currentSpeaker');
    if (indicator) {
        indicator.classList.remove('visible');
    }
}
