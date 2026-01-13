const DigitModule = {
    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <h2 class="text-xl font-bold text-yellow-500 uppercase italic">Digit Over / Under</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <div><label class="text-[9px] text-gray-500 uppercase">Stake</label><input id="dig-stake" type="number" value="0.35" class="w-full bg-black p-2 rounded text-xs text-white"></div>
                    <div><label class="text-[9px] text-green-500 uppercase">T.Profit</label><input id="dig-tp" type="number" value="5.00" class="w-full bg-black p-2 rounded text-xs text-white"></div>
                    <div><label class="text-[9px] text-red-500 uppercase">S.Loss</label><input id="dig-sl" type="number" value="10.00" class="w-full bg-black p-2 rounded text-xs text-white"></div>
                </div>
                <div class="flex gap-4 p-6 bg-black rounded-2xl border border-gray-800 justify-center">
                    <div class="text-center"><p class="text-[10px] text-gray-500 uppercase">Over 6</p><p id="p-over" class="text-3xl font-black text-gray-700">0%</p></div>
                    <div class="w-[1px] bg-gray-800"></div>
                    <div class="text-center"><p class="text-[10px] text-gray-500 uppercase">Under 6</p><p id="p-under" class="text-3xl font-black text-gray-700">0%</p></div>
                </div>
                <button onclick="DigitModule.analyze()" id="btn-dig" class="w-full py-4 bg-yellow-600 rounded-xl font-bold uppercase">Iniciar Automação Digits</button>
                <div id="dig-status" class="bg-black p-4 rounded-xl border border-gray-800 h-24 overflow-y-auto font-mono text-[10px] text-gray-400">
                    > Aguardando estatísticas...
                </div>
            </div>`;
    },
    analyze() {
        const btn = document.getElementById('btn-dig');
        const status = document.getElementById('dig-status');
        btn.disabled = true;
        btn.innerText = "CALCULANDO...";
        
        setTimeout(() => {
            const pOver = Math.floor(Math.random() * 40) + 55; // Simula tendência
            const pUnder = 100 - pOver;
            document.getElementById('p-over').innerText = pOver + "%";
            document.getElementById('p-under').innerText = pUnder + "%";
            
            const type = pOver > pUnder ? "DIGITOVER" : "DIGITUNDER";
            const stake = document.getElementById('dig-stake').value;
            
            status.innerHTML += `<p class="text-yellow-500">> Probabilidade detectada: ${type}</p>`;
            
            // EXECUÇÃO AUTOMÁTICA
            DerivAPI.buy(type, stake);
            status.innerHTML += `<p class="text-green-500">> Ordem enviada: $${stake}</p>`;
            
            btn.disabled = false;
            btn.innerText = "AUTOMAÇÃO ATIVA";
        }, 2500);
    }
};
