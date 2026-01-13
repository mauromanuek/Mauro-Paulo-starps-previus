const DerivAPI = {
    socket: null,
    isAuthorized: false,

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

            // Encaminha todas as respostas para o tratamento global
            this.handleResponses(data);
            if(callback) callback(data);
        };
    },

    buy(type, stake, symbol = "R_100") {
        if (!this.isAuthorized) return alert("Não autorizado!");
        
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
                symbol: symbol
            }
        };
        this.socket.send(JSON.stringify(request));
    },

    handleResponses(data) {
        if (data.msg_type === 'balance') {
            const bal = data.balance.balance;
            document.getElementById('acc-balance').innerText = `$ ${bal.toFixed(2)}`;
        }

        if (data.msg_type === 'buy') {
            // Subscreve para monitorar o contrato aberto
            this.socket.send(JSON.stringify({ 
                proposal_open_contract: 1, 
                contract_id: data.buy.contract_id, 
                subscribe: 1 
            }));
        }

        if (data.msg_type === 'proposal_open_contract') {
            const contract = data.proposal_open_contract;
            if (contract.is_sold) {
                app.displayResult(contract.status, contract.profit);
            }
        }
    }
};
