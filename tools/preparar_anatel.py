"""
Baixa e prepara a base ABERTA e REAL de reclamacoes da ANATEL.

POR QUE ESTE SCRIPT EXISTE
--------------------------
O arquivo publicado pela ANATEL tem 2,5 GB e 15,9 milhoes de linhas. Ele nao
cabe (nem deve caber) num repositorio git. O que este script faz e a unica
coisa honesta possivel: baixa a fonte, faz UMA passada em blocos, e grava
agregados pequenos o suficiente para serem versionados e conferidos por
qualquer pessoa que clone o repositorio.

Quem quiser refazer do zero roda:  python tools/preparar_anatel.py
Quem so quiser ler a analise usa os CSVs ja versionados em data/processed/.

O GRAO DA FONTE
---------------
A base NAO traz reclamacoes individuais. Cada linha ja e uma contagem
(`SOLICITACOES`) para a combinacao mes x UF x municipio x canal x condicao x
tipo x servico x marca x assunto x problema. Toda soma daqui para a frente e
soma de SOLICITACOES, nunca contagem de linhas — confundir os dois foi o
primeiro erro que este script teve de evitar.

Fonte: https://www.anatel.gov.br/dadosabertos/paineis_de_dados/consumidor/
"""

from __future__ import annotations

import hashlib
import io
import ssl
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
BRUTO = RAIZ / "data" / "raw"
SAIDA = RAIZ / "data" / "processed"
URL = (
    "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/"
    "consumidor/consumidor_reclamacoes.zip"
)
CSV = "reclamacoes.csv"
BLOCO = 1_500_000

# Colunas que a analise usa. Ler so estas corta o tempo e a memoria pela metade.
COLS = [
    "Ano", "AnoMês", "UF", "CanalEntrada", "Condição",
    "TipoAtendimento", "Serviço", "Marca", "Assunto", "SOLICITAÇÕES",
]

# Nomes sem acento para o resto do pipeline nao depender de encoding.
RENOMEIA = {
    "AnoMês": "ano_mes", "Ano": "ano", "UF": "uf",
    "CanalEntrada": "canal", "Condição": "condicao",
    "TipoAtendimento": "tipo", "Serviço": "servico",
    "Marca": "marca", "Assunto": "assunto", "SOLICITAÇÕES": "solicitacoes",
}


def baixar() -> Path:
    BRUTO.mkdir(parents=True, exist_ok=True)
    destino = BRUTO / CSV
    if destino.exists():
        print(f"[skip] {destino.name} ja existe ({destino.stat().st_size/1e9:.2f} GB)")
        return destino

    print("Baixando da ANATEL (~334 MB compactados)...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600, context=ctx) as r:
        dados = r.read()
    print(f"  baixado: {len(dados)/1e6:.0f} MB · sha256 {hashlib.sha256(dados).hexdigest()[:16]}")
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        z.extract(CSV, BRUTO)
    print(f"  extraido: {destino.stat().st_size/1e9:.2f} GB")
    return destino


def agregar(csv: Path) -> dict[str, pd.DataFrame]:
    """Uma passada, varios agregados. Ler 2,5 GB uma vez por grao seria burrice."""
    acc: dict[str, list[pd.DataFrame]] = {}
    linhas = 0

    grupos = {
        "marca_mes":       ["ano_mes", "marca", "servico"],
        "uf_marca":        ["uf", "marca"],
        "assunto_marca":   ["assunto", "marca"],
        "uf_mes":          ["uf", "ano_mes"],
        "canal_ano":       ["canal", "ano"],
        "condicao_marca":  ["ano", "marca", "condicao"],
        "tipo_ano":        ["tipo", "ano"],
    }

    for bloco in pd.read_csv(
        csv, sep=";", encoding="utf-8-sig", usecols=COLS,
        dtype=str, chunksize=BLOCO, on_bad_lines="skip",
    ):
        bloco = bloco.rename(columns=RENOMEIA)
        bloco["solicitacoes"] = pd.to_numeric(bloco["solicitacoes"], errors="coerce").fillna(0)
        linhas += len(bloco)
        for nome, chaves in grupos.items():
            g = bloco.groupby(chaves, dropna=False)["solicitacoes"].sum().reset_index()
            acc.setdefault(nome, []).append(g)
        print(f"\r  {linhas:,} linhas", end="", flush=True)

    print()
    saida = {}
    for nome, partes in acc.items():
        df = pd.concat(partes, ignore_index=True)
        chaves = grupos[nome]
        df = df.groupby(chaves, dropna=False)["solicitacoes"].sum().reset_index()
        df["solicitacoes"] = df["solicitacoes"].astype("int64")
        saida[nome] = df.sort_values("solicitacoes", ascending=False)
    saida["_meta"] = pd.DataFrame([{"linhas_lidas": linhas}])
    return saida


def main() -> None:
    csv = baixar()
    print("Agregando (uma passada em blocos de 1,5 M)...")
    tabelas = agregar(csv)
    SAIDA.mkdir(parents=True, exist_ok=True)

    total = int(tabelas["marca_mes"]["solicitacoes"].sum())
    for nome, df in tabelas.items():
        if nome.startswith("_"):
            continue
        caminho = SAIDA / f"agg_{nome}.csv"
        df.to_csv(caminho, index=False, encoding="utf-8")
        print(f"  {caminho.name:26} {len(df):>7,} linhas  {caminho.stat().st_size/1024:>7.0f} KB")

    # Conferencia cruzada: todo agregado tem de fechar no mesmo total.
    print("\nConferencia — todo agregado fecha no mesmo total?")
    ok = True
    for nome, df in tabelas.items():
        if nome.startswith("_"):
            continue
        t = int(df["solicitacoes"].sum())
        marca = "OK " if t == total else "ERRO"
        if t != total:
            ok = False
        print(f"  {marca} agg_{nome:16} {t:>12,}")
    print(f"\nlinhas lidas: {int(tabelas['_meta']['linhas_lidas'][0]):,}")
    print(f"solicitacoes: {total:,}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
