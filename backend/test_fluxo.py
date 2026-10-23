"""Teste end-to-end do funil no modo mock (sem credencial)."""
from fastapi.testclient import TestClient
import main

c = TestClient(main.app)

# 1) captura de respostas do quiz
r = c.post("/api/quiz", json={"answers": {"estado": "seco", "objetivo": "brilho"}})
assert r.status_code == 200 and r.json()["ok"], r.text
print("[1] /api/quiz           -> OK (lead salvo)")

# 2) cria pedido + Pix
r = c.post("/api/orders", json={
    "name": "Maria Teste", "email": "maria@exemplo.com",
    "answers": {"estado": "seco", "incomodo": "brilho", "rotina": "nunca",
                "objetivo": "brilho", "tempo": "15"},
    "diagnosis": "Fios Sedentos de Brilho",
})
assert r.status_code == 200, r.text
o = r.json()
assert o["gateway"] == "mock"
assert o["qr_code"].startswith("00020126")           # copia e cola válido
assert len(o["qr_code_base64"]) > 100                # QR PNG gerado
oid = o["order_id"]
print(f"[2] /api/orders         -> OK (order={oid}, gateway={o['gateway']}, "
      f"copia-cola ok, qr_png={len(o['qr_code_base64'])} bytes b64)")

# 3) status antes do pagamento
r = c.get(f"/api/orders/{oid}")
assert r.json()["status"] == "pending"
assert r.json()["download_token"] is None
print("[3] /api/orders/{id}     -> OK (pending, download bloqueado)")

# 4) download bloqueado antes de pagar
# (pega o token real do banco só para provar que retorna 403)
import storage
tok = storage.get_order(oid)["download_token"]
r = c.get(f"/api/download/{tok}")
assert r.status_code == 403
print("[4] /api/download (pré)  -> OK (403, bloqueado sem pagamento)")

# 5) simula aprovação do Pix
r = c.post(f"/api/dev/approve/{oid}")
assert r.status_code == 200 and r.json()["status"] == "approved", r.text
print("[5] /api/dev/approve     -> OK (pagamento aprovado + entrega disparada)")

# 6) status após pagamento -> libera token
r = c.get(f"/api/orders/{oid}")
assert r.json()["status"] == "approved"
assert r.json()["download_token"], "token deveria ser liberado"
print("[6] /api/orders/{id}     -> OK (approved, download liberado)")

# 7) download do conteúdo (agora é o PDF)
r = c.get(f"/api/download/{tok}")
assert r.status_code == 200
assert r.content[:4] == b"%PDF", "o arquivo entregue deveria ser um PDF"
assert "pdf" in r.headers.get("content-type", "")
print(f"[7] /api/download (pós)  -> OK (200, PDF entregue, {len(r.content)} bytes, "
      f"tipo={r.headers.get('content-type')})")

print("\n✅ FLUXO COMPLETO PASSOU — quiz → Pix → webhook/aprovação → download")
