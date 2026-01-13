// src/utils/analysis_engine.js
const AnalysisEngine = {
    // Tradução da lógica do seu strategy.py (EMA 14)
    calculateSignal(ticks) {
        if (ticks.length < 14) return { action: "CALIBRANDO...", color: "gray" };

        const lastPrice = ticks[ticks.length - 1];
        const sum = ticks.slice(-14).reduce((a, b) => a + b, 0);
        const ema = sum / 14;

        if (lastPrice > ema + 0.05) {
            return { action: "CALL (COMPRA)", color: "#00c076", reason: "Preço em tendência de alta acima da média." };
        } else if (lastPrice < ema - 0.05) {
            return { action: "PUT (VENDA)", color: "#cf304a", reason: "Pressão vendedora abaixo da média." };
        }
        
        return { action: "NEUTRO", color: "#888", reason: "Mercado sem tendência clara." };
    }
};
