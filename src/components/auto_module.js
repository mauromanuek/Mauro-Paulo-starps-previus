const AutoModule = {
    isRunning: false,
    isTrading: false, // Novo estado para controle de fluxo
    currentProfit: 0,

    render() {
        return `
            <div class="space-y-4 max-w-md mx-auto">
                <h2 class="text-xl font-bold text-purple-500 italic uppercase">Auto Robot</h2>
                <div class="grid grid-cols-3 gap-2 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <div>
                        <label class="text-[9px] text-gray-500 font-bold">STAKE</label>
                        <input id="a-stake" type="number" value="10.00" class="w-full bg-black p-2 rounded text-xs text-white">
                    </div>
                    <div>
                        <label class="text-[9px] text-green-500 font-bold">TP</label>
                        <input id="a-tp" type="number" value="5" class="w-full bg-black p-2 rounded text-xs text-white">
                    </div>
                    <div>
                        <label class="text-[9px] text-red-500 font-bold">SL</label>
                        <input id="a-sl" type="number" value="10" class="w-full bg-black p-2 rounded text-xs text-white">
                    </div>
                </div>
                <button id="btn-a-toggle" onclick="AutoModule.toggle()" class="w-full py-4 bg-purple-600 rounded-xl font-bold uppercase">Iniciar Robô</button>
                <div id="a-status" class="bg-black p-3 rounded-xl h-24 overflow-y-auto text-[10px] font-mono text-gray-400 border border-gray-800">> Robô pronto...</div>
                <div class="bg-gray-900 p-4 rounded-xl border border-gray-800">
                    <p class="text-[9px] text-gray-500 uppercase font-bold">Lucro Módulo</p>
                    <p id="a-val-profit" class="text-xl font-black text-gray-600">0.00 USD</p>
                </div>
            </div>`;
    },

    toggle() {
        this.isRunning = !this.isRunning;
        const btn = document.getElementById('btn-a-toggle');
        const status = document.getElementById('a-status');
        
        btn.innerText = this.isRunning ? "PARAR ROBÔ" : "INICIAR ROBÔ";
        btn.style.backgroundColor = this.isRunning ? "#ef4444" : "#9333ea";

        if (this.isRunning) {
            status.innerHTML += `<p class="text-blue-400 font-bold">> [SISTEMA] Robô Iniciado...</p>`;
            this.setupListener(); // Ativa a escuta do ciclo de vida
            this.loop();
        } else {
            status.innerHTML += `<p class="text-red-400">> [SISTEMA] Parando robô...</p>`;
            this.isTrading = false;
        }
    },

    // Escuta o evento de finalização enviado pelo deriv_api.js
    setupListener() {
        // Remove ouvinte antigo se existir para evitar duplicidade
        document.removeEventListener('contract_finished', this.handleFinished.bind(this));
        document.addEventListener('contract_finished', this.handleFinished.bind(this));
    },

    handleFinished(e) {
        if (!this.isRunning || e.detail.prefix !== 'a') return;

        this.isTrading = false; // Libera para a próxima operação
        const status = document.getElementById('a-status');
        
        // Pequena pausa de segurança antes da próxima entrada (2 segundos)
        status.innerHTML += `<p class="text-gray-500">> Aguardando 2s para reentrada...</p>`;
        setTimeout(() => {
            if (this.isRunning) this.loop();
        }, 2000);
    },

    loop() {
        if (!this.isRunning || this.isTrading) return;

        window.currentModulePrefix = 'a';
        const stake = document.getElementById('a-stake').value;
        const status = document.getElementById('a-status');
        
        // Simulação de análise (pode ser substituída por lógica real do analysis_engine)
        const side = Math.random() > 0.5 ? "CALL" : "PUT";
        
        status.innerHTML += `<p class="text-purple-400">> [ANALISANDO] Sinal detectado: ${side}</p>`;
        
        this.isTrading = true; // Bloqueia novas entradas até este contrato fechar
        
        DerivAPI.buy(side, stake, (res) => {
            if (res.buy) {
                status.innerHTML += `<p class="text-green-400">> [EXECUTADO] Contrato ${res.buy.contract_id} aberto.</p>`;
                status.scrollTop = status.scrollHeight;
            } else if (res.error) {
                status.innerHTML += `<p class="text-red-500">> [ERRO] ${res.error.message}</p>`;
                this.isTrading = false;
                this.toggle(); // Para o robô em caso de erro crítico (ex: falta de saldo)
            }
        });
    }
};
