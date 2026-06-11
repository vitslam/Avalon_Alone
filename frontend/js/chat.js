// 战报展示（只读，无人类输入）

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

export function addChatMessage(sender, message, type = 'system') {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;

    const body = document.createElement('div');
    body.className = 'chat-message-body';
    body.innerHTML = `<span class="chat-sender">${escapeHtml(sender)}:</span> ${escapeHtml(stripMarkdownQuotes(message))}`;

    messageDiv.appendChild(body);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}
