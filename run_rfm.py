"""Roda a análise RFM da FiberNet de ponta a ponta e gera a figura do README.

POR QUE ESTE ARQUIVO EXISTE
───────────────────────────
Metade deste repositório é a EDA da ANATEL e a outra metade é o RFM. Só a
primeira tinha figura no README e roteiro executável; o RFM existia como
notebook, que ninguém abre para avaliar candidato — e cujo número ninguém
confere.

Uso:
    python run_rfm.py

Saída:
    outputs/figures/rfm_segmentos.html   interativo
    docs/img/rfm.png                     a figura do README
    outputs/rfm_segmentos.csv            a tabela por trás da figura
"""
from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

import theme                                                   # noqa: E402
from fibernet import REFERENCE_DATE, gerar_base                # noqa: E402
from rfm import assign_segments, calculate_rfm, score_rfm, segment_summary  # noqa: E402

OUT = RAIZ / "outputs"
FIG = OUT / "figures"

# Cor por intenção, não por ordem: o que exige ação agora em vermelho, o que
# sustenta a receita em verde, o resto em neutro. A ordem das barras é o MRR,
# porque a pergunta do painel é "onde está o dinheiro que pode sair".
COR_SEGMENTO = {
    "Campeões":         theme.GREEN,
    "Leais":            theme.GREEN,
    "Potenciais Leais": theme.BLUE,
    "Em Risco":         theme.RED,
    "Hibernando":       theme.AMBER,
    "Perdidos":         theme.SLATE,
}


def main() -> int:
    contratos, boletos = gerar_base()
    print(f"Base sintética · {len(contratos)} contratos · {len(boletos)} boletos "
          f"({int(boletos['paid_at'].notna().sum())} pagos)")

    rfm = calculate_rfm(contratos, boletos, reference_date=REFERENCE_DATE)
    rfm = assign_segments(score_rfm(rfm))
    resumo = segment_summary(rfm).sort_values("mrr_total", ascending=True)

    OUT.mkdir(parents=True, exist_ok=True)
    resumo.to_csv(OUT / "rfm_segmentos.csv", index=False, encoding="utf-8")

    fig = go.Figure(go.Bar(
        x=resumo["mrr_total"],
        y=resumo["segment"],
        orientation="h",
        marker_color=[COR_SEGMENTO.get(s, theme.SLATE) for s in resumo["segment"]],
        text=[f"R$ {v:,.0f}".replace(",", ".") for v in resumo["mrr_total"]],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>MRR R$ %{x:,.0f}<br>%{customdata} contratos<extra></extra>",
        customdata=resumo["clientes"],
    ))
    em_risco = resumo.loc[resumo["segment"] == "Em Risco", "mrr_total"]
    sub = (f"Base sintética de {len(contratos)} contratos · referência "
           f"{REFERENCE_DATE:%d/%m/%Y}")
    if not em_risco.empty:
        sub += f" · R$ {em_risco.iloc[0]:,.0f}".replace(",", ".") + " de MRR em Em Risco"
    theme.finish(fig, "MRR por segmento RFM", sub, height=440)
    fig.update_xaxes(title="MRR mensal (R$)")
    # O rótulo do maior valor encostava na borda direita e ficava cortado no PNG.
    fig.update_layout(xaxis_range=[0, resumo["mrr_total"].max() * 1.18])
    theme.save(fig, FIG, "rfm_segmentos", png=True, width=1400)

    print()
    print(f"{'segmento':<18} {'contratos':>10} {'MRR':>12}")
    for _, r in resumo.sort_values("mrr_total", ascending=False).iterrows():
        print(f"{r['segment']:<18} {int(r['clientes']):>10} {r['mrr_total']:>12,.0f}")
    print(f"\nFiguras em {FIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
