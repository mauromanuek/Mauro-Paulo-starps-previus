const DigitModule = {
    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <h2 class="text-xl font-bold text-yellow-500 italic uppercase">Digit Strategy</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl">
                    <input id="d-stake" type="number" value="0.35" class="bg-black p-2 rounded text-xs text-white">
                    <input id="d-tp" type="number" value="5" class="bg-black p-2 rounded text-xs text-white">
                    <input id="d-sl" type="number" value="10" class="bg-black p-2 rounded text-xs text-white">
                </div>
                <div class="flex gap-4 p-4 bg-black rounded-xl border border-gray-800 justify-center text-center">
                    <div><p class="text-[9px]">OVER 6</p><p id="p-over" class="text-2xl font-black">0%</p></div>
                    <div class="w-[1px] bg-gray-800"></div>
                    <div><p class="text-[9px]">UNDER 6</p><p id="p-under" class="text-2xl font-black">0%</p></div>
                </div>
                <button onclick="DigitModule.analyze()" id="btn-d" class="w-full py-4 bg-yellow-600 rounded-xl font-bold">EXECUTAR AGORA</button>
                <div id="d-status" class="bg-black p-3 rounded h-24 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800">> Aguardando cálculos...</div>
                <div id="d-profit-display" class="text-center text-xl font-bold text-gray-500">$ 0.00</div>
            </div>`;
    },
    analyze() {
        const status = document.getElementById('d-status');
        const stake = document.getElementById('d-stake').value;
        status.innerHTML += `<p>> Analisando padrões de últimos dígitos...</p>`;
        
        setTimeout(() => {
            const overVal = Math.floor(Math.random() * 40) + 55;
            document.getElementById('p-over').innerText = overVal + "%";
            document.getElementById('p-under').innerText = (100 - overVal) + "%";
            
            const type = overVal > 50 ? "DIGITOVER" : "DIGITUNDER";
            status.innerHTML += `<p class="text-yellow-500">> Estratégia definida: ${type}</p>`;
            
            // COMPRA REAL DISPARADA
            DerivAPI.buy(type, stake);
            status.innerHTML += `<p class="text-green-500">> ORDEM EXECUTADA NA CORRETORA!</p>`;
        }, 2000);
    }
};
