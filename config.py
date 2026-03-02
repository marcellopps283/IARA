"""
config.py — Configurações centralizadas do KittyClaw/ZeroClaw
Todas as constantes, limites e paths ficam aqui.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Keys
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_KEY_2 = os.getenv("GROQ_API_KEY_2", "")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
CEREBRAS_API_KEY_2 = os.getenv("CEREBRAS_API_KEY_2", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
NVIDIA_NIM_API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
USER_ID_ALLOWED = int(os.getenv("USER_ID_ALLOWED", "0"))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LLM Providers — configuração dos modelos e endpoints
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LLM_PROVIDERS = [
    {
        "name": "groq",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": GROQ_API_KEY,
        "model": "llama-3.3-70b-versatile",
        "max_tokens": 4096,
        "supports_streaming": True,
        "supports_tools": True,
    },
    {
        "name": "groq_2",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": GROQ_API_KEY_2,
        "model": "llama-3.3-70b-versatile",
        "max_tokens": 4096,
        "supports_streaming": True,
        "supports_tools": True,
    },
    {
        "name": "kimi",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key": NVIDIA_NIM_API_KEY,
        "model": "moonshotai/kimi-k2.5",
        "max_tokens": 4096,
        "supports_streaming": True,
        "supports_tools": False,
    },
    {
        "name": "cerebras",
        "base_url": "https://api.cerebras.ai/v1",
        "api_key": CEREBRAS_API_KEY,
        "model": "llama3.1-8b",
        "max_tokens": 4096,
        "supports_streaming": True,
        "supports_tools": False,  # 8B model não é confiável com tools
    },
    {
        "name": "cerebras_2",
        "base_url": "https://api.cerebras.ai/v1",
        "api_key": CEREBRAS_API_KEY_2,
        "model": "llama3.1-8b",
        "max_tokens": 4096,
        "supports_streaming": True,
        "supports_tools": False,
    },
    {
        "name": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": OPENROUTER_API_KEY,
        "model": "deepseek/deepseek-r1",
        "max_tokens": 4096,
        "supports_streaming": True,
        "supports_tools": False,  # R1 não suporta tools nativamente
    },
    {
        "name": "gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key": GEMINI_API_KEY,
        "model": "gemini-2.5-flash",
        "max_tokens": 8192,
        "supports_streaming": True,
        "supports_tools": True,
    },
    {
        "name": "mistral",
        "base_url": "https://api.mistral.ai/v1",
        "api_key": MISTRAL_API_KEY,
        "model": "mistral-large-latest",
        "max_tokens": 4096,
        "supports_streaming": True,
        "supports_tools": True,
    },
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Guardrails e Stop Conditions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MAX_RETRIES_PER_TASK = 5         # Máximo de tentativas antes de pedir ajuda humana
LLM_TIMEOUT_SECONDS = 60        # Timeout por chamada de LLM
MAX_WORKING_MEMORY = 20         # Mensagens no working memory antes de compactar
MAX_TOOL_CALLS_PER_TURN = 5     # Máximo de tools executadas por turno
MAX_DAILY_LLM_CALLS = 150       # Quota diária máxima de disparos pro LLM Router (Kill Switch financeiro)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Swarm Orchestrator (Load Balancing & Anti-OOM)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MAX_WORKERS_S21FE = 3           # Prioridade 1: Aguenta mais carga isolada
MAX_WORKERS_ULTRA = 1           # Prioridade 2 (Overflow): Protegido pra não crashar o MMRPG

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Paths
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import pathlib

BASE_DIR = pathlib.Path(__file__).parent
DB_PATH = BASE_DIR / "kitty_memory.db"
IDENTITY_DIR = BASE_DIR / "identity"
SKILLS_DIR = BASE_DIR / "skills"
SHADOW_DIR = BASE_DIR / "Kitty_Shadow"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Web Search — limites diários para economizar cotas
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JINA_API_URL = "https://r.jina.ai/"
DDG_MAX_RESULTS = 5
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
BRAVE_MAX_DAILY = 60  # 2000/mês ÷ 30 dias

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Telegram
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STREAMING_EDIT_INTERVAL = 0.8  # Segundos entre edições da mensagem (streaming)
