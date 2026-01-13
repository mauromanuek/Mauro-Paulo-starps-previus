const DerivAPI = {
    socket: null,
    app_id: 114910,

    connect(token, callback) {
        this.socket = new WebSocket(`wss://ws.derivws.com/websockets/v3?app_id=${this.app_id}`);
        this.socket.onopen = () => this.socket.send(JSON.stringify({ authorize: token }));
        this.socket.onmessage = (msg) => {
            const data = JSON.parse(msg.data);
            if(data.msg_type === 'authorize') {
                this.socket.send(JSON.stringify({ balance: 1, subscribe: 1 }));
                this.socket.send(JSON.stringify({ ticks: 'R_100', subscribe: 1 }));
            }
            callback(data);
        };
    },

    // Item 6: Envio de ordens reais
    buyContract(type, amount, symbol) {
        const proposal = {
            proposal: 1, amount: amount, barrier: "0", 
            basis: "stake", contract_type: type, 
            currency: "USD", duration: 1, duration_unit: "t", 
            symbol: symbol
        };
        this.socket.send(JSON.stringify(proposal));
        app.notify(`Enviando ordem ${type} de $${amount}...`);
    }
};
