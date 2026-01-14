const DerivAPI = {
    socket: null,
    isAuthorized: false,
    callbacks: {},

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
            if (data.msg_type === 'buy' && this.callbacks['buy']) {
                this.callbacks['buy'](data);
                delete this.callbacks['buy'];
            }
            this.handleResponses(data);
            if (callback) callback(data);
        };
    },

    buy(type, stake, callback, extraParams = {}) {
        if (!this.isAuthorized) return;
        this.callbacks['buy'] = callback;
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
            this.socket.send(JSON.stringify({
                proposal_open_contract: 1,
                contract_id: data.buy.contract_id,
                subscribe: 1
            }));
        }
        if (data.msg_type === 'proposal_open_contract') {
            const c = data.proposal_open_contract;
            if (c.is_sold) {
                const prefix = window.currentModulePrefix || 'm';
                if (window.app) app.updateModuleProfit(parseFloat(c.profit), prefix);
            }
        }
    }
};
