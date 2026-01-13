const ManualModule = {
    isWorking: false,

    render() {
        return `
            <div class="flex flex-col gap-6">
                <h2 class="text-xl font-bold text-green-500 uppercase italic">Operação Manual</h2>
                
                <div class="flex flex-col gap-4">
                    <button onclick="ManualModule.execute('CALL')" class="group bg-green-600/20 border-2 border-green-600 p-6 rounded-2xl flex items-center justify-between hover:bg-green-600 transition-all">
                        <span class="font-bold text-xl text-green-500 group-hover:text-white uppercase">Comprar (Subida)</span>
                        <i class="fas fa-arrow-up text-2xl text-green-500 group-hover:text-white"></i>
                    </button>
                    
                    <button onclick="ManualModule.execute('PUT')" class="group bg-red-600/20 border-2 border-red-600 p-6 rounded-2xl flex items-center justify-between hover:bg-red-600 transition-all">
                        <span class="font-bold text-xl text-red-500 group-hover:text-white uppercase">Vender (Descida)</span>
                        <i class="fas fa-arrow-down text-2xl text-red-500 group-hover:text-white"></i>
                    </button>
                </div>

                <button id="btn-manual-toggle" onclick="ManualModule.toggle()" class="w-full py-4 rounded-xl border-2 border-gray-700 font-bold hover:border-green-500 transition-all">
                    INICIAR OPERAR
                </button>
            </div>
        `;
    },

    toggle() {
        this.isWorking = !this.isWorking;
        const btn = document.getElementById('btn-manual-toggle');
        if(this.isWorking) {
            btn.innerText = 'DESLIGAR OPERAÇÃO';
            btn.classList.add('active-btn');
            app.notify("Modo Manual Ativado");
        } else {
            btn.innerText = 'INICIAR OPERAR';
            btn.classList.remove('active-btn');
            app.notify("Modo Manual Desativado");
        }
    },

    execute(side) {
        if(!this.isWorking) {
            app.notify("Ative o botão 'OPERAR' primeiro!");
            return;
        }
        app.notify(`Executando ordem de ${side}...`);
        // Lógica de compra/venda original mantida aqui
    }
};
