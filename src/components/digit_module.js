const DigitModule = {
    tickBuffer: [],
    maxTicks: 50, // Reduzido para análise mais reativa e rápida
    isAnalysisRunning: false,
    isTrading: false,
    currentProfit: 0,
    stats: { wins: 0, losses: 0, total: 0 },

    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <div class="flex justify-between items-center">
                    <h2 class="text-xl font-bold text-yellow-500 italic uppercase">Digit Strategy</h2>
                    <div id="d-indicator" class="w-3 h-3 rounded-full bg-gray-600"></div>
                </div>
                
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <div>
                        <label class="text-[9px] text-gray-500 uppercase font-bold">Stake</label>
                        <input id="d-stake" type="number" value="10.00" class="w-full bg-black p-2 rounded text-xs text-white outline-none">
                    </div>
                    <div>
                        <label class="text-[9px] text-green-500 uppercase font-bold">T.Profit</label>
                        <input id="d-tp" type="number" value="5" class="w-full bg-black p-2 rounded text-xs text-white outline-none">
                    </div>
                    <div>
                        <label class="text-[9px] text-red-500 uppercase font-bold">S.Loss</label>
                        <input id="d-sl" type="number" value="10" class="w-full bg-black p-2 rounded text-xs text-white outline-none">
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div id="box-over" class="bg-gray-900 p-4 rounded-2xl border-2 border-transparent text-center transition-all">
                        <p class="text-[10px] text-gray-400 uppercase">Digit Over (5)</p>
                        <p id="perc-over" class="text-2xl font-black text-white">0%</p>
                    </div>
                    <div id="box-under" class="bg-gray-900 p-4 rounded-2xl border-2 border-transparent text-center transition-all">
                        <p class="text-[10px] text-gray-400 uppercase">Digit Under (5)</p>
                        <p id="perc-under" class="text-2xl font-black text-white">0%</p>
                    </div>
                </div>

                <button id="btn-d-toggle" onclick="DigitModule.toggle()" class="w-full py-4 bg-yellow-600 rounded-xl font-bold uppercase shadow-lg transition-all">Analisar & Operar</button>
                
                <div id="d-status" class="bg-black p-3 rounded-xl h-32 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800 shadow-inner">> Aguardando inicialização...</div>
                
                <div class="bg-gray-900 p-4 rounded-xl border border-gray-800 flex justify-between items-center">
                    <div>
                        <p class="text-[9px] text-gray-500 uppercase font-bold">Lucro Acumulado</p>
                        <p id="d-val-profit" class="text-xl font-black text-gray-600">0.00 USD</p>
                    </div>
                    <div class="text-right text-[10px] font-bold font-mono space-y-1">
                        <p class="text-green-400">WIN: <span id="d-stat-w">0</span></p>
                        <p class="text-red-400">LOSS: <span id="d-stat-l">0</span></p>
                    </div>
                </div>
            </div>`;
    },

    log(msg, color = "text-gray-400") {
        const status = document.getElementById('d-status');
        if (status) {
            status.innerHTML += `<p class="${color}">> ${msg}</p>`;
            status.scrollTop = status.scrollHeight;
        }
    },

    toggle() {
        this.isAnalysisRunning = !this.isAnalysisRunning;
        const btn = document.getElementById('btn-d-toggle');
        const indicator = document.getElementById('d-indicator');

        if (this.isAnalysisRunning) {
            btn.innerText = "PARAR OPERAÇÃO";
            btn.classList.replace('bg-yellow-600', 'bg-red-600');
            indicator.classList.replace('bg-gray-600', 'bg-yellow-500');
            this.log("[SISTEMA] Monitoramento e estratégia ativos.", "text-yellow-500");
            this.startTickStream();
            this.setupCycleListener();
        } else {
            btn.innerText = "ANALISAR & OPERAR";
            btn.classList.replace('bg-red-600', 'bg-yellow-600');
            indicator.classList.replace('bg-yellow-500', 'bg-gray-600');
            this.log("[SISTEMA] Operação pausada pelo usuário.", "text-gray-500");
        }
    },

    startTickStream() {
        if (!DerivAPI.socket) return;
        
        DerivAPI.socket.send(JSON.stringify({
            ticks: "R_100",
            subscribe: 1
        }));

        // Listener de ticks único
        const tickHandler = (msg) => {
            if (!this.isAnalysisRunning) {
                // Idealmente enviar um 'forget_all' ticks aqui se necessário
                return;
            }
            
            const data = JSON.parse(msg.data);
            if (data.msg_type === 'tick' && data.tick.symbol === "R_100") {
                const quote = data.tick.quote.toString();
                const lastDigit = parseInt(quote.slice(-1));
                
                this.tickBuffer.push(lastDigit);
                if (this.tickBuffer.length > this.maxTicks) this.tickBuffer.shift();
                
                this.updateUI();
                this.checkStrategy();
            }
        };
        DerivAPI.socket.onmessage = tickHandler; // Nota: DerivAPI.connect sobrepõe isso, ideal é usar addEventListener no core
    },

    updateUI() {
        if (this.tickBuffer.length < 5) return;
        
        const over5 = this.tickBuffer.filter(d => d > 5).length;
        const under5 = this.tickBuffer.filter(d => d < 5).length;
        const total = this.tickBuffer.length;

        const pOver = ((over5 / total) * 100).toFixed(0);
        const pUnder = ((under5 / total) * 100).toFixed(0);

        document.getElementById('perc-over').innerText = pOver + "%";
        document.getElementById('perc-under').innerText = pUnder + "%";

        document.getElementById('box-over').style.borderColor = pOver > 65 ? "#eab308" : "transparent";
        document.getElementById('box-under').style.borderColor = pUnder > 65 ? "#eab308" : "transparent";
    },

    checkStrategy() {
        if (this.isTrading || !this.isAnalysisRunning) return;
        if (this.tickBuffer.length < 20) return;

        if (this.checkLimits()) return;

        const over5 = this.tickBuffer.filter(d => d > 5).length;
        const under5 = this.tickBuffer.filter(d => d < 5).length;
        const total = this.tickBuffer.length;

        const pOver = (over5 / total) * 100;
        const pUnder = (under5 / total) * 100;
        const stake = document.getElementById('d-stake').value;

        if (pOver > 70) {
            this.executeTrade('DIGITOVER', stake);
        } else if (pUnder > 70) {
            this.executeTrade('DIGITUNDER', stake);
        }
    },

    executeTrade(type, stake) {
        this.isTrading = true;
        window.currentModulePrefix = 'd';
        
        this.log(`[ESTRATÉGIA] Probabilidade alta detectada. Entrando ${type}...`, "text-blue-400");

        const params = { 
            barrier: "5", 
            duration: 1,
            duration_unit: 't'
        };

        DerivAPI.buy(type, stake, (res) => {
            if (res.error) {
                this.log(`[ERRO] ${res.error.message}`, "text-red-500");
                this.isTrading = false;
            } else {
                this.log(`[ABERTO] Contrato: ${res.buy.contract_id}`, "text-yellow-500");
            }
        }, params);
    },

    setupCycleListener() {
        const handler = (e) => {
            if (e.detail.prefix === 'd') {
                const profit = e.detail.profit;
                this.currentProfit += profit;
                
                this.stats.total++;
                profit > 0 ? this.stats.wins++ : this.stats.losses++;
                
                this.updateStatsUI(profit);

                // Libera para a próxima operação após delay de segurança
                setTimeout(() => {
                    this.isTrading = false;
                    if (this.isAnalysisRunning) this.log("[SISTEMA] Aguardando nova oportunidade...", "text-gray-500");
                }, 1000);
            }
        };
        document.addEventListener('contract_finished', handler);
    },

    checkLimits() {
        const tp = parseFloat(document.getElementById('d-tp').value);
        const sl = parseFloat(document.getElementById('d-sl').value);

        if (this.currentProfit >= tp) {
            this.log("[META] TAKE PROFIT ATINGIDO!", "text-green-500 font-black");
            this.toggle();
            return true;
        }
        if (this.currentProfit <= (sl * -1)) {
            this.log("[META] STOP LOSS ATINGIDO!", "text-red-500 font-black");
            this.toggle();
            return true;
        }
        return false;
    },

    updateStatsUI(lastProfit) {
        const color = lastProfit >= 0 ? "text-green-500" : "text-red-500";
        this.log(`[RESULTADO] ${lastProfit > 0 ? 'WIN' : 'LOSS'} (${lastProfit.toFixed(2)} USD)`, color);
        
        const profitEl = document.getElementById('d-val-profit');
        if (profitEl) {
            profitEl.innerText = `${this.currentProfit.toFixed(2)} USD`;
            profitEl.className = `text-xl font-black ${this.currentProfit >= 0 ? 'text-green-500' : 'text-red-500'}`;
        }

        document.getElementById('d-stat-w').innerText = this.stats.wins;
        document.getElementById('d-stat-l').innerText = this.stats.losses;
    }
};
