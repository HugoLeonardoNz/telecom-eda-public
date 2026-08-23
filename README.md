# Telecom EDA — reclamações regulatórias e segmentação de base

<div align="center">

![Python](https://img.shields.io/badge/Python-pandas%20%2B%20plotly-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Análises](https://img.shields.io/badge/Análises-EDA%20ANATEL%20%2B%20RFM-2563EB?style=for-the-badge)
![Dados](https://img.shields.io/badge/Dados-sintéticos-10b981?style=for-the-badge)
![testes](https://github.com/HugoLeonardoNz/telecom-eda-public/actions/workflows/tests.yml/badge.svg)

**Duas análises sobre o mesmo setor, de dois ângulos: o que o consumidor reclama
do mercado, e o que a base de uma operadora diz sobre quem está prestes a sair.**

</div>

> Peça do portfólio de **Hugo Leonardo**, Analista de Dados — os oito projetos, com o contexto de cada um, estão em **[hugoleonardonz.github.io/portfolio](https://hugoleonardonz.github.io/portfolio/)**.

![Operadora × motivo](docs/img/heatmap_op_motivo.png)

---

## O que tem aqui

| Análise | Pergunta | Entrada | Saída |
|---|---|---|---|
| **EDA ANATEL** (`run_eda.py`) | O que gera reclamação no setor, e o padrão é de mercado ou de uma marca? | CSV bruto no formato real da ANATEL — latin-1, `;`, duplicatas, nulos implícitos | 7 gráficos + relatório de qualidade do dado + 4 hipóteses testadas e 1 declarada não-testável |
| **RFM** (`notebooks/rfm_analysis.ipynb`) | Quem, na base, está a caminho do cancelamento? | 300 contratos · ~4.2 mil boletos | 6 segmentos com ação recomendada e MRR em risco |

As duas rodam sozinhas, com dados sintéticos versionados. Nenhuma depende de
credencial, banco ou arquivo que não esteja no repositório.

---

## EDA ANATEL — limpeza e teste de hipótese

O ponto do exercício não é o gráfico: é a **sujeira**. O CSV é gerado com os
mesmos defeitos do arquivo real do portal da ANATEL, e o pipeline tem de
sobreviver a todos eles.

| Problema | Por que quebra | Tratamento |
|---|---|---|
| Encoding latin-1 | Todo acento vira caractere corrompido se lido como UTF-8 | `encoding='latin-1'` |
| Separador `;` | Com `sep=','` o arquivo vira uma coluna só | `sep=';'` |
| 2,1% de duplicatas | Infla contagem de volume | `drop_duplicates()` |
| Data em texto `DD/MM/AAAA` | Bloqueia qualquer operação temporal | `to_datetime(format=..., errors='coerce')` |
| Capitalização mista | "CLARO", "Claro" e "claro " viram três empresas | normalização para marca canônica |
| Nulos implícitos (`-`, `N/A`, `' '`) | `isna()` devolve zero e o dado inválido passa | `replace(IMPLICIT_NULLS, pd.NA)` |

O relatório completo, coluna a coluna, sai em
[`outputs/data_quality_report.md`](outputs/data_quality_report.md) — gerado pelo
script, não escrito à mão.

### As cinco hipóteses

Declaradas **antes** de olhar o resultado, e o script imprime confirmada ou
refutada. Uma hipótese que só pode dar certo não é hipótese.

| # | Hipótese | Resultado |
|---|---|---|
| H1 | Velocidade é o motivo #1 de reclamação | **Confirmada** — 35,4% do total |
| H2 | As 3 maiores operadoras concentram mais de 70% do volume | **Confirmada** — 86,0% |
| H3 | Há sazonalidade, com pico no primeiro trimestre | **Confirmada** — pico em T1 |
| H4 | A taxa de resolução varia mais de 20pp entre operadoras | **Refutada** — o gap é de 4,9pp |
| H5 | O volume por estado acompanha a população | **Não testável aqui** — ver abaixo |

**H5 não recebe veredito, e isso é de propósito.** O gerador sorteia a UF de cada
reclamação a partir de `UF_DIST`, que é — por construção — participação populacional:
SP 22%, RJ 12%, MG 10%. Rodar a correlação entre volume estadual e população devolveria
"confirmada" com r perto de 1, e o número mediria a linha de código que escreveu os
pesos, não o setor. É o mesmo defeito que este portfólio removeu do
[churn-predictor](https://github.com/HugoLeonardoNz/churn-predictor), onde as variáveis
eram sorteadas condicionadas ao próprio rótulo e a AUC saía em 0,996.

Para testar H5 de verdade seria preciso um denominador externo — população ou base de
assinantes por UF — e aí a pergunta útil deixa de ser "qual estado reclama mais" e passa
a ser "qual estado reclama mais **por assinante**". É exatamente essa a coluna que o
[telecom-powerbi-public](https://github.com/HugoLeonardoNz/telecom-powerbi-public) traz,
e lá ela inverte o ranking: a SERCOMTEL reclama 4x mais por assinante que a CLARO.

H4 é a mais útil das cinco justamente por ter sido refutada: a intuição de que
"operadora grande atende pior" não se sustenta no dado — todas resolvem em
patamar parecido, e o que as separa é volume, não qualidade de resposta.

![Reclamações por operadora](docs/img/operadoras.png)

---

## RFM — quem está saindo antes de cancelar

Churn em ISP não acontece de uma vez. Existe um padrão de comportamento antes do
cancelamento formal: o cliente começa a atrasar boleto, depois para de pagar, e
só então liga para cancelar. **Recência**, **Frequência** e **Valor** dos
pagamentos capturam esse padrão enquanto ainda dá para agir.

| Métrica | Definição | Leitura |
|---|---|---|
| Recência (R) | Dias desde o último boleto pago | R baixo = pagou recentemente |
| Frequência (F) | Quantidade de boletos pagos | F alto = cliente de longa data |
| Monetário (M) | Soma total paga | M alto = alto valor acumulado |

Cada métrica é cortada em quintis (1–5) e o score é a concatenação dos três —
"545" é recente, frequente e de alto valor.

| Segmento | Clientes | % base | MRR (R$) | % MRR |
|---|---:|---:|---:|---:|
| Campeões | ~44 | 14,7% | ~5.600 | 19,6% |
| Leais | ~61 | 20,3% | ~7.700 | 27,1% |
| Potenciais leais | ~30 | 10,0% | ~3.000 | 10,5% |
| **Em risco** | **~45** | **15,0%** | **~5.400** | **19,0%** |
| Hibernando | ~75 | 25,0% | ~4.200 | 14,9% |
| Perdidos | ~45 | 15,0% | ~2.600 | 9,1% |

> Campeões + Leais são 35% dos clientes e 47% do MRR. Em risco + Hibernando são
> 40% dos clientes e ~R$ 9,6 mil de MRR ameaçado — 33,9% do total.

---

## Como rodar

```bash
pip install -r requirements.txt

python run_eda.py          # EDA ANATEL: gera dados, limpa, testa H1–H5, exporta figuras
jupyter notebook notebooks/rfm_analysis.ipynb
```

`run_eda.py` grava os HTMLs interativos em `outputs/figures/` e os PNGs deste
README em `docs/img/`. O tema dos gráficos fica em
[`src/theme.py`](src/theme.py): título, subtítulo, tipografia, grade e escala de
cor são definidos uma vez e aplicados por `finish()` — gráfico novo sai com o
mesmo acabamento dos outros sem ninguém lembrar de nada.

O notebook de RFM roda em dois modos: **PostgreSQL**, apontando para o schema do
[`sql-analytics-pack`](https://github.com/HugoLeonardoNz/sql-analytics-pack), ou
**standalone**, com os dados sintéticos que já vêm no repositório.

---

## Estrutura

```
telecom-eda-public/
├── run_eda.py                    — EDA ANATEL de ponta a ponta
├── src/
│   ├── theme.py                  — tema único dos gráficos (finish, save)
│   └── rfm.py                    — calculate_rfm(), score_rfm(), assign_segments()
├── notebooks/
│   ├── anatel_eda.ipynb          — a mesma análise, com narrativa
│   └── rfm_analysis.ipynb        — segmentação da base
├── data/                         — CSV sintético gerado pelo script
├── outputs/
│   ├── figures/                  — 7 HTMLs interativos
│   └── data_quality_report.md    — auditoria de qualidade, gerada
└── docs/img/                     — PNGs do README, exportados pelo script
```

---

## Fonte dos dados

**EDA ANATEL:** CSV sintético que reproduz o formato e os defeitos do arquivo
público de reclamações de consumidores (serviço SCM): latin-1, `;`, duplicatas,
nulos implícitos. Serve para demonstrar limpeza e análise — os números não devem
ser citados como fato de mercado. **1.998 reclamações, 88,3% de resolução.**

> **Há dois projetos "ANATEL" neste portfólio, e eles não compartilham base.** Este
> aqui gera 1.998 registros com 8 motivos para exercitar limpeza de CSV sujo; o
> [telecom-powerbi-public](https://github.com/HugoLeonardoNz/telecom-powerbi-public)
> gera 8.000 com 11 categorias, star schema e denominador de assinantes, para
> exercitar modelagem dimensional. Geradores diferentes, propósitos diferentes —
> por isso a taxa de resolução é 88,3% aqui e 71,9% lá. Um não confere o outro.

**RFM:** base FiberNet ISP (sintética) — 300 contratos · 5 cidades da RMBH ·
4 planos de fibra · jan/2022 a out/2024. Mesma **escala e recorte** do
[`sql-analytics-pack`](https://github.com/HugoLeonardoNz/sql-analytics-pack), mas
não a mesma tabela: cada projeto gera a sua. O
[`churn-predictor`](https://github.com/HugoLeonardoNz/churn-predictor) trabalha em
outra escala (15.000 contratos, 5 regiões).

---

*Hugo Leonardo · Analista de Dados Pleno — Speed Fibra*

---

## Os achados publicados são testados

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Número em README não executa — e foi exatamente por isso que este portfólio deixou
texto e código divergirem em silêncio mais de uma vez. Num dos repositórios, um
comentário explicava que 87,0% era número inventado e o gráfico sessenta linhas
abaixo plotava 87,0%. Em outro, o texto dizia "São Paulo tem a melhor taxa do país"
enquanto o CSV ao lado registrava que era o 5º.

Cada hipótese do README vira asserção sobre o que o `run_eda.py` imprime: H1 em
35,4%, H2 em 86,0%, H3 com pico em T1, H4 refutada em 4,9pp. **H5 tem o teste
invertido** — ele falha se ela GANHAR veredito, porque `UF_DIST` é participação
populacional escrita à mão e confirmar mediria o gerador, não o setor.

Se o gerador, a fonte ou a limpeza mudarem, o teste falha e obriga a atualizar o
texto. É a mesma regra que vale para dado: **ou se deriva de uma fonte só, ou se
escreve um teste que falha quando as duas divergirem.**
