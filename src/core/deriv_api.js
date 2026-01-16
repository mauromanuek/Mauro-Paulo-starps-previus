const DerivAPI = {
    socket: null,
    isAuthorized: false,
    callbacks: {},
    activeContracts: {}, // Mapeia contract_id -> prefixo do módulo ('m', 'a', 'd')
    currentSymbol: "R_100", 
    candleSubscriptionId: null,

    connect(token, callback) {
        if (this.socket) this.socket.close();
        
        // Mantendo o app_id original conforme solicitado
        this.socket = new WebSocket('wss://ws.derivws.com/websockets/v3?app_id=1089');

        this.socket.onopen = () => {
            this.socket.send(JSON.stringify({ authorize: token }));
        };

        this.socket.onmessage = (msg) => {
            const data = JSON.parse(msg.data);
            
            if (data.error) {
                // Tratamento de erro preservado
                if (callback) callback(data);
                return;
            }

            if (data.msg_type === 'authorize') {
                this.isAuthorized = true;
                this.socket.send(JSON.stringify({ balance: 1, subscribe: 1 }));
                this.socket.send(JSON.stringify({ 
                    proposal_open_contract: 1, 
                    subscribe: 1 
                }));
            }

            this.handleResponses(data);
            if (callback) callback(data);
        };

        this.socket.onerror = (err) => {
            if (callback) callback({ error: { message: "Erro de conexão com servidor" } });
        };
    },

    // Troca o ativo e garante limpeza de subscrições (Problema 2 e 6)
    changeSymbol(newSymbol) {
        // Removemos a trava de igualdade para permitir re-subscrição em caso de erro
        if (this.candleSubscriptionId) {
            this.socket.send(JSON.stringify({ forget: this.candleSubscriptionId }));
            this.candleSubscriptionId = null;
        }
        
        this.currentSymbol = newSymbol;
        
        // Limpa o histórico no analista antes de começar o novo ativo
        if (window.app && app.analista) {
            app.analista.historicoVelas = [];
        }

        this.subscribeCandles(this.callbacks['candles']);
    },

    subscribeCandles(callback) {
        if (!this.isAuthorized) return;
        this.callbacks['candles'] = callback;
        
        this.socket.send(JSON.stringify({
            ticks_history: this.currentSymbol,
            adjust_start_time: 1,
            count: 50,
            end: "latest",
            granularity: 60, // Mantido 1 minuto (M1)
            style: "candles",
            subscribe: 1
        }));
    },

    buy(type, stake, prefix, callback, extraParams = {}) {
        if (!this.isAuthorized) return;

        this.callbacks['buy'] = callback;
        this._pendingPrefix = prefix || 'm';

        // Ajuste cirúrgico: Permitir que o parâmetro duration venha de fora (extraParams)
        // Se não vier, mantém o padrão, mas prioriza consistência com M1
        const request = {
            buy: 1,
            price: parseFloat(stake),
            parameters: {
                amount: parseFloat(stake),
                basis: 'stake',
                contract_type: type,
                currency: 'USD',
                duration: extraParams.duration || 1,
                duration_unit: extraParams.duration_unit || 'm', // Mudado para 'm' (minutos) para alinhar com análise M1
                symbol: this.currentSymbol,
                ...extraParams
            }
        };

        this.socket.send(JSON.stringify(request));
    },

    handleResponses(data) {
        if (data.msg_type === 'candles' && data.subscription) {
            this.candleSubscriptionId = data.subscription.id;
        }

        if (data.msg_type === 'ohlc' || data.msg_type === 'candles') {
            if (this.callbacks['candles']) {
                const candlesData = data.candles ? data.candles : [data.ohlc];
                this.callbacks['candles'](candlesData);
            }
        }

        if (data.msg_type === 'balance') {
            const el = document.getElementById('acc-balance');
            if (el) el.innerText = `$ ${data.balance.balance.toFixed(2)}`;
        }

        if (data.msg_type === 'buy' && !data.error) {
            const contractId = data.buy.contract_id;
            this.activeContracts[contractId] = this._pendingPrefix;
            
            this.socket.send(JSON.stringify({
                proposal_open_contract: 1,
                contract_id: contractId,
                subscribe: 1
            }));
        }

        if (data.msg_type === 'proposal_open_contract') {
            const c = data.proposal_open_contract;
            if (!c) return;

            // Sincronia de Ativo (Problema 2 e 6)
            if (c.underlying && c.underlying !== this.currentSymbol) {
                // Apenas atualiza a variável, sem disparar onAssetChange para evitar loop infinito
                this.currentSymbol = c.underlying;
            }

            if (c.is_sold) {
                const prefix = this.activeContracts[c.contract_id] || 'm';
                const profit = parseFloat(c.profit);
                
                if (window.app && typeof app.updateModuleProfit === 'function') {
                    app.updateModuleProfit(profit, prefix);
                }

                delete this.activeContracts[c.contract_id];
                
                document.dispatchEvent(new CustomEvent('contract_finished', { 
                    detail: { prefix, profit, contract: c } 
                }));
            }
        }
    }
};
