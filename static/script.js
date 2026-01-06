const API_URL = "http://127.0.0.1:8000";
let currentSessionId = null;

// Initial check for API
async function checkStatus() {
    const badge = document.getElementById('api-status');
    const dot = badge.querySelector('.dot');
    try {
        const resp = await fetch(`${API_URL}/health`);
        const data = await resp.json();
        badge.classList.add('status-online');
        badge.innerHTML = `<span class="dot"></span> מחובר ל-${data.provider}`;
    } catch (e) {
        badge.classList.remove('status-online');
        badge.innerHTML = `<span class="dot"></span> שגיאת חיבור`;
    }
}

function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));

    document.querySelector(`[onclick="switchTab('${tab}')"]`).classList.add('active');
    document.getElementById(`${tab}-section`).classList.add('active');
}

// Search Logic
async function performSearch() {
    const query = document.getElementById('search-input').value;
    if (!query) return;

    const loader = document.getElementById('search-loader');
    const resultsArea = document.getElementById('search-results');
    const btn = document.getElementById('search-btn');

    btn.disabled = true;
    loader.style.display = 'block';
    resultsArea.innerHTML = '';

    try {
        const resp = await fetch(`${API_URL}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, top_k: 5 })
        });
        const data = await resp.json();

        let sourcesHtml = data.sources.map(s => `
            <div class="source-card">
                <div class="source-header">מקור: ${s.doc_id} | עמוד: ${s.metadata.page}</div>
                <div>${s.text}</div>
            </div>
        `).join('');

        resultsArea.innerHTML = `
            <div class="answer-card glass">
                <div style="font-weight: 700; margin-bottom: 15px; color: var(--accent);">תשובה:</div>
                ${data.answer.replace(/\n/g, '<br>')}
            </div>
            <div style="margin-top: 20px; font-weight: 600; color: var(--text-muted);">מקורות ששימשו למציאת התשובה:</div>
            ${sourcesHtml}
        `;
    } catch (e) {
        resultsArea.innerHTML = `<div class="message system" style="color: var(--error)">שגיאה: ${e.message}</div>`;
    } finally {
        btn.disabled = false;
        loader.style.display = 'none';
    }
}

// Chat Logic
async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value;
    if (!text) return;

    appendMessage('user', text);
    input.value = '';

    const chatBtn = document.getElementById('chat-btn');
    chatBtn.disabled = true;

    try {
        const resp = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                session_id: currentSessionId,
                top_k: 5
            })
        });
        const data = await resp.json();
        currentSessionId = data.session_id;

        appendMessage('assistant', data.answer);
    } catch (e) {
        appendMessage('system', `שגיאה: ${e.message}`);
    } finally {
        chatBtn.disabled = false;
    }
}

function appendMessage(role, text) {
    const container = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    msgDiv.innerHTML = text.replace(/\n/g, '<br>');
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

function handleChatKey(e) {
    if (e.key === 'Enter') sendChatMessage();
}

checkStatus();
setInterval(checkStatus, 10000);
