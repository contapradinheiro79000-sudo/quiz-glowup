"""Configuração central lida de variáveis de ambiente (.env)."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass  # python-dotenv é opcional; em produção use env vars do painel

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

# ---- Produto ----
PRODUTO_NOME = os.getenv("PRODUTO_NOME", "Cronograma de Transformacao Capilar - Reveillon")
PRECO = float(os.getenv("PRECO", "29.90"))

# ---- Mercado Pago ----
# Deixe VAZIO para rodar em modo SIMULADO (mock), sem precisar de conta.
# Pegue o Access Token em: https://www.mercadopago.com.br/developers > Suas integracoes
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "").strip()
MP_WEBHOOK_SECRET = os.getenv("MP_WEBHOOK_SECRET", "").strip()  # opcional (valida assinatura)

# URL publica do backend (usada como notification_url do Pix). Ex: https://xxx.onrender.com
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")

# ---- CORS ----
# Em dev deixe "*". Em producao coloque a origem do frontend, ex: https://seuquiz.vercel.app
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

# ---- Entrega ----
CONTEUDO_PATH = os.getenv("CONTEUDO_PATH", str(PROJECT_DIR / "pdf" / "Cronograma-Capilar-A4.pdf"))

# ---- E-mail (opcional, para envio automatico apos pagamento) ----
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER or "no-reply@seuquiz.com")

DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "pedidos.db"))

USE_MOCK = MP_ACCESS_TOKEN == ""
