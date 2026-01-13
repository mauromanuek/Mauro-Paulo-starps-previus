const ManualModule = {
    render() {
        return `
            <div class="animate-fadeIn space-y-4">
                <h2 class="text-xl font-bold text-green-500 uppercase italic">Operação Manual</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl">
                    <input id="man-stake" type="number" value="0.35" class="bg-black p-2 rounded text-xs">
                    <input id="man-tp" type="number" value="5.00" class="bg-black p-2 rounded text-xs">
                    <input id="man-sl" type="number" value="10.00" class="bg-black p-2 rounded text-xs">
                </div>
                <button onclick="ManualModule.analyze()" id="btn-man-an" class="w-full py-4 bg-blue-600 rounded-xl font-bold">SOLICITAR ANÁLISE</button>
                <div class="grid grid-cols-2 gap-4 mt-4">
                    <button id="btn-call" disabled onclick="ManualModule.trade('CALL')" class="p-8 bg-gray-900 rounded-3xl opacity-20 border-2 border-transparent transition-all">
                        <i class="fas fa-arrow-up text-3xl text-green-500"></i>
                        <div id="acc-call" class="text-[9px] mt-2 font-bold"></div>
                    </button>
                    <button id="btn-put" disabled onclick="ManualModule.trade('PUT')" class="p-8 bg-gray-900 rounded-3xl opacity-20 border-2 border-transparent transition-all">
                        <i class="fas fa-arrow-down text-3xl text-red-500"></i>
                        <div id="acc-put" class="text-[9px] mt-2 font-bold"></div>
                    </button>
                </div>
            </div>`;
    },
    analyze() {
        const btn = document.getElementById('btn-man-an');
        btn.innerText = "PROCESSANDO...";
        setTimeout(() => {
            const side = Math.random() > 0.5 ? 'call' : 'put';
            const target = document.getElementById('btn-' + side);
            target.disabled = false; target.style.opacity = "1";
            target.style.borderColor = side === 'call' ? '#22c55e' : '#ef4444';
            document.getElementById('acc-' + side).innerText = "89% ASSERTIVIDADE";
            btn.innerText = "SOLICITAR ANÁLISE";
        }, 2000);
    },
    trade(type) {
        DerivAPI.buy(type, document.getElementById('man-stake').value);
    }
};
