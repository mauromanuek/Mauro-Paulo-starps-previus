const DerivAPI = {
    socket: null,
    isAuthorized: false,
    callbacks: {}, // Armazena callbacks para chamadas específicas

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

            // Tratamento de Resposta de Compra
            if (data.msg_type === 'buy') {
                if (this.callbacks['buy']) {
                    this.callbacks['buy'](data);
                    delete this.callbacks['buy'];
                }
            }

            this.handleResponses(data);
            if(callback) callback(data);
        };
    },

    // Agora aceita extraParams para suportar Digits (barrier)
    buy(type, stake, callback, extraParams = {}) {
        if (!this.isAuthorized) return alert("Por favor, conecte o seu Token primeiro!");
        
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
                symbol: extraParams.symbol || "R_100",
                ...extraParams // Aqui entra o barrier: "5" enviado pelo DigitModule
            }
        };
        this.socket.send(JSON.stringify(request));
    },

    handleResponses(data) {
        if (data.msg_type === 'balance') {
            const bal = data.balance.balance;
            const el = document.getElementById('acc-balance');
            if(el) el.innerText = `$ ${bal.toFixed(2)}`;
        }

        if (data.msg_type === 'buy' && !data.error) {
            // Subscreve imediatamente para monitorar o lucro real
            this.socket.send(JSON.stringify({ 
                proposal_open_contract: 1, 
                contract_id: data.buy.contract_id, 
                subscribe: 1 
            }));
        }

        if (data.msg_type === 'proposal_open_contract') {
            const contract = data.proposal_open_contract;
            if (contract.is_sold) {
                // Atualiza o lucro global baseado no resultado real da Deriv
                if (window.app) app.updateModuleProfit(parseFloat(contract.profit));
            }
        }
    }
};
