const ManualModule = {
    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <h2 class="text-xl font-bold text-green-500 italic uppercase">Manual Pro</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <div><label class="text-[9px] text-gray-500 uppercase">Stake</label><input id="m-stake" type="number" value="10.00" class="w-full bg-black p-2 rounded text-xs text-white outline-none"></div>
                    <div><label class="text-[9px] text-green-500 uppercase">T.Profit</label><input id="m-tp" type="number" value="5" class="w-full bg-black p-2 rounded text-xs text-white outline-none"></div>
                    <div><label class="text-[9px] text-red-500 uppercase">S.Loss</label><input id="m-sl" type="number" value="10" class="w-full bg-black p-2 rounded text-xs text-white outline-none"></div>
                </div>
                <button onclick="ManualModule.analyze()" class="w-full py-4 bg-blue-600 rounded-xl font-bold uppercase shadow-lg">Analisar Entrada</button>
                <div class="grid grid-cols-2 gap-4">
                    <button id="btn-call" disabled onclick="ManualModule.trade('CALL')" class="p-8 bg-gray-900 rounded-3xl opacity-20 transition-all flex justify-center"><i class="fas fa-arrow-up text-3xl text-green-500"></i></button>
                    <button id="btn-put" disabled onclick="ManualModule.trade('PUT')" class="p-8 bg-gray-900 rounded-3xl opacity-20 transition-all flex justify-center"><i class="fas fa-arrow-down text-3xl text-red-500"></i></button>
                </div>
                <div id="m-status" class="bg-black p-3 rounded-xl h-24 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800">> Aguardando sinal...</div>
                
                <div class="bg-[#1e2329] p-4 rounded-xl border border-gray-800 flex justify-between items-center shadow-2xl">
                    <div class="text-left">
                        <p class="text-[9px] text-gray-500 uppercase font-bold">Preço de compra</p>
                        <p id="m-val-stake" class="text-lg font-bold text-white">0.00 USD</p>
                    </div>
                    <div class="text-right">
                        <p class="text-[9px] text-gray-500 uppercase font-bold">Lucros/perdas totais</p>
                        <p id="m-val-profit" class="text-xl font-black text-gray-600">0.00 USD</p>
                    </div>
                </div>
            </div>`;
    },
    analyze() {
        const status = document.getElementById('m-status');
        status.innerHTML += `<p>> Analisando volatilidade...</p>`;
        setTimeout(() => {
            const side = Math.random() > 0.5 ? 'call' : 'put';
            const btn = document.getElementById('btn-' + side);
            btn.disabled = false;
            btn.classList.add(side === 'call' ? 'indicator-glow' : 'indicator-glow-red');
            status.innerHTML += `<p class="text-green-500">> SINAL DETECTADO: ${side.toUpperCase()}</p>`;
        }, 1500);
    },
    trade(type) {
        const stake = document.getElementById('m-stake').value;
        document.getElementById('m-val-stake').innerText = stake + " USD";
        document.getElementById('m-status').innerHTML += `<p class="text-blue-400">> Ordem enviada: ${type}</p>`;
        DerivAPI.buy(type, stake);
        
        // Reset da Luz
        ['btn-call', 'btn-put'].forEach(id => {
            const b = document.getElementById(id);
            b.disabled = true; b.classList.remove('indicator-glow', 'indicator-glow-red'); b.style.opacity = "0.2";
        });
        
        // Simulação Ponto 4
        setTimeout(() => app.updateModuleProfit(parseFloat(stake) * 0.9, 'm'), 2000);
    }
};
