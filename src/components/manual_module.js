const ManualModule = {
    currentProfit: 0,
    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <h2 class="text-xl font-bold text-green-500 italic uppercase">Manual Pro</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <input id="m-stake" type="number" value="10.00" class="bg-black p-2 rounded text-xs text-white outline-none">
                    <input id="m-tp" type="number" value="5" class="bg-black p-2 rounded text-xs text-white outline-none">
                    <input id="m-sl" type="number" value="10" class="bg-black p-2 rounded text-xs text-white outline-none">
                </div>
                <button onclick="ManualModule.analyze()" class="w-full py-4 bg-blue-600 rounded-xl font-bold uppercase shadow-lg">Analisar Mercado</button>
                <div class="grid grid-cols-2 gap-4 mt-4">
                    <button id="btn-call" disabled onclick="ManualModule.trade('CALL')" class="p-8 bg-gray-900 rounded-3xl opacity-20 transition-all flex justify-center"><i class="fas fa-arrow-up text-3xl text-green-500"></i></button>
                    <button id="btn-put" disabled onclick="ManualModule.trade('PUT')" class="p-8 bg-gray-900 rounded-3xl opacity-20 transition-all flex justify-center"><i class="fas fa-arrow-down text-3xl text-red-500"></i></button>
                </div>
                <div id="m-status" class="bg-black p-3 rounded-xl h-24 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800">> Aguardando comando...</div>
            </div>`;
    },
    analyze() {
        const status = document.getElementById('m-status');
        status.innerHTML += `<p class="text-blue-400">> Analisando...</p>`;
        setTimeout(() => {
            ['btn-call', 'btn-put'].forEach(id => {
                const b = document.getElementById(id);
                b.disabled = false; b.style.opacity = "1";
            });
            status.innerHTML += `<p class="text-green-500">> ENTRADA DISPONÍVEL!</p>`;
        }, 400);
    },
    trade(type) {
        const status = document.getElementById('m-status');
        const stake = document.getElementById('m-stake').value;
        status.innerHTML += `<p class="text-yellow-400">> Ordem de ${stake} USD enviada (${type})...</p>`;
        
        DerivAPI.buy(type, stake, (res) => {
            if(res.buy) {
                status.innerHTML += `<p class="text-blue-400">> Contrato ${res.buy.contract_id} em processamento.</p>`;
                this.monitor(res.buy.contract_id);
            }
        });
        ['btn-call', 'btn-put'].forEach(id => { document.getElementById(id).disabled = true; document.getElementById(id).style.opacity = "0.2"; });
    },
    monitor(cid) {
        DerivAPI.subscribeContract(cid, (c) => {
            if (c.is_sold) {
                const profit = parseFloat(c.profit);
                const color = profit > 0 ? "text-green-500" : "text-red-500";
                document.getElementById('m-status').innerHTML += `<p class="${color} font-bold">> OPERAÇÃO FECHADA: ${profit.toFixed(2)} USD</p>`;
                app.updateModuleProfit(profit, 'm');
            }
        });
    }
};
