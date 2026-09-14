// SkillPilot - Simplified Working Version
let currentAI = 'openai';
let apiKeys = {};
let aiMemories = {};
let attachedFiles = [];
let isImageMode = false;

// AI model configurations
const aiModels = {
    openai: { name: 'OpenAI GPT', desc: 'Advanced language model', icon: 'fas fa-robot', color: '#10a37f' },
    claude: { name: 'Claude', desc: 'Helpful AI assistant', icon: 'fas fa-brain', color: '#cc785c' },
    gemini: { name: 'Gemini', desc: 'Google multimodal AI', icon: 'fas fa-gem', color: '#4285f4' },
    grok: { name: 'Grok', desc: 'X.AI reasoning model', icon: 'fab fa-twitter', color: '#1da1f2' },
    deepseek: { name: 'DeepSeek', desc: 'Advanced reasoning AI', icon: 'fas fa-search', color: '#6366f1' },
    llama: { name: 'Llama', desc: 'Meta open model', icon: 'fas fa-fire', color: '#ff6b6b' },
    perplexity: { name: 'Perplexity', desc: 'Search-powered AI', icon: 'fas fa-search-plus', color: '#20bcc7' },
    dalle: { name: 'DALL-E', desc: 'Image generation', icon: 'fas fa-palette', color: '#10a37f' },
    clarifai: { name: 'Clarifai', desc: 'Computer vision', icon: 'fas fa-eye', color: '#3b82f6' },
    census: { name: 'Census', desc: 'Data insights', icon: 'fas fa-chart-line', color: '#8b5cf6' }
};

// Initialize memories
Object.keys(aiModels).forEach(ai => {
    aiMemories[ai] = [];
});

// DOM Elements
let chatInput, sendBtn, chatMessages, sidebar, collapseIcon;

// Initialize app
function init() {
    console.log('Initializing SkillPilot...');

    // Get DOM elements
    chatInput = document.getElementById('chatInput');
    sendBtn = document.getElementById('sendBtn');
    chatMessages = document.getElementById('chatMessages');
    sidebar = document.getElementById('sidebar');
    collapseIcon = document.getElementById('collapseIcon');

    if (!chatInput || !sendBtn || !chatMessages) {
        console.error('Required DOM elements not found');
        return;
    }

    loadData();
    setupEventListeners();
    loadChatHistory();

    console.log('SkillPilot initialized successfully');
}

// Load saved data
function loadData() {
    try {
        const savedKeys = localStorage.getItem('aiacmate_api_keys');
        if (savedKeys) {
            apiKeys = JSON.parse(savedKeys);
        }

        const savedMemories = localStorage.getItem('aiacmate_memories');
        if (savedMemories) {
            aiMemories = JSON.parse(savedMemories);
        }
    } catch (e) {
        console.error('Error loading data:', e);
    }
}

// Save data
function saveData() {
    try {
        localStorage.setItem('aiacmate_api_keys', JSON.stringify(apiKeys));
        localStorage.setItem('aiacmate_memories', JSON.stringify(aiMemories));
    } catch (e) {
        console.error('Error saving data:', e);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Send button
    sendBtn.addEventListener('click', handleSendClick);

    // Enter key
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendClick();
        }
    });

    // Auto-resize textarea
    chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });

    // AI tool selection
    document.querySelectorAll('.ai-tool').forEach(tool => {
        tool.addEventListener('click', () => selectAI(tool));
    });

    // File upload
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileUpload);
    }

    console.log('Event listeners setup complete');
}

// Handle send click
function handleSendClick() {
    const message = chatInput.value.trim();
    if (!message && attachedFiles.length === 0) return;

    console.log('Sending message:', message);

    // Add user message to chat
    addMessageToDOM('user', message, new Date().toISOString());

    // Add to memory
    aiMemories[currentAI].push({
        type: 'user',
        content: message,
        time: new Date().toISOString()
    });

    // Clear input
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Send to AI
    sendToAI(message);

    // Clear files
    attachedFiles = [];
    const attachedFilesContainer = document.getElementById('attachedFiles');
    if (attachedFilesContainer) {
        attachedFilesContainer.innerHTML = '';
    }

    saveData();
}

// Send to AI
async function sendToAI(message) {
    // Show loading
    const loadingDiv = addMessageToDOM('ai', 'Thinking...', new Date().toISOString());

    try {
        const formData = new FormData();
        formData.append('message', message);
        formData.append('api_key', apiKeys[currentAI] || '');

        // Add files
        attachedFiles.forEach(file => {
            formData.append('files', file);
        });

        const response = await fetch(`/api/chat/${currentAI}`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        // Remove loading
        loadingDiv.remove();

        let responseText = data.error ? `Error: ${data.error}` : data.text || 'No response';

        // Add AI response
        addMessageToDOM('ai', responseText, new Date().toISOString(), data.image_url);

        // Add to memory
        aiMemories[currentAI].push({
            type: 'ai',
            content: responseText,
            time: new Date().toISOString(),
            image: data.image_url
        });

    } catch (error) {
        loadingDiv.remove();
        console.error('Error:', error);
        addMessageToDOM('ai', `Connection error: ${error.message}`, new Date().toISOString());
    }

    saveData();
}

// Add message to DOM
function addMessageToDOM(type, content, time, imageUrl = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;

    let html = '';

    if (type !== 'system') {
        html += `
            <div class="message-meta">
                <div class="${type}-avatar">${type === 'user' ? 'U' : 'AI'}</div>
                <span>${type === 'user' ? 'You' : aiModels[currentAI]?.name || 'AI'}</span>
                <span>${new Date(time).toLocaleTimeString()}</span>
            </div>
        `;
    }

    html += `<div class="message-content">`;

    if (imageUrl) {
        html += `<img src="${imageUrl}" style="max-width: 100%; border-radius: 8px; margin: 8px 0;">`;
    }

    html += content;
    html += `</div>`;

    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageDiv;
}

// Select AI
function selectAI(toolElement) {
    document.querySelectorAll('.ai-tool').forEach(tool => {
        tool.classList.remove('active');
    });

    toolElement.classList.add('active');
    currentAI = toolElement.dataset.ai;

    const model = aiModels[currentAI];
    const nameEl = document.getElementById('currentAiName');
    const descEl = document.getElementById('currentAiDesc');

    if (nameEl) nameEl.textContent = model.name;
    if (descEl) descEl.textContent = model.desc;

    const iconEl = document.querySelector('.current-ai-icon i');
    const iconContainer = document.querySelector('.current-ai-icon');
    if (iconEl) iconEl.className = model.icon;
    if (iconContainer) iconContainer.style.background = model.color;

    loadChatHistory();
}

// Load chat history
function loadChatHistory() {
    chatMessages.innerHTML = '';

    addMessageToDOM('system', `Chatting with ${aiModels[currentAI].name}. ${aiMemories[currentAI].length > 0 ? 'Previous conversation loaded.' : 'Start a new conversation!'}`, new Date().toISOString());

    aiMemories[currentAI].forEach(msg => {
        addMessageToDOM(msg.type, msg.content, msg.time, msg.image);
    });
}

// Toggle sidebar
function toggleSidebar() {
    if (!sidebar || !collapseIcon) return;

    sidebar.classList.toggle('collapsed');

    if (sidebar.classList.contains('collapsed')) {
        collapseIcon.className = 'fas fa-chevron-right';
    } else {
        collapseIcon.className = 'fas fa-chevron-left';
    }
}

// Settings functions
function openSettings() {
    const modal = document.getElementById('settingsModal');
    if (modal) modal.style.display = 'flex';
}

function closeSettings() {
    const modal = document.getElementById('settingsModal');
    if (modal) modal.style.display = 'none';
}

function saveSettings() {
    const keyInputs = ['openai', 'claude', 'gemini', 'grok', 'deepseek', 'llama', 'perplexity', 'clarifai', 'census'];

    keyInputs.forEach(key => {
        const input = document.getElementById(key + 'Key');
        if (input && input.value.trim()) {
            apiKeys[key] = input.value.trim();
        }
    });

    saveData();
    closeSettings();
    addMessageToDOM('system', 'API settings saved!', new Date().toISOString());
}

// File handling
function selectFiles() {
    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.click();
}

function handleFileUpload(event) {
    const files = Array.from(event.target.files);
    attachedFiles.push(...files);

    // Show attached files
    const container = document.getElementById('attachedFiles');
    if (container) {
        container.innerHTML = '';
        attachedFiles.forEach(file => {
            const fileDiv = document.createElement('div');
            fileDiv.className = 'attached-file';
            fileDiv.innerHTML = `
                <i class="fas fa-file"></i>
                <span>${file.name}</span>
                <button onclick="removeFile('${file.name}')"><i class="fas fa-times"></i></button>
            `;
            container.appendChild(fileDiv);
        });
    }
}

function removeFile(fileName) {
    attachedFiles = attachedFiles.filter(file => file.name !== fileName);
    handleFileUpload({ target: { files: attachedFiles } });
}

function toggleFileUpload() {
    const area = document.getElementById('fileUploadArea');
    if (area) {
        area.classList.toggle('show');
    }
}

function toggleImageMode() {
    isImageMode = !isImageMode;
    const btn = document.getElementById('imageBtn');
    if (btn) {
        btn.classList.toggle('active', isImageMode);
    }

    if (chatInput) {
        chatInput.placeholder = isImageMode ? 'Describe the image you want...' : 'Message SkillPilot...';
    }
}

function clearMemory() {
    if (confirm(`Clear chat with ${aiModels[currentAI].name}?`)) {
        aiMemories[currentAI] = [];
        saveData();
        loadChatHistory();
    }
}

// Initialize when DOM loads
document.addEventListener('DOMContentLoaded', init);

// Global functions for HTML onclick events
window.toggleSidebar = toggleSidebar;
window.openSettings = openSettings;
window.closeSettings = closeSettings;
window.saveSettings = saveSettings;
window.clearMemory = clearMemory;
window.selectFiles = selectFiles;
window.toggleFileUpload = toggleFileUpload;
window.toggleImageMode = toggleImageMode;
window.removeFile = removeFile;
