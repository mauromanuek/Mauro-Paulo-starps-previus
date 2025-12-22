// Variáveis Globais
let confidence = 0;
const alertSound = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');

// 1. Cronómetro de Fecho de Vela (5 minutos)
function updateCandleTimer() {
    const now = new Date();
    const min = now.getUTCMinutes();
    const sec = now.getUTCSeconds();
    
    const remMin = 4 - (min % 5);
    const remSec = 59 - sec;
    
    const timerElement = document.getElementById('candle-countdown');
    if(timerElement) {
        timerElement.innerText = `${remMin.toString().padStart(2,'0')}:${remSec.toString().padStart(2,'0')}`;
    }

    // Tocar alerta sonoro nos últimos 2 segundos se houver sinal forte
    if (remMin === 0 && remSec <= 2 && confidence >= 85) {
        alertSound.play();
    }
}
setInterval(updateCandleTimer, 1000);

// 2. Função para Ligar/Desligar o Bot
async function controlBot(action) {
    const token = document.getElementById('api-token-input').value;
    const symbol = document.getElementById('symbol-select').value;
    
    const res = await fetch('/control', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: action, symbol: symbol, api_token: token})
    });
    const data = await res.json();
    document.getElementById('bot-status-text').innerText = data.status;
}

// 3. Atualização de Sinais e Logs
async function pollStatus() {
    try {
        const response = await fetch('/status');
        const data = await response.json();
        const sig = data.signal_data;
        confidence = sig.confidence;

        // Atualiza Logs
        const logArea = document.getElementById('log-area');
        logArea.textContent = data.logs.join('\n');
        logArea.scrollTop = logArea.scrollHeight;

        // Atualiza Interface de Sinal
        document.getElementById('main-direction-text').innerText = sig.direction;
        document.getElementById('confidence-text').innerText = sig.confidence + '%';
        document.getElementById('strategy-text').innerText = sig.strategy_used;
        document.getElementById('justification-text').innerText = sig.justification;
        document.getElementById('indicator-status-text').innerText = sig.indicator_status;
        document.getElementById('signal-entry-time').innerText = sig.entry_time;
        document.getElementById('signal-exit-time').innerText = sig.exit_time;

        // Cores Dinâmicas
        const headerBox = document.getElementById('signal-header-box');
        if (sig.direction === 'CALL') headerBox.style.backgroundColor = "#059669";
        else if (sig.direction === 'PUT') headerBox.style.backgroundColor = "#dc2626";
        else headerBox.style.backgroundColor = "#374151";

        // Efeito Sniper (Borda Dourada)
        const card = document.getElementById('signal-display-card');
        if (sig.confidence >= 98) {
            card.style.border = "8px solid #fbbf24";
            document.body.style.backgroundColor = "#1a1405";
        } else {
            card.style.border = "none";
            document.body.style.backgroundColor = "#121417";
        }

    } catch (e) { console.error("Erro na sincronização:", e); }
}
setInterval(pollStatus, 2000);
