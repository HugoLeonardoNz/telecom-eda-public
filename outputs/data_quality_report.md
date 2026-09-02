# Relatório de qualidade — base real da ANATEL

- **Solicitações**: 18.813.384
- **Período**: 2015-01 a 2020-05
- **Fonte**: dados abertos da ANATEL (painel do consumidor)

Este relatório é gerado por `run_eda.py`. Cada item abaixo é uma
armadilha real da fonte, não um defeito fabricado para o exercício.

## 1. Canais renomeados no meio da série

Zerados em 2020: Fale Conosco, Aplicativo Móvel.
Inexistentes em 2015: Usuário WEB, Mobile App.

Não são canais novos: são os mesmos, renomeados. Tratados como
categorias distintas, a série afirma que a reclamação por aplicativo
caiu a zero em 2020 — quando ela é justamente a que mais cresce.

## 2. 2020 é um ano parcial

Meses presentes em 2020: 01, 02, 03, 04, 05.
Qualquer comparação anual precisa recortar os mesmos meses dos dois lados.

## 3. O grão não é a reclamação

Cada linha já é uma contagem, na coluna `SOLICITAÇÕES`. Contar linhas
subestima o volume: são 15.952.407 linhas para 18.813.384 solicitações.

## 4. Mesma categoria, duas grafias

Encontradas: 'Denúncia ANÔNIMA', 'Denúncia Anônima'.
