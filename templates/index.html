<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Previus-Starps OS</title>
    <link rel="stylesheet" href="/static/style.css">
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
</head>
<body>
    <div id="login-view" class="view active">
        <div class="login-card">
            <h1 style="color:#ff4400">PREVIUS-STARPS</h1>
            <input type="password" id="tokenInput" placeholder="Token API Deriv">
            <button onclick="connect()">CONECTAR SISTEMA</button>
            <p id="status-msg"></p>
        </div>
    </div>

    <div id="dashboard-view" class="view">
        <header>
            <div class="header-left">
                <button class="menu-toggle" onclick="toggleMenu()">☰ MENU</button>
                <span class="brand">STARPS <span style="color:#ff4400">PREVIUS</span></span>
            </div>
            <div class="header-right">
                <span id="balance">$0.00</span>
                <span id="acc-type" class="badge">DEMO</span>
            </div>
        </header>

        <div class="wrapper">
            <nav id="sidebar">
                <div class="nav-title">PAINEL DE CONTROLE</div>
                <ul>
                    <li onclick="showScreen('analise')">📊 Análise Geral</li>
                    <li onclick="showScreen('trade-rapido')">⚡ Trade Rápido</li>
                    <li onclick="showScreen('manual')">🎮 Operação Manual</li>
                    <li onclick="showScreen('auto')">🤖 Operação Automática</li>
                    <li onclick="showScreen('graficos')">📈 Gráficos</li>
                    <li onclick="showScreen('risco')">🛡️ Gestão de Risco</li>
                    <li onclick="emergencyStop()" style="color:#ff3344">🛑 STOP EMERGÊNCIA</li>
                </ul>
            </nav>

            <main class="main-content">
                <div id="screen-analise" class="app-screen active">
                    <div class="signal-bar">
                        <div class="sig-box"><small>IA STATUS</small><div id="iaAction">ANALISANDO...</div></div>
                        <div class="sig-box"><small>PROBABILIDADE</small><div id="iaProb">--%</div></div>
                        <div class="sig-box"><small>MOTIVO</small><div id="iaReason">Aguardando...</div></div>
                    </div>
                    <div id="chart-area-analise" class="full-chart"></div>
                </div>

                <div id="screen-trade-rapido" class="app-screen">
                    <div class="trade-container">
                        <h2>Análise de Velas (Próxima Vela)</h2>
                        <div class="analysis-card">
                            <p>Direção Estimada: <strong id="quickAction">--</strong></p>
                            <p>Probabilidade: <span id="quickProb">--%</span></p>
                            <button class="confirm-btn" onclick="confirmTrade()">CONFIRMAR ENTRADA</button>
                        </div>
                    </div>
                </div>

                <div id="screen-auto" class="app-screen">
                    <div class="centered-info">
                        <h2>🤖 Bot Automático</h2>
                        <p>Status: <span style="color:gray">DESLIGADO</span></p>
                        <p>O robô aguarda confluência perfeita para operar sozinho.</p>
                        <button disabled>ATIVAR MODO AUTO</button>
                    </div>
                </div>

                </main>
        </div>
    </div>

    <script>
        let currentChart = null;

        function toggleMenu() { document.getElementById('sidebar').classList.toggle('active'); }

        function showScreen(screenId) {
            document.querySelectorAll('.app-screen').forEach(s => s.classList.remove('active'));
            document.getElementById('screen-' + screenId).classList.add('active');
            if(screenId === 'analise' || screenId === 'graficos') renderChart("1");
            toggleMenu();
        }

        async function connect() {
            const token = document.getElementById('tokenInput').value;
            if(!token) return;
            const res = await fetch('/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({token: token})
            });
            const data = await res.json();
            if(data.status === 'success') {
                document.getElementById('login-view').classList.remove('active');
                document.getElementById('dashboard-view').classList.add('active');
                renderChart("1");
                startLoops();
            }
        }

        function renderChart(interval) {
            new TradingView.widget({
                "autosize": true, "symbol": "DERIV:VOL100", "interval": interval,
                "timezone": "Etc/UTC", "theme": "dark", "style": "1",
                "container_id": "chart-area-analise"
            });
        }

        function startLoops() {
            setInterval(async () => {
                const res = await fetch('/account_info');
                const data = await res.json();
                document.getElementById('balance').innerText = "$" + data.balance.toFixed(2);
                document.getElementById('acc-type').innerText = data.account_type.toUpperCase();
            }, 3000);

            setInterval(async () => {
                const res = await fetch('/get_analysis');
                const data = await res.json();
                if(data.status === 'active') {
                    document.getElementById('iaAction').innerText = data.action;
                    document.getElementById('iaProb').innerText = (data.probability * 100).toFixed(0) + "%";
                    document.getElementById('iaReason').innerText = data.reason;
                }
            }, 2000);
        }

        function emergencyStop() { alert("SISTEMA INTERROMPIDO!"); location.reload(); }
    </script>
</body>
</html>
