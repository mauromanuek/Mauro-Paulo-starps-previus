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
                    <div id="box-under" class="bg-gray-900 p-4 rounded-2xl border-2 border-transparent text-center text-opacity-40">
                        <p class="text-[10px] text-gray-400 uppercase">Digit Under (5)</p>
                        <p id="perc-under" class="text-2xl font-black text-white">0%</p>
                    </div>
                </div>
                <button id="btn-d-toggle" onclick="DigitModule.analyze()" class="w-full py-4 bg-yellow-600 rounded-xl font-bold uppercase shadow-lg">Analisar & Operar</button>
                <div id="d-status" class="bg-black p-3 rounded-xl h-24 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800">> Aguardando ticks...</div>
                <div class="bg-gray-900 p-4 rounded-xl border border-gray-800">
                    <p class="text-[9px] text-gray-500 uppercase font-bold">Lucro Módulo</p>
                    <p id="d-val-profit" class="text-xl font-black text-gray-600">0.00 USD</p>
                </div>
            </div>`;
    },

    executeTrade(type, stake) {
        if (this.isTrading) return;
        
        this.isTrading = true;
        window.currentModulePrefix = 'd';
        const status = document.getElementById('d-status');
        status.innerHTML += `<p class="text-yellow-400">> [EXECUTANDO] Entrada ${type} com ${stake} USD...</p>`;
        
        const params = { 
            barrier: "5", 
            symbol: "R_100",
            duration: 1,
            duration_unit: 't'
        };

        DerivAPI.buy(type, stake, (res) => {
            if (res.buy) {
                status.innerHTML += `<p class="text-blue-400">> [ABERTO] Contrato ${res.buy.contract_id} em análise...</p>`;
                this.trackContract(res.buy.contract_id);
            } else {
                this.isTrading = false;
                status.innerHTML += `<p class="text-red-500">> [ERRO] ${res.error.message}</p>`;
            }
        }, params);
    },

    trackContract(cid) {
        // Agora o DerivAPI.subscribeContract existe e vai funcionar
        DerivAPI.subscribeContract(cid, (c) => {
            if (c.is_sold) {
                const profit = parseFloat(c.profit);
                const color = profit > 0 ? "text-green-500" : "text-red-500";
                const msg = profit > 0 ? "WIN" : "LOSS";
                
                document.getElementById('d-status').innerHTML += `<p class="${color} font-bold">> [FECHADO] ${msg}: ${profit.toFixed(2)} USD</p>`;
                
                if (window.app) {
                    app.updateModuleProfit(profit, 'd');
                }

                // Pequeno atraso para o próximo ciclo de análise
                setTimeout(() => {
                    this.isTrading = false;
                    document.getElementById('d-status').innerHTML += `<p class="text-gray-500">> Retornando para análise de ticks...</p>`;
                }, 1500);
            }
        });
    },

    analyze() {
        this.isAnalysisRunning = !this.isAnalysisRunning;
        const btn = document.getElementById('btn-d-toggle');
        btn.innerText = this.isAnalysisRunning ? "PARAR ANÁLISE" : "ANALISAR & OPERAR";
        btn.style.backgroundColor = this.isAnalysisRunning ? "#ef4444" : "#ca8a04";

        if (this.isAnalysisRunning) {
            document.getElementById('d-status').innerHTML += `<p class="text-green-400">> [SISTEMA] Iniciando Monitoramento de Ticks...</p>`;
            this.startTickStream();
        }
    },

    startTickStream() {
        if (!DerivAPI.socket) return;
        
        DerivAPI.socket.send(JSON.stringify({
            ticks: "R_100",
            subscribe: 1
        }));

        DerivAPI.socket.addEventListener('message', (msg) => {
            if (!this.isAnalysisRunning) return;
            
            const data = JSON.parse(msg.data);
            if (data.msg_type === 'tick') {
                const quote = data.tick.quote.toString();
                const lastDigit = parseInt(quote.slice(-1));
                
                this.tickBuffer.push(lastDigit);
                if (this.tickBuffer.length > this.maxTicks) this.tickBuffer.shift();
                
                this.updateUI();
                this.checkStrategy();
            }
        });
    },

    updateUI() {
        if (this.tickBuffer.length === 0) return;
        
        const over5 = this.tickBuffer.filter(d => d > 5).length;
        const under5 = this.tickBuffer.filter(d => d < 5).length;
        const total = this.tickBuffer.length;

        const pOver = ((over5 / total) * 100).toFixed(0);
        const pUnder = ((under5 / total) * 100).toFixed(0);

        document.getElementById('perc-over').innerText = pOver + "%";
        document.getElementById('perc-under').innerText = pUnder + "%";

        document.getElementById('box-over').style.borderColor = pOver > 60 ? "#22c55e" : "transparent";
        document.getElementById('box-under').style.borderColor = pUnder > 60 ? "#22c55e" : "transparent";
    },

    checkStrategy() {
        if (this.isTrading || !this.isAnalysisRunning) return;

        const over5 = this.tickBuffer.filter(d => d > 5).length;
        const under5 = this.tickBuffer.filter(d => d < 5).length;
        const total = this.tickBuffer.length;

        if (total < 20) return; // Aguarda dados suficientes

        const pOver = (over5 / total) * 100;
        const pUnder = (under5 / total) * 100;
        const stake = document.getElementById('d-stake').value;

        if (pOver > 70) {
            this.executeTrade('DIGITOVER', stake);
        } else if (pUnder > 70) {
            this.executeTrade('DIGITUNDER', stake);
        }
    }
};
