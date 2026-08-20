"""
run_eda.py
Executa a análise completa do notebook anatel_eda.ipynb de forma standalone.

Gera dados sintéticos realistas (2.000 linhas) que reproduzem os padrões de
sujeira do arquivo real ANATEL e exporta todos os gráficos em outputs/figures/.

Uso:
    python run_eda.py

Saídas:
    data/reclamacoes_scm_demo.csv          (dados sintéticos gerados)
    outputs/figures/motivos.html
    outputs/figures/status_pie.html
    outputs/figures/operadoras.html
    outputs/figures/heatmap_op_motivo.html
    outputs/figures/top15_estados.html
    outputs/figures/serie_temporal.html
    outputs/figures/sazonalidade_trimestre.html
    outputs/data_quality_report.md
"""

import io
import random
import sys
import datetime
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.theme import SEQ, finish, save  # noqa: E402

warnings.filterwarnings("ignore")

ROOT    = Path(__file__).resolve().parent
DATA    = ROOT / "data"
OUTPUTS = ROOT / "outputs" / "figures"
DATA.mkdir(parents=True, exist_ok=True)
OUTPUTS.mkdir(parents=True, exist_ok=True)
(ROOT / "outputs").mkdir(parents=True, exist_ok=True)

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# --------------------------------------------------------------------------
# 1. Gerador de dados sintéticos realistas
# --------------------------------------------------------------------------

OPERADORAS_RAW = {
    "CLARO S.A.":                        ("Grande", "Claro",     0.30),
    "CLARO S/A":                         ("Grande", "Claro",     0.04),
    "NET SERVIÇOS DE COMUNICAÇÃO S.A.":  ("Grande", "Claro",     0.04),
    "TELEFONICA BRASIL S.A.":            ("Grande", "Vivo",      0.24),
    "TIM CELULAR":                       ("Grande", "TIM Group", 0.18),
    "OI S.A.":                           ("Grande", "Oi",        0.10),
    "SERCOMTEL S.A.":                    ("Pequeno","Sercomtel", 0.02),
    "EMBRATEL S.A.":                     ("Grande", "Claro",     0.08),
}

UF_DIST = {
    "SP": 0.22, "RJ": 0.12, "MG": 0.10, "BA": 0.07, "RS": 0.06,
    "PR": 0.06, "PE": 0.05, "CE": 0.04, "PA": 0.04, "GO": 0.03,
    "MA": 0.03, "AM": 0.02, "ES": 0.02, "MT": 0.02, "MS": 0.02,
    "PB": 0.02, "RN": 0.02, "AL": 0.01, "PI": 0.01, "SE": 0.01,
    "TO": 0.01, "RO": 0.01, "AC": 0.005,"AP": 0.005,"RR": 0.005,
    "DF": 0.02, "SC": 0.03,
}

MOTIVOS = [
    ("Velocidade",   "Velocidade abaixo do contratado",    0.34),
    ("Cobrança",     "Cobrança indevida",                  0.22),
    ("Falha",        "Falha/Interrupção do serviço",        0.18),
    ("Atendimento",  "Atendimento inadequado",              0.10),
    ("Contrato",     "Cancelamento não realizado",          0.08),
    ("Instalação",   "Prazo de instalação excedido",        0.05),
    ("Outros",       "Outros",                              0.03),
]

STATUS_DIST = [("Respondida", 0.68), ("Não Respondida", 0.20), ("Em Andamento", 0.12)]
IMPLICIT_NULL_VALS = ["-", "N/A", "NÃO INFORMADO", " "]


def _rdate(start, end):
    delta = (end - start).days
    d = start + datetime.timedelta(days=random.randint(0, delta))
    return d.strftime("%d/%m/%Y")


def _noise(value, prob=0.03):
    if random.random() < prob:
        return random.choice(IMPLICIT_NULL_VALS)
    return value


def _op_variant(name):
    variants = [name, name.lower().title(), name.upper()]
    return random.choices(variants, weights=[0.88, 0.06, 0.06], k=1)[0]


def generate_demo_data(n=2000, start_year=2022, end_year=2023) -> pd.DataFrame:
    start = datetime.date(start_year, 1, 1)
    end   = datetime.date(end_year, 12, 31)

    op_names   = list(OPERADORAS_RAW.keys())
    op_weights = [v[2] for v in OPERADORAS_RAW.values()]
    uf_list    = list(UF_DIST.keys())
    uf_weights = list(UF_DIST.values())

    rows = []
    for _ in range(n):
        op    = random.choices(op_names, weights=op_weights, k=1)[0]
        uf    = random.choices(uf_list, weights=uf_weights, k=1)[0]
        mot   = random.choices(MOTIVOS, weights=[m[2] for m in MOTIVOS], k=1)[0]
        st    = random.choices([s[0] for s in STATUS_DIST],
                               weights=[s[1] for s in STATUS_DIST], k=1)[0]
        porte, grupo, _ = OPERADORAS_RAW[op]

        rows.append({
            "Data_Abertura":  _rdate(start, end),
            "Tipo":           "Reclamação",
            "Motivo":         _noise(mot[0]),
            "Detalhe_Motivo": _noise(mot[1]),
            "Status":         st,
            "Agrupamento":    "SCM",
            "Nome":           _noise(_op_variant(op), prob=0.01),
            "Porte":          _noise(porte, prob=0.02),
            "Grupo_Economico":_noise(grupo, prob=0.02),
            "UF":             uf,
        })

    # Inject ~2% duplicates (ANATEL re-uploads)
    n_dup = int(n * 0.02)
    rows += random.choices(rows, k=n_dup)
    random.shuffle(rows)
    return pd.DataFrame(rows)


print("Gerando dados sinteticos realistas (2.000 linhas)...")
df_raw = generate_demo_data(2000)
demo_path = DATA / "reclamacoes_scm_demo.csv"
df_raw.to_csv(demo_path, sep=";", index=False, encoding="latin-1")
print(f"  Salvo em: {demo_path} ({len(df_raw):,} linhas x {df_raw.shape[1]} colunas)")

# --------------------------------------------------------------------------
# 2. Auditoria de qualidade dos dados (antes da limpeza)
# --------------------------------------------------------------------------

IMPLICIT_NULLS = {"-", "N/A", "NA", "NÃO INFORMADO", "NAO INFORMADO", " ", ""}

audit_rows = []
for col in df_raw.columns:
    n_real     = df_raw[col].isna().sum()
    n_implicit = df_raw[col].isin(IMPLICIT_NULLS).sum()
    audit_rows.append({
        "coluna": col,
        "tipo": str(df_raw[col].dtype),
        "nulos_reais": n_real,
        "nulos_implicitos": n_implicit,
        "total_nulos": n_real + n_implicit,
        "pct_nulos": f"{(n_real + n_implicit) / len(df_raw) * 100:.1f}%",
    })

audit_df = pd.DataFrame(audit_rows)
n_dup_raw = df_raw.duplicated().sum()

# Salva relatório de qualidade
quality_report_path = ROOT / "outputs" / "data_quality_report.md"
with open(quality_report_path, "w", encoding="utf-8") as f:
    f.write("# Data Quality Report — ANATEL SCM (Demo)\n\n")
    f.write(f"**Dataset:** reclamacoes_scm_demo.csv  \n")
    f.write(f"**Linhas antes da limpeza:** {len(df_raw):,}  \n")
    f.write(f"**Colunas:** {df_raw.shape[1]}  \n\n")
    f.write("## Problemas identificados\n\n")
    f.write("| # | Problema | Impacto | Estratégia de Tratamento |\n")
    f.write("|---|----------|---------|-------------------------|\n")
    f.write("| 1 | Encoding latin-1 (charset não-padrão) | Todos os caracteres acentuados corrompidos se lido como UTF-8 | `pd.read_csv(..., encoding='latin-1')` |\n")
    f.write("| 2 | Separador `;` (não-padrão) | DataFrame com 1 coluna gigante se lido com sep=',' | `pd.read_csv(..., sep=';')` |\n")
    f.write(f"| 3 | Duplicatas ({n_dup_raw} linhas = {n_dup_raw/len(df_raw)*100:.1f}%) | Contagens infladas de volume | `df.drop_duplicates()` |\n")
    f.write("| 4 | Datas como string (DD/MM/AAAA) | Não permite operações temporais | `pd.to_datetime(format='%d/%m/%Y', errors='coerce')` |\n")
    f.write("| 5 | Capitalização mista em operadoras | Mesma empresa contada 3x | Normalização para brand canônico |\n")
    f.write("| 6 | Nulos implícitos ('-', 'N/A', ' ') | `isna()` retorna 0 mas dado é inválido | `df.replace(IMPLICIT_NULLS, pd.NA)` |\n\n")
    f.write("## Auditoria por coluna\n\n")
    f.write(audit_df.to_markdown(index=False))
    f.write("\n\n## Decisões de limpeza\n\n")
    f.write("- **Data_Abertura + Nome (operadora):** colunas chave — linhas com nulo são descartadas (`dropna`)\n")
    f.write("- **Motivo, Detalhe_Motivo, Status:** nulos preenchidos com 'Não Informado' para preservar a linha\n")
    f.write("- **UF:** nulos substituídos por 'XX' (código de fallback)\n")

print(f"  Relatorio de qualidade: {quality_report_path.name}")

# --------------------------------------------------------------------------
# 3. Pipeline de limpeza
# --------------------------------------------------------------------------

BRAND_MAP = {
    "CLARO":     ["CLARO S.A.", "CLARO S/A", "CLARO", "NET SERV", "EMBRATEL"],
    "VIVO":      ["VIVO", "TELEFONIC"],
    "TIM":       ["TIM"],
    "OI":        ["OI S.A.", "OI MOVEL", "OI "],
    "SERCOMTEL": ["SERCOMTEL"],
}


def normalize_operadora(raw):
    if pd.isna(raw):
        return "DESCONHECIDA"
    raw_up = str(raw).strip().upper()
    for brand, patterns in BRAND_MAP.items():
        if any(p in raw_up for p in patterns):
            return brand
    return raw_up.split()[0]


def clean_pipeline(df):
    df = df.copy()
    df.replace(IMPLICIT_NULLS, pd.NA, inplace=True)
    before = len(df)
    df = df.drop_duplicates()
    removed_dup = before - len(df)
    df["Data_Abertura"] = pd.to_datetime(
        df["Data_Abertura"].str.strip(), format="%d/%m/%Y", errors="coerce"
    )
    invalid_dates = df["Data_Abertura"].isna().sum()
    df = df.dropna(subset=["Data_Abertura"])
    for col in ["Motivo", "Detalhe_Motivo", "Status", "Tipo"]:
        if col in df.columns:
            df[col] = df[col].str.strip().str.title().fillna("Não Informado")
    df["UF"] = df["UF"].str.strip().str.upper().fillna("XX")
    df["Operadora"] = df["Nome"].apply(normalize_operadora)
    df["Ano"]       = df["Data_Abertura"].dt.year
    df["Mes"]       = df["Data_Abertura"].dt.month
    df["AnoMes"]    = df["Data_Abertura"].dt.to_period("M").astype(str)
    df["Trimestre"] = df["Data_Abertura"].dt.quarter.map({1:"T1",2:"T2",3:"T3",4:"T4"})
    return df, removed_dup, invalid_dates


print("\nExecutando pipeline de limpeza...")
df, removed_dup, invalid_dates = clean_pipeline(df_raw)
print(f"  Duplicatas removidas: {removed_dup}")
print(f"  Datas invalidas descartadas: {invalid_dates}")
print(f"  Shape final: {df.shape}")
print(f"  Operadoras: {sorted(df['Operadora'].unique())}")

# Validação pós-limpeza
assert df.duplicated().sum() == 0, "FAIL: ainda ha duplicatas"
assert df["Data_Abertura"].isna().sum() == 0, "FAIL: ainda ha datas nulas"
assert df["Operadora"].isna().sum() == 0, "FAIL: ainda ha operadoras nulas"
print("  Validacao: OK")

# --------------------------------------------------------------------------
# 4. KPIs
# --------------------------------------------------------------------------

total       = len(df)
respondidas = df["Status"].str.contains("Respondid", na=False).sum()
taxa_res    = respondidas / total * 100

print(f"\nKPIs:")
print(f"  Total reclamacoes:    {total:,}")
print(f"  Taxa de resolucao:    {taxa_res:.1f}%")
print(f"  Operadoras:          {df['Operadora'].nunique()}")
print(f"  Estados cobertos:    {df['UF'].nunique()}")
print(f"  Tipos de motivo:     {df['Motivo'].nunique()}")
print(f"  Periodo: {df['Data_Abertura'].min().strftime('%d/%m/%Y')} a {df['Data_Abertura'].max().strftime('%d/%m/%Y')}")

# --------------------------------------------------------------------------
# 5. Gráficos
# --------------------------------------------------------------------------

print("\nGerando graficos...")

# 5.1 Distribuição por motivo
motivo_cnt = df["Motivo"].value_counts().reset_index()
motivo_cnt.columns = ["Motivo", "Total"]
motivo_cnt["Pct"] = (motivo_cnt["Total"] / total * 100).round(1)
top1_motivo = motivo_cnt.iloc[0]["Motivo"]
top1_pct    = motivo_cnt.iloc[0]["Pct"]
h1_ok = "velocidade" in top1_motivo.lower()

fig = px.bar(
    motivo_cnt, x="Pct", y="Motivo", orientation="h",
    text=motivo_cnt["Pct"].astype(str) + "%",
    color="Pct", color_continuous_scale="Blues",
    labels={"Pct": "% do total", "Motivo": "Motivo"},
)
fig.update_traces(textposition="outside")
fig.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
finish(fig, "H1 · Distribuição por motivo de reclamação",
       f"motivo mais frequente: {top1_motivo} ({top1_pct}% do total)", height=420)
save(fig, OUTPUTS, "motivos")
print(f"  OK motivos.html | H1: {'CONFIRMADA' if h1_ok else 'REFUTADA'} ('{top1_motivo}' = {top1_pct}%)")

# 5.2 Status (pie chart)
status_cnt = df["Status"].value_counts().reset_index()
status_cnt.columns = ["Status", "Total"]
fig = px.pie(status_cnt, values="Total", names="Status", hole=0.45,
             color_discrete_sequence=["#0F766E", "#B91C1C", "#B45309"])
finish(fig, "Situação das reclamações", "participação de cada status no total", height=400)
save(fig, OUTPUTS, "status_pie")
print("  OK status_pie.html")

# 5.3 Operadoras: volume + taxa de resolução (H2 + H4)
op = df.groupby("Operadora").agg(
    Total=("Operadora", "count"),
    Respondidas=("Status", lambda x: x.str.contains("Respondid", na=False).sum()),
).assign(Taxa_Res=lambda d: (d["Respondidas"] / d["Total"] * 100).round(1)).sort_values("Total", ascending=False).reset_index()

top3_share = op.head(3)["Total"].sum() / total * 100
gap_res    = op["Taxa_Res"].max() - op["Taxa_Res"].min()
h2_ok = top3_share > 70
h4_ok = gap_res >= 20

fig = make_subplots(rows=1, cols=2,
    subplot_titles=(f"H2: Volume (Top 3 = {top3_share:.1f}%)",
                    f"H4: Taxa de Resolução (Gap = {gap_res:.1f}pp)"))
CORES = {"Claro":"#EE4023","Vivo":"#660099","Tim":"#003087","Oi":"#FFDD00","Sercomtel":"#2ECC71","Desconhecida":"#95A5A6"}
cores = [CORES.get(o.title(), "#95A5A6") for o in op["Operadora"]]
fig.add_trace(go.Bar(x=op["Operadora"], y=op["Total"],
    marker_color=cores, text=op["Total"], textposition="outside", name="Volume"), row=1, col=1)
fig.add_trace(go.Bar(x=op["Operadora"], y=op["Taxa_Res"],
    marker=dict(color=op["Taxa_Res"], colorscale="RdYlGn", cmin=40, cmax=100),
    text=op["Taxa_Res"].astype(str) + "%", textposition="outside", name="Taxa Res."), row=1, col=2)
fig.add_hline(y=op["Taxa_Res"].mean(), row=1, col=2, line_dash="dash", line_color="grey",
              annotation_text=f"Media: {op['Taxa_Res'].mean():.1f}%", annotation_position="right")
fig.update_layout(showlegend=False)
finish(fig, "Reclamações por operadora",
       "volume bruto à esquerda, qualidade do atendimento à direita — as duas leituras discordam",
       height=470)
save(fig, OUTPUTS, "operadoras", png=True)
print(f"  OK operadoras.html | H2: {'CONFIRMADA' if h2_ok else 'REFUTADA'} | H4: {'CONFIRMADA' if h4_ok else 'REFUTADA'}")

# 5.4 Heatmap Operadora × Motivo
hm = df.groupby(["Operadora", "Motivo"]).size().unstack(fill_value=0)
fig = px.imshow(hm, text_auto=True, color_continuous_scale=SEQ, aspect="auto",
                labels=dict(x="Motivo", y="Operadora", color="Reclamações"))
finish(fig, "Operadora × motivo",
       "volume de reclamações no cruzamento — a cor acompanha o número, não o substitui",
       height=460)
save(fig, OUTPUTS, "heatmap_op_motivo", png=True)
print("  OK heatmap_op_motivo.html")

# 5.5 Top 15 estados
REGIAO = {
    "SP":"Sudeste","RJ":"Sudeste","MG":"Sudeste","ES":"Sudeste",
    "RS":"Sul","PR":"Sul","SC":"Sul",
    "BA":"Nordeste","PE":"Nordeste","CE":"Nordeste","MA":"Nordeste",
    "PB":"Nordeste","RN":"Nordeste","AL":"Nordeste","SE":"Nordeste","PI":"Nordeste",
    "PA":"Norte","AM":"Norte","TO":"Norte","RO":"Norte","AC":"Norte","RR":"Norte","AP":"Norte",
    "GO":"Centro-Oeste","DF":"Centro-Oeste","MT":"Centro-Oeste","MS":"Centro-Oeste",
}
COR_REG = {"Sudeste":"#2C3E50","Nordeste":"#E74C3C","Sul":"#27AE60","Norte":"#F39C12","Centro-Oeste":"#9B59B6"}

uf_df = df.groupby("UF").agg(
    Total=("UF", "count"),
    Respondidas=("Status", lambda x: x.str.contains("Respondid", na=False).sum()),
).assign(Taxa_Res=lambda d: (d["Respondidas"] / d["Total"] * 100).round(1)).sort_values("Total", ascending=False).head(15).reset_index()
uf_df["Regiao"] = uf_df["UF"].map(REGIAO).fillna("Outros")

fig = px.bar(uf_df, x="UF", y="Total",
             color="Regiao", color_discrete_map=COR_REG,
             text="Total",
             labels={"Total": "Reclamações", "UF": "Estado"})
fig.update_traces(textposition="outside")
finish(fig, "H5 · Top 15 estados por volume",
       "cor por região · sem denominador populacional, o ranking mede população tanto quanto serviço",
       height=460)
save(fig, OUTPUTS, "top15_estados")
print("  OK top15_estados.html")

# 5.6 Série temporal mensal
ts = df.groupby(["AnoMes", "Operadora"]).size().reset_index(name="Total")
ts = ts.sort_values("AnoMes")

fig = px.line(ts, x="AnoMes", y="Total", color="Operadora",
              markers=True,
              title="<b>Evolução Mensal de Reclamações por Operadora</b>",
              labels={"AnoMes": "Mes", "Total": "Reclamações"},
              color_discrete_map={k.title(): v for k, v in CORES.items()})
finish(fig, "Evolução mensal por operadora",
       "cor fixa por marca, a mesma em todos os gráficos", height=440)
save(fig, OUTPUTS, "serie_temporal")
print("  OK serie_temporal.html")

# 5.7 Sazonalidade por trimestre (H3)
trim_df = df.groupby("Trimestre").size().reset_index(name="Total")
trim_df = trim_df.sort_values("Trimestre")
pico_trim = trim_df.loc[trim_df["Total"].idxmax(), "Trimestre"]
h3_ok = pico_trim == "T1"

fig = px.bar(trim_df, x="Trimestre", y="Total", text="Total",
             color="Total", color_continuous_scale=SEQ)
fig.update_traces(textposition="outside")
fig.update_layout(coloraxis_showscale=False)
finish(fig, "H3 · Sazonalidade por trimestre", f"pico no {pico_trim}", height=400)
save(fig, OUTPUTS, "sazonalidade_trimestre")
print(f"  OK sazonalidade_trimestre.html | H3: {'CONFIRMADA' if h3_ok else 'REFUTADA'} (pico em {pico_trim})")

# --------------------------------------------------------------------------
# 6. Resumo das hipóteses
# --------------------------------------------------------------------------

print("\n" + "=" * 60)
print("RESUMO DAS HIPOTESES")
print("=" * 60)
print(f"  H1: {'CONFIRMADA' if h1_ok else 'REFUTADA':10s} | Motivo #1: {top1_motivo} ({top1_pct}%)")
print(f"  H2: {'CONFIRMADA' if h2_ok else 'REFUTADA':10s} | Top 3 operadoras = {top3_share:.1f}%")
print(f"  H3: {'CONFIRMADA' if h3_ok else 'REFUTADA':10s} | Pico em {pico_trim}")
print(f"  H4: {'CONFIRMADA' if h4_ok else 'REFUTADA':10s} | Gap taxa resolucao = {gap_res:.1f}pp")

print(f"\nFiguras salvas em: {OUTPUTS}")
print(f"Total: 7 graficos HTML interativos")
print(f"Relatorio de qualidade: {quality_report_path}")
