// src/core/deriv_api.js
const DerivAPI = {
    ws: null,
    app_id: 114910,
    state: { balance: 0, currency: 'USD', is_virtual: true, ticks: [] },

    connect(token, onMessage) {
        this.ws = new WebSocket(`wss://ws.derivws.com/websockets/v3?app_id=${this.app_id}`);
        
        this.ws.onopen = () => {
            this.ws.send(JSON.stringify({ authorize: token }));
        };

        this.ws.onmessage = (msg) => {
            const data = JSON.parse(msg.data);
            if (data.msg_type === 'authorize' && !data.error) {
                // Subscrever a saldo e ticks após autorizar
                this.ws.send(JSON.stringify({ balance: 1, subscribe: 1 }));
                this.ws.send(JSON.stringify({ ticks: 'R_100', subscribe: 1 }));
            }
            onMessage(data);
        };
    },

    sendOrder(type, amount, barrier) {
        const proposal = {
            buy: 1,
            price: amount,
            parameters: {
                amount: amount,
                basis: 'stake',
                contract_type: type, // Ex: 'DIGITOVER', 'CALL', etc
                currency: 'USD',
                duration: 1,
                duration_unit: 't',
                symbol: 'R_100'
            }
        };
        if(barrier !== undefined) proposal.parameters.barrier = barrier;
        this.ws.send(JSON.stringify(proposal));
    }
};
