// src/utils/strategy_logic.js
const StrategyLogic = {
    prices: [],
    
    analyze(tick) {
        this.prices.push(tick);
        if(this.prices.length > 50) this.prices.shift();

        if(this.prices.length < 20) return null;

        // Cálculo Simples de Média Móvel (EMA 14)
        const sum = this.prices.slice(-14).reduce((a, b) => a + b, 0);
        const ema = sum / 14;
        const lastPrice = tick;

        let signal = null;
        if (lastPrice > ema + 0.02) signal = 'CALL';
        if (lastPrice < ema - 0.02) signal = 'PUT';

        // Se o Módulo Automático estiver ligado, executa a ordem
        if(signal && typeof AutoModule !== 'undefined' && AutoModule.isRunning) {
            AutoModule.log(`Sinal detectado: ${signal}. Enviando ordem...`);
            DerivAPI.sendOrder(signal, AutoModule.settings.stake);
        }

        return signal;
    }
};
