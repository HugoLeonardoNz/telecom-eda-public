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

## Correção — 2026-08-13: a "v2 (pipeline de ML)" nunca existiu

Este documento descrevia, em detalhe, um pipeline de machine learning com três módulos
(`src/features.py`, `src/churn_model.py`, `src/model_insights.py`), dez arquivos de saída
e uma nota de 9,8/10. **Nada disso existe na pasta.** Nunca existiu: só há `src/rfm.py`.

Um leitor que seguisse as instruções de execução batia em `No such file or directory` no
terceiro comando. Documentação que promete entrega inexistente é pior que documentação
faltando — a seção foi removida.

**A decisão de não construir o pipeline aqui é deliberada**, não desistência: modelo de
churn com SHAP e app de scoring já é o assunto do
[churn-predictor](https://github.com/HugoLeonardoNz/churn-predictor). Dois projetos de
ML de churn no mesmo portfólio seriam redundância, não profundidade.

Este projeto entrega o que o nome diz: **EDA de reclamações ANATEL + segmentação RFM**,
com relatório de qualidade de dados e sete gráficos interativos, executável sem Jupyter.

---

## Como rodar o projeto agora

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Executar EDA completa (gera dados sintéticos + 7 gráficos)
python run_eda.py

# 3. Para análise interativa completa (requer Jupyter)
jupyter notebook notebooks/anatel_eda.ipynb
```

**Para dados reais ANATEL:**
```
a) Acesse: https://dados.anatel.gov.br
b) Baixe o CSV de Reclamações SCM
c) Salve como: data/reclamacoes_scm.csv
d) Execute: python run_eda.py
   (o script detecta automaticamente o CSV real e usa métricas reais de operadora)
```

**Outputs após execução:**
```
data/
└── reclamacoes_scm_demo.csv          (2.040 linhas sintéticas ANATEL)

outputs/
├── data_quality_report.md            (qualidade dos dados de reclamações)
└── figures/
    ├── motivos.html                   (distribuição por motivo)
    ├── status_pie.html                (status das reclamações)
    ├── operadoras.html                (volume + resolução por operadora)
    ├── heatmap_op_motivo.html         (heatmap operadora × motivo)
    ├── top15_estados.html             (top 15 estados)
    ├── serie_temporal.html            (série temporal mensal)
    └── sazonalidade_trimestre.html    (sazonalidade por trimestre)
```

---

## Próximos passos sugeridos

1. **Baixar os dados reais ANATEL** e revalidar os achados da EDA com centenas de
   milhares de registros — hoje a base é sintética, com 2.040 linhas.
2. **Ligar a segmentação RFM a dados de contrato reais**, para que os segmentos
   signifiquem receita e não só recência/frequência de reclamação.
3. **Reduzir o peso dos HTMLs** de `outputs/figures/` com `include_plotlyjs='cdn'` —
   hoje cada arquivo carrega o Plotly inteiro embutido.
4. **Alimentar o dashboard Power BI**: os motivos e a sazonalidade encontrados aqui
   viram hipóteses testáveis no [telecom-powerbi-public](https://github.com/HugoLeonardoNz/telecom-powerbi-public).
