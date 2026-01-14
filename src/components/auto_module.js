const AutoModule = {
    isRunning: false,
    currentProfit: 0,
    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <h2 class="text-xl font-bold text-purple-500 italic uppercase">Auto Robot</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <div><label class="text-[9px] text-gray-500 uppercase">Stake</label><input id="a-stake" type="number" value="10.00" class="w-full bg-black p-2 rounded text-xs text-white outline-none"></div>
                    <div><label class="text-[9px] text-green-500 uppercase">T.Profit</label><input id="a-tp" type="number" value="5" class="w-full bg-black p-2 rounded text-xs text-white outline-none"></div>
                    <div><label class="text-[9px] text-red-500 uppercase">S.Loss</label><input id="a-sl" type="number" value="10" class="w-full bg-black p-2 rounded text-xs text-white outline-none"></div>
                </div>
                <button id="btn-a-toggle" onclick="AutoModule.toggle()" class="w-full py-4 bg-purple-600 rounded-xl font-bold uppercase shadow-lg">Iniciar Robô</button>
                <div id="a-status" class="bg-black p-3 rounded-xl h-24 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800">> Robô em stand-by...</div>
                
                <div class="bg-[#1e2329] p-4 rounded-xl border border-gray-800 flex justify-between items-center shadow-2xl">
                    <div class="text-left"><p class="text-[9px] text-gray-500 uppercase font-bold">Última Entrada</p><p id="a-val-stake" class="text-lg font-bold text-white">0.00 USD</p></div>
                    <div class="text-right"><p class="text-[9px] text-gray-500 uppercase font-bold">Lucro Acumulado</p><p id="a-val-profit" class="text-xl font-black text-gray-600">0.00 USD</p></div>
                </div>
            </div>`;
    },
    toggle() {
        this.isRunning = !this.isRunning;
        const btn = document.getElementById('btn-a-toggle');
        btn.innerText = this.isRunning ? "PARAR ROBÔ" : "INICIAR ROBÔ";
        btn.style.backgroundColor = this.isRunning ? "#ef4444" : "#9333ea";
        if(this.isRunning) {
            document.getElementById('a-status').innerHTML += `<p class="text-green-500">> Robô Iniciado...</p>`;
            this.loop();
        }
    },
    async loop() {
        if(!this.isRunning) return;
        
        const status = document.getElementById('a-status');
        const tp = parseFloat(document.getElementById('a-tp').value);
        const sl = parseFloat(document.getElementById('a-sl').value);
        const stake = document.getElementById('a-stake').value;

        // Verifica Limites (Take Profit / Stop Loss)
        if (this.currentProfit >= tp) {
            status.innerHTML += `<p class="text-green-400 font-bold">> META ATINGIDA: +${this.currentProfit.toFixed(2)} USD</p>`;
            this.toggle(); return;
        }
        if (this.currentProfit <= (sl * -1)) {
            status.innerHTML += `<p class="text-red-400 font-bold">> STOP LOSS ATINGIDO: ${this.currentProfit.toFixed(2)} USD</p>`;
            this.toggle(); return;
        }

        const side = Math.random() > 0.5 ? "CALL" : "PUT";
        document.getElementById('a-val-stake').innerText = stake + " USD";
        status.innerHTML += `<p class="text-purple-400">> Entrada de ${stake} USD em ${side}...</p>`;
        
        DerivAPI.buy(side, stake, (res) => {
            if(res.buy) {
                status.innerHTML += `<p class="text-blue-400">> Contrato ID: ${res.buy.contract_id} aberto.</p>`;
                // Aguarda o resultado real vindo do WebSocket
                this.waitForResult(res.buy.contract_id);
            } else {
                status.innerHTML += `<p class="text-red-500">> Erro API: ${res.error.message}</p>`;
                this.toggle();
            }
        });
    },
    waitForResult(cid) {
        // O resultado será processado pela DerivAPI e chamará o updateModuleProfit
        // Este loop apenas controla o intervalo entre operações
        const check = setInterval(() => {
            if (document.querySelector(`[data-finished="${cid}"]`)) {
                clearInterval(check);
                setTimeout(() => this.loop(), 2000);
            }
        }, 1000);
    }
};
