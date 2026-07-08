"""
RFM Analysis — FiberNet ISP
Módulo de cálculo de Recência, Frequência e Valor Monetário para segmentação de clientes.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import date


# ---------------------------------------------------------------------------
# Segmentos RFM (baseado em scores R, F, M de 1 a 5)
# ---------------------------------------------------------------------------

SEGMENT_RULES: list[dict] = [
    {
        "segment":    "Campeões",
        "r_min": 4, "r_max": 5,
        "f_min": 4, "f_max": 5,
        "m_min": 4, "m_max": 5,
        "description": "Alta recência, frequência e valor — base da receita",
        "action":      "Recompensar com upgrades e programa VIP. Solicitar indicações.",
    },
    {
        "segment":    "Leais",
        "r_min": 3, "r_max": 5,
        "f_min": 4, "f_max": 5,
        "m_min": 3, "m_max": 5,
        "description": "Pagadores consistentes de longa data",
        "action":      "Oferecer fidelidade contratual com desconto progressivo.",
    },
    {
        "segment":    "Potenciais Leais",
        "r_min": 4, "r_max": 5,
        "f_min": 2, "f_max": 3,
        "m_min": 2, "m_max": 4,
        "description": "Recentes mas ainda construindo histórico",
        "action":      "Engajar com campanha de onboarding. Sugerir plano de upgrade.",
    },
    {
        "segment":    "Em Risco",
        "r_min": 2, "r_max": 3,
        "f_min": 3, "f_max": 5,
        "m_min": 3, "m_max": 5,
        "description": "Bom histórico mas recência caindo — sinal de alerta",
        "action":      "Contato proativo (ligação/WhatsApp). Verificar tickets abertos. Oferecer desconto de retenção.",
    },
    {
        "segment":    "Hibernando",
        "r_min": 1, "r_max": 2,
        "f_min": 1, "f_max": 3,
        "m_min": 1, "m_max": 3,
        "description": "Baixa atividade recente — provavelmente inadimplentes ou inativos",
        "action":      "Campanha de reativação. Negociação de débito. Avaliar custo de retenção vs. churn.",
    },
    {
        "segment":    "Perdidos",
        "r_min": 1, "r_max": 1,
        "f_min": 1, "f_max": 2,
        "m_min": 1, "m_max": 2,
        "description": "Sem atividade recente e baixo histórico — cancelados ou inadimplentes crônicos",
        "action":      "Tentar reativação com oferta agressiva. Se sem retorno, encerrar contrato.",
    },
]


def calculate_rfm(
    df_clients: pd.DataFrame,
    df_receivables: pd.DataFrame,
    reference_date: date | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Calcula métricas R, F, M para cada cliente a partir dos boletos pagos.

    Args:
        df_clients:     DataFrame com colunas [client_id, plan, city, monthly_amount, status].
        df_receivables: DataFrame com colunas [client_id, paid_at, amount].
                        Somente boletos com paid_at não-nulo são considerados.
        reference_date: Data de referência para calcular recência.
                        Se None, usa a data máxima de pagamento + 1 dia.

    Returns:
        DataFrame com colunas [client_id, recency_days, frequency, monetary,
                                plan, city, monthly_amount, status].
    """
    paid = df_receivables.dropna(subset=["paid_at"]).copy()
    paid["paid_at"] = pd.to_datetime(paid["paid_at"])

    if reference_date is None:
        reference_date = paid["paid_at"].max() + pd.Timedelta(days=1)
    else:
        reference_date = pd.Timestamp(reference_date)

    rfm = (
        paid.groupby("client_id")
        .agg(
            last_payment=("paid_at",  "max"),
            frequency   =("paid_at",  "count"),
            monetary    =("amount",   "sum"),
        )
        .reset_index()
    )
    rfm["recency_days"] = (reference_date - rfm["last_payment"]).dt.days
    rfm["monetary"]     = rfm["monetary"].round(2)

    # Merge with client metadata
    client_cols = [c for c in ["client_id", "plan", "city", "monthly_amount", "status"]
                   if c in df_clients.columns]
    rfm = rfm.merge(df_clients[client_cols], on="client_id", how="left")

    return rfm[["client_id", "recency_days", "frequency", "monetary"]
               + [c for c in client_cols if c != "client_id"]]


def _quintile_score(series: pd.Series, ascending: bool = True) -> pd.Series:
    """Scores a series into quintiles 1–5 (1 = worst, 5 = best)."""
    labels = [1, 2, 3, 4, 5] if ascending else [5, 4, 3, 2, 1]
    try:
        return pd.qcut(series, q=5, labels=labels, duplicates="drop").astype(int)
    except ValueError:
        # Fallback to rank-based scoring when too many ties
        return pd.cut(
            series.rank(method="first", ascending=ascending),
            bins=5,
            labels=[1, 2, 3, 4, 5],
        ).astype(int)


def score_rfm(df_rfm: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona scores R, F, M (1–5) e score RFM composto ao DataFrame de RFM.

    Convenção de score:
        R: 5 = mais recente (menor recency_days)
        F: 5 = maior frequência
        M: 5 = maior valor monetário
    """
    df = df_rfm.copy()
    df["r_score"] = _quintile_score(df["recency_days"], ascending=False)  # lower = better
    df["f_score"] = _quintile_score(df["frequency"],    ascending=True)
    df["m_score"] = _quintile_score(df["monetary"],     ascending=True)
    df["rfm_score"] = df["r_score"].astype(str) + df["f_score"].astype(str) + df["m_score"].astype(str)
    df["rfm_total"] = df["r_score"] + df["f_score"] + df["m_score"]
    return df


def assign_segments(df_rfm: pd.DataFrame) -> pd.DataFrame:
    """
    Atribui segmento nomeado a cada cliente baseado nos scores R, F, M.

    Se o cliente não se encaixa em nenhuma regra específica, recebe
    o segmento "Outros" com base no rfm_total.

    Returns:
        DataFrame com coluna 'segment' e 'segment_action' adicionadas.
    """
    df = score_rfm(df_rfm).copy()
    df["segment"]        = "Outros"
    df["segment_action"] = "Monitorar. Classificação genérica — revisar regras."

    for rule in SEGMENT_RULES:
        mask = (
            df["r_score"].between(rule["r_min"], rule["r_max"]) &
            df["f_score"].between(rule["f_min"], rule["f_max"]) &
            df["m_score"].between(rule["m_min"], rule["m_max"])
        )
        df.loc[mask & (df["segment"] == "Outros"), "segment"]        = rule["segment"]
        df.loc[mask & (df["segment_action"] == "Monitorar. Classificação genérica — revisar regras."),
               "segment_action"] = rule["action"]

    return df


def segment_summary(df_segmented: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna tabela resumo por segmento: contagem, % base, MRR total, % MRR.

    Espera coluna 'monthly_amount' em df_segmented (mensalidade do plano).
    Se ausente, usa 'monetary' / 'frequency' como proxy de ticket médio mensal.
    """
    if "monthly_amount" in df_segmented.columns:
        mrr_col = "monthly_amount"
    else:
        df_segmented = df_segmented.copy()
        df_segmented["monthly_amount"] = (
            df_segmented["monetary"] / df_segmented["frequency"].replace(0, 1)
        ).round(2)
        mrr_col = "monthly_amount"

    total_clients = len(df_segmented)
    total_mrr     = df_segmented[mrr_col].sum()

    summary = (
        df_segmented.groupby("segment")
        .agg(
            clientes      =(mrr_col, "count"),
            mrr_total     =(mrr_col, "sum"),
            mrr_medio     =(mrr_col, "mean"),
            recency_media =("recency_days", "mean"),
            freq_media    =("frequency",    "mean"),
        )
        .reset_index()
    )
    summary["pct_clientes"] = (summary["clientes"] / total_clients * 100).round(1)
    summary["pct_mrr"]      = (summary["mrr_total"] / total_mrr * 100).round(1)
    summary["mrr_total"]    = summary["mrr_total"].round(2)
    summary["mrr_medio"]    = summary["mrr_medio"].round(2)
    summary["recency_media"] = summary["recency_media"].round(0).astype(int)
    summary["freq_media"]   = summary["freq_media"].round(1)

    segment_order = [r["segment"] for r in SEGMENT_RULES] + ["Outros"]
    summary["_order"] = summary["segment"].map(
        {s: i for i, s in enumerate(segment_order)}
    ).fillna(99)
    return summary.sort_values("_order").drop(columns="_order").reset_index(drop=True)
