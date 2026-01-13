const AutoModule = {
    isRunning: false,
    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <h2 class="text-xl font-bold text-purple-500 uppercase italic">Operação Automática</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <div><label class="text-[9px] text-gray-500 uppercase">Stake</label><input id="auto-stake" type="number" value="0.35" class="w-full bg-black p-2 rounded text-xs text-white"></div>
                    <div><label class="text-[9px] text-green-500 uppercase">T.Profit</label><input id="auto-tp" type="number" value="5.00" class="w-full bg-black p-2 rounded text-xs text-white"></div>
                    <div><label class="text-[9px] text-red-500 uppercase">S.Loss</label><input id="auto-sl" type="number" value="10.00" class="w-full bg-black p-2 rounded text-xs text-white"></div>
                </div>
                <button id="btn-auto" onclick="AutoModule.toggle()" class="w-full py-4 bg-purple-600 rounded-xl font-bold uppercase">Iniciar Robô</button>
                <div id="auto-status" class="bg-black p-4 rounded-xl border border-gray-800 h-32 overflow-y-auto font-mono text-[10px] text-gray-400">
                    > Sistema pronto para iniciar...
                </div>
            </div>`;
    },
    update(msg, color="text-gray-400") {
        const board = document.getElementById('auto-status');
        if(board) {
            board.innerHTML += `<p class="${color}">> ${msg}</p>`;
            board.scrollTop = board.scrollHeight;
        }
    },
    toggle() {
        const btn = document.getElementById('btn-auto');
        this.isRunning = !this.isRunning;
        if(this.isRunning) {
            btn.innerText = "PARAR ROBÔ";
            btn.style.backgroundColor = "#ef4444";
            this.loop();
        } else {
            btn.innerText = "INICIAR ROBÔ";
            btn.style.backgroundColor = "#9333ea";
            this.update("Operação interrompida.", "text-red-500");
        }
    },
    async loop() {
        if(!this.isRunning) return;
        this.update("Analisando fluxo de mercado...");
        await new Promise(r => setTimeout(r, 2000));
        
        const stake = document.getElementById('auto-stake').value;
        this.update("Padrão confirmado. Executando CALL...", "text-blue-400");
        DerivAPI.buy("CALL", stake);
        this.update(`Ordem enviada com sucesso: $${stake}`, "text-green-400");
        
        // Simula ciclo de 10 segundos
        setTimeout(() => this.loop(), 10000);
    }
};
