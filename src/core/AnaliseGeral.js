class AnaliseGeral {
    constructor(backendUrl) {
        // Preserva a URL vinda do app ou usa a padrão do Render
        this.backendUrl = backendUrl || "https://mauro-paulo-starps-previus-2.onrender.com/analisar";
        this.historicoVelas = [];
    }

    adicionarDados(velas) {
        this.historicoVelas = velas;
    }

    calcularIndicadoresLocais() {
        // Aumentado para 10 velas para garantir precisão no RSI inicial
        if (this.historicoVelas.length < 10) return { tendenciaDow: "NEUTRA", isMartelo: false, rsi: 50 };

        const v = this.historicoVelas;
        const atual = v[v.length - 1];
        const anterior = v[v.length - 2];

        // 1. Teoria de Dow (Topos e Fundos simplificados) - Mantida lógica original
        const tendenciaDow = atual.close > anterior.close ? "ALTA" : "BAIXA";

        // 2. Padrão Martelo (Price Action) - CORREÇÃO CIRÚRGICA na variável errada (Problema 5)
        const corpo = Math.abs(atual.open - atual.close);
        const sombraInferior = atual.close > atual.open ? (atual.open - atual.low) : (atual.close - atual.low);
        const isMartelo = sombraInferior > (corpo * 2);

        // 3. RSI Real (Relative Strength Index) - Mantida lógica original
        let ganhos = 0;
        let perdas = 0;
        const periodoRSI = Math.min(this.historicoVelas.length - 1, 14);
        
        for (let i = v.length - periodoRSI; i < v.length; i++) {
            const diferenca = v[i].close - v[i-1].close;
            if (diferenca >= 0) ganhos += diferenca;
            else perdas += Math.abs(diferenca);
        }
        
        const rsi = perdas === 0 ? 100 : 100 - (100 / (1 + (ganhos / perdas)));

        return { tendenciaDow, isMartelo, rsi: Math.round(rsi) };
    }

    async obterVereditoCompleto() {
        const indicadores = this.calcularIndicadoresLocais();
        const assetName = document.getElementById('current-asset-name')?.innerText || "Ativo Desconhecido";
        
        // Payload enriquecido para IA Oportunista (Problema 3)
        // Agora enviamos Open, High, Low e Close (OHLC) para o Llama entender volatilidade
        const payload = {
            contexto: `Ativo: ${assetName} | Timeframe: M1`,
            indicadores: {
                dow: indicadores.tendenciaDow,
                martelo: indicadores.isMartelo,
                rsi_atual: indicadores.rsi,
                // Enviamos dados mais completos das últimas 10 velas para identificar Scalp
                price_action: this.historicoVelas.slice(-10).map(v => ({
                    o: v.open,
                    h: v.high,
                    l: v.low,
                    c: v.close
                }))
            }
        };

        return await this.chamarGroq(payload);
    }

    async chamarGroq(payload) {
        try {
            const response = await fetch(this.backendUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.erro || "Falha na comunicação com Backend");
            }

            const data = await response.json();
            
            // Tratamento de resposta preservado conforme lógica original
            if (data.choices && data.choices[0] && data.choices[0].message) {
                const content = data.choices[0].message.content;
                const veredito = JSON.parse(content);
                
                if (!veredito.direcao || veredito.confianca === undefined) {
                    throw new Error("JSON da IA com campos incompletos");
                }
                
                return veredito;
            } else {
                throw new Error("Estrutura de resposta inesperada da IA");
            }

        } catch (e) {
            console.error("Erro na análise via Groq:", e.message);
            throw e; 
        }
    }
}
