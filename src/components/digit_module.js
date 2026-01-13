// src/components/digit_module.js
const DigitModule = {
    stats: new Array(10).fill(0),
    history: [],

    render() {
        return `
            <div class="col-span-1 md:col-span-3 bg-card p-6 rounded-2xl border border-gray-800 shadow-lg">
                <div class="flex justify-between items-center mb-6">
                    <h3 class="text-xl font-bold text-yellow-500"><i class="fas fa-chart-bar mr-2"></i> Análise Digit Over/Under</h3>
                    <div class="flex gap-2">
                        <input type="number" id="digit-stake" value="1.00" class="w-20 bg-black border border-gray-700 rounded p-1 text-center text-sm">
                        <button onclick="DigitModule.execute('OVER')" class="bg-green-600 px-4 py-1 rounded font-bold text-sm hover:bg-green-500">OVER 5</button>
                        <button onclick="DigitModule.execute('UNDER')" class="bg-red-600 px-4 py-1 rounded font-bold text-sm hover:bg-red-500">UNDER 5</button>
                    </div>
                </div>
                
                <div class="grid grid-cols-10 gap-2 h-32 items-end border-b border-gray-700 pb-2" id="digit-bars">
                    ${this.stats.map((v, i) => `
                        <div class="flex flex-col items-center">
                            <div class="bg-yellow-500/40 w-full rounded-t transition-all duration-500" style="height: ${v}%"></div>
                            <span class="text-[10px] mt-1">${i}</span>
                        </div>
                    `).join('')}
                </div>
                <div id="digit-log" class="mt-4 text-xs text-gray-500 h-10 overflow-hidden italic text-center">Aguardando ticks...</div>
            </div>
        `;
    },

    updateStats(lastDigit) {
        this.history.push(lastDigit);
        if(this.history.length > 50) this.history.shift();
        
        const counts = new Array(10).fill(0);
        this.history.forEach(d => counts[d]++);
        this.stats = counts.map(c => (c / this.history.length) * 100 * 2); // Escala visual
        
        const container = document.getElementById('interface-container');
        if(container && container.dataset.active === 'digit') {
            container.innerHTML = this.render();
        }
    },

    execute(type) {
        const stake = document.getElementById('digit-stake').value;
        const contract = type === 'OVER' ? 'DIGITOVER' : 'DIGITUNDER';
        const barrier = 5;
        DerivAPI.sendOrder(contract, stake, barrier);
        alert(`Ordem ${type} enviada!`);
    }
};
