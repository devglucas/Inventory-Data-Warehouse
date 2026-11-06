"""Lê os marts e escreve as tabelas e o relatório em Markdown."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from src.utils import df_para_markdown, formatar_br

CONSULTAS = {
    "valor_estoque_mensal": "SELECT mes, cd_id, sum(unidades) AS unidades, sum(valor_estoque) AS valor_estoque FROM analises.mart_valor_estoque_mensal GROUP BY 1, 2 ORDER BY 1, 2",
    "ruptura_mensal": """SELECT mes, sum(sku_dias_sem_estoque) * 1.0 / sum(sku_dias) AS taxa_ruptura, sum(unidades_perdidas) AS unidades_perdidas,
                                sum(receita_perdida) AS receita_perdida, sum(margem_perdida) AS margem_perdida
                         FROM analises.mart_ruptura_mensal GROUP BY 1 ORDER BY 1""",
    "ruptura_fornecedor": """SELECT r.fornecedor_id, f.nome, sum(r.sku_dias_sem_estoque) * 1.0 / sum(r.sku_dias) AS taxa_ruptura, sum(r.unidades_perdidas) AS unidades_perdidas,
                                    sum(r.receita_perdida) AS receita_perdida, sum(r.margem_perdida) AS margem_perdida
                             FROM analises.mart_ruptura_mensal r JOIN core.dim_fornecedor f USING (fornecedor_id) GROUP BY 1, 2 ORDER BY receita_perdida DESC""",
    "fornecedores": "SELECT * FROM analises.mart_fornecedores ORDER BY fornecedor_id, trimestre",
    "acuracidade": "SELECT * FROM analises.mart_acuracidade ORDER BY cd_id, categoria",
    "situacao_por_cd": """SELECT cd_id, situacao, count(*) AS sku_cds, sum(valor_estoque) AS valor_estoque
                          FROM analises.mart_giro_cobertura GROUP BY 1, 2 ORDER BY 1, 2""",
    "giro_por_cd": """SELECT cd_id, sum(valor_estoque) AS valor_estoque, median(giro_anual) AS giro_mediano, median(dias_cobertura) AS cobertura_mediana_dias
                      FROM analises.mart_giro_cobertura WHERE ativo GROUP BY 1 ORDER BY 1""",
    "curva_abc": "SELECT * FROM analises.mart_curva_abc ORDER BY participacao_acumulada",
    "resumo_abc": "SELECT classe_abc, count(*) AS skus, sum(receita) AS receita FROM analises.mart_curva_abc GROUP BY 1 ORDER BY 1",
    "estoque_parado": "SELECT * FROM analises.mart_estoque_parado ORDER BY valor_estoque DESC",
    "rebalanceamento": "SELECT * FROM analises.mart_rebalanceamento ORDER BY compra_evitada DESC",
    "movimentos_rejeitados": "SELECT motivo, count(*) AS linhas FROM intermediate.int_movimentos_rejeitados GROUP BY 1 ORDER BY 2 DESC",
}


def _numericos(df: pd.DataFrame) -> pd.DataFrame:
    decimais = [c for c in df.columns if df[c].map(lambda v: v.__class__.__name__ == "Decimal").any()]
    return df.astype({c: float for c in decimais})


def ler_marts(conexao: duckdb.DuckDBPyConnection) -> dict[str, pd.DataFrame]:
    return {nome: _numericos(conexao.execute(consulta).df()) for nome, consulta in CONSULTAS.items()}


def exportar(tabelas: dict[str, pd.DataFrame], pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, tabela in tabelas.items():
        tabela.to_csv(pasta / f"{nome}.csv", index=False, float_format="%.4f")


def escrever(t: dict[str, pd.DataFrame], verificacoes: list[dict], build: dict, destino: Path) -> None:
    ruptura = t["ruptura_mensal"]
    valor_final = t["valor_estoque_mensal"].query("mes == mes.max()")["valor_estoque"].sum()
    tabela_v = pd.DataFrame(verificacoes).assign(resultado=lambda d: d["ok"].map({True: "ok", False: "falhou"}))
    partes = [
        "# Relatório de estoque: Ponte Alta Distribuidora\n",
        "## Resumo\n",
        f"- Valor do estoque em 31/12/2025: R$ {formatar_br(float(valor_final))}",
        f"- Receita perdida por falta de estoque: R$ {formatar_br(float(ruptura['receita_perdida'].sum()))}",
        f"- Estoque parado: R$ {formatar_br(float(t['estoque_parado']['valor_estoque'].sum()))}",
        f"- dbt: {build['por_status']}\n",
        "## Giro e cobertura por CD\n", df_para_markdown(t["giro_por_cd"]), "",
        "## Situação por CD\n", df_para_markdown(t["situacao_por_cd"]), "",
        "## Ruptura por mês\n", df_para_markdown(ruptura.assign(mes=ruptura["mes"].astype(str).str[:7]), 3), "",
        "## Ruptura por fornecedor\n", df_para_markdown(t["ruptura_fornecedor"], 3), "",
        "## Curva ABC\n", df_para_markdown(t["resumo_abc"]), "",
        "## Acuracidade das contagens\n", df_para_markdown(t["acuracidade"], 3), "",
        "## Movimentos rejeitados\n", df_para_markdown(t["movimentos_rejeitados"]), "",
        "## Conferência com o gabarito\n", df_para_markdown(tabela_v[["verificacao", "resultado", "detalhe"]]), "",
    ]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(partes), encoding="utf-8")
