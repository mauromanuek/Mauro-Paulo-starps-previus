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
            // Usa o analista global para obter uma decisão real da IA
            const veredito = await app.analista.obterVereditoCompleto();
            
            if (!this.isRunning) return;

            // Só entra se a IA tiver confiança e direção clara
            if ((veredito.direcao === "CALL" || veredito.direcao === "PUT") && veredito.confianca >= 65) {
                
                const stake = document.getElementById('a-stake').value;
                this.log(`[ENTRADA] IA confirmou ${veredito.direcao} (${veredito.confianca}%)`, "text-green-500");
                this.log(`[MOTIVO] ${veredito.motivo}`, "text-gray-500");

                this.isTrading = true;
                
                // Compra passando o prefixo 'a' explicitamente para evitar erro de atribuição
                DerivAPI.buy(veredito.direcao, stake, 'a', (res) => {
                    if (res.buy) {
                        this.log(`[ATIVO] Contrato: ${res.buy.contract_id}`, "text-yellow-500");
                    } else if (res.error) {
                        this.log(`[API ERROR] ${res.error.message}`, "text-red-500");
                        this.isTrading = false;
                    }
                });
            } else {
                this.log(`[AGUARDANDO] Sinal fraco ou neutro (${veredito.confianca}%). Reanalisando em 5s...`, "text-gray-500");
                setTimeout(() => this.runCycle(), 5000);
            }

        } catch (e) {
            this.log("[FALLBACK] IA indisponível. Usando análise técnica local...", "text-orange-500");
            const local = app.analista.calcularIndicadoresLocais();
            
            // Lógica simples de backup caso a IA falhe
            let direcao = "WAIT";
            if (local.tendenciaDow === "ALTA" && local.rsi < 70) direcao = "CALL";
            if (local.tendenciaDow === "BAIXA" && local.rsi > 30) direcao = "PUT";

            if (direcao !== "WAIT") {
                this.isTrading = true;
                DerivAPI.buy(direcao, document.getElementById('a-stake').value, 'a', (res) => {
                    if (res.error) this.isTrading = false;
                });
            } else {
                setTimeout(() => this.runCycle(), 5000);
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
            this.log("[PAUSA] Ciclo concluído. Nova análise em 3s...", "text-gray-500");
            setTimeout(() => this.runCycle(), 3000);
        }
    },

    checkLimits() {
        const tp = parseFloat(document.getElementById('a-tp').value);
        const sl = parseFloat(document.getElementById('a-sl').value);

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
        this.log(`[RESULTADO] ${lastProfit > 0 ? 'VITÓRIA' : 'DERROTA'} (${lastProfit.toFixed(2)} USD)`, color);
        
        const profitEl = document.getElementById('a-val-profit');
        if (profitEl) {
            profitEl.innerText = `${(this.currentProfit >= 0 ? '+' : '')}${this.currentProfit.toFixed(2)} USD`;
            profitEl.className = `text-xl font-black ${this.currentProfit >= 0 ? 'text-green-500' : 'text-red-500'}`;
        }

        document.getElementById('a-stat-w').innerText = this.stats.wins;
        document.getElementById('a-stat-l').innerText = this.stats.losses;
    }
};
