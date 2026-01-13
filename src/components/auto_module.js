// src/components/auto_module.js
const AutoModule = {
    isRunning: false,
    settings: { stake: 1, tp: 5, sl: 10 },
    stats: { wins: 0, losses: 0, profit: 0 },

    render() {
        return `
            <div class="col-span-1 bg-card p-6 rounded-2xl border border-gray-800 flex flex-col gap-4">
                <h3 class="text-xs font-bold text-gray-500 uppercase italic">Gestão de Risco</h3>
                <div>
                    <label class="text-[10px] text-gray-400">STAKE (USD)</label>
                    <input type="number" id="auto-stake" value="${this.settings.stake}" class="w-full bg-black border border-gray-700 rounded-lg p-2 text-yellow-500 outline-none">
                </div>
                <div class="grid grid-cols-2 gap-2">
                    <div>
                        <label class="text-[10px] text-gray-400">TAKE PROFIT</label>
                        <input type="number" id="auto-tp" value="${this.settings.tp}" class="w-full bg-black border border-gray-700 rounded-lg p-2 text-green-500 outline-none">
                    </div>
                    <div>
                        <label class="text-[10px] text-gray-400">STOP LOSS</label>
                        <input type="number" id="auto-sl" value="${this.settings.sl}" class="w-full bg-black border border-gray-700 rounded-lg p-2 text-red-500 outline-none">
                    </div>
                </div>
                <button onclick="AutoModule.toggle()" id="btn-auto-main" class="w-full py-4 rounded-xl font-bold transition-all ${this.isRunning ? 'bg-red-600' : 'bg-yellow-500 text-black'}">
                    ${this.isRunning ? 'PARAR BOT' : 'LIGAR AUTOMAÇÃO'}
                </button>
            </div>
            
            <div class="col-span-2 bg-card p-6 rounded-2xl border border-gray-800">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-xs font-bold text-gray-500 uppercase">Monitor de Performance</h3>
                    <span class="status-pulse text-[10px] ${this.isRunning ? 'text-green-500' : 'text-gray-600'}">
                        <i class="fas fa-circle mr-1"></i> ${this.isRunning ? 'OPERANDO' : 'DESLIGADO'}
                    </span>
                </div>
                <div class="grid grid-cols-3 gap-4 text-center">
                    <div class="p-4 bg-black/40 rounded-xl"><p class="text-[10px] text-gray-500">WINS</p><p class="text-xl font-bold text-green-500">${this.stats.wins}</p></div>
                    <div class="p-4 bg-black/40 rounded-xl"><p class="text-[10px] text-gray-500">LOSSES</p><p class="text-xl font-bold text-red-500">${this.stats.losses}</p></div>
                    <div class="p-4 bg-black/40 rounded-xl"><p class="text-[10px] text-gray-500">LUCRO ACUM.</p><p class="text-xl font-bold text-yellow-500">$ ${this.stats.profit.toFixed(2)}</p></div>
                </div>
                <div id="auto-log" class="mt-4 text-[10px] text-gray-600 font-mono h-12 overflow-y-auto border-t border-gray-800 pt-2">
                    Aguardando sinal da estratégia...
                </div>
            </div>
        `;
    },

    toggle() {
        this.isRunning = !this.isRunning;
        this.settings.stake = parseFloat(document.getElementById('auto-stake').value);
        this.settings.tp = parseFloat(document.getElementById('auto-tp').value);
        this.settings.sl = parseFloat(document.getElementById('auto-sl').value);
        
        const container = document.getElementById('interface-container');
        container.innerHTML = this.render();
    },

    log(msg) {
        const logger = document.getElementById('auto-log');
        if(logger) logger.innerHTML = `> ${msg}<br>` + logger.innerHTML;
    }
};
