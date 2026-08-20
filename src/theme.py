"""
Tema unico dos graficos da analise.

Existe porque cada figura estava herdando `plotly_white` cru: fonte do sistema,
titulo em negrito dentro da area do grafico, escala de cor diferente por figura
e nenhuma folga entre o titulo e o topo da area de plotagem. Sete graficos, sete
acabamentos.

Aqui a formatacao e definida uma vez e aplicada por `finish()`. Quem acrescentar
um grafico novo chama a mesma funcao e sai igual aos outros — e o PNG do README
passa a ser gerado pelo proprio script, em vez de recortado da tela.
"""

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

# --- tokens -----------------------------------------------------------------

INK      = "#1B1D21"   # texto primario
INK_MUT  = "#5B616B"   # texto secundario
INK_DIM  = "#8D939C"   # texto terciario
PAPER    = "#FFFFFF"
GRID     = "#ECEEF1"

BLUE     = "#2563EB"   # cor de dado primaria
BLUE_DIM = "#93B4F5"
AMBER    = "#B45309"   # atencao
GREEN    = "#0F766E"
RED      = "#B91C1C"
SLATE    = "#64748B"   # residual / "nao informado"

FONT = "Segoe UI, Inter, system-ui, sans-serif"

# Rampa sequencial usada em heatmap e barra colorida por valor. Uma so, em todo
# o relatorio: escala de cor diferente por figura faz o leitor recalibrar o olho
# a cada grafico.
SEQ = [[0.0, "#F1F5FD"], [0.5, "#7DA5F0"], [1.0, "#1E40AF"]]


def finish(fig: go.Figure, title: str, subtitle: str = "", height: int = 420) -> go.Figure:
    """Aplica o acabamento padrao. `title` e `subtitle` ficam fora da area de plotagem."""
    texto = f"<b>{title}</b>"
    if subtitle:
        texto += f"<br><span style='font-size:12px;color:{INK_DIM}'>{subtitle}</span>"
    fig.update_layout(
        template="plotly_white",
        title=dict(text=texto, x=0, xanchor="left", y=0.97, yanchor="top",
                   font=dict(size=17, color=INK, family=FONT)),
        font=dict(family=FONT, size=12, color=INK_MUT),
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        height=height,
        # t=90: com a margem padrao o subtitulo encostava na primeira linha de
        # grade e lia como se fosse rotulo do eixo.
        margin=dict(l=70, r=40, t=90 if subtitle else 70, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11, color=INK_MUT)),
        hoverlabel=dict(font=dict(family=FONT, size=12)),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, ticks="outside",
                     tickcolor=GRID, tickfont=dict(color=INK_MUT))
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor="rgba(0,0,0,0)",
                     tickfont=dict(color=INK_MUT))
    return fig


def save(fig: go.Figure, outdir: Path, name: str, png: bool = False,
         width: int = 1500) -> None:
    """Grava o HTML interativo e, quando pedido, o PNG estatico do README.

    `include_plotlyjs="cdn"` mantem cada HTML em ~30 KB em vez de ~4 MB — sete
    copias da biblioteca dentro do repositorio nao ajudam ninguem.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(outdir / f"{name}.html"), include_plotlyjs="cdn")
    if png:
        img = outdir.parent.parent / "docs" / "img"
        img.mkdir(parents=True, exist_ok=True)
        try:
            fig.write_image(str(img / f"{name}.png"), width=width,
                            height=fig.layout.height or 420, scale=2)
        except Exception as exc:                       # kaleido ausente
            print(f"  (PNG de {name} nao gerado: {exc})")
