class AnaliseGeral {
    constructor(backendUrl) {
        // Define a rota do backend no Render
        this.backendUrl = backendUrl || "https://mauro-paulo-starps-previus-2.onrender.com/analisar";
        this.historicoVelas = [];
    }

    /**
     * Limpa o histórico de velas para evitar contaminação de dados
     * entre ativos diferentes (Resolve Problema 1: Ativo Preso)
     */
    limparHistorico() {
        this.historicoVelas = [];
    }

    adicionarDados(velas) {
        // Garante que as velas recebidas da Deriv API sejam armazenadas corretamente
        // Se receber um array, substitui; se receber um objeto único (tick), gerenciar conforme necessário
        this.historicoVelas = Array.isArray(velas) ? velas : [...this.historicoVelas, velas].slice(-100);
    }

    calcularIndicadoresLocais() {
        // Precisamos de pelo menos 10 velas para uma análise de força confiável
        if (!this.historicoVelas || this.historicoVelas.length < 10) {
            return { tendenciaDow: "NEUTRA", isMartelo: false, rsi: 50 };
        }

        const v = this.historicoVelas;
        const atual = v[v.length - 1];
        const anterior = v[v.length - 2];

        // 1. Teoria de Dow (Direção imediata do preço)
        const tendenciaDow = atual.close > anterior.close ? "ALTA" : "BAIXA";

        // 2. Price Action: Padrão Martelo (Reversão de Fundo)
        [attachment_0](attachment)
        // Corrigido para identificar rejeição real de preço na sombra inferior
        const corpo = Math.abs(atual.open - atual.close);
        const precoMinimoCorpo = Math.min(atual.open, atual.close);
        const sombraInferior = precoMinimoCorpo - atual.low;
        
        // Um martelo clássico tem a sombra inferior pelo menos 2x maior que o corpo
        const isMartelo = sombraInferior > (corpo * 2) && corpo > 0;

        // 3. RSI Real (Relative Strength Index) - Período 14
        let ganhos = 0;
        let perdas = 0;
        const periodoRSI = Math.min(v.length - 1, 14);
        
        for (let i = v.length - periodoRSI; i < v.length; i++) {
            const diferenca = v[i].close - v[i-1].close;
            if (diferenca >= 0) ganhos += diferenca;
            else perdas += Math.abs(diferenca);
        }
        
        const rsi = perdas === 0 ? 100 : 100 - (100 / (1 + (ganhos / perdas)));

        return { 
            tendenciaDow, 
            isMartelo, 
            rsi: Math.round(rsi),
            volume_check: atual.high !== atual.low // Verifica se há volatilidade
        };
    }

    async obterVereditoCompleto() {
        const indicadores = this.calcularIndicadoresLocais();
        const assetName = document.getElementById('current-asset-name')?.innerText || "Ativo Desconhecido";
        
        // Prepara o conjunto de dados OHLC para o Llama 3.3
        // Enviar os preços reais (O, H, L, C) permite que a IA identifique suportes e resistências
        const priceActionData = this.historicoVelas.slice(-15).map(v => ({
            o: v.open,
            h: v.high,
            l: v.low,
            c: v.close
        }));

        const payload = {
            contexto: `Análise Profissional para Scalping - Ativo: ${assetName}`,
            asset: assetName, // Envio explícito do ativo para evitar Problema 1
            indicadores: {
                tendencia: indicadores.tendenciaDow,
                padrao_reversao: indicadores.isMartelo ? "MARTELO DETECTADO" : "NENHUM",
                rsi_valor: indicadores.rsi,
                ohlc_history: priceActionData
            }
        };

        return await this.chamarGroq(payload);
    }

    async chamarGroq(payload) {
        try {
            const response = await fetch(this.backendUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.erro || "Falha no Render");
            }

            const data = await response.json();
            
            if (data.choices && data.choices[0] && data.choices[0].message) {
                const content = data.choices[0].message.content;
                const veredito = JSON.parse(content);
                
                // Validação de segurança do JSON retornado pela IA
                if (!veredito.direcao || veredito.confianca === undefined) {
                    throw new Error("IA retornou dados incompletos");
                }
                
                return veredito;
            } else {
                throw new Error("Resposta da IA fora do padrão");
            }

        } catch (e) {
            console.warn("IA indisponível, usando lógica técnica local...");
            
            // FALLBACK: Se o Render/IA falhar, o bot não para, ele usa análise técnica pura
            const ind = this.calcularIndicadoresLocais();
            let direcao = "WAIT";
            
            // Lógica Oportunista Híbrida de Fallback (Resolve Problema 4)
            if (ind.rsi < 35 || ind.isMartelo) direcao = "CALL";
            else if (ind.rsi > 65) direcao = "PUT";

            return {
                direcao: direcao,
                confianca: 55,
                motivo: "Baseado em RSI e Price Action Local (Modo de Segurança Ativo)"
            };
        }
    }
}
