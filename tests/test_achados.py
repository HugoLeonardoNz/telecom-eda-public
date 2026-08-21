"""
Os achados publicados, como asserção — EDA ANATEL

Execute com: pytest tests/ -v   (roda `run_eda.py` antes, uma vez)

POR QUE ESTE ARQUIVO EXISTE
---------------------------
O README declara quatro hipóteses com veredito e cita números exatos: motivo #1
em 35,4%, top 3 em 86,0%, gap de resolução em 4,9pp. Nada disso era verificado.
Em outros repositórios deste portfólio a mesma ausência deixou o texto e o código
divergirem por meses — um deles chegou a publicar "São Paulo tem a melhor taxa do
país" enquanto o próprio CSV do repositório dizia que era o 5º.

Aqui a asserção lê o que o `run_eda.py` imprime, que é a mesma fonte que o README
cita. Se o gerador ou a limpeza mudarem, o teste falha e obriga a atualizar o
texto, em vez de deixar os dois se afastarem em silêncio.

H5 não tem teste de veredito de propósito: `UF_DIST` é participação populacional
escrita à mão, então correlacionar volume com população mediria o gerador. O que
se testa aqui é que ela continua SEM veredito.
"""

import os
import re
import subprocess
import sys

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def saida():
    """Roda a EDA e devolve o que ela imprime."""
    r = subprocess.run(
        [sys.executable, "run_eda.py"],
        cwd=RAIZ, check=True, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return r.stdout


def _num(saida, padrao):
    r"""Extrai um numero da saida do script.

    O separador de milhar sai do VALOR capturado, nao do padrao. A primeira
    versao fazia `r"([\d,]+)".replace(",", "")`, que altera a EXPRESSAO e deixa
    `[\d]+` — o match para no separador e "1,998" vira 1. O script imprime
    milhar com virgula e decimal com ponto (formato do Python), entao basta
    tirar as virgulas.
    """
    m = re.search(padrao, saida)
    assert m, f"Nao achei {padrao!r} na saida do run_eda.py"
    return float(m.group(1).replace(",", ""))


# ── As quatro hipóteses com veredito ──────────────────────────────────────────

def test_h1_velocidade_e_o_motivo_um(saida):
    """README: "H1 Confirmada — 35,4% do total"."""
    assert "H1: CONFIRMADA" in saida
    assert "Velocidade" in saida
    pct = _num(saida, r"Motivo #1: Velocidade \(([\d.]+)%\)")
    assert 34.0 <= pct <= 37.0, f"Motivo #1 em {pct}%; o README diz 35,4%"


def test_h2_top3_concentra(saida):
    """README: "H2 Confirmada — 86,0%"."""
    assert "H2: CONFIRMADA" in saida
    pct = _num(saida, r"Top 3 operadoras = ([\d.]+)%")
    assert pct > 70.0, "H2 afirma mais de 70%; abaixo disso ela vira refutada"
    assert 84.0 <= pct <= 88.0, f"Top 3 em {pct}%; o README diz 86,0%"


def test_h3_pico_no_primeiro_trimestre(saida):
    """README: "H3 Confirmada — pico em T1"."""
    assert "H3: CONFIRMADA" in saida and "Pico em T1" in saida


def test_h4_continua_refutada(saida):
    """README: "H4 Refutada — o gap é de 4,9pp".

    É a mais útil das quatro justamente por ter sido refutada. Se ela virar
    confirmada, o parágrafo que a explica no README deixa de fazer sentido.
    """
    assert "H4: REFUTADA" in saida
    gap = _num(saida, r"Gap taxa resolucao = ([\d.]+)pp")
    assert gap < 20.0, "H4 previa mais de 20pp; acima disso ela passa a confirmada"
    assert 4.0 <= gap <= 6.0, f"Gap em {gap}pp; o README diz 4,9pp"


def test_h5_nao_recebe_veredito(saida):
    """A quinta hipótese não pode ganhar CONFIRMADA/REFUTADA.

    `UF_DIST` é participação populacional escrita à mão. Um veredito aqui
    mediria a linha de código que escreveu os pesos, não o setor — o mesmo
    defeito que tirou a AUC de 0,996 do churn-predictor.
    """
    assert not re.search(r"H5:\s*(CONFIRMADA|REFUTADA)", saida), (
        "H5 ganhou veredito. Se ela passou a ser testavel, foi porque entrou um "
        "denominador externo — e ai o README precisa dizer qual."
    )


# ── Escala e limpeza ──────────────────────────────────────────────────────────

def test_escala_da_base(saida):
    """README: "1.998 reclamações, 88,3% de resolução".

    Os dois projetos ANATEL do portfólio têm bases diferentes de propósito
    (8.000 e 71,9% no telecom-powerbi). O README diz isso; o teste garante que
    o número citado continua sendo o desta base.
    """
    total = _num(saida, r"Total reclamacoes:\s+([\d,.]+)")
    assert 1900 <= total <= 2100, f"Base em {total:.0f}; o README diz 1.998"
    resol = _num(saida, r"Taxa de resolucao:\s+([\d.]+)%")
    assert 87.0 <= resol <= 90.0, f"Resolucao em {resol}%; o README diz 88,3%"


def test_cobertura_geografica(saida):
    assert "Estados cobertos:    27" in saida


def test_pipeline_valida_o_dado(saida):
    """A EDA existe para exercitar limpeza de CSV sujo — a validação faz parte."""
    assert "Validacao: OK" in saida
