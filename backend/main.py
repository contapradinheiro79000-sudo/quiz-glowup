"""
API do Quiz Glow-Up Réveillon.

Fluxo:
  1. POST /api/quiz            -> salva as respostas (lead)
  2. POST /api/orders          -> cria pedido + cobrança Pix (QR + copia e cola)
  3. GET  /api/orders/{id}     -> frontend faz polling do status
  4. POST /webhooks/mercadopago-> Mercado Pago avisa quando o Pix é aprovado
  5. GET  /api/download/{token}-> libera o conteúdo (só se pago)
  (dev) POST /api/dev/approve/{id} -> simula aprovação no modo mock
"""
import hashlib
import hmac
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

import config
import storage
from gateway import get_gateway

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("quiz")

app = FastAPI(title="Quiz Glow-Up Réveillon", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Inicializa o banco já no import (idempotente) — garante as tabelas mesmo
# fora do ciclo de startup (ex.: testes, workers).
storage.init_db()


@app.on_event("startup")
def _startup():
    storage.init_db()
    gw = get_gateway()
    log.info("Gateway ativo: %s  | preço: R$ %.2f", gw.name, config.PRECO)
    if gw.name == "mock":
        log.warning(">> MODO MOCK: nenhum pagamento real. Defina MP_ACCESS_TOKEN para produção.")


# --------------------------------------------------------------------------- #
#  Models
# --------------------------------------------------------------------------- #
class QuizIn(BaseModel):
    answers: dict


class OrderIn(BaseModel):
    name: str
    email: EmailStr
    answers: dict
    diagnosis: str | None = None


# --------------------------------------------------------------------------- #
#  Entrega do conteúdo
# --------------------------------------------------------------------------- #
def entregar(order: dict):
    """Marca como entregue e dispara o e-mail (se SMTP configurado)."""
    if order.get("delivered"):
        return
    storage.mark_delivered(order["id"])
    link = f"{config.PUBLIC_BASE_URL}/api/download/{order['download_token']}"
    log.info("ENTREGA liberada p/ %s -> %s", order["email"], link)
    if config.SMTP_HOST:
        try:
            _enviar_email(order["email"], order["name"], link)
            log.info("E-mail enviado para %s", order["email"])
        except Exception as e:
            log.error("Falha ao enviar e-mail: %s", e)


def _enviar_email(to_email, nome, link):
    corpo = (
        f"Oi {nome}!\n\nSeu pagamento foi aprovado 🎉\n"
        f"Seu Cronograma de Transformação Capilar está em anexo neste e-mail,\n"
        f"e também pode ser baixado por aqui:\n{link}\n\n"
        "Qualquer dúvida é só responder este e-mail.\nBeijos 💕"
    )
    msg = MIMEMultipart()
    msg["Subject"] = "Seu Cronograma Capilar está liberado! 💆‍♀️"
    msg["From"] = config.EMAIL_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(corpo, "plain", "utf-8"))

    # anexa o PDF (o mesmo arquivo entregue na tela)
    p = Path(config.CONTEUDO_PATH)
    if p.exists():
        with open(p, "rb") as f:
            part = MIMEApplication(f.read(), _subtype=(p.suffix.lstrip(".") or "octet-stream"))
        part.add_header("Content-Disposition", "attachment",
                        filename=f"Cronograma-Capilar-Reveillon{p.suffix}")
        msg.attach(part)

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as s:
        s.starttls()
        if config.SMTP_USER:
            s.login(config.SMTP_USER, config.SMTP_PASS)
        s.send_message(msg)


# --------------------------------------------------------------------------- #
#  Rotas da API
# --------------------------------------------------------------------------- #
@app.post("/api/quiz")
def captura_quiz(data: QuizIn):
    storage.save_lead(data.answers)
    return {"ok": True}


@app.post("/api/orders")
def criar_pedido(data: OrderIn):
    gw = get_gateway()
    oid, token = storage.create_order(
        data.name, str(data.email), data.answers,
        data.diagnosis or "", config.PRECO, gw.name,
    )
    try:
        pix = gw.create_pix(
            amount=config.PRECO,
            description=config.PRODUTO_NOME,
            payer_email=str(data.email),
            payer_name=data.name,
            external_reference=oid,
        )
    except Exception as e:
        log.error("Erro ao criar Pix: %s", e)
        raise HTTPException(status_code=502, detail="Falha ao gerar cobrança Pix")

    storage.attach_payment(oid, pix["payment_id"], pix["qr_code"], pix["qr_code_base64"])
    return {
        "order_id": oid,
        "status": "pending",
        "gateway": gw.name,
        "amount": config.PRECO,
        "qr_code": pix["qr_code"],
        "qr_code_base64": pix["qr_code_base64"],
    }


@app.get("/api/orders/{order_id}")
def status_pedido(order_id: str):
    order = storage.get_order(order_id)
    if not order:
        raise HTTPException(404, "Pedido não encontrado")

    # Se ainda pendente, confirma com o gateway (fallback além do webhook)
    if order["status"] == "pending" and order.get("payment_id"):
        try:
            st = get_gateway().get_status(order["payment_id"])
            if st == "approved":
                storage.set_status(order_id, "approved")
                order = storage.get_order(order_id)
                entregar(order)
        except Exception as e:
            log.warning("Consulta de status falhou: %s", e)

    return {
        "order_id": order_id,
        "status": order["status"],
        "download_token": order["download_token"] if order["status"] in ("approved", "paid") else None,
    }


@app.post("/webhooks/mercadopago")
async def webhook_mp(request: Request):
    """Recebe a notificação do Mercado Pago e confirma o pagamento."""
    if not _assinatura_valida(request):
        log.warning("Webhook com assinatura inválida — ignorado")
        return JSONResponse({"ok": False}, status_code=401)

    body = await _safe_json(request)
    qp = request.query_params
    topic = qp.get("type") or qp.get("topic") or (body.get("type") if body else None)
    payment_id = (
        qp.get("data.id") or qp.get("id")
        or (body.get("data", {}) or {}).get("id") if body else None
    )
    if topic == "payment" and payment_id:
        try:
            st = get_gateway().get_status(str(payment_id))
            order = storage.get_order_by_payment(str(payment_id))
            if order and st == "approved":
                storage.set_status(order["id"], "approved")
                entregar(storage.get_order(order["id"]))
                log.info("Pagamento %s aprovado via webhook", payment_id)
        except Exception as e:
            log.error("Erro no webhook: %s", e)
    return {"ok": True}


@app.get("/api/download/{token}")
def download(token: str):
    # localiza o pedido pelo token
    import sqlite3
    with sqlite3.connect(config.DB_PATH) as c:
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT * FROM orders WHERE download_token=?", (token,)).fetchone()
    order = dict(row) if row else None
    if not order:
        raise HTTPException(404, "Link inválido")
    if order["status"] not in ("approved", "paid"):
        raise HTTPException(403, "Pagamento ainda não confirmado")

    path = Path(config.CONTEUDO_PATH)
    if not path.exists():
        raise HTTPException(500, "Conteúdo não encontrado no servidor")
    import mimetypes
    media = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, filename=f"Cronograma-Capilar-Reveillon{path.suffix}",
                        media_type=media)


# -------- Endpoint de TESTE: só funciona no modo mock -------- #
@app.post("/api/dev/approve/{order_id}")
def dev_approve(order_id: str):
    gw = get_gateway()
    if gw.name != "mock":
        raise HTTPException(403, "Disponível apenas no modo mock")
    order = storage.get_order(order_id)
    if not order:
        raise HTTPException(404, "Pedido não encontrado")
    gw.force_approve(order["payment_id"])
    storage.set_status(order_id, "approved")
    entregar(storage.get_order(order_id))
    return {"ok": True, "status": "approved"}


# --------------------------------------------------------------------------- #
#  Helpers de webhook
# --------------------------------------------------------------------------- #
async def _safe_json(request: Request):
    try:
        return await request.json()
    except Exception:
        return {}


def _assinatura_valida(request: Request) -> bool:
    """Valida x-signature do Mercado Pago (HMAC). Se não houver secret, aceita."""
    if config.USE_MOCK or not config.MP_WEBHOOK_SECRET:
        return True
    sig = request.headers.get("x-signature", "")
    req_id = request.headers.get("x-request-id", "")
    data_id = request.query_params.get("data.id", "")
    try:
        parts = dict(p.strip().split("=", 1) for p in sig.split(","))
        ts, v1 = parts.get("ts", ""), parts.get("v1", "")
        manifest = f"id:{data_id};request-id:{req_id};ts:{ts};"
        expected = hmac.new(config.MP_WEBHOOK_SECRET.encode(),
                            manifest.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, v1)
    except Exception:
        return False


# --------------------------------------------------------------------------- #
#  Servir o frontend (mesma origem -> sem CORS). Deixe por último.
# --------------------------------------------------------------------------- #
FRONT_DIR = config.PROJECT_DIR / "frontend"
if FRONT_DIR.exists():
    @app.get("/", response_class=HTMLResponse)
    def home():
        return (FRONT_DIR / "index.html").read_text(encoding="utf-8")

    app.mount("/", StaticFiles(directory=str(FRONT_DIR), html=True), name="static")
