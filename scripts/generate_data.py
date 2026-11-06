"""
Gera os dados de estoque da Ponte Alta Distribuidora (empresa fictícia), 2025 inteiro, dia a dia.

Três centros de distribuição vendem materiais de construção. A simulação controla estoque real e
estoque do sistema: furtos e perdas não registradas só aparecem quando há contagem física.

Saídas em data/raw:
    wms/movimentos_AAAA-MM.csv.gz   razão de movimentos, um arquivo por mês de carga
    wms/saldo_inicial.csv           saldo em 31/12/2024
    wms/contagens.csv               contagens cíclicas
    erp/produtos_AAAA-MM.csv        catálogo completo no fim de cada mês
    erp/fornecedores.csv
    compras/pedidos_compra.json     pedidos com itens aninhados e recebimentos
    vendas/demanda_perdida.csv      demanda que não pôde ser atendida

A sujeira entra só na exportação; o gabarito em data/external sai do razão limpo.
"""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEMENTE = 8
rng = np.random.default_rng(SEMENTE)

RAIZ = Path(__file__).resolve().parents[1]
RAW, EXTERNOS = RAIZ / "data" / "raw", RAIZ / "data" / "external"
INICIO, FIM = date(2025, 1, 1), date(2025, 12, 31)
DIAS = (FIM - INICIO).days + 1

CDS = ["GRU", "CWB", "REC"]
PESO_CD = np.array([0.55, 0.27, 0.18])
N_SKUS = 320
CATEGORIAS = {"Ferramentas": 0.25, "Elétrica": 0.25, "Hidráulica": 0.2, "EPI": 0.1, "Pintura": 0.1, "Fixadores": 0.1}
FORNECEDORES = [
    ("F01", "Metalúrgica Forte", "Ferramentas", 9), ("F02", "Aço Sul Ferramentas", "Ferramentas", 12),
    ("F03", "Eletrofio Condutores", "Elétrica", 7), ("F04", "Luminar Componentes", "Elétrica", 14),
    ("F05", "Tubonorte", "Hidráulica", 10), ("F06", "Proteja EPIs", "EPI", 8),
    ("F07", "Cor Viva Tintas", "Pintura", 6), ("F08", "Rosca Fina Fixadores", "Fixadores", 5),
]
FORNECEDOR_ATRASADO = "F01"                     # lead time piora a partir de agosto
FORNECEDOR_REAJUSTE = "F03"                     # custo sobe 8% em julho
MES_ATRASO, MES_REAJUSTE = 8, 7
FATORES_CAIXA = [6, 10, 12, 24]


@dataclass
class Produto:
    sku: str
    nome: str
    categoria: str
    fornecedor: str
    custo: float
    preco: float
    fator: int
    ativo: bool = True
    atualizado_em: datetime = datetime(2024, 11, 4, 9, 0)


@dataclass
class Pedido:
    pedido_id: str
    fornecedor: str
    cd: str
    emitido: date
    previsto: date
    itens: list = field(default_factory=list)


def criar_catalogo() -> tuple[list[Produto], np.ndarray]:
    categorias = rng.choice(list(CATEGORIAS), N_SKUS, p=list(CATEGORIAS.values()))
    produtos = []
    for i, categoria in enumerate(categorias):
        opcoes = [f[0] for f in FORNECEDORES if f[2] == categoria]
        preco = round(float(rng.lognormal(3.6, 0.9)), 2)
        produtos.append(Produto(f"SKU-{i + 1:05d}", f"{categoria} item {i + 1:03d}", categoria, str(rng.choice(opcoes)),
                                round(preco * float(rng.uniform(0.55, 0.75)), 2), preco, int(rng.choice(FATORES_CAIXA))))
    posicoes = rng.permutation(N_SKUS) + 1
    demanda = 190 / posicoes ** 0.95                 # poucos itens concentram o volume
    return produtos, demanda


def sazonalidade(dia: date) -> float:
    mes = {1: 0.9, 2: 0.95, 3: 1.0, 4: 1.0, 5: 1.05, 6: 1.0, 7: 0.95, 8: 1.0, 9: 1.05, 10: 1.1, 11: 1.7, 12: 0.85}[dia.month]
    return mes * (0.15 if dia.weekday() >= 5 else 1.0)


class Simulacao:
    def __init__(self) -> None:
        self.produtos, demanda_total = criar_catalogo()
        self.lamb = demanda_total[:, None] * PESO_CD[None, :] * rng.uniform(0.7, 1.3, (N_SKUS, 3))
        self.lead = np.array([next(f[3] for f in FORNECEDORES if f[0] == p.fornecedor) for p in self.produtos])
        self.fatores = np.array([p.fator for p in self.produtos])
        lento = self.lamb.sum(axis=1) < np.quantile(self.lamb.sum(axis=1), 0.5)
        self.rop = np.ceil(self.lamb * (self.lead[:, None] + 4))
        self.lote = np.ceil(self.lamb * 30)
        self.lote[lento, 2] *= 4                    # Recife compra lotes grandes demais de itens lentos
        estoque = np.ceil(self.lamb * rng.uniform(20, 45, (N_SKUS, 3)))
        estoque[lento, 2] *= 4
        self.real = estoque.astype(np.int64)
        self.sistema = self.real.copy()
        self.saldo_inicial = self.real.copy()
        self.encomendado = np.zeros((N_SKUS, 3), dtype=np.int64)
        self.chegadas: dict[date, list] = {}
        self.transito: dict[date, list] = {}
        self.ledger: list[tuple] = []
        self.pedidos: list[Pedido] = []
        self.perdidos: list[tuple] = []
        self.contagens: list[tuple] = []
        self.versoes: dict[str, list[Produto]] = {}
        self.proximo_id = 1_000_000
        self.proximo_pedido = 5000
        self.proxima_transferencia = 700
        self.descontinuados = set(rng.choice(np.where(lento)[0], 12, replace=False).tolist())
        self.quebra_de_caixa = rng.choice(N_SKUS, 15, replace=False).tolist()
        self.mudanca_fornecedor = rng.choice(N_SKUS, 6, replace=False).tolist()

    def registrar(self, dia: date, i: int, c: int, tipo: str, impacto: int, ref: str = "") -> int:
        self.proximo_id += 1
        momento = datetime(dia.year, dia.month, dia.day, int(rng.integers(7, 19)), int(rng.integers(0, 60)), int(rng.integers(0, 60)))
        self.ledger.append((self.proximo_id, i, c, tipo, impacto, momento, ref))
        return self.proximo_id

    def eventos_de_catalogo(self, dia: date) -> None:
        momento = datetime(dia.year, dia.month, dia.day, 10, 0)
        if dia == date(2025, 4, 10):                # nova embalagem: o fator de caixa muda no meio do ano
            for i in self.quebra_de_caixa:
                novo = [f for f in FATORES_CAIXA if f != self.produtos[i].fator][int(rng.integers(0, 3))]
                self.produtos[i].fator, self.produtos[i].atualizado_em = novo, momento
                self.fatores[i] = novo
        if dia == date(2025, 5, 12):                # categoria renomeada
            for p in self.produtos:
                if p.categoria == "EPI":
                    p.categoria, p.atualizado_em = "Segurança", momento
        if dia == date(2025, 6, 16):
            for i in self.descontinuados:
                self.produtos[i].ativo, self.produtos[i].atualizado_em = False, momento
                self.lamb[i] = 0
        if dia == date(2025, MES_REAJUSTE, 7):
            for p in self.produtos:
                if p.fornecedor == FORNECEDOR_REAJUSTE:
                    p.custo, p.atualizado_em = round(p.custo * 1.08, 2), momento
        if dia == date(2025, 9, 8):                 # troca de fornecedor em alguns itens
            for i in self.mudanca_fornecedor:
                p = self.produtos[i]
                opcoes = [f[0] for f in FORNECEDORES if f[2] in (p.categoria, "EPI" if p.categoria == "Segurança" else p.categoria) and f[0] != p.fornecedor]
                if opcoes:
                    p.fornecedor, p.atualizado_em = str(rng.choice(opcoes)), momento

    def receber(self, dia: date) -> None:
        for pedido, item, quantidade, ultimo in self.chegadas.pop(dia, []):
            i, c = item["i"], item["c"]
            self.real[i, c] += quantidade
            self.sistema[i, c] += quantidade
            if ultimo:
                self.encomendado[i, c] -= item["pedido_un"]
            self.registrar(dia, i, c, "ENTRADA_COMPRA", quantidade, pedido.pedido_id)
            item["recebimentos"].append({"data": dia, "quantidade_un": quantidade, "fator": int(self.fatores[i])})
        for transferencia, i, origem, destino, quantidade in self.transito.pop(dia, []):
            self.real[i, destino] += quantidade
            self.sistema[i, destino] += quantidade
            self.registrar(dia, i, destino, "TRANSF_ENTRADA", quantidade, transferencia)

    def vender(self, dia: date) -> None:
        demanda = rng.poisson(self.lamb * sazonalidade(dia))
        vendido = np.minimum(demanda, self.real)
        self.real -= vendido
        self.sistema -= vendido
        for i, c in zip(*np.nonzero(vendido)):
            self.registrar(dia, int(i), int(c), "VENDA", -int(vendido[i, c]))
            sorteio = rng.random()
            if sorteio < 0.012:                     # devolução de parte da venda
                quantidade = max(1, int(vendido[i, c] * 0.3))
                self.real[i, c] += quantidade
                self.sistema[i, c] += quantidade
                self.registrar(dia, int(i), int(c), "DEVOLUCAO", quantidade)
            elif sorteio < 0.015 and dia < date(2025, 12, 20):     # lançamento errado e o estorno, dias depois
                original = self.registrar(dia, int(i), int(c), "VENDA", -int(vendido[i, c]))
                self.registrar(dia + timedelta(days=int(rng.integers(1, 4))), int(i), int(c), "ESTORNO", int(vendido[i, c]), str(original))
        for i, c in zip(*np.nonzero(demanda - vendido)):
            self.perdidos.append((dia, int(i), int(c), int(demanda[i, c] - vendido[i, c])))

    def perder(self, dia: date) -> None:
        if dia.weekday() != 2:
            return
        ferramentas = np.array([p.categoria == "Ferramentas" for p in self.produtos])
        taxa = np.full((N_SKUS, 3), 0.0002)
        taxa[ferramentas, 2] = 0.006                 # furto silencioso em Recife
        sumiu = rng.binomial(self.real, taxa)
        self.real -= sumiu                           # só o estoque real cai: o sistema não sabe
        avaria = rng.binomial(self.real, 0.0004)
        self.real -= avaria
        self.sistema -= avaria
        for i, c in zip(*np.nonzero(avaria)):
            self.registrar(dia, int(i), int(c), "PERDA", -int(avaria[i, c]))

    def contar(self, dia: date) -> None:
        if dia.weekday() != 0:
            return
        escolhidos = rng.random((N_SKUS, 3)) < 0.05
        for i, c in zip(*np.nonzero(escolhidos)):
            sistema, contado = int(self.sistema[i, c]), int(self.real[i, c])
            self.contagens.append((dia, int(i), int(c), sistema, contado))
            if sistema != contado:
                self.sistema[i, c] = contado
                self.registrar(dia, int(i), int(c), "AJUSTE_INVENTARIO", contado - sistema, f"CONT-{dia:%Y%m%d}")

    def transferir(self, dia: date) -> None:
        if dia.weekday() != 1:
            return
        cobertura = self.real / np.maximum(self.lamb, 0.01)
        for i in np.where((cobertura[:, 0] < 5) & (cobertura[:, 2] > 60) & (self.lamb[:, 0] > 0))[0]:
            quantidade = int(min(self.real[i, 2] * 0.3, self.lamb[i, 0] * 15))
            if quantidade <= 0:
                continue
            self.real[i, 2] -= quantidade
            self.sistema[i, 2] -= quantidade
            self.proxima_transferencia += 1
            codigo = f"TR-{self.proxima_transferencia}"
            self.registrar(dia, int(i), 2, "TRANSF_SAIDA", -quantidade, codigo)
            self.transito.setdefault(dia + timedelta(days=int(rng.integers(2, 5))), []).append((codigo, int(i), 2, 0, quantidade))

    def repor(self, dia: date) -> None:
        if dia.weekday() >= 5:
            return
        precisa = (self.sistema + self.encomendado <= self.rop) & (self.lamb > 0)
        grupos: dict[tuple, list] = {}
        for i, c in zip(*np.nonzero(precisa)):
            grupos.setdefault((self.produtos[i].fornecedor, int(c)), []).append(int(i))
        for (fornecedor, c), itens in grupos.items():
            prazo = next(f[3] for f in FORNECEDORES if f[0] == fornecedor)
            self.proximo_pedido += 1
            pedido = Pedido(f"PC-{self.proximo_pedido}", fornecedor, CDS[c], dia, dia + timedelta(days=prazo))
            self.pedidos.append(pedido)
            atraso_base = rng.normal(0.5, 1.5)
            if fornecedor == FORNECEDOR_ATRASADO and dia.month >= MES_ATRASO:
                atraso_base = rng.normal(prazo * 1.4, 3)
            for i in itens:
                caixas = int(np.ceil(self.lote[i, c] / self.fatores[i]))
                quantidade = caixas * int(self.fatores[i])
                item = {"i": i, "c": c, "pedido_un": quantidade, "caixas": caixas, "recebimentos": [], "custo": self.produtos[i].custo}
                pedido.itens.append(item)
                self.encomendado[i, c] += quantidade
                chegada = dia + timedelta(days=max(1, prazo + int(round(atraso_base))))
                if caixas >= 4 and rng.random() < 0.08:          # recebimento parcial
                    primeira = int(caixas * 0.7) * int(self.fatores[i])
                    self._agendar(chegada, pedido, item, primeira, False)
                    self._agendar(chegada + timedelta(days=int(rng.integers(3, 8))), pedido, item, quantidade - primeira, True)
                else:
                    self._agendar(chegada, pedido, item, quantidade, True)

    def _agendar(self, dia: date, pedido: Pedido, item: dict, quantidade: int, ultimo: bool) -> None:
        self.chegadas.setdefault(dia, []).append((pedido, item, quantidade, ultimo))

    def rodar(self) -> None:
        for n in range(DIAS):
            dia = INICIO + timedelta(days=n)
            self.eventos_de_catalogo(dia)
            self.receber(dia)
            self.vender(dia)
            self.perder(dia)
            self.contar(dia)
            self.transferir(dia)
            self.repor(dia)
            if (dia + timedelta(days=1)).day == 1:
                self.versoes[f"{dia:%Y-%m}"] = [Produto(**vars(p)) for p in self.produtos]


# ---- exportação: a sujeira entra aqui ----

def sku_sujo(sku: str) -> str:
    numero = sku[4:]
    sorteio = rng.random()
    if sorteio < 0.05:
        return f" sku{numero} "
    if sorteio < 0.10:
        return f"SKU{int(numero)}"
    if sorteio < 0.14:
        return sku.lower()
    return sku


APELIDOS_CD = {"GRU": ["GRU", "CD-GRU", "Guarulhos", "gru "], "CWB": ["CWB", "CD-CWB", "Curitiba"], "REC": ["REC", "CD-REC", "Recife", "rec"]}
TIPOS_ANTIGOS = {"VENDA": "SAIDA_VENDA", "DEVOLUCAO": "DEV_CLIENTE"}


def exportar_movimentos(sim: Simulacao) -> dict:
    df = pd.DataFrame(sim.ledger, columns=["movimento_id", "i", "c", "tipo", "impacto", "momento", "referencia"])
    df["sku"] = [sim.produtos[i].sku for i in df["i"]]
    df["cd"] = [CDS[c] for c in df["c"]]
    df["mes_evento"] = df["momento"].dt.strftime("%Y-%m")

    # fator de caixa vigente na data, para gravar a entrada em caixas como o WMS faz
    fator_inicial = {}
    primeiro_catalogo = sim.versoes["2025-01"]
    for i, produto in enumerate(primeiro_catalogo):
        fator_inicial[i] = produto.fator
    troca = datetime(2025, 4, 10, 10, 0)
    fator_final = {i: sim.versoes["2025-12"][i].fator for i in range(N_SKUS)}
    fator = np.where(df["momento"] < troca, df["i"].map(fator_inicial), df["i"].map(fator_final))
    em_caixa = (df["tipo"] == "ENTRADA_COMPRA").to_numpy()
    assert (df.loc[em_caixa, "impacto"].to_numpy() % fator[em_caixa] == 0).mean() > 0.97

    quantidade = df["impacto"].abs().astype(float).to_numpy()
    unidade = np.where(em_caixa & (df["impacto"].to_numpy() % fator == 0), "CX", "UN")
    quantidade = np.where(unidade == "CX", quantidade / fator, quantidade)
    sinalizado = (df["momento"] >= datetime(2025, 7, 1)) & (df["impacto"] < 0)   # desde julho o WMS grava saídas como negativas
    df["quantidade"] = np.where(sinalizado, -quantidade, quantidade)
    ajuste = df["tipo"] == "AJUSTE_INVENTARIO"
    df.loc[ajuste, "quantidade"] = df.loc[ajuste, "impacto"]                      # ajuste sempre tem sinal
    df["unidade"] = unidade
    df["tipo_exportado"] = df["tipo"]
    antes_de_julho = df["momento"] < datetime(2025, 7, 1)
    df.loc[antes_de_julho, "tipo_exportado"] = df.loc[antes_de_julho, "tipo"].replace(TIPOS_ANTIGOS)

    # 1% dos eventos do fim do mês só chega no arquivo seguinte
    meses = sorted(df["mes_evento"].unique())
    proximo = dict(zip(meses, meses[1:] + [meses[-1]]))
    df["mes_carga"] = df["mes_evento"]
    tardio = (df["momento"].dt.day >= 28) & (rng.random(len(df)) < 0.04)
    df.loc[tardio, "mes_carga"] = df.loc[tardio, "mes_evento"].map(proximo)

    base = df[["movimento_id", "sku", "cd", "tipo_exportado", "quantidade", "unidade", "momento", "referencia", "mes_carga"]].rename(columns={"tipo_exportado": "tipo"})

    def seguinte(linhas: pd.DataFrame) -> pd.DataFrame:
        return linhas.assign(mes_carga=linhas["mes_carga"].map(proximo))

    candidatas = base[base["mes_carga"] != meses[-1]]
    reenviadas = seguinte(candidatas.sample(frac=0.004, random_state=1))          # reprocesso: a mesma linha volta
    corrigidas = candidatas[candidatas["tipo"].isin(["VENDA", "SAIDA_VENDA"])].sample(frac=0.002, random_state=2)
    erradas = corrigidas.assign(quantidade=(corrigidas["quantidade"] * 2 + np.sign(corrigidas["quantidade"])))
    base = base.drop(corrigidas.index)                                            # a primeira versão sai errada...
    base = pd.concat([base, erradas, seguinte(corrigidas), reenviadas], ignore_index=True)    # ...e a correta chega no mês seguinte

    fantasmas = base.sample(int(len(df) * 0.0005), random_state=3).assign(sku=lambda d: [f"SKU-9{n:04d}" for n in rng.integers(0, 9999, len(d))])
    invalidas = base.sample(int(len(df) * 0.0002), random_state=4).assign(quantidade="N/D")
    extras = pd.concat([fantasmas, invalidas], ignore_index=True)
    extras["movimento_id"] = np.arange(9_000_000, 9_000_000 + len(extras))
    base = pd.concat([base.astype({"quantidade": object}), extras], ignore_index=True)

    base["sku"] = base["sku"].map(sku_sujo)
    base["cd"] = base["cd"].map(lambda c: str(rng.choice(APELIDOS_CD[c])))
    base["quantidade"] = base["quantidade"].map(lambda q: q if isinstance(q, str) else (f"{q:.0f}"))
    pasta = RAW / "wms"
    pasta.mkdir(parents=True, exist_ok=True)
    for mes, grupo in base.groupby("mes_carga"):
        saida = grupo.drop(columns="mes_carga").sort_values("momento")
        saida["momento"] = saida["momento"].dt.strftime("%Y-%m-%d %H:%M:%S")
        with gzip.GzipFile(pasta / f"movimentos_{mes}.csv.gz", "wb", mtime=0) as arquivo:
            arquivo.write(saida.to_csv(index=False).encode("utf-8"))
    return {"linhas_exportadas": len(base), "reenviadas": len(reenviadas), "corrigidas": len(corrigidas), "sku_inexistente": len(fantasmas),
            "quantidade_invalida": len(invalidas), "tardias": int(tardio.sum())}


def exportar_catalogo(sim: Simulacao) -> None:
    pasta = RAW / "erp"
    pasta.mkdir(parents=True, exist_ok=True)
    for mes, versao in sim.versoes.items():
        df = pd.DataFrame([vars(p) for p in versao]).rename(columns={"fator": "unidades_por_caixa", "fornecedor": "fornecedor_id"})
        df["atualizado_em"] = df["atualizado_em"].map(lambda d: d.strftime("%Y-%m-%d %H:%M:%S"))
        repetidas = df.sample(frac=0.01, random_state=int(mes[-2:]))
        df = pd.concat([df, repetidas.assign(sku=repetidas["sku"].str.lower())], ignore_index=True)
        df["categoria"] = df["categoria"].map(lambda c: c.upper() if rng.random() < 0.03 else c)
        df["custo"] = df["custo"].map(lambda v: f"{v:.2f}".replace(".", ","))
        df["preco"] = df["preco"].map(lambda v: f"{v:.2f}".replace(".", ","))
        df.to_csv(pasta / f"produtos_{mes}.csv", sep=";", index=False)
    pd.DataFrame([{"fornecedor_id": f[0], "nome": f[1], "categoria_principal": f[2], "prazo_contratual_dias": f[3]} for f in FORNECEDORES]).to_csv(
        pasta / "fornecedores.csv", index=False)


def exportar_estoque_e_demanda(sim: Simulacao) -> None:
    pasta = RAW / "wms"
    linhas = [(sim.produtos[i].sku, CDS[c], int(sim.saldo_inicial[i, c])) for i in range(N_SKUS) for c in range(3)]
    pd.DataFrame(linhas, columns=["sku", "cd", "quantidade"]).assign(data="31/12/2024").to_csv(pasta / "saldo_inicial.csv", index=False)
    contagens = pd.DataFrame([(d.strftime("%d/%m/%Y"), sim.produtos[i].sku, CDS[c], s, r) for d, i, c, s, r in sim.contagens],
                             columns=["data", "sku", "cd", "quantidade_sistema", "quantidade_contada"])
    contagens.to_csv(pasta / "contagens.csv", index=False)
    (RAW / "vendas").mkdir(parents=True, exist_ok=True)
    perdidos = pd.DataFrame([(d.isoformat(), sim.produtos[i].sku, CDS[c], q) for d, i, c, q in sim.perdidos], columns=["data", "sku", "cd", "quantidade"])
    with gzip.GzipFile(RAW / "vendas" / "demanda_perdida.csv.gz", "wb", mtime=0) as arquivo:
        arquivo.write(perdidos.to_csv(index=False).encode("utf-8"))


def exportar_pedidos(sim: Simulacao) -> None:
    formatos = ["%Y-%m-%d", "%d/%m/%Y"]
    registros = []
    for pedido in sim.pedidos:
        formato = formatos[int(rng.random() < 0.3)]
        registros.append({
            "pedido_id": pedido.pedido_id, "fornecedor_id": pedido.fornecedor, "cd": pedido.cd, "emitido_em": pedido.emitido.strftime(formato),
            "previsto_para": pedido.previsto.strftime(formato),
            "itens": [{"sku": sim.produtos[item["i"]].sku, "caixas": item["caixas"], "unidades_pedidas": item["pedido_un"], "custo_unitario": item["custo"],
                       "recebimentos": [{"data": r["data"].strftime(formato), "unidades": r["quantidade_un"]} for r in item["recebimentos"]]}
                      for item in pedido.itens],
        })
    (RAW / "compras").mkdir(parents=True, exist_ok=True)
    (RAW / "compras" / "pedidos_compra.json").write_text(json.dumps(registros, ensure_ascii=False), encoding="utf-8")


def gabarito(sim: Simulacao, sujeira: dict) -> dict:
    ledger = pd.DataFrame(sim.ledger, columns=["id", "i", "c", "tipo", "impacto", "momento", "ref"])
    ledger["mes"] = ledger["momento"].dt.strftime("%Y-%m")
    saldo_inicial = int(sim.saldo_inicial.sum())
    por_mes = ledger.groupby("mes")["impacto"].sum().cumsum() + saldo_inicial
    custo_final = np.array([p.custo for p in sim.produtos])
    em_transito = sum(q for lista in sim.transito.values() for _, _, _, _, q in lista)
    return {
        "movimentos_validos": len(ledger), "saldo_inicial_unidades": saldo_inicial, "saldo_total_fim_do_mes": {k: int(v) for k, v in por_mes.items()},
        "saldo_final_por_cd": {CDS[c]: int(sim.sistema[:, c].sum()) for c in range(3)}, "valor_estoque_final": round(float((sim.sistema.sum(axis=1) * custo_final).sum()), 2),
        "unidades_em_transito_no_fim": int(em_transito), "unidades_demanda_perdida": int(sum(p[3] for p in sim.perdidos)),
        "unidades_vendidas": int(-ledger.loc[ledger["tipo"] == "VENDA", "impacto"].sum()),
        "pedidos_de_compra": len(sim.pedidos), "contagens": len(sim.contagens), "fornecedor_atrasado": FORNECEDOR_ATRASADO,
        "skus_descontinuados": len(sim.descontinuados), "sujeira": sujeira,
    }


def main() -> None:
    sim = Simulacao()
    sim.rodar()
    sujeira = exportar_movimentos(sim)
    exportar_catalogo(sim)
    exportar_estoque_e_demanda(sim)
    exportar_pedidos(sim)
    EXTERNOS.mkdir(parents=True, exist_ok=True)
    resultado = gabarito(sim, sujeira)
    (EXTERNOS / "gabarito.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in resultado.items() if k != "saldo_total_fim_do_mes"}, ensure_ascii=False))
    print(list(resultado["saldo_total_fim_do_mes"].values()))


if __name__ == "__main__":
    main()
