"""
Extract-load: leva os arquivos para o esquema raw sem interpretar nada.

No ELT a transformação fica no warehouse. Aqui tudo entra como texto, com o nome do arquivo e o
horário da carga, para que o dbt decida como limpar e para que dê para reprocessar sem voltar à fonte.
Arquivos já carregados são reconhecidos pelo hash.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT_DIR / "data" / "raw"


def conectar(caminho: Path) -> duckdb.DuckDBPyConnection:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conexao = duckdb.connect(str(caminho))
    conexao.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conexao.execute("CREATE TABLE IF NOT EXISTS raw.carga_arquivos (arquivo VARCHAR PRIMARY KEY, hash VARCHAR, linhas BIGINT, carregado_em TIMESTAMP)")
    return conexao


def _ja_carregado(conexao, arquivo: str, assinatura: str) -> bool:
    return conexao.execute("SELECT 1 FROM raw.carga_arquivos WHERE arquivo = ? AND hash = ?", [arquivo, assinatura]).fetchone() is not None


def _registrar(conexao, arquivo: str, assinatura: str, linhas: int, momento: datetime) -> None:
    conexao.execute("INSERT OR REPLACE INTO raw.carga_arquivos VALUES (?, ?, ?, ?)", [arquivo, assinatura, linhas, momento])


def _anexar(conexao, tabela: str, df: pd.DataFrame, arquivo: str, momento: datetime) -> int:
    """Acrescenta à tabela raw, criando-a na primeira vez."""
    dados = df.astype("string").assign(_arquivo=arquivo, _carregado_em=momento)
    conexao.register("lote", dados)
    existe = conexao.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = 'raw' AND table_name = ?", [tabela]).fetchone()
    conexao.execute(f"INSERT INTO raw.{tabela} BY NAME SELECT * FROM lote" if existe else f"CREATE TABLE raw.{tabela} AS SELECT * FROM lote")
    conexao.unregister("lote")
    return len(dados)


def _carregar_arquivo(conexao, caminho: Path, tabela: str, leitor, momento: datetime) -> int:
    assinatura = hashlib.sha256(caminho.read_bytes()).hexdigest()
    if _ja_carregado(conexao, caminho.name, assinatura):
        return 0
    linhas = _anexar(conexao, tabela, leitor(caminho), caminho.name, momento)
    _registrar(conexao, caminho.name, assinatura, linhas, momento)
    return linhas


def _ler_texto(caminho: Path, separador: str = ",") -> pd.DataFrame:
    return pd.read_csv(caminho, sep=separador, dtype=str, keep_default_na=False)


def achatar_pedidos(caminho: Path) -> pd.DataFrame:
    """Uma linha por recebimento de item. Item ainda não recebido vira uma linha sem recebimento."""
    linhas = []
    for pedido in json.loads(caminho.read_text(encoding="utf-8")):
        cabecalho = {k: pedido[k] for k in ["pedido_id", "fornecedor_id", "cd", "emitido_em", "previsto_para"]}
        for item in pedido["itens"]:
            base = {**cabecalho, **{k: item[k] for k in ["sku", "caixas", "unidades_pedidas", "custo_unitario"]}}
            for ordem, recebimento in enumerate(item["recebimentos"] or [{"data": "", "unidades": ""}], start=1):
                linhas.append({**base, "recebimento_ordem": ordem, "recebido_em": recebimento["data"], "unidades_recebidas": recebimento["unidades"]})
    return pd.DataFrame(linhas)


def momento_da_carga(mes: str) -> datetime:
    """Horário simulado: a carga de um mês acontece no primeiro dia do mês seguinte."""
    return (pd.Period(mes, "M") + 1).start_time.to_pydatetime() + timedelta(hours=3)


def meses_disponiveis() -> list[str]:
    return sorted(p.name.removeprefix("movimentos_").removesuffix(".csv.gz") for p in (RAW_DIR / "wms").glob("movimentos_*.csv.gz"))


def carregar_mes(conexao, mes: str) -> int:
    """Carrega o catálogo e os movimentos de um mês, como aconteceria na rotina mensal."""
    momento = momento_da_carga(mes)
    linhas = _carregar_arquivo(conexao, RAW_DIR / "erp" / f"produtos_{mes}.csv", "produtos", lambda c: _ler_texto(c, ";"), momento)
    return linhas + _carregar_arquivo(conexao, RAW_DIR / "wms" / f"movimentos_{mes}.csv.gz", "movimentos", _ler_texto, momento)


def carregar_cadastros(conexao) -> int:
    """Fontes que não são mensais: entram uma vez, depois do último mês."""
    momento = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    fontes = [
        (RAW_DIR / "erp" / "fornecedores.csv", "fornecedores", _ler_texto), (RAW_DIR / "wms" / "saldo_inicial.csv", "saldo_inicial", _ler_texto),
        (RAW_DIR / "wms" / "contagens.csv", "contagens", _ler_texto), (RAW_DIR / "vendas" / "demanda_perdida.csv.gz", "demanda_perdida", _ler_texto),
        (RAW_DIR / "compras" / "pedidos_compra.json", "pedidos_compra", achatar_pedidos),
    ]
    return sum(_carregar_arquivo(conexao, caminho, tabela, leitor, momento) for caminho, tabela, leitor in fontes)
