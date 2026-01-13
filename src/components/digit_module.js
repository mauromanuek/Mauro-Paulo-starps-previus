const DigitModule = {
    isAnalyzing: false,
    wins: 0,
    losses: 0,
    profit: 0.00,

    render() {
        return `
            <div class="flex flex-col gap-4 animate-fadeIn">
                <h2 class="text-xl font-bold text-yellow-500 italic">DIGITS OVER/UNDER</h2>
                
                <div class="grid grid-cols-2 gap-2">
                    <div class="bg-black/40 p-3 rounded-lg border border-gray-800">
                        <p class="text-[10px] text-gray-500 uppercase">Lucro Real</p>
                        <p id="digit-profit-val" class="text-lg font-bold text-green-500">$ ${this.profit.toFixed(2)}</p>
                    </div>
                    <div class="bg-black/40 p-3 rounded-lg border border-gray-800">
                        <p class="text-[10px] text-gray-500 uppercase">Resultado</p>
                        <p class="text-lg font-bold text-blue-400">${this.wins}W - ${this.losses}L</p>
                    </div>
                </div>

                <button id="btn-digit-toggle" onclick="DigitModule.toggleAnalysis()" 
                    class="w-full py-4 rounded-xl font-bold text-white transition-all shadow-lg ${this.isAnalyzing ? 'bg-red-600' : 'bg-green-600'}">
                    ${this.isAnalyzing ? 'PARAR OPERAÇÃO / DESLIGAR' : 'INICIAR ANÁLISE'}
                </button>

                <div id="digit-stats" class="grid grid-cols-5 gap-1 mt-2 text-center font-mono">
                    </div>
            </div>
        `;
    },

    toggleAnalysis() {
        this.isAnalyzing = !this.isAnalyzing;
        const btn = document.getElementById('btn-digit-toggle');
        
        if(this.isAnalyzing) {
            btn.innerText = 'PARAR OPERAÇÃO / DESLIGAR';
            btn.classList.replace('bg-green-600', 'bg-red-600');
            this.startLoop();
        } else {
            btn.innerText = 'INICIAR ANÁLISE';
            btn.classList.replace('bg-red-600', 'bg-green-600');
            this.stopLoop();
        }
    },

    startLoop() {
        console.log("Análise de Digits Iniciada...");
        // Mantém sua lógica original de análise aqui
    },

    stopLoop() {
        console.log("Análise de Digits Parada.");
    },

    updateProfit(val) {
        this.profit += val;
        const display = document.getElementById('digit-profit-val');
        if(display) {
            display.innerText = `$ ${this.profit.toFixed(2)}`;
            display.className = `text-lg font-bold ${this.profit >= 0 ? 'text-green-500' : 'text-red-500'}`;
        }
    }
};
