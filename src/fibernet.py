"""Base sintética da FiberNet — contratos e boletos, para a análise RFM.

POR QUE ESTE ARQUIVO EXISTE
───────────────────────────
O gerador vivia dentro de uma célula do `notebooks/rfm_analysis.ipynb`. Isso
tinha duas consequências, e a segunda é a que dói:

1. **Não havia figura de RFM no README.** A parte do repositório que fala de
   churn — a metade que interessa a quem contrata analista de ISP — não tinha
   nada para ver sem abrir o notebook. Toda imagem do README vinha da EDA da
   ANATEL.
2. **Só existia um jeito de rodar: à mão, célula por célula.** Um número citado
   no README não podia ser conferido por script, e é justamente isso que os
   outros repositórios deste portfólio passaram a fazer.

Aqui a base fica num módulo, `run_rfm.py` roda o pipeline inteiro sem
intervenção e a mesma definição serve aos dois. Manter gerador em dois lugares é
exatamente o padrão de defeito que a auditoria de 21/08 encontrou em quatro
arquivos deste portfólio.

O QUE É E O QUE NÃO É
─────────────────────
É base **sintética**, e o repositório diz isso em todo lugar onde o número
aparece. O que ela imita não é um cliente real: é a FORMA do problema — plano
mais barato cancela mais, boleto atrasa em ~8% das vezes, cliente cancelado para
de gerar boleto no meio da vida do contrato. O RFM tem que enxergar esse padrão;
é isso que o exercício mostra.

A semente é fixa (42). Com a mesma semente a base é a mesma em qualquer máquina,
então o número do README é conferível — que é a diferença entre dado sintético e
dado inventado.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SEED = 42
REFERENCE_DATE = pd.Timestamp("2024-10-15")
INICIO = pd.Timestamp("2022-01-01")

# Preço mensal por plano, em reais.
PLANOS = {
    "Fibra 100MB":  89.0,
    "Fibra 200MB": 119.0,
    "Fibra 500MB": 149.0,
    "Empresarial": 449.0,
}

# Probabilidade de cancelamento por plano. A relação inversa entre preço e churn
# é a mesma que o sql-analytics-pack mede na sua própria base: quem paga menos
# sai mais. Não é acaso do gerador — é a premissa que o exercício assume, e ela
# está escrita aqui em vez de escondida numa célula.
CHURN_POR_PLANO = {
    "Fibra 100MB": 0.367,
    "Fibra 200MB": 0.25,
    "Fibra 500MB": 0.18,
    "Empresarial": 0.10,
}

CIDADES = ["Betim", "Contagem", "Ribeirão das Neves", "Esmeraldas", "Ibirité"]
PESO_CIDADE = [0.274, 0.240, 0.200, 0.160, 0.126]
PESO_PLANO = [0.35, 0.30, 0.25, 0.10]

N_CONTRATOS = 300
PROB_ATRASO = 0.08


def gerar_base(
    n: int = N_CONTRATOS,
    seed: int = SEED,
    referencia: pd.Timestamp = REFERENCE_DATE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devolve (contratos, boletos) da FiberNet.

    `contratos`: client_id, city, plan, monthly_amount, status, start_date,
    active_months.
    `boletos`:   client_id, due_date, paid_at, amount — um por mês ativo.
    `paid_at` vem nulo quando o pagamento cairia depois da data de referência:
    é o boleto em aberto, que é o que a Recência do RFM enxerga.
    """
    rng = np.random.default_rng(seed)

    planos = rng.choice(list(PLANOS.keys()), size=n, p=PESO_PLANO)
    cidades = rng.choice(CIDADES, size=n, p=PESO_CIDADE)
    dias_inicio = rng.integers(0, (referencia - INICIO).days, size=n)
    inicio = INICIO + pd.to_timedelta(dias_inicio, unit="D")
    meses_de_casa = np.maximum(1, ((referencia - inicio) / pd.Timedelta(days=30)).astype(int))

    cancelou = rng.random(n) < np.array([CHURN_POR_PLANO[p] for p in planos])
    # Quem cancelou saiu num ponto qualquer da própria vida de contrato, não no
    # fim dela: é isso que faz a Recência distinguir quem está saindo de quem
    # acabou de entrar.
    meses_ativos = np.where(
        cancelou,
        np.maximum(1, (meses_de_casa * rng.uniform(0.3, 0.9, n)).astype(int)),
        meses_de_casa,
    )

    contratos = pd.DataFrame({
        "client_id":      range(1, n + 1),
        "city":           cidades,
        "plan":           planos,
        "monthly_amount": [PLANOS[p] for p in planos],
        "status":         np.where(cancelou, "cancelled", "active"),
        "start_date":     inicio,
        "active_months":  meses_ativos,
    })

    linhas = []
    for _, c in contratos.iterrows():
        for m in range(int(c["active_months"])):
            vencimento = c["start_date"] + pd.DateOffset(months=m + 1)
            atrasou = rng.random() < PROB_ATRASO
            dias = rng.integers(1, 5) if not atrasou else rng.integers(6, 21)
            pago_em = vencimento + pd.Timedelta(days=int(dias))
            if pago_em > referencia:
                pago_em = None
            linhas.append({
                "client_id": c["client_id"],
                "due_date":  vencimento,
                "paid_at":   pago_em,
                "amount":    round(c["monthly_amount"] * rng.uniform(0.98, 1.02), 2),
            })

    return contratos, pd.DataFrame(linhas)
