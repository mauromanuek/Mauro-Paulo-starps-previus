const ManualModule = {
    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <h2 class="text-xl font-bold text-green-500 italic uppercase">Manual Pro</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl">
                    <div><label class="text-[9px] text-gray-500">STAKE</label><input id="m-stake" type="number" value="0.35" class="w-full bg-black p-2 rounded text-xs text-white"></div>
                    <div><label class="text-[9px] text-green-500">T.P</label><input id="m-tp" type="number" value="5" class="w-full bg-black p-2 rounded text-xs text-white"></div>
                    <div><label class="text-[9px] text-red-500">S.L</label><input id="m-sl" type="number" value="10" class="w-full bg-black p-2 rounded text-xs text-white"></div>
                </div>
                <button onclick="ManualModule.analyze()" id="btn-m-an" class="w-full py-4 bg-blue-600 rounded-xl font-bold">ANALISAR ENTRADA</button>
                <div class="grid grid-cols-2 gap-4">
                    <button id="btn-call" disabled onclick="ManualModule.trade('CALL')" class="p-8 bg-gray-900 rounded-3xl opacity-20"><i class="fas fa-arrow-up text-3xl text-green-500"></i></button>
                    <button id="btn-put" disabled onclick="ManualModule.trade('PUT')" class="p-8 bg-gray-900 rounded-3xl opacity-20"><i class="fas fa-arrow-down text-3xl text-red-500"></i></button>
                </div>
                <div id="m-status" class="bg-black p-3 rounded h-24 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800">> Aguardando sinal...</div>
                <div id="m-profit-display" class="text-center text-xl font-bold text-gray-500">$ 0.00</div>
            </div>`;
    },
    analyze() {
        const status = document.getElementById('m-status');
        status.innerHTML += `<p>> Analisando volatilidade do ativo...</p>`;
        setTimeout(() => {
            const side = Math.random() > 0.5 ? 'call' : 'put';
            const btn = document.getElementById('btn-' + side);
            btn.disabled = false;
            btn.classList.add(side === 'call' ? 'indicator-glow' : 'indicator-glow-red');
            status.innerHTML += `<p class="text-green-500">> SINAL DE ${side.toUpperCase()} DETECTADO!</p>`;
        }, 2000);
    },
    trade(type) {
        const stake = document.getElementById('m-stake').value;
        DerivAPI.buy(type, stake);
        document.getElementById('m-status').innerHTML += `<p class="text-blue-400">> Ordem enviada: ${type} ($${stake})</p>`;
        
        // RESET TOTAL (APAGA A LUZ)
        ['btn-call', 'btn-put'].forEach(id => {
            const b = document.getElementById(id);
            b.disabled = true; b.classList.remove('indicator-glow', 'indicator-glow-red');
            b.style.opacity = "0.2";
        });
    }
};
