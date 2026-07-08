# Dados — Reclamações ANATEL

## Download

O notebook usa dados públicos da ANATEL disponíveis no Portal de Dados Abertos.

### Passo a passo

1. Acesse **dados.anatel.gov.br** → seção "Reclamações de Consumidores"
2. Selecione o serviço **SCM** (Serviço de Comunicação Multimídia — internet banda larga)
3. Baixe o arquivo CSV do período desejado (recomendado: 2022–2023 para reproduzir os resultados)
4. Salve como `reclamacoes_scm.csv` nesta pasta (`data/`)

### Estrutura esperada do arquivo

```
Data_Abertura;Hora_Abertura;Tipo;Motivo;Detalhe_Motivo;Status;Agrupamento;Nome;Porte;Grupo_Economico;UF;Municipio;Sigla
15/01/2023;08:42;Reclamaã§ÃÆo;Velocidade;Velocidade abaixo do contratado;Respondida;SCM;CLARO S.A.;Grande;Claro;SP;SÃO PAULO;SCM
```

> **Atenção:** O arquivo original usa encoding `ISO-8859-1` e separador `;`. O notebook detecta e corrige isso automaticamente — não converta o arquivo antes de rodar.

### Características do dado bruto (dirty data intencional)

- Encoding: `ISO-8859-1` (latin-1) — caracteres especiais corrompidos se lidos como UTF-8
- Separador: `;` (não vírgula)
- Datas: formato `DD/MM/AAAA` como string
- Nomes de operadoras: caixa mista inconsistente (`CLARO S.A.`, `Claro`, `CLARO`)
- Valores nulos implícitos: `"-"`, `"N/A"`, `"NÃO INFORMADO"`
- Duplicatas: presentes por re-uploads incrementais

O notebook trata todos esses casos explicitamente.
