"""Ponta a ponta: repassa os 12 meses em um warehouse temporário e confere o resultado."""

import duckdb
import pytest

from main import executar
from src import orquestracao


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("warehouse")
    banco = pasta / "teste.duckdb"
    return banco, pasta, executar(banco, pasta / "saida")


def _consulta(banco, sql):
    with duckdb.connect(str(banco)) as conexao:
        return conexao.execute(sql).fetchall()


def test_build_passa_e_confere_com_o_gabarito(warehouse):
    _, _, resultado = warehouse
    assert resultado["manifesto"]["sucesso"]
    assert [v for v in resultado["verificacoes"] if not v["ok"]] == []


def test_dbt_roda_testes_de_dados_e_unitarios(warehouse):
    _, _, resultado = warehouse
    por_tipo = resultado["manifesto"]["dbt"]["por_tipo"]
    assert por_tipo["test"] >= 40 and por_tipo["unit_test"] >= 5


def test_alertas_ficam_visiveis_sem_derrubar_o_build(warehouse):
    _, _, resultado = warehouse
    assert {a["teste"] for a in resultado["manifesto"]["dbt"]["alertas"]} == {"saldo_nao_negativo", "contagem_bate_com_saldo"}


def test_snapshot_guarda_a_troca_de_embalagem(warehouse):
    banco, _, _ = warehouse
    trocas = _consulta(banco, """SELECT count(*) FROM (SELECT sku FROM core.dim_produto GROUP BY sku
                                 HAVING count(DISTINCT unidades_por_caixa) > 1)""")[0][0]
    assert trocas == 15


def test_versao_do_snapshot_vale_desde_a_mudanca_no_erp_e_nao_desde_a_carga(warehouse):
    banco, _, _ = warehouse
    datas = _consulta(banco, "SELECT DISTINCT cast(valido_de AS date)::varchar FROM core.dim_produto WHERE cast(valido_de AS date) > DATE '2025-01-01' ORDER BY 1")
    assert ("2025-04-10",) in datas


def test_correcao_tardia_substitui_o_movimento_sem_duplicar(warehouse):
    banco, _, _ = warehouse
    assert _consulta(banco, "SELECT count(*) - count(DISTINCT movimento_id) FROM core.fct_movimentos")[0][0] == 0


def test_incremental_chega_ao_mesmo_resultado_do_full_refresh(warehouse):
    banco, _, _ = warehouse
    orquestracao.preparar(banco)
    consulta = "SELECT count(*), sum(impacto), sum(impacto_valor) FROM core.fct_movimentos"
    incremental = _consulta(banco, consulta)
    orquestracao.dbt("run", "--select", "fct_movimentos", "--full-refresh")
    assert _consulta(banco, consulta) == incremental


def test_segunda_execucao_nao_carrega_nada_nem_muda_o_saldo(warehouse):
    banco, pasta, primeira = warehouse
    saldo = "SELECT sum(saldo) FROM core.fct_estoque_diario WHERE data = DATE '2025-12-31'"
    antes = _consulta(banco, saldo)
    segunda = executar(banco, pasta / "saida2")
    assert segunda["manifesto"]["linhas_carregadas"] == 0
    assert _consulta(banco, saldo) == antes


def test_saidas_foram_geradas(warehouse):
    _, pasta, _ = warehouse
    assert (pasta / "saida" / "relatorio.md").exists()
    assert len(list((pasta / "saida" / "charts").glob("*.png"))) == 6
