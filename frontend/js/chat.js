// 战报展示（只读，无人类输入）

let lastChatLogId = 0;

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

function createChatMessageElement(sender, message, type = 'system') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;

    const body = document.createElement('div');
    body.className = 'chat-message-body';
    body.innerHTML = `<span class="chat-sender">${escapeHtml(sender)}:</span> ${escapeHtml(stripMarkdownQuotes(message))}`;

    messageDiv.appendChild(body);
    return messageDiv;
}

export function addChatMessage(sender, message, type = 'system') {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = createChatMessageElement(sender, message, type);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

export function appendChatLogEntry(entry) {
    if (!entry || typeof entry.id !== 'number') return false;
    if (entry.id <= lastChatLogId) return false;

    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return false;

    const type = entry.type || 'system';
    const messageDiv = createChatMessageElement(entry.sender, entry.message, type);
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
