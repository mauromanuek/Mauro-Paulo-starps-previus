const DigitModule = {
    tickBuffer: [],
    maxTicks: 50,
    isAnalysisRunning: false,
    isTrading: false,
    currentProfit: 0,
    stats: { wins: 0, losses: 0 },
    _tickListener: null,

    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <h2 class="text-xl font-bold text-yellow-500 italic uppercase">Digit Strategy</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <div>
                        <label class="text-[9px] text-gray-500 uppercase font-bold">Stake</label>
                        <input id="d-stake" type="number" value="1.00" class="w-full bg-black p-2 rounded text-xs text-white outline-none">
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
                    <div id="box-over" class="bg-gray-900 p-4 rounded-2xl border-2 border-transparent text-center">
                        <p class="text-[10px] text-gray-400 uppercase">Digit Over (5)</p>
                        <p id="perc-over" class="text-2xl font-black text-white">0%</p>
                    </div>
                    <div id="box-under" class="bg-gray-900 p-4 rounded-2xl border-2 border-transparent text-center">
                        <p class="text-[10px] text-gray-400 uppercase">Digit Under (5)</p>
                        <p id="perc-under" class="text-2xl font-black text-white">0%</p>
                    </div>
                </div>
                <button id="btn-d-toggle" onclick="DigitModule.analyze()" class="w-full py-4 bg-yellow-600 rounded-xl font-bold uppercase shadow-lg">Analisar & Operar</button>
                <div id="d-status" class="bg-black p-3 rounded-xl h-24 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800 shadow-inner">> Aguardando ticks...</div>
                <div class="bg-gray-900 p-4 rounded-xl border border-gray-800 flex justify-between items-center">
                    <div>
                        <p class="text-[9px] text-gray-500 uppercase font-bold">Lucro Módulo</p>
                        <p id="d-val-profit" class="text-xl font-black text-gray-600">0.00 USD</p>
                    </div>
                    <div class="text-[10px] font-bold">
                        <p class="text-green-500">W: <span id="d-stat-w">0</span></p>
                        <p class="text-red-500">L: <span id="d-stat-l">0</span></p>
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

    analyze() {
        this.isAnalysisRunning = !this.isAnalysisRunning;
        const btn = document.getElementById('btn-d-toggle');
        
        if (this.isAnalysisRunning) {
            btn.innerText = "PARAR OPERAÇÃO";
            btn.style.backgroundColor = "#ef4444";
            this.log("[SISTEMA] Estratégia ativa. Monitorando mercado...", "text-green-400");
            this.startTickStream();
            this.setupContractListener();
        } else {
            btn.innerText = "ANALISAR & OPERAR";
            btn.style.backgroundColor = "#ca8a04";
            this.isTrading = false;
            this.log("[SISTEMA] Estratégia pausada.", "text-yellow-600");
        }
    },

    startTickStream() {
        if (!DerivAPI.socket) return;
        if (this._tickListener) DerivAPI.socket.removeEventListener('message', this._tickListener);

        DerivAPI.socket.send(JSON.stringify({ ticks: "R_100", subscribe: 1 }));

        this._tickListener = (msg) => {
            if (!this.isAnalysisRunning) return;
            const data = JSON.parse(msg.data);
            if (data.msg_type === 'tick') {
                const lastDigit = parseInt(data.tick.quote.toString().slice(-1));
                this.tickBuffer.push(lastDigit);
                if (this.tickBuffer.length > this.maxTicks) this.tickBuffer.shift();
                this.updateUI();
                this.checkStrategy();
            }
        };
        DerivAPI.socket.addEventListener('message', this._tickListener);
    },

    updateUI() {
        const total = this.tickBuffer.length;
        if (total === 0) return;
        const over5 = this.tickBuffer.filter(d => d > 5).length;
        const under5 = this.tickBuffer.filter(d => d < 5).length;
        const pOver = Math.round((over5 / total) * 100);
        const pUnder = Math.round((under5 / total) * 100);

        document.getElementById('perc-over').innerText = pOver + "%";
        document.getElementById('perc-under').innerText = pUnder + "%";
        document.getElementById('box-over').className = `bg-gray-900 p-4 rounded-2xl border-2 text-center transition-all ${pOver >= 70 ? 'border-green-500 shadow-[0_0_10px_#22c55e]' : 'border-transparent'}`;
        document.getElementById('box-under').className = `bg-gray-900 p-4 rounded-2xl border-2 text-center transition-all ${pUnder >= 70 ? 'border-green-500 shadow-[0_0_10px_#22c55e]' : 'border-transparent'}`;
    },

    checkStrategy() {
        if (this.isTrading || !this.isAnalysisRunning || this.tickBuffer.length < 10) return;

        const tp = parseFloat(document.getElementById('d-tp').value);
        const sl = parseFloat(document.getElementById('d-sl').value);

        if (this.currentProfit >= tp || this.currentProfit <= (sl * -1)) {
            this.log("[SISTEMA] Meta de gerenciamento atingida.", "text-blue-500 font-bold");
            this.analyze();
            return;
        }

        const total = this.tickBuffer.length;
        const pOver = (this.tickBuffer.filter(d => d > 5).length / total) * 100;
        const pUnder = (this.tickBuffer.filter(d => d < 5).length / total) * 100;
        const stake = document.getElementById('d-stake').value;

        if (pOver >= 70) this.executeTrade('DIGITOVER', stake);
        else if (pUnder >= 70) this.executeTrade('DIGITUNDER', stake);
    },

    executeTrade(type, stake) {
        this.isTrading = true;
        window.currentModulePrefix = 'd';
        
        // LOGS PADRONIZADOS
        this.log(`[ANALISADO] Chance detectada, enviando ordem...`, "text-yellow-500");

        const params = { barrier: "5", duration: 1, duration_unit: 't', symbol: "R_100" };

        DerivAPI.buy(type, stake, (res) => {
            if (res.buy) {
                this.log(`[ABERTO] Contrato ID: ${res.buy.contract_id}`, "text-blue-400 font-bold");
            } else if (res.error) {
                this.log(`[ERRO] ${res.error.message}`, "text-red-500");
                this.isTrading = false;
            }
        }, params);
    },

    setupContractListener() {
        if (this._contractHandler) document.removeEventListener('contract_finished', this._contractHandler);
        
        this._contractHandler = (e) => {
            if (e.detail.prefix === 'd') {
                const profit = parseFloat(e.detail.profit);
                this.currentProfit += profit;
                
                profit > 0 ? this.stats.wins++ : this.stats.losses++;
                document.getElementById('d-stat-w').innerText = this.stats.wins;
                document.getElementById('d-stat-l').innerText = this.stats.losses;
                
                const profitEl = document.getElementById('d-val-profit');
                profitEl.innerText = (this.currentProfit >= 0 ? "+" : "") + this.currentProfit.toFixed(2) + " USD";
                profitEl.className = `text-xl font-black ${this.currentProfit >= 0 ? 'text-green-500' : 'text-red-500'}`;

                // LOGS DE RESULTADO IGUAIS AOS OUTROS MÓDULOS
                const resultColor = profit > 0 ? "text-green-500" : "text-red-500";
                this.log(`[FECHADO] Resultado: ${profit > 0 ? 'WIN' : 'LOSS'} (${profit.toFixed(2)} USD)`, resultColor);
                
                setTimeout(() => {
                    this.isTrading = false;
                    if(this.isAnalysisRunning) this.log("[STATUS] Aguardando nova oportunidade...", "text-gray-500");
                }, 2000);
            }
        };
        document.addEventListener('contract_finished', this._contractHandler);
    }
};
