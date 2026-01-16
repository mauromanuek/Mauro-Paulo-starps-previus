const AutoModule = {
    isRunning: false,
    isTrading: false,
    currentProfit: 0,
    stats: { wins: 0, losses: 0, total: 0 },

    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <div class="flex justify-between items-center">
                    <h2 class="text-xl font-bold text-purple-500 italic uppercase">Auto Robot</h2>
                    <div id="a-indicator" class="w-3 h-3 rounded-full bg-gray-600"></div>
                </div>
                
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <div>
                        <label class="text-[9px] text-gray-500 font-bold uppercase">Stake</label>
                        <input id="a-stake" type="number" value="10.00" class="w-full bg-black p-2 rounded text-xs text-white outline-none">
                    </div>
                    <div>
                        <label class="text-[9px] text-green-500 font-bold uppercase">T.Profit</label>
                        <input id="a-tp" type="number" value="5" class="w-full bg-black p-2 rounded text-xs text-white outline-none">
                    </div>
                    <div>
                        <label class="text-[9px] text-red-500 font-bold uppercase">S.Loss</label>
                        <input id="a-sl" type="number" value="10" class="w-full bg-black p-2 rounded text-xs text-white outline-none">
                    </div>
                </div>

                <button id="btn-a-toggle" onclick="AutoModule.toggle()" class="w-full py-4 bg-purple-600 rounded-xl font-bold uppercase shadow-lg transition-all">Iniciar Robô</button>
                
                <div id="a-status" class="bg-black p-3 rounded-xl h-32 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800 shadow-inner">> Robô pronto para operar...</div>
                
                <div class="bg-gray-900 p-4 rounded-xl border border-gray-800 flex justify-between items-center">
                    <div>
                        <p class="text-[9px] text-gray-500 uppercase font-bold">Lucro Acumulado</p>
                        <p id="a-val-profit" class="text-xl font-black text-gray-600">0.00 USD</p>
                    </div>
                    <div class="text-right text-[10px] font-bold font-mono space-y-1">
                        <p class="text-green-500">WIN: <span id="a-stat-w">0</span></p>
                        <p class="text-red-500">LOSS: <span id="a-stat-l">0</span></p>
                    </div>
                </div>
            </div>`;
    },

    log(msg, color = "text-gray-400") {
        const status = document.getElementById('a-status');
        if (status) {
            status.innerHTML += `<p class="${color}">> ${msg}</p>`;
            status.scrollTop = status.scrollHeight;
        }
    },

    toggle() {
        this.isRunning = !this.isRunning;
        const btn = document.getElementById('btn-a-toggle');
        const indicator = document.getElementById('a-indicator');
        
        if (this.isRunning) {
            btn.innerText = "PARAR ROBÔ";
            btn.classList.replace('bg-purple-600', 'bg-red-600');
            indicator.classList.replace('bg-gray-600', 'bg-purple-500');
            this.log("[SISTEMA] Modo automático ativado.", "text-purple-400 font-bold");
            this.setupListener(); 
            this.runCycle();
        } else {
            btn.innerText = "INICIAR ROBÔ";
            btn.classList.replace('bg-red-600', 'bg-purple-600');
            indicator.classList.replace('bg-purple-500', 'bg-gray-600');
            this.log("[SISTEMA] Parada solicitada. Aguardando conclusão...", "text-yellow-600");
            this.isTrading = false;
        }
    },

    setupListener() {
        if (this._handler) document.removeEventListener('contract_finished', this._handler);
        this._handler = (e) => {
            if (e.detail.prefix === 'a') {
                this.handleContractResult(e.detail.profit);
            }
        };
        document.addEventListener('contract_finished', this._handler);
    },

    async runCycle() {
        if (!this.isRunning || this.isTrading) return;

        if (this.checkLimits()) return;

        this.log("[IA] Solicitando veredito ao Grok...", "text-blue-400");
        
        try {
            const veredito = await app.analista.obterVereditoCompleto();
            
            if (!this.isRunning) return;

            // Ajuste de Confiança para Oportunismo (Problema 3)
            // Reduzido de 65 para 55 para permitir scalps mais agressivos validados pela IA
            if ((veredito.direcao === "CALL" || veredito.direcao === "PUT") && veredito.confianca >= 55) {
                
                const stake = document.getElementById('a-stake').value;
                this.log(`[ENTRADA] IA confirmou ${veredito.direcao} (${veredito.confianca}%)`, "text-green-500");
                this.log(`[MOTIVO] ${veredito.motivo}`, "text-gray-500 text-[8px]");

                this.isTrading = true;
                
                DerivAPI.buy(veredito.direcao, stake, 'a', (res) => {
                    if (res.buy) {
                        this.log(`[ATIVO] Contrato: ${res.buy.contract_id}`, "text-yellow-500");
                    } else if (res.error) {
                        this.log(`[ERRO API] ${res.error.message}`, "text-red-500");
                        this.isTrading = false;
                        // Tenta novamente após erro de API
                        setTimeout(() => this.runCycle(), 2000);
                    }
                });
            } else {
                // Reduzido tempo de espera de 5s para 2s para não perder o timing do mercado
                this.log(`[AGUARDANDO] Sinal insuficiente (${veredito.confianca}%). Reanalisando...`, "text-gray-600");
                setTimeout(() => this.runCycle(), 2000);
            }

        } catch (e) {
            this.log("[FALLBACK] IA indisponível. Usando lógica técnica...", "text-orange-500");
            const local = app.analista.calcularIndicadoresLocais();
            
            // Backup Local mais inteligente usando Price Action (Problema 5)
            let direcao = "WAIT";
            if ((local.tendenciaDow === "ALTA" || local.isMartelo) && local.rsi < 75) direcao = "CALL";
            else if (local.tendenciaDow === "BAIXA" && local.rsi > 25) direcao = "PUT";

            if (direcao !== "WAIT") {
                this.isTrading = true;
                this.log(`[LOCAL] Entrada via ${local.isMartelo ? 'Price Action' : 'Tendência'}`, "text-orange-400");
                DerivAPI.buy(direcao, document.getElementById('a-stake').value, 'a', (res) => {
                    if (res.error) {
                        this.isTrading = false;
                        setTimeout(() => this.runCycle(), 2000);
                    }
                });
            } else {
                setTimeout(() => this.runCycle(), 2000);
            }
        }
    },

    handleContractResult(profit) {
        this.isTrading = false;
        this.currentProfit += profit;
        
        this.stats.total++;
        profit > 0 ? this.stats.wins++ : this.stats.losses++;
        
        this.updateUI(profit);

        if (this.isRunning) {
            // Ciclo de scalp rápido: redução do tempo de pausa entre contratos
            this.log("[PROXIMO] Buscando nova oportunidade...", "text-gray-500");
            setTimeout(() => this.runCycle(), 1000);
        }
    },

    checkLimits() {
        const tpInput = document.getElementById('a-tp');
        const slInput = document.getElementById('a-sl');
        if (!tpInput || !slInput) return false;

        const tp = parseFloat(tpInput.value);
        const sl = parseFloat(slInput.value);

        if (this.currentProfit >= tp) {
            this.log("[META] TAKE PROFIT ATINGIDO!", "text-green-500 font-black");
            this.toggle();
            return true;
        }
        if (this.currentProfit <= (sl * -1)) {
            this.log("[ALERTA] STOP LOSS ATINGIDO!", "text-red-500 font-black");
            this.toggle();
            return true;
        }
        return false;
    },

    updateUI(lastProfit) {
        const color = lastProfit >= 0 ? 'text-green-500' : 'text-red-500';
        this.log(`[RESULTADO] ${lastProfit > 0 ? 'WIN' : 'LOSS'} (${lastProfit.toFixed(2)} USD)`, color);
        
        const profitEl = document.getElementById('a-val-profit');
        if (profitEl) {
            profitEl.innerText = `${(this.currentProfit >= 0 ? '+' : '')}${this.currentProfit.toFixed(2)} USD`;
            profitEl.className = `text-xl font-black ${this.currentProfit >= 0 ? 'text-green-500' : 'text-red-500'}`;
        }

        const winEl = document.getElementById('a-stat-w');
        const lossEl = document.getElementById('a-stat-l');
        if (winEl) winEl.innerText = this.stats.wins;
        if (lossEl) lossEl.innerText = this.stats.losses;
    }
};
