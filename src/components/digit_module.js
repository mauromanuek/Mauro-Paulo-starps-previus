const DigitModule = {
    tickBuffer: [],
    maxTicks: 100,
    isAnalysisRunning: false,
    isTrading: false,

    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <h2 class="text-xl font-bold text-yellow-500 italic uppercase">Digit Strategy</h2>
                
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <div><label class="text-[9px] text-gray-500 uppercase">Stake</label><input id="d-stake" type="number" value="10.00" class="w-full bg-black p-2 rounded text-xs text-white outline-none"></div>
                    <div><label class="text-[9px] text-green-500 uppercase">T.Profit</label><input id="d-tp" type="number" value="5" class="w-full bg-black p-2 rounded text-xs text-white outline-none"></div>
                    <div><label class="text-[9px] text-red-500 uppercase">S.Loss</label><input id="d-sl" type="number" value="10" class="w-full bg-black p-2 rounded text-xs text-white outline-none"></div>
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div id="box-over" class="bg-gray-900 p-4 rounded-2xl border-2 border-transparent transition-all text-center">
                        <p class="text-[10px] text-gray-400 uppercase">Digit Over (5)</p>
                        <p id="perc-over" class="text-2xl font-black text-white">0%</p>
                    </div>
                    <div id="box-under" class="bg-gray-900 p-4 rounded-2xl border-2 border-transparent transition-all text-center">
                        <p class="text-[10px] text-gray-400 uppercase">Digit Under (5)</p>
                        <p id="perc-under" class="text-2xl font-black text-white">0%</p>
                    </div>
                </div>

                <button onclick="DigitModule.analyze()" id="btn-d-start" class="w-full py-4 bg-yellow-600 rounded-xl font-bold uppercase shadow-lg">Executar Estratégia</button>
                
                <div id="d-status" class="bg-black p-3 rounded-xl h-24 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800">> Aguardando inicialização de ticks...</div>
                
                <div class="bg-[#1e2329] p-4 rounded-xl border border-gray-800 flex justify-between items-center shadow-2xl">
                    <div class="text-left">
                        <p class="text-[9px] text-gray-500 uppercase font-bold">Preço de compra</p>
                        <p id="d-val-stake" class="text-lg font-bold text-white">0.00 USD</p>
                    </div>
                    <div class="text-right">
                        <p class="text-[9px] text-gray-500 uppercase font-bold">Lucros/perdas totais</p>
                        <p id="d-val-profit" class="text-xl font-black text-gray-600">0.00 USD</p>
                    </div>
                </div>
            </div>`;
    },

    initTickStream() {
        if (this.isAnalysisRunning) return;
        this.isAnalysisRunning = true;
        this.tickInterval = setInterval(() => {
            const lastDigit = Math.floor(Math.random() * 10);
            this.tickBuffer.push(lastDigit);
            if (this.tickBuffer.length > this.maxTicks) this.tickBuffer.shift();
            this.updateProbabilities();
            // PONTO: Verifica entrada a cada novo tick para ser imediato
            this.checkAutoEntry();
        }, 1000);
    },

    updateProbabilities() {
        if (this.tickBuffer.length < 5) return;
        const total = this.tickBuffer.length;
        const overCount = this.tickBuffer.filter(d => d > 5).length;
        const probOver = Math.round((overCount / total) * 100);
        const probUnder = 100 - probOver;

        const pOver = document.getElementById('perc-over');
        const pUnder = document.getElementById('perc-under');
        const bOver = document.getElementById('box-over');
        const bUnder = document.getElementById('box-under');

        if (pOver) {
            pOver.innerText = probOver + "%";
            pUnder.innerText = probUnder + "%";
            bOver.className = `bg-gray-900 p-4 rounded-2xl border-2 transition-all text-center ${probOver > 55 ? 'border-yellow-500 indicator-glow' : 'border-transparent opacity-50'}`;
            bUnder.className = `bg-gray-900 p-4 rounded-2xl border-2 transition-all text-center ${probUnder > 55 ? 'border-blue-500 indicator-glow' : 'border-transparent opacity-50'}`;
        }
        this.currentProbOver = probOver;
        this.currentProbUnder = probUnder;
    },

    checkAutoEntry() {
        if (!this.autoTradeActive || this.isTrading) return;
        const minProb = 58;
        if (this.currentProbOver >= minProb) this.executeTrade("DIGITOVER", document.getElementById('d-stake').value);
        else if (this.currentProbUnder >= minProb) this.executeTrade("DIGITUNDER", document.getElementById('d-stake').value);
    },

    analyze() {
        this.initTickStream();
        this.autoTradeActive = !this.autoTradeActive;
        const btn = document.getElementById('btn-d-start');
        const status = document.getElementById('d-status');
        
        if(this.autoTradeActive) {
            btn.innerText = "PARAR ESTRATÉGIA";
            btn.classList.replace('bg-yellow-600', 'bg-red-600');
            status.innerHTML += `<p class="text-yellow-500">> Robô de Dígitos Ligado...</p>`;
        } else {
            btn.innerText = "EXECUTAR ESTRATÉGIA";
            btn.classList.replace('bg-red-600', 'bg-yellow-600');
            status.innerHTML += `<p class="text-gray-500">> Robô de Dígitos Desligado.</p>`;
        }
    },

    executeTrade(type, stake) {
        this.isTrading = true;
        const status = document.getElementById('d-status');
        document.getElementById('d-val-stake').innerText = stake + " USD";
        
        // PONTO 4: PAYLOAD TÉCNICO COMPLETO (Essencial para funcionar)
        const params = {
            amount: parseFloat(stake),
            basis: 'stake',
            contract_type: type,
            currency: 'USD',
            duration: 1,
            duration_unit: 't',
            symbol: 'R_100', // Volatility 100
            barrier: "5"      // OBRIGATÓRIO para Over/Under 5
        };

        DerivAPI.buy(type, stake, (response) => {
            if (response.buy) {
                status.innerHTML += `<p class="text-green-400">> Ordem ${type} enviada!</p>`;
                this.trackContract(response.buy.contract_id);
            } else {
                this.isTrading = false;
                status.innerHTML += `<p class="text-red-500">> Falha: ${response.error.message}</p>`;
            }
        }, params);
    },

    trackContract(contractId) {
        DerivAPI.subscribeContract(contractId, (contract) => {
            if (contract.is_sold) {
                const profit = parseFloat(contract.profit);
                this.finishTrade(profit > 0, profit);
            }
        });
    },

    finishTrade(win, profit) {
        const status = document.getElementById('d-status');
        const color = win ? "text-green-500" : "text-red-500";
        status.innerHTML += `<p class="${color} font-bold">> DIGIT ${win ? 'WIN' : 'LOSS'} (${profit.toFixed(2)})</p>`;
        app.updateModuleProfit(profit, 'd');
        this.isTrading = false;
    },

    cleanup() {
        if (this.tickInterval) clearInterval(this.tickInterval);
        this.isAnalysisRunning = false;
        this.autoTradeActive = false;
        this.isTrading = false;
        DerivAPI.send({ "forget_all": "proposal_open_contract" });
    }
};
