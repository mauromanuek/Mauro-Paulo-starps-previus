const ManualModule = {
    isAnalyzing: false,
    render() {
        return `
            <div class="flex flex-col gap-4">
                <h2 class="font-bold text-green-500 uppercase">Operação Manual</h2>
                <div class="grid grid-cols-3 gap-2 mb-4">
                    <input type="number" placeholder="Entrada" class="bg-black p-2 rounded border border-gray-700 text-xs">
                    <input type="number" placeholder="T.P" class="bg-black p-2 rounded border border-gray-700 text-xs">
                    <input type="number" placeholder="S.L" class="bg-black p-2 rounded border border-gray-700 text-xs">
                </div>
                
                <button id="btn-man-toggle" onclick="ManualModule.toggle()" class="w-full py-4 bg-blue-600 rounded-xl font-bold mb-4">INICIAR ANÁLISE</button>

                <div class="grid grid-cols-2 gap-4">
                    <button id="btn-call" disabled class="opacity-50 bg-gray-800 p-6 rounded-2xl flex flex-col items-center border-2 border-transparent">
                        <i class="fas fa-arrow-up text-2xl text-green-500"></i>
                        <span class="font-bold mt-2">COMPRAR</span>
                    </button>
                    <button id="btn-put" disabled class="opacity-50 bg-gray-800 p-6 rounded-2xl flex flex-col items-center border-2 border-transparent">
                        <i class="fas fa-arrow-down text-2xl text-red-500"></i>
                        <span class="font-bold mt-2">VENDER</span>
                    </button>
                </div>
                <div id="manual-profit" class="mt-4 text-center font-bold text-xl">$ 0.00</div>
            </div>
        `;
    },
    toggle() {
        const btn = document.getElementById('btn-man-toggle');
        this.isAnalyzing = !this.isAnalyzing;
        if(this.isAnalyzing) {
            btn.innerText = "DESLIGAR ANÁLISE";
            btn.classList.add('btn-active');
            app.notify("Analisando mercado para entrada manual...");
            this.simulateAnalysis();
        } else {
            btn.innerText = "INICIAR ANÁLISE";
            btn.classList.remove('btn-active');
            this.resetButtons();
        }
    },
    simulateAnalysis() {
        // Simulação de análise: Acende um botão aleatoriamente após 2s
        setTimeout(() => {
            if(!this.isAnalyzing) return;
            const side = Math.random() > 0.5 ? 'call' : 'put';
            const target = document.getElementById('btn-' + side);
            this.resetButtons();
            target.disabled = false;
            target.classList.remove('opacity-50', 'bg-gray-800');
            target.classList.add('indicator-glow', side === 'call' ? 'bg-green-600' : 'bg-red-600');
            app.notify("Sinal Detectado: " + side.toUpperCase());
        }, 2000);
    },
    resetButtons() {
        ['btn-call', 'btn-put'].forEach(id => {
            const b = document.getElementById(id);
            b.disabled = true;
            b.className = "opacity-50 bg-gray-800 p-6 rounded-2xl flex flex-col items-center border-2 border-transparent text-white";
        });
    }
};
