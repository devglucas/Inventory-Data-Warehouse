"""
Pipeline de estoque (ELT): arquivos -> raw -> dbt (staging, snapshot, marts, testes) -> relatório.

    python main.py             carrega o que falta e reconstrói o warehouse
    python main.py --recriar   apaga o warehouse e repassa todos os meses
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from src import elt, orquestracao, quality, report, visualize
from src.utils import configurar_logger, gravar_logs_em

ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT_DIR / "output"

log = configurar_logger("main")


def executar(banco: Path = orquestracao.BANCO_PADRAO, saida: Path = OUTPUT_DIR) -> dict:
    inicio = time.perf_counter()
    orquestracao.preparar(banco)
    with elt.conectar(banco) as conexao:
        linhas = elt.carregar_cadastros(conexao)
    orquestracao.dbt("seed")

    for mes in elt.meses_disponiveis():
        novas = orquestracao.rotina_mensal(banco, mes)
        linhas += novas
        if novas:
            log.info("%s: %d linhas carregadas", mes, novas)

    resultado = orquestracao.dbt("build", tolerar_falha=True)
    build = quality.resumir_build(resultado)
    log.info("dbt build: %s", build["por_status"])

    with duckdb.connect(str(banco)) as conexao:
        verificacoes = quality.verificar_gabarito(conexao) if resultado.success else []
        tabelas = report.ler_marts(conexao) if resultado.success else {}
    falhas = [v for v in verificacoes if not v["ok"]]
    sucesso = bool(resultado.success) and not falhas

    if resultado.success:
        report.exportar(tabelas, saida / "reports")
        report.escrever(tabelas, verificacoes, build, saida / "relatorio.md")
        visualize.gerar(tabelas, saida / "charts")

    manifesto = {
        "executado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sucesso": sucesso, "duracao_s": round(time.perf_counter() - inicio, 2),
        "linhas_carregadas": linhas, "dbt": build, "conferencias": {"total": len(verificacoes), "com_falha": len(falhas)},
    }
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "run_manifest.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    for falha in falhas:
        log.error("conferência falhou: %s (%s)", falha["verificacao"], falha["detalhe"])
    log.info("concluído em %.1fs | %d conferências, %d com falha", manifesto["duracao_s"], len(verificacoes), len(falhas))
    return {"manifesto": manifesto, "verificacoes": verificacoes, "tabelas": tabelas}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--recriar", action="store_true", help="apaga o warehouse local e repassa todos os meses")
    argumentos = parser.parse_args()
    gravar_logs_em(OUTPUT_DIR / "logs" / "pipeline.log")
    if argumentos.recriar:
        orquestracao.BANCO_PADRAO.unlink(missing_ok=True)
    return 0 if executar()["manifesto"]["sucesso"] else 1


if __name__ == "__main__":
    sys.exit(main())
