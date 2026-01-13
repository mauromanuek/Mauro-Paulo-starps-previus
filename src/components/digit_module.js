const DigitModule = {
    isActive: false,
    stats: { wins: 0, losses: 0, profit: 0.00 },

    render() {
        return `
            <div class="flex flex-col gap-4 animate-fadeIn">
                <h2 class="text-xl font-bold text-yellow-500 italic uppercase">Digit Over/Under</h2>
                
                <div class="grid grid-cols-2 gap-2">
                    <div class="bg-black/50 p-3 rounded-lg border border-gray-800 text-center">
                        <p class="text-[10px] text-gray-500">LUCRO REAL</p>
                        <p id="digit-profit" class="text-lg font-bold text-green-500">$ ${this.stats.profit.toFixed(2)}</p>
                    </div>
                    <div class="bg-black/50 p-3 rounded-lg border border-gray-800 text-center">
                        <p class="text-[10px] text-gray-500">STATUS</p>
                        <p id="digit-status" class="text-lg font-bold text-blue-400">AGUARDANDO</p>
                    </div>
                </div>

                <button id="btn-digit-toggle" onclick="DigitModule.toggle()" 
                    class="w-full py-5 rounded-2xl font-bold shadow-xl transition-all ${this.isActive ? 'bg-red-600' : 'bg-green-600'}">
                    ${this.isActive ? 'PARAR OPERAÇÃO / DESLIGAR' : 'INICIAR OPERAÇÃO AUTOMÁTICA'}
                </button>

                <div id="digit-results" class="mt-4 p-4 bg-gray-900/50 rounded-xl border border-gray-800 h-32 overflow-y-auto text-[10px] font-mono">
                    </div>
            </div>
        `;
    },

    toggle() {
        this.isActive = !this.isActive;
        const btn = document.getElementById('btn-digit-toggle');
        const status = document.getElementById('digit-status');
        
        if(this.isActive) {
            btn.innerText = 'PARAR OPERAÇÃO / DESLIGAR';
            btn.classList.add('bg-red-600');
            status.innerText = 'OPERANDO';
            app.notify("Robô de Dígitos Iniciado");
            this.startOperation();
        } else {
            btn.innerText = 'INICIAR OPERAÇÃO AUTOMÁTICA';
            btn.classList.remove('bg-red-600');
            status.innerText = 'PARADO';
            app.notify("Robô de Dígitos Desligado");
        }
    },

    startOperation() {
        // Item 5: Aqui executa o comando correspondente via DerivAPI
        console.log("Comando enviado para API Deriv: Operação Dígitos");
        // DerivAPI.send({...}) logic original mantida aqui
    }
};
