// 战报展示（只读，无人类输入）
import state from './state.js';

let lastChatLogId = 0;

const ROLE_NAMES = {
    merlin: '梅林',
    percival: '派西维尔',
    loyal_servant: '忠臣',
    morgana: '莫甘娜',
    assassin: '刺客',
    oberon: '奥伯伦',
    mordred: '莫德雷德',
    minion: '爪牙',
};

const EVIL_ROLES = new Set(['morgana', 'assassin', 'oberon', 'mordred', 'minion']);

function escapeHtml(text) {
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

/** 去掉 Markdown 引用行首的 > / ＞ 前缀 */
export function stripMarkdownQuotes(text) {
    return String(text)
        .split('\n')
        .map(line => line.replace(/^\s*(?:>|＞)+\s?/, ''))
        .join('\n')
        .trim();
}

function formatTimestamp(iso) {
    if (!iso) return '';
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
    });
}

function resolveRoleName(entry) {
    if (entry.role_name) return entry.role_name;
    if (entry.role) return ROLE_NAMES[entry.role] || entry.role;
    return '';
}

function resolvePlayerMeta(entry) {
    const meta = {
        seat: entry.seat ?? null,
        role: entry.role ?? null,
        roleName: resolveRoleName(entry),
        isAi: entry.is_ai ?? null,
    };

    const players = state.gameState?.players;
    if (!players?.length || entry.sender === '系统') return meta;

    const index = players.findIndex((p) => p.name === entry.sender);
    if (index < 0) return meta;

    const player = players[index];
    if (meta.seat == null) meta.seat = index + 1;
    if (!meta.role && player.role) meta.role = player.role;
    if (!meta.roleName && player.role) meta.roleName = ROLE_NAMES[player.role] || player.role;
    if (meta.isAi == null && player.is_ai != null) meta.isAi = player.is_ai;

    return meta;
}

function buildMetaLine(entry) {
    const meta = document.createElement('div');
    meta.className = 'chat-message-meta';

    if (entry.type === 'system' || entry.sender === '系统') {
        meta.innerHTML = `
            <span class="chat-meta-sender">系统</span>
            ${entry.timestamp ? `<span class="chat-meta-time">${escapeHtml(formatTimestamp(entry.timestamp))}</span>` : ''}
        `;
        return meta;
    }

    const playerMeta = resolvePlayerMeta(entry);
    const parts = [];

    if (playerMeta.seat != null) {
        parts.push(`<span class="chat-meta-seat">#${escapeHtml(playerMeta.seat)}</span>`);
    }

    parts.push(`<span class="chat-meta-name">${escapeHtml(entry.sender)}</span>`);

    if (playerMeta.roleName) {
        const roleClass = playerMeta.role && EVIL_ROLES.has(playerMeta.role) ? 'role-evil' : 'role-good';
        parts.push(`<span class="chat-meta-role ${roleClass}">${escapeHtml(playerMeta.roleName)}</span>`);
    }

    if (playerMeta.isAi === true) {
        parts.push('<span class="chat-meta-tag">AI</span>');
    } else if (playerMeta.isAi === false) {
        parts.push('<span class="chat-meta-tag">玩家</span>');
    }

    if (entry.timestamp) {
        parts.push(`<span class="chat-meta-time">${escapeHtml(formatTimestamp(entry.timestamp))}</span>`);
    }

    meta.innerHTML = parts.join('');
    return meta;
}

function normalizeEntry(senderOrEntry, message, type) {
    if (senderOrEntry && typeof senderOrEntry === 'object') {
        return {
            sender: senderOrEntry.sender ?? '系统',
            message: senderOrEntry.message ?? '',
            type: senderOrEntry.type || 'system',
            timestamp: senderOrEntry.timestamp ?? null,
            role: senderOrEntry.role ?? null,
            role_name: senderOrEntry.role_name ?? null,
            seat: senderOrEntry.seat ?? null,
            is_ai: senderOrEntry.is_ai ?? null,
            id: senderOrEntry.id,
        };
    }

    return {
        sender: senderOrEntry,
        message,
        type: type || 'system',
        timestamp: new Date().toISOString(),
        role: null,
        role_name: null,
        seat: null,
        is_ai: null,
        id: undefined,
    };
}

function createChatMessageElement(senderOrEntry, message, type = 'system') {
    const entry = normalizeEntry(senderOrEntry, message, type);
    const messageDiv = document.createElement('div');
    const playerMeta = resolvePlayerMeta(entry);
    const isEvil = playerMeta.role && EVIL_ROLES.has(playerMeta.role);

    messageDiv.className = `chat-message ${entry.type}`;
    if (isEvil && entry.type !== 'system') {
        messageDiv.classList.add('role-evil-msg');
    }

    messageDiv.appendChild(buildMetaLine(entry));

    const body = document.createElement('div');
    body.className = 'chat-message-content';
    body.textContent = stripMarkdownQuotes(entry.message);

    messageDiv.appendChild(body);
    return messageDiv;
}

export function addChatMessage(sender, message, type = 'system') {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;

    const messageDiv = createChatMessageElement(sender, message, type);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

export function appendChatLogEntry(entry) {
    if (!entry || typeof entry.id !== 'number') return false;
    if (entry.id <= lastChatLogId) return false;

    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return false;

    const messageDiv = createChatMessageElement(entry);
    messageDiv.dataset.chatLogId = String(entry.id);
    chatMessages.appendChild(messageDiv);
    lastChatLogId = entry.id;
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return true;
}

export function renderChatLog(entries) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages || !entries?.length) return;

    chatMessages.innerHTML = '';
    lastChatLogId = 0;

    for (const entry of entries) {
        appendChatLogEntry(entry);
    }
}

export function resetChatLogState() {
    lastChatLogId = 0;
}
