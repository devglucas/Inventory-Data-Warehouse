"""Gráficos do relatório de estoque."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logging.getLogger("matplotlib").setLevel(logging.WARNING)

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
CINZA, TINTA_2, GRADE, EIXO, SUPERFICIE = "#b5b3ab", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
RAMPA_LARANJA = ["#fde3d3", "#f9c0a0", "#f29a6c", "#eb6834", "#c74f20"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
NOMES_CD = {"GRU": "Guarulhos", "CWB": "Curitiba", "REC": "Recife"}
NOMES_SITUACAO = {"saudavel": "Saudável", "excesso": "Excesso", "risco": "Risco", "sem_giro": "Sem giro"}


def _rs(texto: str) -> str:
    return texto.replace("$", r"\$")


def _estilo() -> None:
    plt.rcParams.update({
        "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE, "savefig.facecolor": SUPERFICIE, "font.size": 11,
        "axes.edgecolor": EIXO, "axes.labelcolor": TINTA_2, "xtick.color": TINTA_2, "ytick.color": TINTA_2,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRADE,
        "axes.axisbelow": True, "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlepad": 24, "axes.titlelocation": "left",
    })


def _salvar(fig, pasta: Path, nome: str) -> None:
    fig.tight_layout()
    fig.savefig(pasta / f"{nome}.png", dpi=150)
    plt.close(fig)


def receita_perdida(ruptura: pd.DataFrame, pasta: Path) -> None:
    rotulos = [MESES[pd.Timestamp(m).month - 1] for m in ruptura["mes"]]
    valores = ruptura["receita_perdida"] / 1000
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    cores = [SERIES[1] if v == valores.max() else SERIES[0] for v in valores]
    barras = ax.bar(rotulos, valores, color=cores)
    ax.bar_label(barras, fmt="%.0f", padding=3, color=TINTA_2, fontsize=10)
    ax.set_ylabel(_rs("Receita perdida (R$ mil)"))
    ax.set_title("A falta de estoque começa em setembro e explode em novembro")
    ax.margins(y=0.12)
    _salvar(fig, pasta, "01_receita_perdida")


def lead_time(fornecedores: pd.DataFrame, pasta: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    trimestres = sorted(fornecedores["trimestre"].unique())
    rotulos = [f"{i + 1}º tri" for i in range(len(trimestres))]
    for fornecedor, grupo in fornecedores.groupby("fornecedor_id"):
        destaque = fornecedor == "F01"
        ax.plot(rotulos, grupo.sort_values("trimestre")["lead_time_medio"], color=SERIES[1] if destaque else CINZA, linewidth=2.6 if destaque else 1.2, zorder=3 if destaque else 2)
    ultimo = fornecedores[fornecedores["fornecedor_id"] == "F01"].sort_values("trimestre").iloc[-1]
    ax.annotate(f"{ultimo['nome']}: {ultimo['lead_time_medio']:.0f} dias", (rotulos[-1], ultimo["lead_time_medio"]), textcoords="offset points", xytext=(-6, 8), ha="right", color=SERIES[1], fontweight="bold")
    ax.set_ylim(0, None)
    ax.set_ylabel("Lead time médio (dias)")
    ax.set_title("Um fornecedor dobrou o prazo de entrega a partir do 3º trimestre")
    _salvar(fig, pasta, "02_lead_time_fornecedores")


def perda_por_fornecedor(tabela: pd.DataFrame, pasta: Path) -> None:
    dados = tabela.sort_values("receita_perdida")
    fig, ax = plt.subplots(figsize=(9, 4.8))
    barras = ax.barh(dados["nome"], dados["receita_perdida"] / 1000, color=SERIES[0])
    ax.bar_label(barras, fmt="%.0f", padding=4, color=TINTA_2)
    ax.grid(False)
    ax.set_xlabel(_rs("Receita perdida no ano (R$ mil)"))
    ax.set_title("Dois fornecedores concentram a receita perdida")
    ax.margins(x=0.1)
    _salvar(fig, pasta, "03_perda_por_fornecedor")


def acuracidade(tabela: pd.DataFrame, pasta: Path) -> None:
    categorias = tabela.assign(categoria=tabela["categoria"].replace({"EPI": "Segurança"}))
    agrupado = categorias.groupby(["cd_id", "categoria"]).apply(lambda g: np.average(g["acuracidade"], weights=g["contagens"]), include_groups=False).unstack()
    agrupado = agrupado.loc[["GRU", "CWB", "REC"]] * 100
    fig, ax = plt.subplots(figsize=(9.5, 3.6))
    cor = matplotlib.colors.ListedColormap(RAMPA_LARANJA[::-1])
    ax.imshow(agrupado.to_numpy(), cmap=cor, vmin=40, vmax=100, aspect="auto")
    ax.set_xticks(range(agrupado.shape[1]), agrupado.columns)
    ax.set_yticks(range(3), [NOMES_CD[c] for c in agrupado.index])
    for (linha, coluna), valor in np.ndenumerate(agrupado.to_numpy()):
        ax.text(coluna, linha, f"{valor:.0f}%", ha="center", va="center", color="white" if valor < 70 else TINTA_2, fontweight="bold" if valor < 70 else "normal")
    ax.grid(False)
    ax.tick_params(length=0)
    for lado in ax.spines.values():
        lado.set_visible(False)
    ax.set_title("Em Recife, só 41% das contagens de ferramentas batem com o sistema")
    _salvar(fig, pasta, "04_acuracidade")


def situacao_por_cd(tabela: pd.DataFrame, pasta: Path) -> None:
    dados = tabela[tabela["situacao"] != "ruptura"].pivot(index="cd_id", columns="situacao", values="valor_estoque").fillna(0).loc[["GRU", "CWB", "REC"]]
    fatias = dados.div(dados.sum(axis=1), axis=0) * 100
    fig, ax = plt.subplots(figsize=(9.5, 3.8))
    nomes = [NOMES_CD[c] for c in fatias.index][::-1]
    esquerda = np.zeros(3)
    for situacao, cor in [("saudavel", SERIES[0]), ("excesso", SERIES[1]), ("sem_giro", CINZA), ("risco", SERIES[3])]:
        valores = fatias[situacao].to_numpy()[::-1]
        ax.barh(nomes, valores, left=esquerda, color=cor, label=NOMES_SITUACAO[situacao])
        for y, (v, x) in enumerate(zip(valores, esquerda)):
            if v >= 5:
                ax.text(x + v / 2, y, f"{v:.0f}%", ha="center", va="center", color="white", fontweight="bold")
        esquerda += valores
    ax.grid(False)
    ax.set_xlabel("Participação no valor do estoque (%)")
    ax.set_title("Um quinto do estoque de Recife é excesso")
    ax.legend(frameon=False, ncols=4, loc="lower left", bbox_to_anchor=(0, 1.0), borderaxespad=0, fontsize=10)
    _salvar(fig, pasta, "05_situacao_por_cd")


def curva_abc(tabela: pd.DataFrame, pasta: Path) -> None:
    posicao = np.arange(1, len(tabela) + 1) / len(tabela) * 100
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(posicao, tabela["participacao_acumulada"] * 100, color=SERIES[0], linewidth=2.4)
    classe_a = (tabela["classe_abc"] == "A").sum() / len(tabela) * 100
    ax.axhline(80, color=CINZA, linewidth=1)
    ax.axvline(classe_a, color=CINZA, linewidth=1)
    ax.annotate(f"{classe_a:.0f}% dos SKUs = 80% da receita", (classe_a, 80), textcoords="offset points", xytext=(10, -18), color=TINTA_2)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 102)
    ax.set_xlabel("SKUs, do que mais vende ao que menos vende (%)")
    ax.set_ylabel("Receita acumulada (%)")
    ax.set_title("Um quarto dos SKUs responde por 80% da receita")
    _salvar(fig, pasta, "06_curva_abc")


def gerar(t: dict[str, pd.DataFrame], pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    _estilo()
    receita_perdida(t["ruptura_mensal"], pasta)
    lead_time(t["fornecedores"], pasta)
    perda_por_fornecedor(t["ruptura_fornecedor"], pasta)
    acuracidade(t["acuracidade"], pasta)
    situacao_por_cd(t["situacao_por_cd"], pasta)
    curva_abc(t["curva_abc"], pasta)
