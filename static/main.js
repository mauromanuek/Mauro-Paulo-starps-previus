document.addEventListener('DOMContentLoaded', () => {
    const tokenInputContainer = document.getElementById('token-input-container');
    const controlPanelContainer = document.getElementById('control-panel-container');
    const apiTokenInput = document.getElementById('api-token');
    const saveTokenButton = document.getElementById('save-token-btn');
    const startBotButton = document.getElementById('start-bot-btn');
    const stopBotButton = document.getElementById('stop-bot-btn');
    const assetSelect = document.getElementById('asset-select');
    const modeSelect = document.getElementById('mode-select');
    const statusText = document.getElementById('status-text');
    const directionText = document.getElementById('direction-text');
    const confidenceText = document.getElementById('confidence-text');
    const justificationText = document.getElementById('justification-text');
    const timingText = document.getElementById('timing-text');
    const logsList = document.getElementById('logs-list');
    const strategyText = document.getElementById('strategy-text');
    const indicatorStatusText = document.getElementById('indicator-status-text');

    // --- UTILS ---

    function showTokenInput() {
        tokenInputContainer.style.display = 'block';
        controlPanelContainer.style.display = 'none';
        // Limpar o campo para forçar a inserção
        apiTokenInput.value = '';
    }

    function showControlPanel(tokenValue) {
        tokenInputContainer.style.display = 'none';
        controlPanelContainer.style.display = 'block';
        // Definir o valor para que possa ser enviado para o backend
        apiTokenInput.value = tokenValue; 
    }
    
    // --- TOKEN HANDLER (MODIFICADO) ---
    
    // NUNCA SALVAR O TOKEN. Apenas lê o valor para usar na sessão.
    saveTokenButton.addEventListener('click', () => {
        const token = apiTokenInput.value.trim();
        if (token) {
            showControlPanel(token);
            // Começa a verificar o status do bot
            fetchStatus(); 
            // Atualiza o display dos inputs para disabled/enabled
            updateControls(false); 
        } else {
            alert("Por favor, insira um Token API válido.");
        }
    });

    // Ao carregar a página, sempre mostra o input do token
    showTokenInput(); 

    // --- API CALLS ---

    function controlBot(action) {
        // Enviar o token lido do campo (agora não salvo)
        const token = apiTokenInput.value; 
        const asset = assetSelect.value;
        const mode = modeSelect.value;

        fetch('/control', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: action,
                api_token: token,
                asset: asset,
                mode: mode
            }),
        })
        .then(response => response.json())
        .then(data => {
            console.log(data.message);
            // Se for iniciar e for sucesso, desativa os controles de seleção
            if (action === 'start' && data.status === 'success') {
                 updateControls(true);
            }
            // Se for parar, reativa os controles
            if (action === 'stop' && data.status === 'success') {
                updateControls(false);
            }
        })
        .catch(error => {
            console.error('Erro ao controlar o bot:', error);
            // Em caso de erro, reativa os controles para que o usuário possa tentar novamente
            updateControls(false);
        });
    }

    function fetchStatus() {
        fetch('/status')
            .then(response => response.json())
            .then(data => {
                // Atualizar o display com os dados mais recentes
                statusText.textContent = data.status;
                directionText.textContent = data.direction;
                confidenceText.textContent = `${data.confidence}%`;
                justificationText.textContent = data.justification;
                timingText.textContent = data.timing;
                strategyText.textContent = data.strategy || 'N/A';
                indicatorStatusText.textContent = data.indicators || 'N/A';

                // Cores de status
                statusText.className = getStatusClass(data.status);
                directionText.className = getDirectionClass(data.direction);
                
                // Atualizar logs
                logsList.innerHTML = '';
                if (data.logs && data.logs.length > 0) {
                    data.logs.forEach(log => {
                        const li = document.createElement('li');
                        li.textContent = log;
                        logsList.appendChild(li);
                    });
                }
                
                // Habilitar/desabilitar botões
                if (data.current_status === 'ON') {
                    startBotButton.disabled = true;
                    stopBotButton.disabled = false;
                } else {
                    startBotButton.disabled = false;
                    stopBotButton.disabled = true;
                }
            })
            .catch(error => {
                console.error('Erro ao buscar status:', error);
                statusText.textContent = 'ERRO DE CONEXÃO COM O SERVIDOR';
                statusText.className = 'status-error';
            });
    }

    // Função para atualização dos controles
    function updateControls(isBotRunning) {
        assetSelect.disabled = isBotRunning;
        modeSelect.disabled = isBotRunning;
    }

    // Função para atribuição de classes CSS
    function getStatusClass(status) {
        switch (status) {
            case 'SINAL ATIVO!':
                return 'status-active';
            case 'AGUARDANDO':
                return 'status-waiting';
            case 'INICIANDO':
            case 'PARANDO':
                return 'status-starting';
            case 'ERRO - PARADO':
                return 'status-error';
            default:
                return 'status-default';
        }
    }

    function getDirectionClass(direction) {
        switch (direction) {
            case 'CALL':
                return 'direction-call';
            case 'PUT':
                return 'direction-put';
            default:
                return 'direction-neutral';
        }
    }


    // --- EVENT LISTENERS ---

    startBotButton.addEventListener('click', () => {
        // Envia o token que foi lido no saveTokenButton
        controlBot('start');
    });

    stopBotButton.addEventListener('click', () => {
        controlBot('stop');
    });

    // Iniciar a busca de status a cada segundo
    setInterval(fetchStatus, 1000);
});
