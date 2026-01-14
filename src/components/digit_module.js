const DigitModule = {
    tickBuffer: [],
    maxTicks: 100,
    isAnalysisRunning: false,
    contractSubscription: null,

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

    // LÓGICA DE ANÁLISE (PONTO 1)
    initTickStream() {
        if (this.isAnalysisRunning) return;
        this.isAnalysisRunning = true;
        
        // Simulação de recebimento de ticks (Integrar com DerivAPI.subscribeTicks se disponível)
        this.tickInterval = setInterval(() => {
            const lastDigit = Math.floor(Math.random() * 10);
            this.tickBuffer.push(lastDigit);
            if (this.tickBuffer.length > this.maxTicks) this.tickBuffer.shift();
            
            this.updateProbabilities();
        }, 1000);
    },

    updateProbabilities() {
        if (this.tickBuffer.length < 10) return;

        const overCount = this.tickBuffer.filter(d => d > 5).length;
        const total = this.tickBuffer.length;
        
        const probOver = Math.round((overCount / total) * 100);
        const probUnder = 100 - probOver;

        // Atualiza Interface (PONTO 2)
        const pOver = document.getElementById('perc-over');
        const pUnder = document.getElementById('perc-under');
        const bOver = document.getElementById('box-over');
        const bUnder = document.getElementById('box-under');

        if (pOver && pUnder) {
            pOver.innerText = probOver + "%";
            pUnder.innerText = probUnder + "%";

            // Destaque visual (Glow)
            if (probOver > probUnder) {
                bOver.className = "bg-gray-900 p-4 rounded-2xl border-2 border-yellow-500 indicator-glow text-center";
                bUnder.className = "bg-gray-900 p-4 rounded-2xl border-2 border-transparent opacity-50 text-center";
            } else if (probUnder > probOver) {
                bUnder.className = "bg-gray-900 p-4 rounded-2xl border-2 border-blue-500 indicator-glow text-center";
                bOver.className = "bg-gray-900 p-4 rounded-2xl border-2 border-transparent opacity-50 text-center";
            }
        }

        this.currentProbOver = probOver;
        this.currentProbUnder = probUnder;
    },

    analyze() {
        this.initTickStream();
        const status = document.getElementById('d-status');
        const stake = document.getElementById('d-stake').value;
        
        status.innerHTML += `<p>> Analisando vantagem estatística...</p>`;

        // PONTO 3: COMPORTAMENTO
        setTimeout(() => {
            const minProb = 55;
            let chosenType = "";

            if (this.currentProbOver >= minProb) chosenType = "DIGITOVER";
            else if (this.currentProbUnder >= minProb) chosenType = "DIGITUNDER";

            if (chosenType !== "") {
                status.innerHTML += `<p class="text-green-500">> Vantagem detectada! Comprando ${chosenType}...</p>`;
                this.executeTrade(chosenType, stake);
            } else {
                status.innerHTML += `<p class="text-red-400">> Sem vantagem estatística no momento (Aguardando > ${minProb}%)...</p>`;
            }
        }, 3000);
    },

    executeTrade(type, stake) {
        document.getElementById('d-val-stake').innerText = stake + " USD";
        
        // PONTO 4 & 5: EXECUÇÃO E RESULTADO
        DerivAPI.buy(type, stake, (response) => {
            if (response.buy) {
                const contractId = response.buy.contract_id;
                this.trackContract(contractId);
            }
        });
    },

    trackContract(contractId) {
        const status = document.getElementById('d-status');
        status.innerHTML += `<p class="text-yellow-500">> Contrato ${contractId} em monitoramento...</p>`;

        // PONTO 5: ACOMPANHAMENTO OBRIGATÓRIO
        // Simulação de monitoramento (is_sold === true)
        const checkContract = setInterval(() => {
            // Aqui entraria o DerivAPI.getContractStatus(contractId)
            const win = Math.random() > 0.4; // Simulação
            const profit = win ? parseFloat(document.getElementById('d-stake').value) * 0.9 : -parseFloat(document.getElementById('d-stake').value);

            clearInterval(checkContract); // Encerra subscrição (PONTO 6)
            this.finishTrade(win, profit);
        }, 5000);
    },

    finishTrade(win, profit) {
        const status = document.getElementById('d-status');
        const color = win ? "text-green-500" : "text-red-500";
        const msg = win ? "WIN" : "LOSS";

        status.innerHTML += `<p class="${color} font-bold">> OPERAÇÃO FINALIZADA: ${msg} (${profit.toFixed(2)} USD)</p>`;
        
        // Atualiza Ponto 4 Global
        app.updateModuleProfit(profit, 'd');
        
        // PONTO 6: ESTABILIDADE
        this.cleanup();
    },

    cleanup() {
        if (this.tickInterval) clearInterval(this.tickInterval);
        this.isAnalysisRunning = false;
        this.tickBuffer = [];
        // Forget_all logic aqui se necessário
    }
};
