const DigitModule = {
    render() {
        return `
            <div class="animate-fadeIn space-y-4">
                <h2 class="text-xl font-bold text-yellow-500 uppercase italic">Digit Over/Under</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <input id="dig-stake" type="number" value="0.35" class="bg-black p-2 rounded text-xs border border-gray-700">
                    <input id="dig-tp" type="number" value="5" class="bg-black p-2 rounded text-xs border border-gray-700">
                    <input id="dig-sl" type="number" value="10" class="bg-black p-2 rounded text-xs border border-gray-700">
                </div>
                <div class="flex gap-4 p-6 bg-black rounded-2xl border border-gray-800 justify-center">
                    <div class="text-center">
                        <p class="text-[10px] text-gray-500">OVER (%)</p>
                        <p id="p-over" class="text-3xl font-black text-gray-700">0%</p>
                    </div>
                    <div class="w-[1px] bg-gray-800"></div>
                    <div class="text-center">
                        <p class="text-[10px] text-gray-500">UNDER (%)</p>
                        <p id="p-under" class="text-3xl font-black text-gray-700">0%</p>
                    </div>
                </div>
                <button onclick="DigitModule.analyze()" id="btn-dig" class="w-full py-4 bg-yellow-600 rounded-xl font-bold">ANALISAR & EXECUTAR</button>
            </div>`;
    },
    analyze() {
        const btn = document.getElementById('btn-dig');
        btn.disabled = true; btn.innerText = "CALCULANDO...";
        setTimeout(() => {
            const pOver = Math.floor(Math.random() * 40) + 55; // Simula tendência alta
            const pUnder = 100 - pOver;
            document.getElementById('p-over').innerText = pOver + "%";
            document.getElementById('p-under').innerText = pUnder + "%";
            
            const best = pOver > pUnder ? "DIGITOVER" : "DIGITUNDER";
            document.getElementById(pOver > pUnder ? 'p-over' : 'p-under').classList.add('text-green-500', 'animate-bounce');
            
            DerivAPI.buy(best, document.getElementById('dig-stake').value);
            btn.disabled = false; btn.innerText = "ORDEM EXECUTADA!";
        }, 2500);
    }
};
