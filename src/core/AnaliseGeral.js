class AnaliseGeral {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.historicoVelas = [];
    }

    adicionarDados(velas) {
        this.historicoVelas = velas;
    }

    calcularIndicadoresLocais() {
        if (this.historicoVelas.length < 5) return { tendenciaDow: "NEUTRA", isMartelo: false };

        const v = this.historicoVelas;
        const atual = v[v.length - 1];
        const anterior = v[v.length - 2];

        // 1. Teoria de Dow (Topos e Fundos)
        const tendenciaDow = atual.close > anterior.close ? "ALTA" : "BAIXA";

        // 2. Padrão Martelo (Corpo pequeno, sombra inferior longa)
        const corpo = Math.abs(atual.open - atual.close);
        const sombraInferior = atual.close > atual.open ? (atual.open - atual.low) : (atual.close - atual.low);
        const isMartelo = sombraInferior > (corpo * 2);

        // 3. RSI Simplificado (Força do Mercado)
        const rsi = this.historicoVelas.reduce((acc, cur) => acc + (cur.close > cur.open ? 1 : -1), 0);

        return { tendenciaDow, isMartelo, rsi };
    }

    async obterVereditoCompleto() {
        const indicadores = this.calcularIndicadoresLocais();
        const contexto = {
            ativo: document.getElementById('current-asset-name').innerText,
            velas: this.historicoVelas.slice(-5).map(v => ({ o: v.open, h: v.high, l: v.low, c: v.close })),
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
                            content: `Você é um Trader Expert da Deriv. Use estas regras do eBook: 
                            - Se Tendência ALTA + Martelo em Suporte: CALL.
                            - Se Tendência BAIXA + Estrela Cadente: PUT.
                            - Se RSI > 70: Cuidado com PUT.
                            - Responda apenas JSON: {"direcao": "CALL"|"PUT"|"WAIT", "motivo": "frase curta"}`
                        },
                        { role: "user", content: `Analise estes dados: ${JSON.stringify(contexto)}` }
                    ],
                    temperature: 0.2
                })
            });

            if (!response.ok) throw new Error();
            const data = await response.json();
            return JSON.parse(data.choices[0].message.content);
        } catch (e) {
            throw e; // Lança o erro para o index ativar o modo Fallback
        }
    }
}
