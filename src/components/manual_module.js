const ManualModule = {
    isRunning: false,

    render() {
        return `
            <div class="flex flex-col gap-6 animate-fadeIn">
                <h2 class="text-xl font-bold text-green-500">OPERAÇÃO MANUAL</h2>
                
                <div class="flex flex-col gap-4">
                    <button onclick="ManualModule.trade('CALL')" class="bg-green-600 hover:bg-green-500 p-6 rounded-2xl flex items-center justify-between px-10 transition-all active:scale-95">
                        <span class="font-bold text-xl text-white">COMPRAR (SUBIDA)</span>
                        <i class="fas fa-arrow-up text-2xl"></i>
                    </button>
                    
                    <button onclick="ManualModule.trade('PUT')" class="bg-red-600 hover:bg-red-500 p-6 rounded-2xl flex items-center justify-between px-10 transition-all active:scale-95">
                        <span class="font-bold text-xl text-white">VENDER (DESCIDA)</span>
                        <i class="fas fa-arrow-down text-2xl"></i>
                    </button>
                </div>

                <button id="btn-manual-toggle" onclick="ManualModule.toggle()" 
                    class="w-full py-4 rounded-xl font-bold border-2 transition-all ${this.isRunning ? 'bg-red-600 border-red-400' : 'bg-transparent border-gray-700 hover:border-green-500'}">
                    ${this.isRunning ? 'PARAR OPERAÇÃO / DESLIGAR' : 'INICIAR OPERAR'}
                </button>
            </div>
        `;
    },

    toggle() {
        this.isRunning = !this.isRunning;
        const btn = document.getElementById('btn-manual-toggle');
        if(this.isRunning) {
            btn.innerText = 'PARAR OPERAÇÃO / DESLIGAR';
            btn.classList.add('bg-red-600');
        } else {
            btn.innerText = 'INICIAR OPERAR';
            btn.classList.remove('bg-red-600');
        }
    },

    trade(type) {
        console.log("Ordem Manual enviada: " + type);
        // Lógica de envio de contrato original
    }
};
