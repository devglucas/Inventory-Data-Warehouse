"""
Publica o warehouse no BigQuery repassando os meses em ordem, como a rotina local faz.

Precisa de projeto no Google Cloud, de `gcloud auth application-default login` e destas variáveis:
    GCP_PROJECT   projeto
    BQ_LOCATION   região, por padrão southamerica-east1

Antes, rode `python main.py` para ter o raw no DuckDB local. Este script não foi executado contra o
BigQuery real, porque isso depende de uma conta. O projeto dbt foi validado com `dbt parse --target bigquery`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb
from google.cloud import bigquery

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import elt, orquestracao

TABELAS_FIXAS = ["fornecedores", "saldo_inicial", "contagens", "demanda_perdida", "pedidos_compra"]


def enviar(cliente: bigquery.Client, df, tabela: str) -> None:
    destino = f"{cliente.project}.raw.{tabela}"
    configuracao = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    cliente.load_table_from_dataframe(df, destino, job_config=configuracao).result()


def main() -> None:
    cliente = bigquery.Client(project=os.environ["GCP_PROJECT"])
    cliente.create_dataset(bigquery.Dataset(f"{cliente.project}.raw"), exists_ok=True)
    os.environ["ESTOQUE_DUCKDB"] = str(orquestracao.BANCO_PADRAO)
    alvo = ("--target", "bigquery")

    with duckdb.connect(str(orquestracao.BANCO_PADRAO), read_only=True) as local:
        for tabela in TABELAS_FIXAS:
            enviar(cliente, local.execute(f"SELECT * FROM raw.{tabela}").df(), tabela)
        orquestracao.dbt("seed", *alvo)
        for mes in elt.meses_disponiveis():
            for tabela, arquivo in [("produtos", f"produtos_{mes}.csv"), ("movimentos", f"movimentos_{mes}.csv.gz")]:
                enviar(cliente, local.execute(f"SELECT * FROM raw.{tabela} WHERE _arquivo = ?", [arquivo]).df(), tabela)
            orquestracao.dbt("run", "--select", "stg_erp__produtos", *alvo)
            orquestracao.dbt("snapshot", *alvo)
            orquestracao.dbt("run", "--select", "+fct_movimentos", "--exclude", "snap_produtos", *alvo)
    orquestracao.dbt("build", *alvo)


if __name__ == "__main__":
    main()
