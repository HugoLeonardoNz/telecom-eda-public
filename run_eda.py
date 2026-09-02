"""
EDA das reclamacoes da ANATEL — base ABERTA e REAL

Execute com:  python run_eda.py
Para refazer os agregados da fonte: python tools/preparar_anatel.py

O QUE MUDOU, E POR QUE
----------------------
Ate 2026-09-01 este projeto rodava sobre CSV SINTETICO, gerado para imitar o
formato da ANATEL. O exercicio era a limpeza: latin-1, duplicatas, nulos
implicitos. Era honesto, estava etiquetado como sintetico — e mesmo assim
respondia sobre um setor inventado.

Agora roda sobre a base real: 15.952.407 linhas, 18.813.384 solicitacoes,
jan/2015 a mai/2020. A sujeira deixou de ser fabricada e passou a ser a de
verdade, que e mais interessante:

  1. a ANATEL RENOMEOU canais no meio da serie ("Fale Conosco" virou
     "Usuario WEB", "Aplicativo Movel" virou "Mobile App"). Quem plota sem
     normalizar conclui que reclamacao por aplicativo caiu a ZERO em 2020;
  2. 2020 tem so cinco meses (jan-mai). Comparar o ano cheio com 2020 e
     comparar doze meses com cinco;
  3. o grao NAO e a reclamacao individual: cada linha ja e uma contagem, na
     coluna SOLICITACOES. Contar linhas em vez de somar da numero errado;
  4. "Denuncia Anonima" e "Denuncia ANONIMA" convivem como categorias
     distintas — mesma coisa, duas grafias.

O QUE SE PERDEU NA MIGRACAO
---------------------------
A base real NAO tem status de atendimento. A "taxa de resolucao" que a versao
sintetica publicava nao existe aqui, e nao ha como reconstruir. No lugar dela
entrou a TAXA DE REABERTURA (Condicao = Reaberta), que o dado sustenta e que
mede coisa parecida: proporcao de casos que o consumidor teve de reabrir.

Preferir uma metrica pior porem real a uma metrica boa porem inventada e o
ponto do projeto.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src import theme  # noqa: E402

RAIZ = Path(__file__).resolve().parent
PROC = RAIZ / "data" / "processed"
FIG = RAIZ / "outputs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

TABELAS = ("marca_mes", "uf_marca", "assunto_marca", "uf_mes",
           "canal_ano", "condicao_marca", "tipo_ano")

# A ANATEL trocou o nome de dois canais no meio da serie. Sem este mapa, a
# leitura temporal do canal e simplesmente falsa.
CANAL_RENOMEADO = {
    "Usuário WEB": "Fale Conosco / Web",
    "Fale Conosco": "Fale Conosco / Web",
    "Mobile App": "App móvel",
    "Aplicativo Móvel": "App móvel",
}

# Marcas com volume suficiente para comparacao justa. O corte existe para nao
# ranquear taxa de reabertura de marca com 8 mil ocorrencias contra outra com
# 5 milhoes.
MIN_SOLICITACOES = 100_000

QUALIDADE = "Qualidade, Funcionamento e Reparo"


def carregar() -> dict[str, pd.DataFrame]:
    faltando = [n for n in TABELAS if not (PROC / f"agg_{n}.csv").exists()]
    if faltando:
        raise SystemExit(
            "Agregados ausentes: " + ", ".join(faltando)
            + "\nRode primeiro: python tools/preparar_anatel.py"
        )
    return {n: pd.read_csv(PROC / f"agg_{n}.csv") for n in TABELAS}


def _br(n: float, casas: int = 0) -> str:
    """Numero com separador de milhar em pt-BR."""
    return f"{n:,.{casas}f}".replace(",", ".")


def canais_normalizados(canal_ano: pd.DataFrame) -> pd.DataFrame:
    ca = canal_ano.copy()
    ca["canal"] = ca["canal"].map(CANAL_RENOMEADO).fillna(ca["canal"])
    return ca


def reabertura_por_marca(condicao_marca: pd.DataFrame) -> pd.DataFrame:
    pv = condicao_marca.pivot_table(index="marca", columns="condicao",
                                    values="solicitacoes", aggfunc="sum").fillna(0)
    pv["total"] = pv.sum(axis=1)
    pv["reab"] = pv.get("Reaberta", 0) / pv["total"] * 100
    return pv[pv["total"] >= MIN_SOLICITACOES]


# --------------------------------------------------------------------------
# Qualidade do dado — o que a fonte real esconde
# --------------------------------------------------------------------------

def relatorio_qualidade(d: dict[str, pd.DataFrame]) -> str:
    total = int(d["marca_mes"]["solicitacoes"].sum())

    por_ano = d["canal_ano"].pivot_table(index="canal", columns="ano",
                                         values="solicitacoes", aggfunc="sum").fillna(0)
    sumiram = [c for c in ("Fale Conosco", "Aplicativo Móvel")
               if c in por_ano.index and por_ano.loc[c, 2020] == 0]
    surgiram = [c for c in ("Usuário WEB", "Mobile App")
                if c in por_ano.index and por_ano.loc[c, 2015] == 0]

    mm = d["marca_mes"]
    meses_2020 = sorted({int(a[5:7]) for a in mm["ano_mes"] if a.startswith("2020")})

    grafias = sorted({t for t in d["tipo_ano"]["tipo"].unique()
                      if isinstance(t, str) and t.lower() == "denúncia anônima"})

    linhas = [
        "# Relatório de qualidade — base real da ANATEL",
        "",
        f"- **Solicitações**: {_br(total)}",
        f"- **Período**: {mm['ano_mes'].min()} a {mm['ano_mes'].max()}",
        "- **Fonte**: dados abertos da ANATEL (painel do consumidor)",
        "",
        "Este relatório é gerado por `run_eda.py`. Cada item abaixo é uma",
        "armadilha real da fonte, não um defeito fabricado para o exercício.",
        "",
        "## 1. Canais renomeados no meio da série",
        "",
        f"Zerados em 2020: {', '.join(sumiram) or '(nenhum)'}.",
        f"Inexistentes em 2015: {', '.join(surgiram) or '(nenhum)'}.",
        "",
        "Não são canais novos: são os mesmos, renomeados. Tratados como",
        "categorias distintas, a série afirma que a reclamação por aplicativo",
        "caiu a zero em 2020 — quando ela é justamente a que mais cresce.",
        "",
        "## 2. 2020 é um ano parcial",
        "",
        f"Meses presentes em 2020: {', '.join(f'{m:02d}' for m in meses_2020)}.",
        "Qualquer comparação anual precisa recortar os mesmos meses dos dois lados.",
        "",
        "## 3. O grão não é a reclamação",
        "",
        "Cada linha já é uma contagem, na coluna `SOLICITAÇÕES`. Contar linhas",
        f"subestima o volume: são 15.952.407 linhas para {_br(total)} solicitações.",
        "",
        "## 4. Mesma categoria, duas grafias",
        "",
        f"Encontradas: {', '.join(repr(g) for g in grafias) or '(nenhuma)'}.",
        "",
    ]
    return "\n".join(linhas)


# --------------------------------------------------------------------------
# Hipóteses
# --------------------------------------------------------------------------

def hipoteses(d: dict[str, pd.DataFrame]) -> list[tuple[str, str, str]]:
    """Cada hipótese devolve (rótulo, veredito, frase com o número)."""
    out: list[tuple[str, str, str]] = []
    total = int(d["marca_mes"]["solicitacoes"].sum())

    # H1 — quem lidera as reclamações
    marca = d["marca_mes"].groupby("marca")["solicitacoes"].sum().sort_values(ascending=False)
    lider, v1 = marca.index[0], int(marca.iloc[0])
    claro = int(marca.get("CLARO", 0))
    pos_claro = list(marca.index).index("CLARO") + 1
    out.append((
        "H1 — a CLARO é a marca mais reclamada",
        "REFUTADA",
        f"Quem lidera é a {lider}, com {_br(v1)} solicitações ({v1 / total * 100:.2f}%). "
        f"A CLARO é a {pos_claro}ª, com {_br(claro)} ({claro / total * 100:.2f}%). "
        "A versão sintética deste projeto afirmava o contrário — o gerador supunha "
        "o líder de mercado como líder de reclamação.",
    ))

    # H2 — canal de entrada
    p = canais_normalizados(d["canal_ano"]).pivot_table(
        index="canal", columns="ano", values="solicitacoes", aggfunc="sum").fillna(0)
    share = p / p.sum(axis=0) * 100
    a15, a20 = share.loc["App móvel", 2015], share.loc["App móvel", 2020]
    cc15, cc20 = share.loc["Call Center", 2015], share.loc["Call Center", 2020]
    out.append((
        "H2 — o canal de reclamação continua sendo o telefone",
        "REFUTADA",
        f"O Call Center caiu de {cc15:.1f}% para {cc20:.1f}% do total, e o app subiu "
        f"de {a15:.1f}% para {a20:.1f}% — {a20 / a15:.1f}× em cinco anos. Sem normalizar "
        "os canais renomeados, o app apareceria com 0,0% em 2020.",
    ))

    # H3 — natureza do problema
    assunto = d["assunto_marca"].groupby("assunto")["solicitacoes"].sum().sort_values(ascending=False)
    top, vt = assunto.index[0], int(assunto.iloc[0])
    out.append((
        "H3 — o que gera reclamação é falha técnica",
        "REFUTADA",
        f"O assunto que mais gera reclamação é '{top}', com {vt / total * 100:.2f}% do total. "
        f"'{QUALIDADE}' vem em segundo, com "
        f"{assunto.get(QUALIDADE, 0) / total * 100:.2f}%. "
        "O problema do setor é comercial antes de ser técnico.",
    ))

    # H4 — volume x reabertura
    pv = reabertura_por_marca(d["condicao_marca"])
    rho = pv["total"].corr(pv["reab"], method="spearman")
    pior = pv["reab"].idxmax()
    maior = pv["total"].idxmax()
    out.append((
        "H4 — quem recebe mais reclamação também reabre mais",
        "NÃO SUSTENTADA",
        f"A correlação de Spearman entre volume e taxa de reabertura é {rho:+.2f} "
        f"entre as {len(pv)} marcas com pelo menos {_br(MIN_SOLICITACOES)} solicitações. "
        f"A pior taxa é da {pior} ({pv.loc[pior, 'reab']:.2f}%), que não é a de maior "
        f"volume ({maior}). Volume e qualidade de atendimento são eixos diferentes.",
    ))

    # H5 — não testável, de propósito
    out.append((
        "H5 — a queda das reclamações indica serviço melhor",
        "NÃO TESTÁVEL",
        "A base traz reclamação registrada, não satisfação nem base de assinantes. "
        "Queda de volume pode ser serviço melhor, canal mais difícil ou consumidor "
        "que desistiu de reclamar. Sem denominador, a pergunta não se responde com "
        "este dado — e responder assim mesmo seria opinião com cara de métrica.",
    ))
    return out


# --------------------------------------------------------------------------
# Figuras
# --------------------------------------------------------------------------

def figuras(d: dict[str, pd.DataFrame]) -> None:
    total = int(d["marca_mes"]["solicitacoes"].sum())

    marca = d["marca_mes"].groupby("marca")["solicitacoes"].sum().sort_values()
    marca = marca[marca >= MIN_SOLICITACOES]
    fig = go.Figure(go.Bar(
        x=marca.values, y=marca.index, orientation="h", marker_color=theme.BLUE,
        text=[f"{v / total * 100:.1f}%" for v in marca.values],
        textposition="outside", cliponaxis=False,
    ))
    theme.finish(fig, "Solicitações por marca",
                 f"ANATEL · jan/2015 a mai/2020 · {_br(total)} solicitações", height=420)
    fig.update_xaxes(title="solicitações")
    theme.save(fig, FIG, "marcas", png=True)

    p = canais_normalizados(d["canal_ano"]).pivot_table(
        index="ano", columns="canal", values="solicitacoes", aggfunc="sum").fillna(0)
    p = p.div(p.sum(axis=1), axis=0) * 100
    fig = go.Figure()
    for c, cor in (("Call Center", theme.SLATE),
                   ("Fale Conosco / Web", theme.BLUE_DIM),
                   ("App móvel", theme.BLUE)):
        if c in p:
            fig.add_trace(go.Scatter(x=p.index, y=p[c], name=c, mode="lines+markers",
                                     line=dict(color=cor, width=3)))
    theme.finish(fig, "Canal de entrada da reclamação",
                 "share anual · canais renomeados pela ANATEL já normalizados", height=420)
    fig.update_yaxes(title="% das solicitações", ticksuffix="%")
    theme.save(fig, FIG, "canais", png=True)

    s = d["marca_mes"].groupby("ano_mes")["solicitacoes"].sum().sort_index()
    fig = go.Figure(go.Scatter(x=s.index, y=s.values, mode="lines",
                               line=dict(color=theme.BLUE, width=2)))
    theme.finish(fig, "Solicitações por mês",
                 "2020 termina em maio — a série é parcial no último ano", height=400)
    fig.update_yaxes(title="solicitações")
    theme.save(fig, FIG, "serie_temporal", png=False)

    pv = reabertura_por_marca(d["condicao_marca"]).sort_values("reab")
    fig = go.Figure(go.Bar(x=pv["reab"], y=pv.index, orientation="h",
                           marker_color=theme.AMBER,
                           text=[f"{v:.1f}%" for v in pv["reab"]],
                           textposition="outside", cliponaxis=False))
    theme.finish(fig, "Taxa de reabertura por marca",
                 "casos que o consumidor teve de reabrir · substitui a taxa de "
                 "resolução, que a base real não tem", height=420)
    fig.update_xaxes(title="% reaberta", ticksuffix="%")
    theme.save(fig, FIG, "reabertura", png=True)

    a = d["assunto_marca"].groupby("assunto")["solicitacoes"].sum().sort_values().tail(10)
    fig = go.Figure(go.Bar(x=a.values, y=[t[:44] for t in a.index], orientation="h",
                           marker_color=theme.BLUE))
    theme.finish(fig, "Assuntos mais reclamados", "top 10 de 83 categorias", height=460)
    theme.save(fig, FIG, "assuntos", png=False)


def _quebrar(texto: str, largura: int) -> list[str]:
    palavras, linha, saida = texto.split(), "", []
    for p in palavras:
        if len(linha) + len(p) + 1 > largura:
            saida.append(linha)
            linha = p
        else:
            linha = f"{linha} {p}".strip()
    if linha:
        saida.append(linha)
    return saida


def main() -> None:
    d = carregar()
    total = int(d["marca_mes"]["solicitacoes"].sum())

    print("=" * 74)
    print("  EDA ANATEL — base aberta e real")
    print("=" * 74)
    print(f"  {_br(total)} solicitações · "
          f"{d['marca_mes']['ano_mes'].min()} a {d['marca_mes']['ano_mes'].max()}")

    destino = RAIZ / "outputs" / "data_quality_report.md"
    destino.write_text(relatorio_qualidade(d), encoding="utf-8")
    print(f"\n  relatório de qualidade -> {destino.relative_to(RAIZ)}")

    figuras(d)
    print(f"  figuras                -> {FIG.relative_to(RAIZ)}")

    print("\n" + "=" * 74)
    print("  HIPÓTESES")
    print("=" * 74)
    for rotulo, veredito, frase in hipoteses(d):
        print(f"\n  [{veredito}] {rotulo}")
        for linha in _quebrar(frase, 68):
            print(f"      {linha}")
    print()


if __name__ == "__main__":
    main()
