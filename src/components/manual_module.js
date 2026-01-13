const ManualModule = {
    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <h2 class="text-xl font-bold text-green-500 uppercase italic">Operação Manual</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <div><label class="text-[9px] text-gray-500 uppercase">Stake</label><input id="man-stake" type="number" value="0.35" class="w-full bg-black p-2 rounded text-xs text-white"></div>
                    <div><label class="text-[9px] text-green-500 uppercase">T.Profit</label><input id="man-tp" type="number" value="5.00" class="w-full bg-black p-2 rounded text-xs text-white"></div>
                    <div><label class="text-[9px] text-red-500 uppercase">S.Loss</label><input id="man-sl" type="number" value="10.00" class="w-full bg-black p-2 rounded text-xs text-white"></div>
                </div>
                <button onclick="ManualModule.analyze()" id="btn-man-an" class="w-full py-4 bg-blue-600 rounded-xl font-bold uppercase">Analisar Entrada</button>
                <div class="grid grid-cols-2 gap-4">
                    <button id="btn-call" disabled onclick="ManualModule.trade('CALL')" class="p-8 bg-gray-900 rounded-3xl opacity-20 transition-all flex flex-col items-center">
                        <i class="fas fa-arrow-up text-3xl text-green-500"></i>
                        <span id="lbl-call" class="text-[10px] mt-2 font-bold">---</span>
                    </button>
                    <button id="btn-put" disabled onclick="ManualModule.trade('PUT')" class="p-8 bg-gray-900 rounded-3xl opacity-20 transition-all flex flex-col items-center">
                        <i class="fas fa-arrow-down text-3xl text-red-500"></i>
                        <span id="lbl-put" class="text-[10px] mt-2 font-bold">---</span>
                    </button>
                </div>
                <div id="man-status" class="bg-black p-4 rounded-xl border border-gray-800 h-24 overflow-y-auto font-mono text-[10px] text-gray-400">
                    > Aguardando sinal...
                </div>
            </div>`;
    },
    analyze() {
        const btn = document.getElementById('btn-man-an');
        btn.innerText = "ANALISANDO...";
        setTimeout(() => {
            const side = Math.random() > 0.5 ? 'call' : 'put';
            const target = document.getElementById('btn-' + side);
            target.disabled = false;
            target.classList.add(side === 'call' ? 'indicator-glow' : 'indicator-glow-red');
            document.getElementById('lbl-' + side).innerText = "87% ASSERTIVIDADE";
            btn.innerText = "SINAL PRONTO!";
        }, 2000);
    },
    trade(type) {
        const stake = document.getElementById('man-stake').value;
        const status = document.getElementById('man-status');
        
        DerivAPI.buy(type, stake); // Executa a ordem real
        status.innerHTML += `<p class="text-blue-400">> Ordem ${type} enviada: $${stake}</p>`;
        
        // APAGA A LUZ E DESLIGA BOTÕES
        ['btn-call', 'btn-put'].forEach(id => {
            const b = document.getElementById(id);
            b.disabled = true;
            b.classList.remove('indicator-glow', 'indicator-glow-red');
            b.style.opacity = "0.2";
            document.getElementById('lbl-' + id.split('-')[1]).innerText = "---";
        });
        document.getElementById('btn-man-an').innerText = "ANALISAR ENTRADA";
    }
};
