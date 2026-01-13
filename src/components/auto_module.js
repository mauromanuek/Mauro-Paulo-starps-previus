const AutoModule = {
    isRunning: false,
    render() {
        return `
            <div id="panel-auto" class="flex flex-col gap-4 animate-fadeIn">
                <h2 class="text-xl font-bold text-purple-500 uppercase italic">Operação Automática</h2>
                <div class="bg-gray-900 p-4 rounded-xl border border-gray-800 space-y-3 shadow-inner">
                    <label class="text-[10px] text-gray-500 uppercase font-bold">Valor da Entrada (Stake)</label>
                    <input id="auto-stake" type="number" value="0.35" class="w-full bg-black border border-gray-700 p-3 rounded text-white font-mono">
                    <button id="btn-auto-toggle" onclick="AutoModule.toggle()" class="w-full py-4 bg-purple-600 rounded-xl font-bold transition-all hover:bg-purple-500">
                        INICIAR OPERAÇÃO
                    </button>
                </div>
                <div id="auto-status" class="text-center text-[10px] text-gray-600 italic">Robô pausado.</div>
            </div>`;
    },
    toggle() {
        const btn = document.getElementById('btn-auto-toggle');
        this.isRunning = !this.isRunning;
        if(this.isRunning) {
            btn.innerText = "DESLIGAR OPERAÇÃO";
            btn.style.backgroundColor = "#ef4444";
            document.getElementById('auto-status').innerText = "ROBÔ OPERANDO...";
            this.loop();
        } else {
            btn.innerText = "INICIAR OPERAÇÃO";
            btn.style.backgroundColor = "#9333ea";
            document.getElementById('auto-status').innerText = "Robô pausado.";
        }
    },
    loop() {
        if(!this.isRunning) return;
        const stake = document.getElementById('auto-stake').value;
        DerivAPI.buy("CALL", stake); // Exemplo de estratégia automática
        setTimeout(() => this.loop(), 10000); // Tenta a cada 10s
    }
};
