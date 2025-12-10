// Arquivo: main.js

document.addEventListener('DOMContentLoaded', () => {
    const startButton = document.getElementById('start-bot');
    const stopButton = document.getElementById('stop-bot');
    const apiTokenInput = document.getElementById('api-token');
    const logsDiv = document.getElementById('logs');
    const statusDiv = document.getElementById('status-box');
    const signalDiv = document.getElementById('signal-box');
    const confidenceDiv = document.getElementById('confidence-box');

    // 1. Limpa o token ao carregar (Impede o salvamento)
    apiTokenInput.value = '';

    // Função principal para atualizar a interface
    const updateStatus = async () => {
        try {
            const response = await fetch('/status');
            const data = await response.json();

            // --- 1. Atualizar Status do Bot ---
            const botStatus = data.status;
            statusDiv.textContent = `STATUS: ${botStatus}`;
            
            if (botStatus === 'ON') {
                statusDiv.className = 'status-box running';
                startButton.disabled = true;
                stopButton.disabled = false;
                apiTokenInput.disabled = true; // Desabilita o campo enquanto está a correr
            } else if (botStatus === 'OFF') {
                statusDiv.className = 'status-box stopped';
                startButton.disabled = false;
                stopButton.disabled = true;
                apiTokenInput.disabled = false;
            } else {
                 statusDiv.className = 'status-box pending';
                 startButton.disabled = true;
                 stopButton.disabled = true;
            }

            // --- 2. Atualizar Logs ---
            logsDiv.innerHTML = data.logs.reverse().map(log => `<p>${log}</p>`).join('');

            // --- 3. Atualizar Sinal e Confiança ---
            const signalData = data.signal_data;
            const direction = signalData.direction;

            signalDiv.textContent = direction;
            confidenceDiv.textContent = `Confiança: ${signalData.confidence}%`;

            if (direction === 'CALL') {
                signalDiv.className = 'signal-box call';
            } else if (direction === 'PUT') {
                signalDiv.className = 'signal-box put';
            } else {
                signalDiv.className = 'signal-box neutral';
            }

            // Atualizar Detalhes
            document.getElementById('display-trend').textContent = signalData.trend;
            document.getElementById('display-strategy').textContent = signalData.strategy_used;
            document.getElementById('display-entry').textContent = signalData.entry_time;
            document.getElementById('display-exit').textContent = signalData.exit_time;
            document.getElementById('display-indicators').textContent = signalData.indicator_status;
            document.getElementById('display-justification').textContent = signalData.justification;

        } catch (error) {
            console.error('Erro ao buscar status:', error);
            statusDiv.textContent = 'STATUS: ERRO DE CONEXÃO';
            statusDiv.className = 'status-box error';
        }
    };

    // --- Controladores de Botões ---

    startButton.addEventListener('click', async () => {
        const apiToken = apiTokenInput.value.trim();
        const symbol = document.getElementById('asset-select').value;
        const mode = document.getElementById('mode-select').value;

        if (!apiToken) {
            alert("Por favor, insira o Token API.");
            return;
        }

        try {
            const response = await fetch('/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'start', api_token: apiToken, symbol: symbol, mode: mode })
            });

            const result = await response.json();
            if (result.status === 'ERROR') {
                alert(`Erro ao Iniciar: ${result.message}`);
            }

        } catch (error) {
            alert('Erro de rede ao comunicar com o servidor.');
        }
    });

    stopButton.addEventListener('click', async () => {
        try {
            await fetch('/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'stop' })
            });
        } catch (error) {
            alert('Erro de rede ao comunicar com o servidor.');
        }
    });

    // Atualiza o status a cada 1 segundo
    setInterval(updateStatus, 1000);
    // Chama a função uma vez no início para carregar o estado
    updateStatus(); 
});
