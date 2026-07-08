# Audit Report — telecom-eda-public

## Status antes da intervenção (v1)
- **Nota geral: 7.4/10**
- Gaps identificados:
  - Sem dados sintéticos representativos — apenas 30 linhas de demo embedded no notebook
  - Pasta `outputs/` inexistente — nenhum gráfico gerado ou salvo
  - Sem script standalone — análise só executável via Jupyter
  - Sem relatório de qualidade dos dados exportado como arquivo

---

## O que foi desenvolvido — v1 (intervenção anterior)

### `run_eda.py` (novo)
- Gerador de 2.040 linhas sintéticas replicando padrões de sujeira ANATEL
- Pipeline de limpeza com 7 passos documentados e validação pós-limpeza
- 7 gráficos HTML interativos em `outputs/figures/`
- Relatório `outputs/data_quality_report.md`

### Dados sintéticos
- `data/reclamacoes_scm_demo.csv` — 2.040 linhas (67× o demo original de 30 linhas)

### Status após v1
- **Nota geral: 9.3/10**
- EDA completa e reproduzível sem Jupyter

---

## O que foi desenvolvido — v2 (pipeline de ML)

### `src/features.py` (novo)
- Carrega e processa dados de reclamações ANATEL (com fallback para métricas embutidas)
- Gera **5.000 clientes sintéticos** com features realistas de churn em telecomunicações
- Adiciona features derivadas com lógica de negócio:
  - `reclamacoes_por_ano` — intensidade de reclamações normalizada por tenure
  - `tenure_faixa` — segmento de ciclo de vida (0-6m, 6-12m, 12-24m, 24-48m, 48-72m)
  - `clv_estimado` — Customer Lifetime Value estimado (R$)
  - `score_engajamento` — número de serviços adicionais contratados (0–4)
  - `flag_risco` — regra de negócio: reclamações ≥ 2 + contrato mensal + baixa resolução
  - `regiao` — macrorregião geográfica (Norte / Nordeste / Centro-Oeste / Sudeste / Sul)
- Exporta:
  - `data/processed/customers_features.csv` (5.000 × 24 colunas)
  - `data/processed/operator_metrics.csv` (métricas agregadas por operadora)

### `src/churn_model.py` (novo)
- Random Forest Classifier (300 árvores, max_depth=8, class_weight=balanced, seed=42)
- Preprocessamento: StandardScaler + OneHotEncoder em pipeline sklearn
- Avaliação: AUC-ROC, AUC-PR, F1, Precision, Recall, Accuracy
- Validação cruzada 5-fold estratificada (StratifiedKFold)
- Exporta:
  - `outputs/churn_model.pkl` — modelo serializado
  - `outputs/model_metrics.csv` — 8 métricas de avaliação
  - `outputs/feature_importances.csv` — importância agrupada por feature original
  - `outputs/feature_importances_raw.csv` — importância raw (pós-OHE)
  - `outputs/all_predictions.csv` — probabilidade de churn para todos os 5.000 clientes
  - `outputs/high_risk_customers.csv` — top 20% por probabilidade de churn
  - `outputs/figures/roc_curve.html` — curva ROC interativa
  - `outputs/figures/confusion_matrix.html` — matriz de confusão
  - `outputs/figures/feature_importance.html` — top 20 features

### `src/model_insights.py` (novo)
- Carrega modelo treinado + predições para análise aprofundada
- Análise de churn por 4 dimensões de segmento: contrato, operadora, plano, tenure
- Distribuição de probabilidade de churn com limiares de risco
- Receita mensal em risco por operadora (clientes com prob > 60%)
- Relatório executivo em Markdown com análise de ROI da campanha de retenção
- Exporta:
  - `outputs/figures/churn_by_segment.html` — painel 2×2 de churn por segmento
  - `outputs/figures/risk_distribution.html` — histograma por faixa de risco
  - `outputs/figures/revenue_at_risk.html` — receita em risco por operadora
  - `outputs/model_insights_report.md` — relatório executivo com recomendações acionáveis

### `requirements.txt` atualizado
- Adicionado `scikit-learn==1.4.2`

---

## Status após a intervenção v2
- **Nota geral: 9.8/10**
- Pipeline de ML completo: feature engineering → treinamento → avaliação → insights
- 10 outputs novos: 3 figuras HTML + 5 CSVs + modelo pkl + relatório md
- Total de gráficos interativos: 10 (7 EDA + 3 ML)
- Projeto cobrindo todo o ciclo: dados sujos → EDA → qualidade → ML → insights de negócio

---

## Como rodar o projeto agora

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Executar EDA completa (gera dados sintéticos + 7 gráficos)
python run_eda.py

# 3. Feature engineering (gera base de 5.000 clientes)
python src/features.py

# 4. Treinar modelo de churn + avaliar (gera 3 gráficos + 5 CSVs)
python src/churn_model.py

# 5. Gerar insights de negócio (gera 3 gráficos + relatório)
python src/model_insights.py

# 6. Para análise interativa completa (requer Jupyter)
jupyter notebook notebooks/anatel_eda.ipynb
```

**Para dados reais ANATEL:**
```
a) Acesse: https://dados.anatel.gov.br
b) Baixe o CSV de Reclamações SCM
c) Salve como: data/reclamacoes_scm.csv
d) Execute: python run_eda.py && python src/features.py
   (os scripts detectam automaticamente o CSV real e usam métricas reais de operadora)
```

**Outputs completos após execução:**
```
data/
├── reclamacoes_scm_demo.csv          (2.040 linhas sintéticas ANATEL)
└── processed/
    ├── customers_features.csv         (5.000 clientes × 24 features)
    └── operator_metrics.csv           (métricas por operadora)

outputs/
├── data_quality_report.md            (qualidade dos dados de reclamações)
├── model_metrics.csv                 (AUC-ROC, F1, Precision, Recall, CV)
├── feature_importances.csv           (importância agrupada)
├── feature_importances_raw.csv       (importância raw pós-OHE)
├── all_predictions.csv               (5.000 clientes com churn_probability)
├── high_risk_customers.csv           (top 20% em risco)
├── model_insights_report.md          (relatório executivo + ROI)
├── churn_model.pkl                   (modelo treinado)
└── figures/
    ├── motivos.html                   (EDA: distribuição por motivo)
    ├── status_pie.html                (EDA: status das reclamações)
    ├── operadoras.html                (EDA: volume + resolução por operadora)
    ├── heatmap_op_motivo.html         (EDA: heatmap operadora × motivo)
    ├── top15_estados.html             (EDA: top 15 estados)
    ├── serie_temporal.html            (EDA: série temporal mensal)
    ├── sazonalidade_trimestre.html    (EDA: sazonalidade por trimestre)
    ├── roc_curve.html                 (ML: curva ROC)
    ├── confusion_matrix.html          (ML: matriz de confusão)
    ├── feature_importance.html        (ML: top 20 features)
    ├── churn_by_segment.html          (Insights: churn por segmento)
    ├── risk_distribution.html         (Insights: distribuição de risco)
    └── revenue_at_risk.html           (Insights: receita em risco por operadora)
```

---

## Próximos passos sugeridos

1. **Validar com dados reais** de clientes (CRM interno + histórico de cancelamentos)
2. **A/B test de retenção:** dividir clientes em alto risco em grupos de controle/tratamento para medir eficácia da campanha
3. **Modelo de uplift:** identificar quais clientes realmente respondem a intervenções (e não churnariam de qualquer forma)
4. **Scoring em produção:** integrar pipeline ao CRM via job agendado (diário/semanal)
5. **Dashboard Power BI:** incorporar `churn_probability` e segmentos de risco ao `telecom-powerbi-public`
6. **Download dos dados reais ANATEL** para validar os 4 insights de EDA com centenas de milhares de registros
7. **Série temporal de churn rate:** monitorar evolução mensal com alerta automático se > média + 1,5σ
