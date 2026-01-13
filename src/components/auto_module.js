const AutoModule = {
    isRunning: false,
    render() {
        return `
            <div class="animate-fadeIn space-y-4">
                <h2 class="text-xl font-bold text-purple-500 uppercase italic">Robô Automático</h2>
                
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <div><label class="text-[9px] text-gray-500">STAKE</label><input id="auto-stake" type="number" value="0.35" class="w-full bg-black p-2 rounded text-xs text-white"></div>
                    <div><label class="text-[9px] text-green-500">T.P</label><input id="auto-tp" type="number" value="5.00" class="w-full bg-black p-2 rounded text-xs text-white"></div>
                    <div><label class="text-[9px] text-red-500">S.L</label><input id="auto-sl" type="number" value="10.00" class="w-full bg-black p-2 rounded text-xs text-white"></div>
                </div>

                <div class="grid grid-cols-2 gap-4 text-center bg-black/40 p-4 rounded-xl border border-gray-800 font-mono">
                    <div class="text-green-500"><p class="text-[9px] text-gray-500">LUCRO</p>$ 0.00</div>
                    <div class="text-red-500"><p class="text-[9px] text-gray-500">PERDA</p>$ 0.00</div>
                </div>

                <button id="btn-auto" onclick="AutoModule.toggle()" class="w-full py-4 bg-purple-600 rounded-2xl font-bold shadow-lg">INICIAR ROBÔ</button>

                <div class="bg-black p-4 rounded-xl border border-gray-800">
                    <p class="text-[10px] text-purple-400 font-bold mb-2 tracking-widest uppercase">Quadro de Status</p>
                    <div id="status-board" class="h-32 overflow-y-auto text-[11px] font-mono text-gray-400 space-y-1">
                        <p class="text-gray-600">> Aguardando inicialização...</p>
                    </div>
                </div>
            </div>`;
    },
    updateStatus(msg) {
        const board = document.getElementById('status-board');
        board.innerHTML += `<p class="text-blue-300 animate-pulse">> ${msg}</p>`;
        board.scrollTop = board.scrollHeight;
    },
    toggle() {
        const btn = document.getElementById('btn-auto');
        this.isRunning = !this.isRunning;
        if(this.isRunning) {
            btn.innerText = "PARAR ROBÔ"; btn.classList.add('bg-red-600');
            this.loop();
        } else {
            btn.innerText = "INICIAR ROBÔ"; btn.classList.remove('bg-red-600');
            this.updateStatus("Bot desligado.");
        }
    },
    async loop() {
        if(!this.isRunning) return;
        this.updateStatus("Analisando tendência de mercado...");
        await new Promise(r => setTimeout(r, 2000));
        this.updateStatus("Verificando Suporte/Resistência...");
        await new Promise(r => setTimeout(r, 1500));
        this.updateStatus("Entrada executada: CALL ($0.35)");
        DerivAPI.buy("CALL", document.getElementById('auto-stake').value);
        setTimeout(() => this.loop(), 8000);
    }
};
