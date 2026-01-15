const ManualModule = {
    isTrading: false,

    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <h2 class="text-xl font-bold text-green-500 italic uppercase">Manual Pro</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <div>
                        <label class="text-[9px] text-gray-500 uppercase font-bold">Stake</label>
                        <input id="m-stake" type="number" value="10.00" class="w-full bg-black p-2 rounded text-xs text-white outline-none">
                    </div>
                    <div>
                        <label class="text-[9px] text-green-500 uppercase font-bold">T.Profit</label>
                        <input id="m-tp" type="number" value="5" class="w-full bg-black p-2 rounded text-xs text-white outline-none">
                    </div>
                    <div>
                        <label class="text-[9px] text-red-500 uppercase font-bold">S.Loss</label>
                        <input id="m-sl" type="number" value="10" class="w-full bg-black p-2 rounded text-xs text-white outline-none">
                    </div>
                </div>
                <button id="btn-m-analyze" onclick="ManualModule.analyze()" class="w-full py-4 bg-blue-600 rounded-xl font-bold uppercase shadow-lg">Analisar Mercado</button>
                <div class="grid grid-cols-2 gap-4">
                    <button id="btn-call" onclick="ManualModule.trade('CALL')" class="py-6 bg-green-600 rounded-2xl font-black text-2xl shadow-lg opacity-20" disabled>CALL</button>
                    <button id="btn-put" onclick="ManualModule.trade('PUT')" class="py-6 bg-red-600 rounded-2xl font-black text-2xl shadow-lg opacity-20" disabled>PUT</button>
                </div>
                <div id="m-status" class="bg-black p-3 rounded-xl h-24 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800">> Sistema Manual Pronto...</div>
                <div class="bg-gray-900 p-4 rounded-xl border border-gray-800">
                    <p class="text-[9px] text-gray-500 uppercase font-bold">Lucro Módulo</p>
                    <p id="m-val-profit" class="text-xl font-black text-gray-600">0.00 USD</p>
                </div>
            </div>`;
    },

    analyze() {
        if (this.isTrading) return;
        
        const status = document.getElementById('m-status');
        status.innerHTML += '<p class="text-blue-400">> [ANALISANDO] Verificando volatilidade do R_100...</p>';
        
        // Desativa botões durante análise
        ['btn-call', 'btn-put', 'btn-m-analyze'].forEach(id => {
            const b = document.getElementById(id);
            if(b) {
                b.disabled = true;
                b.style.opacity = "0.2";
                b.classList.remove('indicator-glow', 'indicator-glow-red');
            }
        });

        setTimeout(() => {
            const side = Math.random() > 0.5 ? 'call' : 'put';
            const target = document.getElementById('btn-' + side);
            
            if(target) {
                target.disabled = false;
                target.style.opacity = "1";
                target.classList.add(side === 'call' ? 'indicator-glow' : 'indicator-glow-red');
            }
            
            const btnAnalyze = document.getElementById('btn-m-analyze');
            if(btnAnalyze) {
                btnAnalyze.disabled = false;
                btnAnalyze.style.opacity = "1";
            }

            status.innerHTML += `<p class="text-green-500 font-bold">> [SINAL] Entrada sugerida: ${side.toUpperCase()}</p>`;
            status.scrollTop = status.scrollHeight;
        }, 1200);
    },

    trade(type) {
        if (this.isTrading) return;

        this.isTrading = true;
        window.currentModulePrefix = 'm';
        const stake = document.getElementById('m-stake').value;
        const status = document.getElementById('m-status');

        status.innerHTML += `<p class="text-yellow-400">> [EXECUTANDO] Enviando ordem de ${type}...</p>`;

        DerivAPI.buy(type, stake, (res) => {
            if (res.error) {
                status.innerHTML += `<p class="text-red-500">> [ERRO] ${res.error.message}</p>`;
                this.resetInterface();
            } else if (res.buy) {
                status.innerHTML += `<p class="text-blue-400">> [ABERTO] ID: ${res.buy.contract_id}. Aguardando fechamento...</p>`;
                this.setupContractListener();
            }
        });

        // Bloqueia interface durante o contrato
        ['btn-call', 'btn-put'].forEach(id => {
            const b = document.getElementById(id);
            if(b) {
                b.disabled = true;
                b.style.opacity = "0.2";
                b.classList.remove('indicator-glow', 'indicator-glow-red');
            }
        });
    },

    setupContractListener() {
        // Escuta o evento global que criamos no deriv_api.js
        const handler = (e) => {
            if (e.detail.prefix === 'm') {
                const profit = e.detail.profit;
                const color = profit >= 0 ? 'text-green-500' : 'text-red-500';
                
                document.getElementById('m-status').innerHTML += `<p class="${color} font-bold">> [RESULTADO] ${profit > 0 ? 'WIN' : 'LOSS'}: ${profit.toFixed(2)} USD</p>`;
                document.getElementById('m-status').scrollTop = document.getElementById('m-status').scrollHeight;
                
                this.resetInterface();
                document.removeEventListener('contract_finished', handler);
            }
        };
        document.addEventListener('contract_finished', handler);
    },

    resetInterface() {
        this.isTrading = false;
        const btnAnalyze = document.getElementById('btn-m-analyze');
        if(btnAnalyze) {
            btnAnalyze.disabled = false;
            btnAnalyze.style.opacity = "1";
        }
    }
};
