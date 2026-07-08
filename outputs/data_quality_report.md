# Data Quality Report — ANATEL SCM (Demo)

**Dataset:** reclamacoes_scm_demo.csv  
**Linhas antes da limpeza:** 2,040  
**Colunas:** 10  

## Problemas identificados

| # | Problema | Impacto | Estratégia de Tratamento |
|---|----------|---------|-------------------------|
| 1 | Encoding latin-1 (charset não-padrão) | Todos os caracteres acentuados corrompidos se lido como UTF-8 | `pd.read_csv(..., encoding='latin-1')` |
| 2 | Separador `;` (não-padrão) | DataFrame com 1 coluna gigante se lido com sep=',' | `pd.read_csv(..., sep=';')` |
| 3 | Duplicatas (42 linhas = 2.1%) | Contagens infladas de volume | `df.drop_duplicates()` |
| 4 | Datas como string (DD/MM/AAAA) | Não permite operações temporais | `pd.to_datetime(format='%d/%m/%Y', errors='coerce')` |
| 5 | Capitalização mista em operadoras | Mesma empresa contada 3x | Normalização para brand canônico |
| 6 | Nulos implícitos ('-', 'N/A', ' ') | `isna()` retorna 0 mas dado é inválido | `df.replace(IMPLICIT_NULLS, pd.NA)` |

## Auditoria por coluna

| coluna          | tipo   |   nulos_reais |   nulos_implicitos |   total_nulos | pct_nulos   |
|:----------------|:-------|--------------:|-------------------:|--------------:|:------------|
| Data_Abertura   | object |             0 |                  0 |             0 | 0.0%        |
| Tipo            | object |             0 |                  0 |             0 | 0.0%        |
| Motivo          | object |             0 |                 56 |            56 | 2.7%        |
| Detalhe_Motivo  | object |             0 |                 74 |            74 | 3.6%        |
| Status          | object |             0 |                  0 |             0 | 0.0%        |
| Agrupamento     | object |             0 |                  0 |             0 | 0.0%        |
| Nome            | object |             0 |                 14 |            14 | 0.7%        |
| Porte           | object |             0 |                 34 |            34 | 1.7%        |
| Grupo_Economico | object |             0 |                 48 |            48 | 2.4%        |
| UF              | object |             0 |                  0 |             0 | 0.0%        |

## Decisões de limpeza

- **Data_Abertura + Nome (operadora):** colunas chave — linhas com nulo são descartadas (`dropna`)
- **Motivo, Detalhe_Motivo, Status:** nulos preenchidos com 'Não Informado' para preservar a linha
- **UF:** nulos substituídos por 'XX' (código de fallback)
