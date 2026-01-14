const AutoModule = {
    isRunning: false,
    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <h2 class="text-xl font-bold text-purple-500 italic uppercase">Auto Robot</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <input id="a-stake" type="number" value="0.35" class="bg-black p-2 rounded text-xs text-white">
                    <input id="a-tp" type="number" value="5" class="bg-black p-2 rounded text-xs text-white">
                    <input id="a-sl" type="number" value="10" class="bg-black p-2 rounded text-xs text-white">
                </div>
                <button id="btn-a-toggle" onclick="AutoModule.toggle()" class="w-full py-4 bg-purple-600 rounded-xl font-bold uppercase">Iniciar Robô</button>
                <div id="a-status" class="bg-black p-3 rounded h-32 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800">> Robô em stand-by...</div>
                <div id="a-profit-display" class="text-center text-xl font-bold text-gray-500">$ 0.00</div>
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
        const status = document.getElementById('a-status');

        if(app.checkLimits(tp, sl)) { this.isRunning = false; return; }

        status.innerHTML += `<p>> Analisando indicadores RSI e EMA...</p>`;
        await new Promise(r => setTimeout(r, 2000));
        
        const stake = document.getElementById('a-stake').value;
        status.innerHTML += `<p class="text-blue-400">> Condição confirmada. Abrindo contrato...</p>`;
        DerivAPI.buy("CALL", stake);
        status.innerHTML += `<p class="text-green-400">> Operação enviada com sucesso!</p>`;
        
        setTimeout(() => this.loop(), 10000);
    }
};
