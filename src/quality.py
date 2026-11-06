"""
Conferências fora do dbt. Os testes do dbt garantem que o warehouse é coerente por dentro;
aqui ele é comparado com o razão limpo do gerador, que o warehouse nunca viu.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import duckdb

ROOT_DIR = Path(__file__).resolve().parents[1]


def _item(nome: str, ok: bool, detalhe: str) -> dict:
    return {"verificacao": nome, "severidade": "critica", "ok": bool(ok), "detalhe": detalhe}


def verificar_gabarito(conexao: duckdb.DuckDBPyConnection, caminho: Path = ROOT_DIR / "data" / "external" / "gabarito.json") -> list[dict]:
    g = json.loads(caminho.read_text(encoding="utf-8"))
    valor = lambda consulta: conexao.execute(consulta).fetchone()[0]
    fim_de_mes = dict(conexao.execute("""
        SELECT strftime(e.data, '%Y-%m'), sum(e.saldo) FROM core.fct_estoque_diario e
        JOIN core.dim_data d USING (data) WHERE d.fim_de_mes GROUP BY 1""").fetchall())
    meses_errados = [m for m, saldo in g["saldo_total_fim_do_mes"].items() if float(fim_de_mes.get(m, -1)) != saldo]
    por_cd = dict(conexao.execute("SELECT cd_id, sum(saldo) FROM core.fct_estoque_diario WHERE data = DATE '2025-12-31' GROUP BY 1").fetchall())
    rejeitados = dict(conexao.execute("SELECT motivo, count(*) FROM intermediate.int_movimentos_rejeitados GROUP BY 1").fetchall())
    valor_final = float(valor("SELECT sum(valor_estoque) FROM core.fct_estoque_diario WHERE data = DATE '2025-12-31'"))
    comparacoes = {
        "movimentos válidos": (valor("SELECT count(*) FROM core.fct_movimentos"), g["movimentos_validos"]),
        "unidades vendidas": (-float(valor("SELECT sum(impacto) FROM core.fct_movimentos WHERE tipo = 'VENDA'")), g["unidades_vendidas"]),
        "demanda perdida": (float(valor("SELECT sum(quantidade) FROM core.fct_demanda_perdida")), g["unidades_demanda_perdida"]),
        "pedidos de compra": (valor("SELECT count(DISTINCT pedido_id) FROM core.fct_itens_pedido"), g["pedidos_de_compra"]),
        "contagens": (valor("SELECT count(*) FROM core.fct_contagens"), g["contagens"]),
        "unidades em trânsito": (float(valor("SELECT coalesce(sum(unidades), 0) FROM analises.mart_em_transito")), g["unidades_em_transito_no_fim"]),
        "SKU inexistente": (rejeitados.get("sku_desconhecido", 0), g["sujeira"]["sku_inexistente"]),
        "quantidade inválida": (rejeitados.get("quantidade_invalida", 0), g["sujeira"]["quantidade_invalida"]),
    }
    itens = [_item(f"gabarito: {nome}", atual == esperado, f"{atual} x {esperado}") for nome, (atual, esperado) in comparacoes.items()]
    return itens + [
        _item("gabarito: saldo total nos 12 fins de mês", not meses_errados, f"{len(meses_errados)} meses diferentes"),
        _item("gabarito: saldo final por CD", all(float(por_cd[c]) == s for c, s in g["saldo_final_por_cd"].items()), str({k: int(v) for k, v in por_cd.items()})),
        _item("gabarito: valor do estoque final", abs(valor_final - g["valor_estoque_final"]) < 0.01, f"{valor_final:.2f} x {g['valor_estoque_final']:.2f}"),
    ]


def resumir_build(resultado) -> dict:
    """Separa o que o dbt fez: modelos, testes de dados, testes unitários e alertas."""
    contagem = Counter()
    alertas = []
    for no in resultado.result.results:
        tipo = no.node.resource_type
        contagem[str(tipo)] += 1
        contagem[f"status_{no.status}"] += 1
        if str(no.status) == "warn":
            alertas.append({"teste": no.node.name, "linhas": no.failures})
    return {"por_tipo": {k: v for k, v in contagem.items() if not k.startswith("status_")},
            "por_status": {k.removeprefix("status_"): v for k, v in contagem.items() if k.startswith("status_")}, "alertas": alertas}
