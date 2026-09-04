"""
Os achados publicados, como asserção — EDA ANATEL (base real)

Execute com: pytest tests/ -v

POR QUE ESTE ARQUIVO EXISTE
---------------------------
O README declara hipóteses com veredito e cita números exatos. Nada disso era
verificado antes. Em outros repositórios deste portfólio a mesma ausência deixou
o texto e o código divergirem por meses — um deles chegou a publicar "São Paulo
tem a melhor taxa do país" enquanto o próprio CSV do repositório dizia que era
o 5º. Aqui a asserção lê os mesmos agregados que o `run_eda.py` publica.

O QUE MUDOU EM 2026-09-01
-------------------------
O projeto migrou de CSV sintético para a base ABERTA E REAL da ANATEL
(15.952.407 linhas, 18.813.384 solicitações, jan/2015 a mai/2020). Os testes
antigos afirmavam coisas sobre o gerador — "motivo #1 em 35,4%", "top 3 em
86,0%" — e não sobreviveram à migração, porque mediam dado inventado.

Estes testam três coisas diferentes:

  1. os números que o README publica batem com os agregados versionados;
  2. as armadilhas da fonte continuam tratadas (canal renomeado, ano parcial,
     grão agregado) — se alguém remover a normalização, o teste quebra;
  3. H5 continua SEM veredito, porque confirmá-la exigiria um denominador que
     a base não tem.
"""

import os
import sys

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)

PROC = os.path.join(RAIZ, "data", "processed")

# Os números que o README publica. Espelhados aqui de propósito: se o agregado
# mudar, o teste falha e obriga a atualizar o texto — que é o ponto.
TOTAL = 18_813_384
LINHAS_FONTE = 15_952_407
LIDER = "OI"
LIDER_SHARE = 26.36
CLARO_POSICAO = 4
COBRANCA_SHARE = 33.62
APP_2015, APP_2020 = 2.8, 21.4
CALL_2015, CALL_2020 = 64.8, 42.8
PIOR_REABERTURA = "NEXTEL"


@pytest.fixture(scope="module")
def agg():
    import run_eda
    if not os.path.isdir(PROC) or not os.listdir(PROC):
        pytest.skip("agregados ausentes — rode tools/preparar_anatel.py")
    return run_eda.carregar()


@pytest.fixture(scope="module")
def eda():
    import run_eda
    return run_eda


# --- 1. os números publicados -----------------------------------------------


def test_total_de_solicitacoes(agg):
    assert int(agg["marca_mes"]["solicitacoes"].sum()) == TOTAL


def test_todo_agregado_fecha_no_mesmo_total(agg):
    """Sete recortes do mesmo dado: divergir significa erro de agregação."""
    for nome, df in agg.items():
        assert int(df["solicitacoes"].sum()) == TOTAL, f"agg_{nome} não fecha"


def test_h1_a_oi_lidera_e_a_claro_e_a_quarta(agg):
    marca = agg["marca_mes"].groupby("marca")["solicitacoes"].sum().sort_values(ascending=False)
    assert marca.index[0] == LIDER
    assert round(marca.iloc[0] / TOTAL * 100, 2) == LIDER_SHARE
    assert list(marca.index).index("CLARO") + 1 == CLARO_POSICAO


def test_h3_cobranca_domina(agg, eda):
    assunto = agg["assunto_marca"].groupby("assunto")["solicitacoes"].sum().sort_values(ascending=False)
    assert assunto.index[0] == "Cobrança"
    assert round(assunto.iloc[0] / TOTAL * 100, 2) == COBRANCA_SHARE
    # o segundo colocado é o técnico — é o que torna H3 refutada, não trivial
    assert assunto.index[1] == eda.QUALIDADE


def test_h4_pior_reabertura_nao_e_a_de_maior_volume(agg, eda):
    pv = eda.reabertura_por_marca(agg["condicao_marca"])
    assert pv["reab"].idxmax() == PIOR_REABERTURA
    assert pv["reab"].idxmax() != pv["total"].idxmax()


# --- 2. as armadilhas da fonte continuam tratadas ---------------------------


def test_canais_renomeados_continuam_normalizados(agg, eda):
    """Sem o mapa, o app aparece com 0,0% em 2020 — e a conclusão inverte."""
    cru = agg["canal_ano"].pivot_table(index="canal", columns="ano",
                                       values="solicitacoes", aggfunc="sum").fillna(0)
    assert cru.loc["Aplicativo Móvel", 2020] == 0, "a fonte mudou; revisar o mapa"
    assert cru.loc["Mobile App", 2015] == 0

    p = eda.canais_normalizados(agg["canal_ano"]).pivot_table(
        index="canal", columns="ano", values="solicitacoes", aggfunc="sum").fillna(0)
    share = p / p.sum(axis=0) * 100
    assert round(share.loc["App móvel", 2015], 1) == APP_2015
    assert round(share.loc["App móvel", 2020], 1) == APP_2020
    assert round(share.loc["Call Center", 2015], 1) == CALL_2015
    assert round(share.loc["Call Center", 2020], 1) == CALL_2020


def test_mapa_de_canal_cobre_os_dois_pares(eda):
    assert set(eda.CANAL_RENOMEADO) == {
        "Usuário WEB", "Fale Conosco", "Mobile App", "Aplicativo Móvel"
    }
    assert len(set(eda.CANAL_RENOMEADO.values())) == 2


def test_2020_e_parcial(agg):
    """Comparar 2020 com ano cheio é comparar 5 meses com 12."""
    meses = {a[5:7] for a in agg["marca_mes"]["ano_mes"] if a.startswith("2020")}
    assert meses == {"01", "02", "03", "04", "05"}


def test_o_grao_nao_e_a_reclamacao(agg):
    """Contar linhas subestima: a fonte tem menos linhas que solicitações."""
    assert TOTAL > LINHAS_FONTE


def test_relatorio_de_qualidade_documenta_as_armadilhas(agg, eda):
    md = eda.relatorio_qualidade(agg)
    for termo in ("renomeados", "parcial", "grão não é a reclamação", "duas grafias"):
        assert termo.lower() in md.lower(), f"o relatório deixou de citar: {termo}"


# --- 3. H5 continua sem veredito -------------------------------------------


def test_h5_nao_recebe_veredito(agg, eda):
    hs = {r: v for r, v, _ in eda.hipoteses(agg)}
    h5 = [r for r in hs if r.startswith("H5")]
    assert h5, "H5 sumiu"
    assert hs[h5[0]] == "NÃO TESTÁVEL", (
        "H5 ganhou veredito. Confirmá-la exigiria base de assinantes, que a fonte "
        "não tem — o veredito mediria a suposição, não o setor."
    )


def test_as_outras_hipoteses_tem_veredito(agg, eda):
    hs = eda.hipoteses(agg)
    assert len(hs) == 5
    for rotulo, veredito, frase in hs:
        assert veredito, f"{rotulo} sem veredito"
        assert any(c.isdigit() for c in frase) or veredito == "NÃO TESTÁVEL", (
            f"{rotulo} não cita número"
        )


# --- 4. procedência ---------------------------------------------------------


def test_readme_declara_dado_observado_e_nao_sintetico():
    md = open(os.path.join(RAIZ, "README.md"), encoding="utf-8").read()
    assert "sintéticos" not in md.split("## ")[0], (
        "o cabeçalho ainda anuncia dado sintético"
    )
    assert "ANATEL" in md and ("observad" in md.lower() or "real" in md.lower())


# ─────────────────────────────────────────────────────────────────────────────
# RFM — as afirmações do README viram asserção
#
# A tabela de segmentos do README trazia números com "~" que o pipeline NUNCA
# produziu: dizia 61 "Leais" contra 32 reais, 5.600 de MRR em "Campeões" contra
# 8.736, listava "Perdidos" com 45 contratos quando o segmento sai vazio, e
# omitia inteiramente o balde "Outros" — que é o maior bloco de MRR da base.
# Eram estimativas escritas à mão numa tabela que parecia saída de execução.
#
# Estes testes existem para que isso não volte: se o número do README divergir
# do pipeline, o CI quebra. Mesmo princípio das suítes de market-expansion e
# sql-analytics-pack.
# ─────────────────────────────────────────────────────────────────────────────
import sys as _sys
from pathlib import Path as _Path

_SRC = _Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in _sys.path:
    _sys.path.insert(0, str(_SRC))


def _resumo_rfm():
    from fibernet import REFERENCE_DATE, gerar_base
    from rfm import assign_segments, calculate_rfm, score_rfm, segment_summary

    contratos, boletos = gerar_base()
    rfm = assign_segments(score_rfm(calculate_rfm(contratos, boletos,
                                                  reference_date=REFERENCE_DATE)))
    return contratos, boletos, rfm, segment_summary(rfm)


def test_base_sintetica_e_reprodutivel():
    """Mesma semente, mesma base — é o que separa sintético de inventado."""
    contratos, boletos, _, _ = _resumo_rfm()
    assert len(contratos) == 300
    assert len(boletos) == 4398, "o README publica 4.398 boletos"
    assert int(boletos["paid_at"].notna().sum()) == 4306


def test_rfm_cobre_288_dos_300_contratos():
    """Cliente sem boleto pago não tem R, F nem M — e o README diz isso."""
    _, _, rfm, _ = _resumo_rfm()
    assert len(rfm) == 288


def test_tabela_de_segmentos_do_readme():
    _, _, _, resumo = _resumo_rfm()
    esperado = {
        "Outros":           (63, 11697),
        "Campeões":         (54, 8736),
        "Hibernando":       (73, 8507),
        "Em Risco":         (38, 5242),
        "Leais":            (32, 4048),
        "Potenciais Leais": (28, 3332),
    }
    obtido = {r["segment"]: (int(r["clientes"]), round(r["mrr_total"]))
              for _, r in resumo.iterrows()}
    assert obtido == esperado


def test_o_residual_e_o_maior_bloco_de_mrr():
    """O achado que o README passou a declarar em vez de esconder."""
    _, _, _, resumo = _resumo_rfm()
    maior = resumo.sort_values("mrr_total", ascending=False).iloc[0]
    assert maior["segment"] == "Outros"
    assert maior["clientes"] / resumo["clientes"].sum() > 0.20


def test_perdidos_sai_vazio():
    """Existe nas regras e não classifica ninguém — o README declara isso."""
    from rfm import SEGMENT_RULES
    _, _, _, resumo = _resumo_rfm()
    assert "Perdidos" in {r["segment"] for r in SEGMENT_RULES}
    assert "Perdidos" not in set(resumo["segment"])
