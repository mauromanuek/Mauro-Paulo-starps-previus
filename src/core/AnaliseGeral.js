class AnaliseGeral {
    constructor(backendUrl) {
        // Agora recebe a URL do seu backend no Render em vez da API Key direta
        this.backendUrl = backendUrl || "https://mauro-paulo-starps-previus-2.onrender.com/analisar";
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
        const assetName = document.getElementById('current-asset-name')?.innerText || "Ativo Desconhecido";
        
        // Formata os dados exatamente como o Backend Flask espera
        const payload = {
            contexto: `Ativo: ${assetName} | Timeframe: M1 | Últimas 10 velas processadas.`,
            indicadores: JSON.stringify({
                dow: indicadores.tendenciaDow,
                martelo: indicadores.isMartelo,
                rsi_atual: indicadores.rsi,
                price_action: this.historicoVelas.slice(-5).map(v => ({ c: v.close }))
            })
        };

        return await this.chamarGrok(payload);
    }

    async chamarGrok(payload) {
        try {
            // Chamada agora é feita para o SEU BACKEND no Render
            const response = await fetch(this.backendUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.erro || "Erro na comunicação com o Backend");
            }

            const data = await response.json();
            
            // O backend já sanitizou o JSON no campo 'content'
            // O frontend apenas faz o parse final para retornar o objeto direcao/confianca
            if (data.choices && data.choices[0] && data.choices[0].message) {
                const content = data.choices[0].message.content;
                return JSON.parse(content);
            } else {
                throw new Error("Resposta da IA com estrutura inválida");
            }

        } catch (e) {
            console.error("Falha na análise via Backend/Grok:", e.message);
            throw e; // Lança para o index ativar o modo Fallback (Local)
        }
    }
}
