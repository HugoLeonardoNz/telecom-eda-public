# Dados

## `processed/` — o que está versionado

Sete agregados extraídos da base **aberta e real** da ANATEL, somando 136 KB.
São eles que o `run_eda.py` lê; por isso a análise roda em segundos e qualquer
pessoa que clone o repositório reproduz os mesmos números sem baixar nada.

| Arquivo | Grão |
|---|---|
| `agg_marca_mes.csv` | ano-mês × marca × serviço |
| `agg_uf_marca.csv` | UF × marca |
| `agg_assunto_marca.csv` | assunto × marca |
| `agg_uf_mes.csv` | UF × ano-mês |
| `agg_canal_ano.csv` | canal de entrada × ano |
| `agg_condicao_marca.csv` | ano × marca × condição (nova/reaberta/reencaminhada) |
| `agg_tipo_ano.csv` | tipo de atendimento × ano |

Todos fecham no mesmo total — **18.813.384 solicitações** — e o
`tools/preparar_anatel.py` confere isso ao final de cada execução. Sete recortes
do mesmo dado que não batem entre si significam erro de agregação, e o script
sai com código 1 se acontecer.

## `raw/` — o que **não** está versionado

O CSV publicado pela ANATEL tem **2,5 GB e 15.952.408 linhas**. Não cabe (nem
deve caber) num repositório git. A pasta é ignorada.

Para baixar e reprocessar:

```bash
python tools/preparar_anatel.py
```

O script baixa ~334 MB compactados, extrai, faz **uma** passada em blocos de
1,5 milhão de linhas e regrava os agregados acima.

Fonte: `https://www.anatel.gov.br/dadosabertos/paineis_de_dados/consumidor/`

## Cuidado com o grão

Cada linha da fonte **já é uma contagem**, na coluna `SOLICITAÇÕES`. Contar
linhas dá número errado: são 15.952.408 linhas para 18.813.384 solicitações.
Toda soma neste projeto é soma de `SOLICITAÇÕES`.
