// /static/main.js

const BOT_STATUS_TEXT = document.getElementById('bot-status-text');
const LOG_AREA = document.getElementById('log-area');
const START_BTN = document.getElementById('start-bot-btn');
const STOP_BTN = document.getElementById('stop-bot-btn');
const SYMBOL_SELECT = document.getElementById('symbol-select');
const MODE_SELECT = document.getElementById('mode-select');

// Sinalização
const HEADER_BOX = document.getElementById('signal-header-box');
const MAIN_DIRECTION_TEXT = document.getElementById('main-direction-text');
const CONFIDENCE_TEXT = document.getElementById('confidence-text');
const STRATEGY_TEXT = document.getElementById('strategy-text');
const INDICATOR_TEXT = document.getElementById('indicator-status-text');
const JUSTIFICATION_BOX = document.getElementById('justification-box');
const JUSTIFICATION_TEXT = document.getElementById('justification-text');
const ENTRY_TIME = document.getElementById('signal-entry-time');
const EXIT_TIME = document.getElementById('signal-exit-time');

// Login
const LOGIN_SCREEN = document.getElementById('login-screen');
const MAIN_APP_CONTENT = document.getElementById('main-app-content');
const API_TOKEN_INPUT = document.getElementById('api-token-input');
const SAVE_TOKEN_BTN = document.getElementById('save-token-btn');
const TOKEN_STATUS = document.getElementById('token-status');

let statusInterval;

// --- FUNÇÕES DE LOGIN E AUTENTICAÇÃO ---

function checkTokenAndDisplay() {
    // Carrega o token salvo do armazenamento local
    const tokenStored = localStorage.getItem('deriv_api_token');
    if (tokenStored && tokenStored.length > 10) {
        // Se houver token, mostra a aplicação principal
        LOGIN_SCREEN.style.display = 'none';
        MAIN_APP_CONTENT.style.display = 'block';
        TOKEN_STATUS.textContent = 'Token API Carregado!';
        TOKEN_STATUS.style.color = '#00bf00'; 
        API_TOKEN_INPUT.value = tokenStored; // Preenche o campo
        checkBotStatusAndLogs();
    } else {
        // Mostra a tela de login
        LOGIN_SCREEN.style.display = 'flex';
        MAIN_APP_CONTENT.style.display = 'none';
        TOKEN_STATUS.textContent = 'Aguardando Token...';
        TOKEN_STATUS.style.color = 'orange';
    }
}

SAVE_TOKEN_BTN.onclick = () => {
    const token = API_TOKEN_INPUT.value.trim();
    if (token.length > 10) {
        localStorage.setItem('deriv_api_token', token);
        checkTokenAndDisplay();
    } else {
        alert('Por favor, insira um token API válido.');
    }
};

// --- FUNÇÕES DE CONTROLO DO BOT ---

async function controlBot(action) {
    const apiToken = API_TOKEN_INPUT.value; 
    
    if (action === 'start' && !apiToken) {
        alert('O Token API é obrigatório para iniciar a conexão.');
        return;
    }
    
    const symbol = SYMBOL_SELECT.value;
    const mode = MODE_SELECT.value;
    
    try {
        const response = await fetch('/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                action, 
                symbol, 
                mode, 
                api_token: apiToken // O token é enviado ao backend
            }) 
        });
        const result = await response.json();
        
        if (!response.ok) {
            alert(`Erro: ${result.message}`);
        }
    } catch (error) {
        alert('Erro de conexão com o servidor.');
    }
}

START_BTN.onclick = () => controlBot('start');
STOP_BTN.onclick = () => controlBot('stop');

// --- FUNÇÃO DE RENDERIZAÇÃO DE SINAL ---

function renderFinalSignal(signalData) {
    const direction = signalData.direction;

    // Estado NEUTRO/AGUARDANDO/OFF
    if (direction === 'NEUTRA' || direction === 'AGUARDANDO' || direction === 'OFF') {
        const color = direction === 'OFF' ? '#4a4a4a' : 'gray';
        MAIN_DIRECTION_TEXT.textContent = `Robot Analista: ${direction}`;
        HEADER_BOX.style.backgroundColor = color;
        HEADER_BOX.classList.remove('call', 'put');
        JUSTIFICATION_BOX.classList.remove('call', 'put');
        JUSTIFICATION_BOX.style.borderTopColor = color;
        
        CONFIDENCE_TEXT.innerHTML = '';
        STRATEGY_TEXT.textContent = signalData.strategy_used;
        INDICATOR_TEXT.textContent = signalData.indicator_status;
        JUSTIFICATION_TEXT.textContent = signalData.justification;
        ENTRY_TIME.textContent = '--:--:--';
        EXIT_TIME.textContent = '--:--:--';
        return;
    }

    // Estado CALL / PUT
    const isCall = direction === 'CALL';
    const color = isCall ? '#00bf00' : '#ff3333';
    
    MAIN_DIRECTION_TEXT.textContent = `SINAL: ${direction.toUpperCase()} (${isCall ? 'COMPRA' : 'VENDA'})`;
    
    // Atualização das Cores e Classes
    HEADER_BOX.classList.toggle('call', isCall);
    HEADER_BOX.classList.toggle('put', !isCall);
    JUSTIFICATION_BOX.classList.toggle('call', isCall);
    JUSTIFICATION_BOX.classList.toggle('put', !isCall);
    JUSTIFICATION_BOX.style.borderTopColor = color;
    
    // Atualização dos Detalhes
    CONFIDENCE_TEXT.innerHTML = `<span style="color: ${color};">${signalData.confidence}%</span>`;
    STRATEGY_TEXT.textContent = signalData.strategy_used;
    INDICATOR_TEXT.textContent = signalData.indicator_status;
    JUSTIFICATION_TEXT.textContent = signalData.justification;

    // Atualização dos Tempos
    ENTRY_TIME.textContent = signalData.entry_time;
    EXIT_TIME.textContent = signalData.exit_time;
}

// --- CHECK DE STATUS PRINCIPAL ---

async function checkBotStatusAndLogs() {
    try {
        const response = await fetch('/status');
        const data = await response.json();
        
        // 1. Atualiza Status
        const status = data.status;
        BOT_STATUS_TEXT.textContent = status;
        START_BTN.disabled = (status === 'ON');
        STOP_BTN.disabled = (status === 'OFF');
        
        // 2. Atualiza Logs (Rolagem automática)
        const logsHtml = data.logs.join('\n');
        const shouldScroll = LOG_AREA.scrollTop + LOG_AREA.clientHeight === LOG_AREA.scrollHeight;
        LOG_AREA.textContent = logsHtml;
        if (shouldScroll || data.logs.length === 1) {
            LOG_AREA.scrollTop = LOG_AREA.scrollHeight;
        }

        // 3. Renderiza o Sinal
        renderFinalSignal(data.signal_data);

    } catch (error) {
        // Ocorre se o Render estiver a dormir ou a iniciar
        BOT_STATUS_TEXT.textContent = 'ERRO DE CONEXÃO / SERVIDOR OFFLINE';
        console.error('Erro ao buscar status:', error);
    }
}

// Inicia a verificação de status a cada 1 segundo
window.onload = () => {
    checkTokenAndDisplay();
    // Inicia a verificação de status independentemente de o token estar salvo
    statusInterval = setInterval(checkBotStatusAndLogs, 1000);
};

window.onbeforeunload = () => {
    clearInterval(statusInterval);
};
