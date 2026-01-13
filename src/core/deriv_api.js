const DerivAPI = {
    socket: null,
    app_id: 1089, // App ID padrão para testes ou o seu próprio

    connect(token, callback) {
        this.socket = new WebSocket(`wss://ws.derivws.com/websockets/v3?app_id=${this.app_id}`);

        this.socket.onopen = () => {
            this.socket.send(JSON.stringify({ authorize: token }));
        };

        this.socket.onmessage = (msg) => {
            const data = JSON.parse(msg.data);
            
            // Ao autorizar, já pede o saldo automaticamente
            if (data.msg_type === 'authorize' && !data.error) {
                this.socket.send(JSON.stringify({ balance: 1, subscribe: 1 }));
            }
            
            callback(data);
        };

        this.socket.onerror = (err) => {
            console.error("Erro Socket:", err);
            alert("Erro na conexão com a Deriv.");
        };
    },

    send(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(data));
        }
    }
};
