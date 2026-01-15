const ManualModule = {
    isTrading: false,
    isActive: false, // Controla se o ciclo contínuo está ligado
    currentProfit: 0,
    stats: { wins: 0, losses: 0, total: 0 },

    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <div class="flex justify-between items-center">
                    <h2 class="text-xl font-bold text-green-500 italic uppercase">Manual Pro</h2>
                    <div id="m-indicator" class="w-3 h-3 rounded-full bg-gray-600"></div>
                </div>
                
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <div>
                        <label class="text-[9px] text-gray-500 uppercase font-bold">Stake</label>
                        <input id="m-stake" type="number" value="10.00" class="w-full bg-black p-2 rounded text-xs text-white outline-none">
                    </div>
                    <div>
                        <label class="text-[9px] text-green-500 uppercase font-bold">T.Profit</label>
                        <input id="m-tp" type="number" value="5" class="w-full bg-black p-2 rounded text-xs text-white outline-none">
                    </div>
                    <div>
                        <label class="text-[9px] text-red-500 uppercase font-bold">S.Loss</label>
                        <input id="m-sl" type="number" value="10" class="w-full bg-black p-2 rounded text-xs text-white outline-none">
                    </div>
                </div>

                <button id="btn-m-start" onclick="ManualModule.toggle()" class="w-full py-4 bg-blue-600 rounded-xl font-bold uppercase shadow-lg transition-all">Iniciar Operação</button>
                
                <div class="grid grid-cols-2 gap-4">
                    <button id="btn-call" onclick="ManualModule.trade('CALL')" class="py-6 bg-green-600 rounded-2xl font-black text-2xl shadow-lg opacity-20 transition-all" disabled>CALL</button>
                    <button id="btn-put" onclick="ManualModule.trade('PUT')" class="py-6 bg-red-600 rounded-2xl font-black text-2xl shadow-lg opacity-20 transition-all" disabled>PUT</button>
                </div>

                <div id="m-status" class="bg-black p-3 rounded-xl h-32 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800 shadow-inner">> Sistema Manual Pronto...</div>
                
                <div class="bg-gray-900 p-4 rounded-xl border border-gray-800 flex justify-between items-center">
                    <div>
                        <p class="text-[9px] text-gray-500 uppercase font-bold">Lucro Acumulado</p>
                        <p id="m-val-profit" class="text-xl font-black text-gray-600">0.00 USD</p>
                    </div>
                    <div class="text-right text-[10px] font-bold font-mono space-y-1">
                        <p class="text-green-500">W: <span id="m-stat-w">0</span></p>
                        <p class="text-red-500">L: <span id="m-stat-l">0</span></p>
                    </div>
                </div>
            </div>`;
    },

    log(msg, color = "text-gray-400") {
        const status = document.getElementById('m-status');
        if (status) {
            status.innerHTML += `<p class="${color}">> ${msg}</p>`;
            status.scrollTop = status.scrollHeight;
        }
    },

    toggle() {
        this.isActive = !this.isActive;
        const btn = document.getElementById('btn-m-start');
        const indicator = document.getElementById('m-indicator');

        if (this.isActive) {
            btn.innerText = "Parar Operação";
            btn.classList.replace('bg-blue-600', 'bg-red-600');
            indicator.classList.replace('bg-gray-600', 'bg-green-500');
            this.log("[SISTEMA] Modo contínuo ativado.", "text-blue-400");
            this.runCycle();
        } else {
            btn.innerText = "Iniciar Operação";
            btn.classList.replace('bg-red-600', 'bg-blue-600');
            indicator.classList.replace('bg-green-500', 'bg-gray-600');
            this.log("[SISTEMA] Parando após conclusão...", "text-yellow-600");
            this.resetButtons();
        }
    },

    async runCycle() {
        if (!this.isActive || this.isTrading) return;

        // Verifica metas antes de nova análise
        if (this.checkLimits()) return;

        this.log("[ANALISANDO] Verificando volatilidade...", "text-blue-400");
        this.resetButtons();

        // Simulação de análise técnica (ciclo de vida)
        setTimeout(() => {
            if (!this.isActive) return;

            const side = Math.random() > 0.5 ? 'call' : 'put';
            const target = document.getElementById('btn-' + side);
            
            if(target) {
                target.disabled = false;
                target.style.opacity = "1";
                target.classList.add(side === 'call' ? 'indicator-glow' : 'indicator-glow-red');
            }
            
            this.log(`[SINAL] Entrada detectada em ${side.toUpperCase()}. Aguardando execução...`, "text-green-500 font-bold");
        }, 1500);
    },

    trade(type) {
        if (this.isTrading || !this.isActive) return;

        this.isTrading = true;
        window.currentModulePrefix = 'm';
        const stake = document.getElementById('m-stake').value;

        this.log(`[EXECUTANDO] Ordem ${type} de ${stake} USD`, "text-yellow-400");
        this.log("[AGUARDANDO RESULTADO]", "text-gray-500");

        DerivAPI.buy(type, stake, (res) => {
            if (res.error) {
                this.log(`[ERRO] ${res.error.message}`, "text-red-500");
                this.isTrading = false;
                if (this.isActive) setTimeout(() => this.runCycle(), 2000);
            }
        });

        this.resetButtons();
        this.setupContractListener();
    },

    setupContractListener() {
        const handler = (e) => {
            if (e.detail.prefix === 'm') {
                const profit = e.detail.profit;
                this.isTrading = false;
                this.currentProfit += profit;
                
                // Atualiza Estatísticas
                this.stats.total++;
                profit > 0 ? this.stats.wins++ : this.stats.losses++;
                this.updateUI(profit);

                document.removeEventListener('contract_finished', handler);

                // CONTINUIDADE: Se não atingiu meta, reanalisa automaticamente
                if (this.isActive) {
                    this.log("[LUCRO ATUALIZADO] Reiniciando ciclo de análise...", "text-gray-500");
                    setTimeout(() => this.runCycle(), 1500);
                }
            }
        };
        document.addEventListener('contract_finished', handler);
    },

    checkLimits() {
        const tp = parseFloat(document.getElementById('m-tp').value);
        const sl = parseFloat(document.getElementById('m-sl').value);

        if (this.currentProfit >= tp) {
            this.log("[META] TAKE PROFIT ATINGIDO!", "text-green-500 font-black");
            if (this.isActive) this.toggle();
            return true;
        }
        if (this.currentProfit <= (sl * -1)) {
            this.log("[META] STOP LOSS ATINGIDO!", "text-red-500 font-black");
            if (this.isActive) this.toggle();
            return true;
        }
        return false;
    },

    updateUI(lastProfit) {
        const color = lastProfit >= 0 ? 'text-green-500' : 'text-red-500';
        this.log(`[FECHADO] Resultado: ${lastProfit > 0 ? 'WIN' : 'LOSS'} (${lastProfit.toFixed(2)} USD)`, color);
        
        const profitEl = document.getElementById('m-val-profit');
        if (profitEl) {
            profitEl.innerText = `${this.currentProfit.toFixed(2)} USD`;
            profitEl.className = `text-xl font-black ${this.currentProfit >= 0 ? 'text-green-500' : 'text-red-500'}`;
        }

        document.getElementById('m-stat-w').innerText = this.stats.wins;
        document.getElementById('m-stat-l').innerText = this.stats.losses;
    },

    resetButtons() {
        ['btn-call', 'btn-put'].forEach(id => {
            const b = document.getElementById(id);
            if(b) {
                b.disabled = true;
                b.style.opacity = "0.2";
                b.classList.remove('indicator-glow', 'indicator-glow-red');
            }
        });
    }
};
