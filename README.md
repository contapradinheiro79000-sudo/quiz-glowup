# Quiz Glow-Up Réveillon 💆‍♀️

Funil completo de quiz interativo → diagnóstico → checkout Pix → entrega automática.
Nicho de autocuidado/glow-up feminino de fim de ano.

- **Frontend:** HTML + Tailwind (um arquivo, mobile-first, roda em qualquer lugar)
- **Backend:** FastAPI (Python) com Pix via **Mercado Pago** + **webhook** + entrega automática
- **Modo mock:** roda de ponta a ponta **sem precisar de conta/credencial** (pra testar hoje)

```
quiz-glowup/
├── frontend/index.html              # o quiz (5 perguntas, animação, checkout Pix)
├── backend/
│   ├── main.py                      # API + rotas + webhook + entrega
│   ├── gateway.py                   # Mercado Pago (real) + Mock (teste)
│   ├── storage.py                   # SQLite (pedidos e leads)
│   ├── config.py                    # lê variáveis do .env
│   ├── requirements.txt
│   ├── .env.example
│   └── test_fluxo.py                # teste automático do funil
└── conteudo/cronograma_capilar.html # o produto entregue após o pagamento
```

---

## 1. Rodar localmente (5 minutos)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# opcional: copie o exemplo de config (sem token = modo mock)
cp .env.example .env

uvicorn main:app --reload --port 8000
```

Abra **http://localhost:8000** no navegador (de preferência no modo mobile do DevTools).
O FastAPI já serve o frontend na mesma origem — não precisa abrir o `index.html` separado.

### Testar o pagamento no modo mock
No modo mock aparece um botão **"🧪 Simular pagamento aprovado"** na tela do Pix.
Clicou → o status vira aprovado e a tela de download libera sozinha. É assim que o
Mercado Pago real vai se comportar quando o Pix cair.

### Rodar o teste automático do funil
```bash
source .venv/bin/activate
python test_fluxo.py
```
Valida: captura do quiz → criação do Pix → bloqueio do download → aprovação → liberação.

---

## 2. Ligar o Mercado Pago de verdade

1. Crie conta e acesse o [painel de desenvolvedores](https://www.mercadopago.com.br/developers).
2. Em **Suas integrações → Credenciais**, copie o **Access Token** (produção).
3. No `.env`:
   ```env
   MP_ACCESS_TOKEN=APP_USR-xxxxxxxx...
   PUBLIC_BASE_URL=https://seu-backend.onrender.com
   ```
4. Em **Webhooks**, cadastre a URL `https://seu-backend.onrender.com/webhooks/mercadopago`
   e eventos de **pagamentos**. Copie a assinatura secreta para `MP_WEBHOOK_SECRET` (valida a origem).

Com `MP_ACCESS_TOKEN` preenchido, o sistema sai do mock automaticamente e passa a gerar
Pix real (QR + copia e cola) e a confirmar via webhook.

> **Trocar por Asaas:** é só criar uma classe em `gateway.py` com os métodos
> `create_pix(...)` e `get_status(...)` e apontar a `get_gateway()` para ela. O resto não muda.

---

## 3. Colocar no ar de graça

### Backend → Render (free)
1. Suba o projeto num repositório no GitHub.
2. No [Render](https://render.com): **New → Web Service**, aponte pro repo, pasta `backend`.
3. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Em **Environment**, adicione as variáveis do `.env` (`MP_ACCESS_TOKEN`, `PUBLIC_BASE_URL` = a URL que o Render te der, etc.).

> O plano free do Render "dorme" após inatividade (primeira requisição demora alguns segundos).
> Para o webhook, isso é ok. Alternativas free: Railway, Fly.io.

### Frontend → já vem junto (ou separado na Vercel)
O backend **já serve o frontend**, então publicar o backend no Render basta.

Se quiser o frontend separado na **Vercel** (CDN, mais rápido):
1. Publique a pasta `frontend/` como projeto estático na Vercel.
2. No `frontend/index.html`, troque a constante:
   ```js
   const API_BASE = "https://seu-backend.onrender.com";
   ```
3. No backend, ajuste o CORS no `.env`:
   ```env
   CORS_ORIGINS=https://seu-quiz.vercel.app
   ```

---

## 4. E-mail automático (opcional)
Para enviar o link do produto por e-mail quando o Pix for aprovado, preencha no `.env`:
```env
SMTP_HOST=smtp.seuprovedor.com
SMTP_PORT=587
SMTP_USER=seu@email.com
SMTP_PASS=suasenha
EMAIL_FROM=seu@email.com
```
Sem SMTP, a entrega acontece na própria tela (botão de download) e o link vai pro log do servidor.

---

## Fluxo técnico resumido
```
Quiz (5 perguntas) → diagnóstico calculado no front → CTA R$29,90
   → POST /api/orders  (cria pedido + Pix: QR e copia-e-cola)
   → front faz polling em GET /api/orders/{id}
   → Mercado Pago aprova → POST /webhooks/mercadopago  (confirma + libera entrega)
   → GET /api/download/{token}  (conteúdo só sai se status = approved)
```

## Personalizar
- **Perguntas / diagnóstico:** `frontend/index.html` → `QUESTIONS` e `gerarDiagnostico()`.
- **Preço:** `.env` → `PRECO`.
- **Produto entregue:** troque `conteudo/cronograma_capilar.html` (pode ser PDF — ajuste `CONTEUDO_PATH` e o `media_type` em `main.py`).
- **Cores/visual:** bloco `tailwind.config` e `<style>` no topo do `index.html`.
