const DerivAPI = {
    socket: null,
    isAuthorized: false,
    callbacks: {},
    activeContracts: {}, 
    currentSymbol: "R_100", 
    candleSubscriptionId: null,
    isSubscribing: false,

    connect(token, callback) {
        if (this.socket) this.socket.close();
        
        this.socket = new WebSocket('wss://ws.derivws.com/websockets/v3?app_id=1089');

        this.socket.onopen = () => {
            this.socket.send(JSON.stringify({ authorize: token }));
        };

        this.socket.onmessage = (msg) => {
            const data = JSON.parse(msg.data);
            
            if (data.error) {
                if (data.error.code === 'AlreadySubscribed') return; 
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

    changeSymbol(newSymbol) {
        if (this.currentSymbol === newSymbol && this.candleSubscriptionId) return;

        if (this.candleSubscriptionId) {
            this.socket.send(JSON.stringify({ forget: this.candleSubscriptionId }));
            this.candleSubscriptionId = null;
        }
        
        this.currentSymbol = newSymbol;
        
        // Limpeza profunda para evitar Problema 1 (Ativo Preso) e Problema 3 (Dados Imaturos)
        if (window.app && app.analista) {
            app.analista.limparHistorico();
        }

        this.subscribeCandles(this.callbacks['candles']);
    },

    subscribeCandles(callback) {
        if (!this.isAuthorized || this.isSubscribing) return;
        
        this.isSubscribing = true;
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

        setTimeout(() => { this.isSubscribing = false; }, 2000);
    },

    buy(type, stake, prefix, callback, extraParams = {}) {
        if (!this.isAuthorized) return;

        this.callbacks['buy'] = callback;
        this._pendingPrefix = prefix || 'm';

        const isFastAsset = this.currentSymbol.includes('1Z') || this.currentSymbol.includes('1HZ');
        
        const request = {
            buy: 1,
            price: parseFloat(stake),
            parameters: {
                amount: parseFloat(stake),
                basis: 'stake',
                contract_type: type,
                currency: 'USD',
                duration: isFastAsset ? 5 : 1,
                duration_unit: isFastAsset ? 't' : 'm', 
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

        // Priorização de histórico completo para evitar Problema 3 (Dados Imaturos)
        if (data.msg_type === 'candles') {
            if (this.callbacks['candles']) {
                this.callbacks['candles'](data.candles);
            }
        } 
        // Update de tick individual (OHLC)
        else if (data.msg_type === 'ohlc') {
            // Verifica se o tick pertence ao símbolo atual para evitar Problema 1
            if (data.ohlc.symbol === this.currentSymbol && this.callbacks['candles']) {
                this.callbacks['candles'](data.ohlc);
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

            // Removida a reatribuição automática de currentSymbol para resolver Problema 1 definitivamente

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
