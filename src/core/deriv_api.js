const DerivAPI = {
    socket: null,
    isAuthorized: false,
    callbacks: {},
    activeContracts: {}, // Mapeia contract_id -> prefixo do módulo ('m', 'a', 'd')

    connect(token, callback) {
        this.socket = new WebSocket('wss://ws.derivws.com/websockets/v3?app_id=1089');

        this.socket.onopen = () => {
            this.socket.send(JSON.stringify({ authorize: token }));
        };

        this.socket.onmessage = (msg) => {
            const data = JSON.parse(msg.data);
            
            if (data.msg_type === 'authorize' && !data.error) {
                this.isAuthorized = true;
                this.socket.send(JSON.stringify({ balance: 1, subscribe: 1 }));
            }

            if (data.msg_type === 'buy') {
                if (this.callbacks['buy']) {
                    this.callbacks['buy'](data);
                }
            }

            if (data.msg_type === 'proposal_open_contract') {
                if (this.callbacks['contract_update']) {
                    this.callbacks['contract_update'](data.proposal_open_contract);
                }
            }

            this.handleResponses(data);
            if (callback) callback(data);
        };
    },

    subscribeContract(contract_id, callback) {
        this.callbacks['contract_update'] = callback;
        this.socket.send(JSON.stringify({
            proposal_open_contract: 1,
            contract_id: contract_id,
            subscribe: 1
        }));
    },

    buy(type, stake, callback, extraParams = {}) {
        if (!this.isAuthorized) return;
        this.callbacks['buy'] = callback;
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
                symbol: "R_100",
                ...extraParams
            }
        };
        this.socket.send(JSON.stringify(request));
    },

    handleResponses(data) {
        if (data.msg_type === 'balance') {
            const el = document.getElementById('acc-balance');
            if (el) el.innerText = `$ ${data.balance.balance.toFixed(2)}`;
        }

        if (data.msg_type === 'buy' && !data.error) {
            const contractId = data.buy.contract_id;
            const prefix = window.currentModulePrefix || 'm';
            this.activeContracts[contractId] = prefix;

            this.socket.send(JSON.stringify({
                proposal_open_contract: 1,
                contract_id: contractId,
                subscribe: 1
            }));
        }

        if (data.msg_type === 'proposal_open_contract') {
            const c = data.proposal_open_contract;
            if (c.is_sold) {
                const prefix = this.activeContracts[c.contract_id] || window.currentModulePrefix || 'm';
                
                if (window.app) {
                    app.updateModuleProfit(parseFloat(c.profit), prefix);
                }

                delete this.activeContracts[c.contract_id];
                
                // GATILHO CRÍTICO: Avisa os módulos que o ciclo terminou
                const event = new CustomEvent('contract_finished', { 
                    detail: { prefix: prefix, profit: parseFloat(c.profit) } 
                });
                document.dispatchEvent(event);
            }
        }
    }
};
