#!/usr/bin/env python3
"""
Gerador de PDF premium a partir de Markdown/texto.
Transforma o cronograma (ou qualquer .md) num PDF diagramado com capa,
em formato A4 ou Mobile, pronto para ser o arquivo entregue no funil.

Uso:
    python gerar_pdf.py cronograma.md
    python gerar_pdf.py cronograma.md -o saida.pdf --format mobile
    python gerar_pdf.py cronograma.md --title "Meu Guia" --subtitle "Edição 2026"

Requisitos:
    pip install weasyprint markdown
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

import markdown
from weasyprint import HTML

# --------------------------------------------------------------------------- #
#  Paleta / marca  (troque aqui para reaproveitar em outros nichos)
# --------------------------------------------------------------------------- #
BRAND = {
    "primary": "#f24a85",
    "primary_dark": "#b11f59",
    "accent": "#ff9fbf",
    "ink": "#2b2b2b",
    "soft": "#fff5f7",
    "mark": "Glow Réveillon",
}

FORMATS = {
    # nome: (largura, altura, margem)  — valores CSS
    "a4":     ("210mm", "297mm", "18mm 16mm"),
    "mobile": ("150mm", "266mm", "14mm 12mm"),  # proporção ~9:16, leitura no celular
}


def css_premium(fmt: str) -> str:
    w, h, margin = FORMATS[fmt]
    p = BRAND
    return f"""
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&family=Nunito:wght@400;600;700&display=swap');

    @page {{
        size: {w} {h};
        margin: {margin};
        @bottom-center {{
            content: "{p['mark']}  ·  página " counter(page);
            font-family: 'Nunito', sans-serif; font-size: 9px; color: #c98ba5;
        }}
    }}
    @page cover {{ margin: 0; }}

    * {{ box-sizing: border-box; }}
    body {{
        font-family: 'Nunito', 'DejaVu Sans', sans-serif;
        color: {p['ink']}; font-size: 12.5px; line-height: 1.65;
    }}

    /* ---------- CAPA ---------- */
    .cover {{
        page: cover; page-break-after: always;
        height: {h}; width: {w};
        background: linear-gradient(150deg, {p['primary']} 0%, {p['primary_dark']} 55%, #7d1442 100%);
        color: #fff; position: relative; overflow: hidden;
        display: flex; flex-direction: column; justify-content: center;
        padding: 0 16mm;
    }}
    .cover::before {{
        content: ""; position: absolute; top: -120px; right: -120px;
        width: 360px; height: 360px; border-radius: 50%;
        background: rgba(255,255,255,.12);
    }}
    .cover::after {{
        content: ""; position: absolute; bottom: -90px; left: -90px;
        width: 260px; height: 260px; border-radius: 50%;
        background: rgba(255,255,255,.08);
    }}
    .cover .kicker {{
        font-family: 'Poppins', sans-serif; font-weight: 700; letter-spacing: 3px;
        text-transform: uppercase; font-size: 11px; opacity: .9; margin-bottom: 14px;
    }}
    .cover h1 {{
        font-family: 'Poppins', sans-serif; font-weight: 800; font-size: 33px;
        line-height: 1.12; margin: 0 0 14px; max-width: 95%;
        color: #fff; word-break: break-word;
    }}
    .cover .sub {{ font-size: 15px; opacity: .95; max-width: 85%; }}
    .cover .seal {{
        position: absolute; bottom: 22mm; left: 16mm;
        font-family: 'Poppins', sans-serif; font-weight: 700; font-size: 12px;
        background: rgba(255,255,255,.18); padding: 8px 16px; border-radius: 999px;
    }}
    .cover .badge {{
        position: absolute; top: 20mm; right: 16mm;
        width: 70px; height: 70px; border-radius: 20px;
        background: rgba(255,255,255,.2);
        display: flex; align-items: center; justify-content: center; font-size: 34px;
    }}

    /* ---------- CONTEÚDO ---------- */
    h1 {{
        font-family: 'Poppins', sans-serif; font-weight: 800; color: {p['primary_dark']};
        font-size: 21px; margin: 26px 0 6px; page-break-after: avoid;
    }}
    main h1::before {{ content: "✦ "; color: {p['primary']}; }}
    h2 {{
        font-family: 'Poppins', sans-serif; color: {p['primary']};
        font-size: 16px; margin-top: 18px;
    }}
    p {{ margin: 8px 0; }}
    strong {{ color: {p['primary_dark']}; }}

    table {{
        width: 100%; border-collapse: collapse; margin: 12px 0;
        font-size: 11.5px; page-break-inside: avoid;
    }}
    th, td {{ border: 1px solid #f0c9d8; padding: 7px 9px; text-align: left; }}
    th {{ background: {p['soft']}; color: {p['primary_dark']};
          font-family: 'Poppins', sans-serif; font-weight: 600; }}
    tr:nth-child(even) td {{ background: #fffafc; }}

    blockquote {{
        margin: 14px 0; padding: 12px 16px;
        background: #fffbe6; border-left: 4px solid {p['accent']};
        border-radius: 8px; font-size: 12px; page-break-inside: avoid;
    }}
    blockquote p {{ margin: 0; }}
    blockquote::before {{ content: "💡 "; }}

    ol, ul {{ margin: 8px 0 8px 2px; padding-left: 20px; }}
    li {{ margin-bottom: 5px; }}

    .toc-divider {{ height: 3px; width: 60px; background: {p['accent']};
                    border-radius: 3px; margin: 2px 0 18px; }}
    """


def construir_html(md_text: str, title: str, subtitle: str, fmt: str) -> str:
    corpo = markdown.markdown(
        md_text,
        extensions=["extra", "tables", "sane_lists"],
    )
    hoje = datetime.now().strftime("%d/%m/%Y")
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<style>{css_premium(fmt)}</style></head>
<body>
  <section class="cover">
    <div class="badge">💆‍♀️</div>
    <div class="kicker">{BRAND['mark']} · Edição Réveillon</div>
    <h1>{title}</h1>
    <p class="sub">{subtitle}</p>
    <div class="seal">Protocolo exclusivo · {hoje}</div>
  </section>
  <main>
    <div class="toc-divider"></div>
    {corpo}
  </main>
</body></html>"""


def main():
    ap = argparse.ArgumentParser(description="Gera PDF premium a partir de Markdown.")
    ap.add_argument("input", help="arquivo .md de entrada")
    ap.add_argument("-o", "--output", help="arquivo .pdf de saída")
    ap.add_argument("--format", choices=list(FORMATS), default="a4",
                    help="formato da página (a4 ou mobile)")
    ap.add_argument("--title", default="Cronograma de Transformação Capilar",
                    help="título da capa")
    ap.add_argument("--subtitle",
                    default="Seu protocolo semana a semana para chegar a 31/12 com o cabelo no auge.",
                    help="subtítulo da capa")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        sys.exit(f"Arquivo não encontrado: {src}")

    out = Path(args.output) if args.output else src.with_suffix(f".{args.format}.pdf")
    md_text = src.read_text(encoding="utf-8")
    html = construir_html(md_text, args.title, args.subtitle, args.format)
    HTML(string=html).write_pdf(str(out))
    kb = out.stat().st_size / 1024
    print(f"✅ PDF gerado: {out}  ({kb:.0f} KB, formato {args.format})")


if __name__ == "__main__":
    main()
