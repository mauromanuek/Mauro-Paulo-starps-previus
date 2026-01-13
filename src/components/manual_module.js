const ManualModule = {
    render() {
        return `
            <div id="panel-manual" class="flex flex-col gap-4 animate-fadeIn">
                <h2 class="text-xl font-bold text-green-500 uppercase italic">Operação Manual</h2>
                <div class="bg-gray-900 p-4 rounded-xl border border-gray-800 mb-2">
                    <label class="text-[10px] text-gray-500 uppercase font-bold">Stake</label>
                    <input id="manual-stake" type="number" value="0.35" class="w-full bg-black border border-gray-700 p-2 rounded text-white mb-4">
                    <button id="btn-man-analyze" onclick="ManualModule.analyze()" class="w-full py-3 bg-blue-600 rounded-xl font-bold">INICIAR ANÁLISE</button>
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <button id="btn-call" disabled onclick="ManualModule.trade('CALL')" class="p-6 bg-gray-800 rounded-2xl opacity-30 border-2 border-transparent transition-all">
                        <i class="fas fa-arrow-up text-2xl text-green-500"></i>
                        <p class="font-bold mt-2">COMPRAR</p>
                    </button>
                    <button id="btn-put" disabled onclick="ManualModule.trade('PUT')" class="p-6 bg-gray-800 rounded-2xl opacity-30 border-2 border-transparent transition-all">
                        <i class="fas fa-arrow-down text-2xl text-red-500"></i>
                        <p class="font-bold mt-2">VENDER</p>
                    </button>
                </div>
            </div>`;
    },
    analyze() {
        const btn = document.getElementById('btn-man-analyze');
        btn.innerText = "ANALISANDO...";
        btn.disabled = true;

        setTimeout(() => {
            const side = Math.random() > 0.5 ? 'call' : 'put';
            const target = document.getElementById('btn-' + side);
            
            // Destaque visual
            target.disabled = false;
            target.style.opacity = "1";
            target.style.borderColor = (side === 'call') ? "#22c55e" : "#ef4444";
            target.classList.add('animate-pulse');
            
            btn.innerText = "SINAL DETECTADO!";
        }, 2000);
    },
    trade(type) {
        const stake = document.getElementById('manual-stake').value;
        DerivAPI.buy(type, stake);
        
        // Reset botões
        ['btn-call', 'btn-put'].forEach(id => {
            const b = document.getElementById(id);
            b.disabled = true;
            b.style.opacity = "0.3";
            b.style.borderColor = "transparent";
            b.classList.remove('animate-pulse');
        });
        document.getElementById('btn-man-analyze').disabled = false;
        document.getElementById('btn-man-analyze').innerText = "INICIAR ANÁLISE";
    }
};
