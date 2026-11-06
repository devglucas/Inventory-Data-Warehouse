"""Executa o dbt pela API em Python e faz a rotina mensal: carregar, guardar histórico, atualizar fatos."""

from __future__ import annotations

import os
from pathlib import Path

from dbt.cli.main import dbtRunner

from src import elt
from src.utils import configurar_logger

ROOT_DIR = Path(__file__).resolve().parents[1]
DBT_DIR = ROOT_DIR / "dbt"
BANCO_PADRAO = ROOT_DIR / "warehouse" / "estoque.duckdb"

log = configurar_logger("dbt")


class FalhaNoDbt(Exception):
    pass


def dbt(*argumentos: str, tolerar_falha: bool = False):
    resultado = dbtRunner().invoke([*argumentos, "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR), "--quiet"])
    if not resultado.success and not tolerar_falha:
        raise FalhaNoDbt(f"dbt {' '.join(argumentos)}: {resultado.exception or 'há nós com falha'}")
    return resultado


def preparar(banco: Path) -> None:
    os.environ["ESTOQUE_DUCKDB"] = str(banco)
    os.environ.setdefault("DBT_SEND_ANONYMOUS_USAGE_STATS", "false")
    if not (DBT_DIR / "dbt_packages").exists():
        dbt("deps")


def rotina_mensal(banco: Path, mes: str) -> int:
    """
    A ordem importa: o snapshot do catálogo precisa rodar antes dos fatos,
    porque cada movimento busca o fator de caixa que valia na própria data.
    """
    with elt.conectar(banco) as conexao:
        linhas = elt.carregar_mes(conexao, mes)
    if linhas:
        dbt("run", "--select", "stg_erp__produtos")
        dbt("snapshot")
        dbt("run", "--select", "+fct_movimentos", "--exclude", "snap_produtos")
    return linhas
