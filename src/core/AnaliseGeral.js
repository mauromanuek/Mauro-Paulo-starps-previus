class AnaliseGeral {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.historicoVelas = [];
    }

    adicionarDados(velas) {
        this.historicoVelas = velas;
    }

    calcularIndicadoresLocais() {
        if (this.historicoVelas.length < 5) return { tendenciaDow: "NEUTRA", isMartelo: false, rsi: 50 };

        const v = this.historicoVelas;
        const atual = v[v.length - 1];
        const anterior = v[v.length - 2];

        // 1. Teoria de Dow (Topos e Fundos)
        const tendenciaDow = atual.close > anterior.close ? "ALTA" : "BAIXA";

        // 2. Padrão Martelo (Corpo pequeno, sombra inferior longa)
        const corpo = Math.abs(atual.open - atual.close);
        const sombraInferior = atual.close > atual.open ? (atual.open - atual.low) : (atual.close - atual.low);
        const isMartelo = sombraInferior > (corpo * 2);

        // 3. RSI Real (Força Relativa - Baseado nas últimas 14 velas ou disponíveis)
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
        const contexto = {
            ativo: document.getElementById('current-asset-name').innerText,
            velas: this.historicoVelas.slice(-10).map(v => ({ o: v.open, h: v.high, l: v.low, c: v.close })),
            analiseTecnica: indicadores
        };

        return await this.chamarGrok(contexto);
    }

    async chamarGrok(contexto) {
        try {
            const response = await fetch("https://api.x.ai/v1/chat/completions", {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${this.apiKey}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    model: "grok-beta",
                    messages: [
                        { 
                            role: "system", 
                            content: `Você é um Trader Expert da Deriv. Analise os dados reais do mercado.
                            Regras do eBook: 
                            - Tendência ALTA + Martelo em Suporte: CALL.
                            - Tendência BAIXA + Estrela Cadente: PUT.
                            - RSI > 70 indica sobrecompra (procure PUT), RSI < 30 sobrevenda (procure CALL).
                            Responda estritamente em JSON: {"direcao": "CALL"|"PUT"|"WAIT", "confianca": 0-100, "motivo": "frase curta"}`
                        },
                        { role: "user", content: `Analise estes dados agora: ${JSON.stringify(contexto)}` }
                    ],
                    temperature: 0.1
                })
            });

            if (!response.ok) throw new Error("Erro na API Grok");
            const data = await response.json();
            
            // Limpa o conteúdo de possíveis marcações markdown antes de dar o parse
            const content = data.choices[0].message.content.replace(/```json|```/g, '').trim();
            return JSON.parse(content);
        } catch (e) {
            console.error("Falha na análise Grok:", e);
            throw e; // Lança o erro para o index ativar o modo Fallback (Local)
        }
    }
}
