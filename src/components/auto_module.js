const AutoModule = {
    isRunning: false,

    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <h2 class="text-xl font-bold text-purple-500 italic uppercase">Auto Robot</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <div>
                        <label class="text-[9px] text-gray-500 font-bold">STAKE</label>
                        <input id="a-stake" type="number" value="10.00" class="w-full bg-black p-2 rounded text-xs text-white">
                    </div>
                    <div>
                        <label class="text-[9px] text-green-500 font-bold">TP</label>
                        <input id="a-tp" type="number" value="5" class="w-full bg-black p-2 rounded text-xs text-white">
                    </div>
                    <div>
                        <label class="text-[9px] text-red-500 font-bold">SL</label>
                        <input id="a-sl" type="number" value="10" class="w-full bg-black p-2 rounded text-xs text-white">
                    </div>
                </div>
                <button id="btn-a-toggle" onclick="AutoModule.toggle()" class="w-full py-4 bg-purple-600 rounded-xl font-bold uppercase">Iniciar Robô</button>
                <div id="a-status" class="bg-black p-3 rounded-xl h-24 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800">> Robô pronto...</div>
                <div class="bg-gray-900 p-4 rounded-xl border border-gray-800">
                    <p class="text-[9px] text-gray-500 uppercase font-bold">Lucro Módulo</p>
                    <p id="a-val-profit" class="text-xl font-black text-gray-600">0.00 USD</p>
                </div>
            </div>`;
    },

    toggle() {
        this.isRunning = !this.isRunning;
        const btn = document.getElementById('btn-a-toggle');
        btn.innerText = this.isRunning ? "PARAR ROBÔ" : "INICIAR ROBÔ";
        btn.style.backgroundColor = this.isRunning ? "#ef4444" : "#9333ea";
        if (this.isRunning) this.loop();
    },

    loop() {
        if (!this.isRunning) return;
        window.currentModulePrefix = 'a';
        const stake = document.getElementById('a-stake').value;
        const side = Math.random() > 0.5 ? "CALL" : "PUT";
        
        DerivAPI.buy(side, stake, (res) => {
            if (res.buy) {
                const check = setInterval(() => {
                    if (document.querySelector('[data-finished]')) {
                        clearInterval(check);
                        setTimeout(() => this.loop(), 2000);
                    }
                }, 1000);
            } else {
                this.toggle();
            }
        });
    }
};
