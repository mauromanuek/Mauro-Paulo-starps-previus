// src/components/manual_module.js
const ManualModule = {
    render() {
        return `
            <div class="bg-card p-6 rounded-2xl border border-gray-800 flex flex-col justify-between">
                <h3 class="font-bold text-gray-400 mb-4 uppercase text-xs">Configurações de Entrada</h3>
                <div class="space-y-4">
                    <div>
                        <label class="text-[10px] text-gray-500">VALOR (USD)</label>
                        <input type="number" id="manual-stake" value="10.00" class="w-full bg-black border border-gray-700 rounded-lg p-3 outline-none focus:border-yellow-500">
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <button onclick="ManualModule.buy('CALL')" class="bg-green-600 hover:bg-green-500 py-4 rounded-xl font-bold shadow-lg shadow-green-900/20">COMPRAR</button>
                        <button onclick="ManualModule.buy('PUT')" class="bg-red-600 hover:bg-red-500 py-4 rounded-xl font-bold shadow-lg shadow-red-900/20">VENDER</button>
                    </div>
                </div>
            </div>
            <div class="col-span-2 bg-card p-6 rounded-2xl border border-gray-800">
                <h3 class="font-bold text-gray-400 mb-4 uppercase text-xs">Status da Estratégia</h3>
                <div id="strategy-signal" class="flex items-center justify-center h-full text-2xl font-bold text-gray-700">
                    ANALISANDO MERCADO...
                </div>
            </div>
        `;
    },

    buy(side) {
        const stake = document.getElementById('manual-stake').value;
        DerivAPI.sendOrder(side, stake);
    }
};
