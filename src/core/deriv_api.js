const DerivAPI = {
    socket: null,
    isAuthorized: false,
    callbacks: {},
    activeContracts: {}, // Mapeia contract_id -> prefixo do módulo ('m', 'a', 'd')
    currentSymbol: "R_100", // Armazena o ativo atual para sincronia

    connect(token, callback) {
        // Mantendo a estrutura de conexão original
        this.socket = new WebSocket('wss://ws.derivws.com/websockets/v3?app_id=1089');

        this.socket.onopen = () => {
            this.socket.send(JSON.stringify({ authorize: token }));
        };

        this.socket.onmessage = (msg) => {
            const data = JSON.parse(msg.data);
            
            if (data.msg_type === 'authorize' && !data.error) {
                this.isAuthorized = true;
                // Inscrição de saldo obrigatória para o footer
                this.socket.send(JSON.stringify({ balance: 1, subscribe: 1 }));
                
                // NOVO: Subscreve para detectar quando o usuário troca de ativo na plataforma
                this.socket.send(JSON.stringify({ 
                    proposal_open_contract: 1, 
                    subscribe: 1 
                }));
            }

            // Encaminhamento para handlers internos
            this.handleResponses(data);
            
            if (callback) callback(data);
        };
    },

    // --- NOVA FUNÇÃO DE CONEXÃO COM O ANALISTA GERAL ---
    subscribeCandles(callback) {
        this.callbacks['candles'] = callback;
        // Agora usa o this.currentSymbol em vez de ficar fixo em R_100
        this.socket.send(JSON.stringify({
            ticks_history: this.currentSymbol,
            adjust_start_time: 1,
            count: 50,
            end: "latest",
            granularity: 60,
            style: "candles",
            subscribe: 1
        }));
    },

    // Inscrição específica para monitorar um contrato até o fim
    subscribeContract(contract_id, callback) {
        this.callbacks['contract_update'] = callback;
        this.socket.send(JSON.stringify({
            proposal_open_contract: 1,
            contract_id: contract_id,
            subscribe: 1
        }));
    },

    buy(type, stake, callback, extraParams = {}) {
        if (!this.isAuthorized) {
            console.error("API não autorizada.");
            return;
        }

        // Armazena o callback de compra
        this.callbacks['buy'] = callback;
        
        // Captura o prefixo do módulo que disparou a ordem
        const currentPrefix = window.currentModulePrefix || 'm';

        const request = {
            buy: 1,
            price: parseFloat(stake),
            parameters: {
                amount: parseFloat(stake),
                basis: 'stake',
                contract_type: type,
                currency: 'USD',
                duration: 1,
                duration_unit: 't',
                symbol: this.currentSymbol, // USANDO O ATIVO SINCRONIZADO EM TEMPO REAL
                ...extraParams
            }
        };

        this.socket.send(JSON.stringify(request));
    },

    handleResponses(data) {
        // --- HANDLER PARA DADOS DE VELAS (ANÁLISE GERAL) ---
        if (data.msg_type === 'ohlc' || data.msg_type === 'candles') {
            if (this.callbacks['candles']) {
                const candlesData = data.candles ? data.candles : [data.ohlc];
                this.callbacks['candles'](candlesData);
            }
        }

        // Atualização de Saldo no Header
        if (data.msg_type === 'balance') {
            const el = document.getElementById('acc-balance');
            if (el) el.innerText = `$ ${data.balance.balance.toFixed(2)}`;
        }

        // Resposta da Ordem de Compra
        if (data.msg_type === 'buy') {
            if (!data.error) {
                const contractId = data.buy.contract_id;
                const prefix = window.currentModulePrefix || 'm';
                
                this.activeContracts[contractId] = prefix;

                this.socket.send(JSON.stringify({
                    proposal_open_contract: 1,
                    contract_id: contractId,
                    subscribe: 1
                }));
            }
            
            if (this.callbacks['buy']) {
                this.callbacks['buy'](data);
            }
        }

        // Monitoramento de Contratos Abertos (Update em Tempo Real)
        if (data.msg_type === 'proposal_open_contract') {
            const c = data.proposal_open_contract;
            
            if (!c) return;

            // NOVO: SINCRONIA DE ATIVO (Se o ativo mudar na Deriv, o bot percebe aqui)
            if (c.underlying && c.underlying !== this.currentSymbol) {
                this.currentSymbol = c.underlying;
                if (window.app && typeof app.onAssetChange === 'function') {
                    app.onAssetChange(c.underlying);
                }
            }

            // Se o contrato acabou de ser vendido (Fechado)
            if (c.is_sold) {
                const prefix = this.activeContracts[c.contract_id] || window.currentModulePrefix || 'm';
                const profit = parseFloat(c.profit);
                
                if (window.app && typeof app.updateModuleProfit === 'function') {
                    app.updateModuleProfit(profit, prefix);
                }

                delete this.activeContracts[c.contract_id];
                
                const event = new CustomEvent('contract_finished', { 
                    detail: { 
                        prefix: prefix, 
                        profit: profit,
                        contract: c 
                    } 
                });
                document.dispatchEvent(event);
            }

            if (this.callbacks['contract_update']) {
                this.callbacks['contract_update'](c);
            }
        }

        // Tratamento de erros de autorização/socket
        if (data.error) {
            console.warn("DerivAPI Error:", data.error.message);
        }
    }
};
