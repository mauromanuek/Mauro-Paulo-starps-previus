const DerivAPI = {
    socket: null,
    isAuthorized: false,
    callbacks: {},
    activeContracts: {}, 
    currentSymbol: "R_100", 
    candleSubscriptionId: null,
    isSubscribing: false, // Trava de segurança para evitar duplicidade (Problema resolvido)

    connect(token, callback) {
        if (this.socket) this.socket.close();
        
        // Conexão oficial via WebSocket
        this.socket = new WebSocket('wss://ws.derivws.com/websockets/v3?app_id=1089');

        this.socket.onopen = () => {
            this.socket.send(JSON.stringify({ authorize: token }));
        };

        this.socket.onmessage = (msg) => {
            const data = JSON.parse(msg.data);
            
            // Filtro para silenciar erros de subscrição duplicada no console/alertas
            if (data.error) {
                if (data.error.code === 'AlreadySubscribed') return; 
                if (callback) callback(data);
                return;
            }

            if (data.msg_type === 'authorize') {
                this.isAuthorized = true;
                // Inscrições de conta essenciais
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

    // Troca o ativo com limpeza profunda de cache (Problema 2 e 6 resolvidos)
    changeSymbol(newSymbol) {
        // Se já estivermos no ativo e inscritos, não faz nada para poupar banda
        if (this.currentSymbol === newSymbol && this.candleSubscriptionId) return;

        // Cancela a subscrição anterior antes de mudar
        if (this.candleSubscriptionId) {
            this.socket.send(JSON.stringify({ forget: this.candleSubscriptionId }));
            this.candleSubscriptionId = null;
        }
        
        this.currentSymbol = newSymbol;
        
        // Limpa o histórico de velas no analista para não poluir a análise da IA (Problema 3)
        if (window.app && app.analista) {
            app.analista.historicoVelas = [];
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
            granularity: 60, // M1 para análise técnica consistente
            style: "candles",
            subscribe: 1
        }));

        // Libera a trava após 2 segundos para permitir futuras trocas
        setTimeout(() => { this.isSubscribing = false; }, 2000);
    },

    buy(type, stake, prefix, callback, extraParams = {}) {
        if (!this.isAuthorized) return;

        this.callbacks['buy'] = callback;
        this._pendingPrefix = prefix || 'm';

        // LÓGICA DE DURAÇÃO INTELIGENTE (Problema da demora resolvido)
        // Detecta se é um ativo de 1 segundo (ex: Volatility 100 (1s) ou 15 (1s))
        const isFastAsset = this.currentSymbol.includes('1Z') || this.currentSymbol.includes('1HZ');
        
        const request = {
            buy: 1,
            price: parseFloat(stake),
            parameters: {
                amount: parseFloat(stake),
                basis: 'stake',
                contract_type: type,
                currency: 'USD',
                // Para ativos (1s), usa 5 ticks (~10s). Para normais, 1 min.
                duration: isFastAsset ? 5 : 1,
                duration_unit: isFastAsset ? 't' : 'm', 
                symbol: this.currentSymbol,
                ...extraParams
            }
        };

        this.socket.send(JSON.stringify(request));
    },

    handleResponses(data) {
        // Captura o ID da subscrição de velas
        if (data.msg_type === 'candles' && data.subscription) {
            this.candleSubscriptionId = data.subscription.id;
        }

        // Encaminha dados de velas/OHLC para o AnaliseGeral.js
        if (data.msg_type === 'ohlc' || data.msg_type === 'candles') {
            if (this.callbacks['candles']) {
                const candlesData = data.candles ? data.candles : [data.ohlc];
                this.callbacks['candles'](candlesData);
            }
        }

        // Atualização de saldo em tempo real
        if (data.msg_type === 'balance') {
            const el = document.getElementById('acc-balance');
            if (el) el.innerText = `$ ${data.balance.balance.toFixed(2)}`;
        }

        // Monitoramento de compra realizada
        if (data.msg_type === 'buy' && !data.error) {
            const contractId = data.buy.contract_id;
            this.activeContracts[contractId] = this._pendingPrefix;
            
            // Subscreve ao contrato específico para saber o resultado assim que fechar
            this.socket.send(JSON.stringify({
                proposal_open_contract: 1,
                contract_id: contractId,
                subscribe: 1
            }));
        }

        // Processamento de resultado (Win/Loss)
        if (data.msg_type === 'proposal_open_contract') {
            const c = data.proposal_open_contract;
            if (!c) return;

            // Mantém a sincronia do símbolo
            if (c.underlying && c.underlying !== this.currentSymbol) {
                this.currentSymbol = c.underlying;
            }

            // Quando o contrato é finalizado (Vendido)
            if (c.is_sold) {
                const prefix = this.activeContracts[c.contract_id] || 'm';
                const profit = parseFloat(c.profit);
                
                // Atualiza o lucro no módulo correspondente
                if (window.app && typeof app.updateModuleProfit === 'function') {
                    app.updateModuleProfit(profit, prefix);
                }

                delete this.activeContracts[c.contract_id];
                
                // Dispara o evento que o AutoModule está ouvindo
                document.dispatchEvent(new CustomEvent('contract_finished', { 
                    detail: { prefix, profit, contract: c } 
                }));
            }
        }
    }
};
