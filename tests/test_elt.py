import json
from datetime import datetime

import pandas as pd

from src import elt


def test_pedido_vira_uma_linha_por_recebimento(tmp_path):
    arquivo = tmp_path / "p.json"
    arquivo.write_text(json.dumps([{"pedido_id": "P1", "fornecedor_id": "F1", "cd": "GRU", "emitido_em": "2025-01-01", "previsto_para": "2025-01-05", "itens": [
        {"sku": "A", "caixas": 2, "unidades_pedidas": 20, "custo_unitario": 1.5, "recebimentos": [{"data": "2025-01-05", "unidades": 10}, {"data": "2025-01-08", "unidades": 10}]},
        {"sku": "B", "caixas": 1, "unidades_pedidas": 12, "custo_unitario": 2.0, "recebimentos": []},
    ]}]))
    df = elt.achatar_pedidos(arquivo)
    assert df["sku"].tolist() == ["A", "A", "B"]
    assert df["recebimento_ordem"].tolist() == [1, 2, 1]
    assert df.loc[2, "recebido_em"] == ""          # item em aberto continua aparecendo


def test_carga_do_mes_acontece_no_mes_seguinte():
    assert elt.momento_da_carga("2025-12") == datetime(2026, 1, 1, 3, 0)


def test_arquivo_ja_carregado_e_ignorado_e_arquivo_alterado_entra(tmp_path):
    csv = tmp_path / "a.csv"
    csv.write_text("x\n1\n")
    with elt.conectar(tmp_path / "w.duckdb") as conexao:
        momento = datetime(2025, 1, 1)
        assert elt._carregar_arquivo(conexao, csv, "t", elt._ler_texto, momento) == 1
        assert elt._carregar_arquivo(conexao, csv, "t", elt._ler_texto, momento) == 0
        csv.write_text("x\n1\n2\n")
        assert elt._carregar_arquivo(conexao, csv, "t", elt._ler_texto, momento) == 2
        assert conexao.execute("SELECT count(*) FROM raw.t").fetchone()[0] == 3     # raw é append-only


def test_raw_guarda_tudo_como_texto_com_origem(tmp_path):
    with elt.conectar(tmp_path / "w.duckdb") as conexao:
        elt._anexar(conexao, "t", pd.DataFrame({"a": ["N/D", "1"]}), "arq.csv", datetime(2025, 1, 1))
        linha = conexao.execute("SELECT a, _arquivo FROM raw.t").fetchone()
    assert linha == ("N/D", "arq.csv")
