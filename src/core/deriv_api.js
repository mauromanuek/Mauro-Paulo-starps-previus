const DerivAPI = {
    socket: null,
    isAuthorized: false,
    callbacks: {},
    activeContracts: {}, // Mapeia contract_id -> prefixo do módulo ('m', 'a', 'd')

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
            }

            // Encaminhamento para handlers internos
            this.handleResponses(data);
            
            if (callback) callback(data);
        };
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
                symbol: "R_100", // Volatilidade 100 padrão conforme index
                ...extraParams
            }
        };

        this.socket.send(JSON.stringify(request));
    },

    handleResponses(data) {
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
                
                // Mapeia o ID do contrato ao módulo correspondente
                this.activeContracts[contractId] = prefix;

                // INÍCIO DO CICLO: Subscreve para acompanhar o fechamento
                this.socket.send(JSON.stringify({
                    proposal_open_contract: 1,
                    contract_id: contractId,
                    subscribe: 1
                }));
            }
            
            // Executa o callback do módulo (Manual, Auto ou Digit)
            if (this.callbacks['buy']) {
                this.callbacks['buy'](data);
            }
        }

        // Monitoramento de Contratos Abertos (Update em Tempo Real)
        if (data.msg_type === 'proposal_open_contract') {
            const c = data.proposal_open_contract;
            
            if (!c) return;

            // Se o contrato acabou de ser vendido (Fechado)
            if (c.is_sold) {
                const prefix = this.activeContracts[c.contract_id] || window.currentModulePrefix || 'm';
                const profit = parseFloat(c.profit);
                
                // 1. Atualiza Lucro no App (Lógica do index.html)
                if (window.app && typeof app.updateModuleProfit === 'function') {
                    app.updateModuleProfit(profit, prefix);
                }

                // 2. Limpa o mapeamento para liberar memória
                delete this.activeContracts[c.contract_id];
                
                // 3. GATILHO DE CICLO DE VIDA: 
                // Dispara evento para que o módulo saiba que pode operar novamente
                const event = new CustomEvent('contract_finished', { 
                    detail: { 
                        prefix: prefix, 
                        profit: profit,
                        contract: c 
                    } 
                });
                document.dispatchEvent(event);
            }

            // Callback genérico de update se necessário
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
