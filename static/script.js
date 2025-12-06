let isConnecting = false;
let statusInterval = null;

document.addEventListener("DOMContentLoaded", () => {
    const connectBtn = document.getElementById("connect-btn");
    const tokenInput = document.getElementById("token-input");
    const statusBox = document.getElementById("status-box");
    const balanceBox = document.getElementById("balance-box");
    const accountBox = document.getElementById("account-box");

    // ------------------------------
    // BOTÃO CONECTAR
    // ------------------------------
    connectBtn.addEventListener("click", async () => {
        const token = tokenInput.value.trim();

        if (!token) {
            alert("Por favor insira o token.");
            return;
        }

        isConnecting = true;
        connectBtn.innerText = "Conectando...";
        connectBtn.disabled = true;

        try {
            // Enviar token ao servidor
            const response = await fetch("/set_token", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ token: token })
            });

            const data = await response.json();

            if (data.error) {
                alert("Erro: " + data.error);
                isConnecting = false;
                connectBtn.disabled = false;
                connectBtn.innerText = "Conectar";
                return;
            }

            console.log("Token enviado ao backend:", data);

            // Começar a verificar status
            if (!statusInterval) {
                statusInterval = setInterval(updateStatus, 1000);
            }

        } catch (err) {
            console.error("Erro ao enviar token:", err);
            alert("Falha ao enviar token.");
            isConnecting = false;
            connectBtn.disabled = false;
            connectBtn.innerText = "Conectar";
        }
    });

    // ------------------------------
    // FUNÇÃO DE STATUS
    // ------------------------------
    async function updateStatus() {
        try {
            const res = await fetch("/status");
            const data = await res.json();

            if (data.connected) {
                statusBox.innerText = "🟢 Conectado";
                balanceBox.innerText = data.balance + " USD";
                accountBox.innerText = data.account_type || "Desconhecido";

                if (isConnecting) {
                    isConnecting = false;
                    connectBtn.innerText = "Conectado";
                    connectBtn.style.backgroundColor = "#2196f3";
                }
            } else {
                statusBox.innerText = "🔴 Desconectado";
                balanceBox.innerText = "--";
                accountBox.innerText = "--";

                if (!isConnecting) {
                    connectBtn.disabled = false;
                    connectBtn.innerText = "Conectar";
                    connectBtn.style.backgroundColor = "#4CAF50";
                }
            }
        } catch (err) {
            console.error("Erro ao atualizar status:", err);
        }
    }
});
