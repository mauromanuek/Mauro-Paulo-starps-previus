// src/core/contract_manager.js
const ContractManager = {
    buy(type, amount) {
        if (!DerivAPI.ws || DerivAPI.ws.readyState !== WebSocket.OPEN) return;

        const request = {
            buy: 1,
            price: parseFloat(amount),
            parameters: {
                amount: parseFloat(amount),
                basis: 'stake',
                contract_type: type, // CALL ou PUT
                currency: 'USD',
                duration: 1,
                duration_unit: 'm', // Baseado no seu strategy.py original
                symbol: 'R_100'
            }
        };

        DerivAPI.ws.send(JSON.stringify(request));
        console.log(`Ordem de ${type} enviada via WebSocket.`);
    }
};
