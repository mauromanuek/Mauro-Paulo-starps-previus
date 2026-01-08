import os

class Config:
    # O APP_ID padrão da Deriv para apps genéricos é 1089, 
    # ou o seu específico se você criou um no portal de desenvolvedores.
    APP_ID = "114910" 
    
    # Este campo ficará vazio aqui por segurança. 
    # O Bot vai receber o Token que você digitar na tela de Login.
    DERIV_TOKEN = os.environ.get('DERIV_TOKEN', '') 

    # Configurações de Gerenciamento de Risco Padrão
    DEFAULT_SYMBOL = "R_100"  # Volatility 100 Index
    MIN_PROBABILITY = 0.75    # Só avisa se a chance for maior que 75%
