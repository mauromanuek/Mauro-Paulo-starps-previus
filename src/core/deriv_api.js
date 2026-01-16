const DerivAPI = {
    socket: null,
    isAuthorized: false,
    callbacks: {},
    activeContracts: {}, // Mapeia contract_id -> prefixo do módulo ('m', 'a', 'd')
    currentSymbol: "R_100", 
    candleSubscriptionId: null,

    connect(token, callback) {
        if (this.socket) this.socket.close();
        
        this.socket = new WebSocket('wss://ws.derivws.com/websockets/v3?app_id=1089');

        this.socket.onopen = () => {
            this.socket.send(JSON.stringify({ authorize: token }));
        };

        this.socket.onmessage = (msg) => {
            const data = JSON.parse(msg.data);
            
            // Tratamento de Erro Global (Problema 2)
            if (data.error) {
                if (callback) callback(data);
                return;
            }

            if (data.msg_type === 'authorize') {
                this.isAuthorized = true;
                this.socket.send(JSON.stringify({ balance: 1, subscribe: 1 }));
                // Inscrição para monitoramento geral de eventos da conta
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

    // Troca o ativo e limpa inscrições anteriores (Problema 3)
    changeSymbol(newSymbol) {
        if (this.currentSymbol === newSymbol) return;
        
        // Cancela inscrição de velas anterior se existir
        if (this.candleSubscriptionId) {
            this.socket.send(JSON.stringify({ forget: this.candleSubscriptionId }));
            this.candleSubscriptionId = null;
        }
        
        this.currentSymbol = newSymbol;
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
            granularity: 60,
            style: "candles",
            subscribe: 1
        }));
    },

    buy(type, stake, prefix, callback, extraParams = {}) {
        if (!this.isAuthorized) return;

        this.callbacks['buy'] = callback;
        
        // Armazena temporariamente qual prefixo solicitou a compra
        this._pendingPrefix = prefix || 'm';

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
                symbol: this.currentSymbol,
                ...extraParams
            }
        };

        this.socket.send(JSON.stringify(request));
    },

    handleResponses(data) {
        // Captura o ID da inscrição de velas para poder cancelar depois
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
            // Vincula o contrato ao módulo de forma confiável (Problema 5)
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

            // Sincronia de Ativo via contrato (Problema 3)
            if (c.underlying && c.underlying !== this.currentSymbol) {
                this.currentSymbol = c.underlying;
                if (window.app && typeof app.onAssetChange === 'function') {
                    app.onAssetChange(c.underlying);
                }
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
