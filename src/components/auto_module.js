const AutoModule = {
    isRunning: false,
    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <h2 class="text-xl font-bold text-purple-500 italic uppercase">Auto Robot</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <input id="a-stake" type="number" value="10.00" class="bg-black p-2 rounded text-xs text-white outline-none">
                    <input id="a-tp" type="number" value="5" class="bg-black p-2 rounded text-xs text-white outline-none">
                    <input id="a-sl" type="number" value="10" class="bg-black p-2 rounded text-xs text-white outline-none">
                </div>
                <button id="btn-a-toggle" onclick="AutoModule.toggle()" class="w-full py-4 bg-purple-600 rounded-xl font-bold uppercase shadow-lg">Iniciar Robô</button>
                <div id="a-status" class="bg-black p-3 rounded-xl h-24 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800">> Robô em stand-by...</div>
                
                <div class="bg-[#1e2329] p-4 rounded-xl border border-gray-800 flex justify-between items-center shadow-2xl">
                    <div class="text-left">
                        <p class="text-[9px] text-gray-500 uppercase font-bold">Preço de compra</p>
                        <p id="a-val-stake" class="text-lg font-bold text-white">0.00 USD</p>
                    </div>
                    <div class="text-right">
                        <p class="text-[9px] text-gray-500 uppercase font-bold">Lucros/perdas totais</p>
                        <p id="a-val-profit" class="text-xl font-black text-gray-600">0.00 USD</p>
                    </div>
                </div>
            </div>`;
    },
    toggle() {
        this.isRunning = !this.isRunning;
        document.getElementById('btn-a-toggle').innerText = this.isRunning ? "PARAR ROBÔ" : "INICIAR ROBÔ";
        document.getElementById('btn-a-toggle').style.backgroundColor = this.isRunning ? "#ef4444" : "#9333ea";
        if(this.isRunning) this.loop();
    },
    async loop() {
        if(!this.isRunning) return;
        const tp = parseFloat(document.getElementById('a-tp').value);
        const sl = parseFloat(document.getElementById('a-sl').value);
        if(app.checkLimits(tp, sl)) { this.isRunning = false; return; }

        const status = document.getElementById('a-status');
        const stake = document.getElementById('a-stake').value;
        status.innerHTML += `<p>> Analisando indicadores...</p>`;
        await new Promise(r => setTimeout(r, 2000));
        
        document.getElementById('a-val-stake').innerText = stake + " USD";
        status.innerHTML += `<p class="text-green-400">> Abrindo contrato CALL...</p>`;
        DerivAPI.buy("CALL", stake);
        
        setTimeout(() => {
            app.updateModuleProfit(parseFloat(stake) * 0.9, 'a');
            this.loop();
        }, 10000);
    }
};
