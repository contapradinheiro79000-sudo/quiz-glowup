"""
Camada de pagamento Pix com duas implementações:
  - MercadoPagoGateway : chamadas reais à API do Mercado Pago (quando há Access Token)
  - MockGateway        : simula tudo localmente (sem conta/credencial)

Trocar para Asaas depois é só criar uma classe com os mesmos 2 métodos
(create_pix / get_status) e apontar a factory para ela.
"""
import uuid
import base64
import io
import httpx
import config


# --------------------------------------------------------------------------- #
#  MERCADO PAGO (produção)
# --------------------------------------------------------------------------- #
class MercadoPagoGateway:
    name = "mercadopago"
    API = "https://api.mercadopago.com"

    def __init__(self, access_token: str):
        self.token = access_token

    def _headers(self, idem: str | None = None):
        h = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        if idem:
            h["X-Idempotency-Key"] = idem
        return h

    def create_pix(self, *, amount, description, payer_email, payer_name, external_reference):
        payload = {
            "transaction_amount": round(float(amount), 2),
            "description": description,
            "payment_method_id": "pix",
            "notification_url": f"{config.PUBLIC_BASE_URL}/webhooks/mercadopago",
            "external_reference": external_reference,
            "payer": {
                "email": payer_email,
                "first_name": (payer_name or "Cliente").split(" ")[0],
            },
        }
        with httpx.Client(timeout=20) as cli:
            r = cli.post(f"{self.API}/v1/payments",
                         headers=self._headers(idem=str(uuid.uuid4())),
                         json=payload)
        r.raise_for_status()
        data = r.json()
        tx = data.get("point_of_interaction", {}).get("transaction_data", {}) or {}
        return {
            "payment_id": str(data["id"]),
            "status": data.get("status", "pending"),
            "qr_code": tx.get("qr_code", ""),                 # copia e cola
            "qr_code_base64": tx.get("qr_code_base64", ""),   # imagem PNG em base64
        }

    def get_status(self, payment_id: str) -> str:
        with httpx.Client(timeout=20) as cli:
            r = cli.get(f"{self.API}/v1/payments/{payment_id}", headers=self._headers())
        r.raise_for_status()
        return r.json().get("status", "pending")  # "approved" quando pago


# --------------------------------------------------------------------------- #
#  MOCK (desenvolvimento / demo) — não cobra nada, aprova via endpoint /dev
# --------------------------------------------------------------------------- #
class MockGateway:
    name = "mock"

    def __init__(self):
        self._status: dict[str, str] = {}

    @staticmethod
    def _fake_qr_png(text: str) -> str:
        """Gera um QR PNG de verdade se a lib 'qrcode' existir; senão retorna vazio."""
        try:
            import qrcode
            img = qrcode.make(text)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode()
        except Exception:
            return ""  # o frontend mostra um placeholder quando vier vazio

    def create_pix(self, *, amount, description, payer_email, payer_name, external_reference):
        pid = "mock_" + uuid.uuid4().hex[:12]
        copia_cola = (
            "00020126580014BR.GOV.BCB.PIX0136"
            f"{uuid.uuid4().hex}520400005303986540{amount:.2f}"
            "5802BR5913QUIZ GLOWUP6009SAO PAULO62070503***6304MOCK"
        )
        self._status[pid] = "pending"
        return {
            "payment_id": pid,
            "status": "pending",
            "qr_code": copia_cola,
            "qr_code_base64": self._fake_qr_png(copia_cola),
        }

    def get_status(self, payment_id: str) -> str:
        return self._status.get(payment_id, "pending")

    def force_approve(self, payment_id: str):
        self._status[payment_id] = "approved"


# --------------------------------------------------------------------------- #
#  FACTORY (singleton)
# --------------------------------------------------------------------------- #
_gateway = None


def get_gateway():
    global _gateway
    if _gateway is None:
        if config.USE_MOCK:
            _gateway = MockGateway()
        else:
            _gateway = MercadoPagoGateway(config.MP_ACCESS_TOKEN)
    return _gateway
