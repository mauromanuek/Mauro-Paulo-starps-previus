const DigitModule = {
    tickBuffer: [],
    maxTicks: 100,
    isAnalysisRunning: false,
    isTrading: false,
    currentProfit: 0,

    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <h2 class="text-xl font-bold text-yellow-500 italic uppercase">Digit Strategy</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <input id="d-stake" type="number" value="10.00" class="bg-black p-2 rounded text-xs text-white outline-none">
                    <input id="d-tp" type="number" value="5" class="bg-black p-2 rounded text-xs text-white outline-none">
                    <input id="d-sl" type="number" value="10" class="bg-black p-2 rounded text-xs text-white outline-none">
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
                <button onclick="DigitModule.analyze()" id="btn-d-start" class="w-full py-4 bg-yellow-600 rounded-xl font-bold uppercase shadow-lg">Executar Estratégia</button>
                <div id="d-status" class="bg-black p-3 rounded-xl h-24 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800">> Aguardando ticks...</div>
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
            if (this.autoTradeActive) this.checkAutoEntry();
        }, 1000);
    },

    updateProbabilities() {
        const overCount = this.tickBuffer.filter(d => d > 5).length;
        this.currentProbOver = Math.round((overCount / this.tickBuffer.length) * 100);
        this.currentProbUnder = 100 - this.currentProbOver;
        document.getElementById('perc-over').innerText = this.currentProbOver + "%";
        document.getElementById('perc-under').innerText = this.currentProbUnder + "%";
    },

    checkAutoEntry() {
        if (this.isTrading) return;
        const stake = document.getElementById('d-stake').value;
        if (this.currentProbOver >= 60) this.executeTrade("DIGITOVER", stake);
        else if (this.currentProbUnder >= 60) this.executeTrade("DIGITUNDER", stake);
    },

    executeTrade(type, stake) {
        this.isTrading = true;
        const status = document.getElementById('d-status');
        status.innerHTML += `<p class="text-yellow-400">> Entrada de ${stake} USD em ${type}...</p>`;
        
        // PARÂMETROS CRÍTICOS PARA O CONTRATO ABRIR
        const params = { barrier: "5", symbol: "R_100" };

        DerivAPI.buy(type, stake, (res) => {
            if (res.buy) {
                status.innerHTML += `<p class="text-green-400">> Contrato ${res.buy.contract_id} aberto.</p>`;
                this.trackContract(res.buy.contract_id);
            } else {
                this.isTrading = false;
                status.innerHTML += `<p class="text-red-500">> Erro: ${res.error.message}</p>`;
            }
        }, params);
    },

    trackContract(cid) {
        DerivAPI.subscribeContract(cid, (c) => {
            if (c.is_sold) {
                const profit = parseFloat(c.profit);
                const color = profit > 0 ? "text-green-500" : "text-red-500";
                document.getElementById('d-status').innerHTML += `<p class="${color} font-bold">> RESULTADO: ${profit.toFixed(2)} USD</p>`;
                app.updateModuleProfit(profit, 'd');
                this.isTrading = false;
            }
        });
    },

    analyze() {
        this.initTickStream();
        this.autoTradeActive = !this.autoTradeActive;
        document.getElementById('btn-d-start').innerText = this.autoTradeActive ? "PARAR" : "INICIAR";
    }
};
