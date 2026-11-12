"""Gera a base de exemplo: 1000 processos de uma operação fictícia de comex.

Os dados são sintéticos. Clientes, transportadores e valores foram inventados
e não representam nenhuma empresa real. A semente é fixa, então rodar o script
de novo produz exatamente o mesmo arquivo.

O CSV sai "sujo" de propósito, do jeito que uma exportação de sistema costuma
chegar: separador ponto e vírgula, decimal com vírgula, datas em dd/mm/aaaa e
alguns campos de texto com caixa e espaços inconsistentes. Quem arruma é o ETL.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from pergunte_comex import CSV_BRUTO

SEMENTE = 42
TOTAL = 1000
INICIO = date(2025, 1, 2)
FIM = date(2026, 9, 30)
DATA_DE_CORTE = date(2026, 10, 31)

PORTOS_BR = {
    "Marítimo": ["Santos", "Paranaguá", "Rio de Janeiro", "Itajaí", "Suape", "Rio Grande"],
    "Aéreo": ["Guarulhos", "Viracopos", "Galeão"],
    "Rodoviário": ["Uruguaiana", "Foz do Iguaçu"],
}

# país: (peso de sorteio, portos marítimos, aeroportos, fronteira rodoviária)
PAISES = {
    "China": (26, ["Xangai", "Ningbo", "Shenzhen"], ["Xangai Pudong"], None),
    "Estados Unidos": (16, ["Houston", "Miami", "Nova York"], ["Miami"], None),
    "Alemanha": (9, ["Hamburgo", "Bremerhaven"], ["Frankfurt"], None),
    "Argentina": (9, ["Buenos Aires"], ["Ezeiza"], "Paso de los Libres"),
    "Índia": (7, ["Nhava Sheva", "Mundra"], ["Mumbai"], None),
    "Itália": (6, ["Gênova", "La Spezia"], ["Milão Malpensa"], None),
    "México": (5, ["Veracruz", "Altamira"], ["Cidade do México"], None),
    "Holanda": (5, ["Roterdã"], ["Amsterdã Schiphol"], None),
    "Coreia do Sul": (5, ["Busan"], ["Seul Incheon"], None),
    "Japão": (4, ["Yokohama", "Kobe"], ["Tóquio Narita"], None),
    "Chile": (4, ["San Antonio", "Valparaíso"], ["Santiago"], None),
    "Paraguai": (4, [], ["Assunção"], "Ciudad del Este"),
}

# NCM (4 dígitos): (descrição, faixa de valor FOB por kg em USD)
PRODUTOS = {
    "8471": ("Máquinas de processamento de dados", (35.0, 120.0)),
    "8517": ("Aparelhos de telefonia e comunicação", (60.0, 220.0)),
    "8708": ("Partes e acessórios de veículos", (6.0, 25.0)),
    "3004": ("Medicamentos", (80.0, 400.0)),
    "3901": ("Polímeros de etileno", (1.1, 2.2)),
    "7210": ("Laminados planos de aço", (0.7, 1.5)),
    "8413": ("Bombas para líquidos", (12.0, 45.0)),
    "9018": ("Instrumentos médicos e cirúrgicos", (90.0, 350.0)),
    "0901": ("Café", (3.5, 7.0)),
    "1201": ("Soja", (0.4, 0.6)),
    "0202": ("Carne bovina congelada", (4.5, 7.5)),
    "4703": ("Celulose", (0.5, 0.9)),
    "6403": ("Calçados de couro", (18.0, 55.0)),
    "2204": ("Vinhos", (3.0, 14.0)),
}
REFRIGERADOS = {"0202", "3004"}

# cliente: (tipo de operação, NCMs com que trabalha)
CLIENTES = {
    "Alvorada Componentes": ("Importação", ["8471", "8517"]),
    "Cais Norte Importadora": ("Importação", ["8471", "8517", "2204"]),
    "Delta Farma Distribuição": ("Importação", ["3004", "9018"]),
    "Guará Autopeças": ("Importação", ["8708"]),
    "Ipê Tecnologia": ("Importação", ["8471", "8517"]),
    "Jangada Bebidas": ("Importação", ["2204"]),
    "Lumen Equipamentos Médicos": ("Importação", ["9018", "3004"]),
    "Mirante Plásticos": ("Importação", ["3901"]),
    "Quilha Offshore": ("Importação", ["8413", "7210"]),
    "Serra Azul Máquinas": ("Importação", ["8413", "8708"]),
    "Tucano Eletrônicos": ("Importação", ["8517", "8471"]),
    "Brisa Sul Alimentos": ("Exportação", ["0202"]),
    "Estrela do Vale Agro": ("Exportação", ["1201", "0901"]),
    "Ferro Leste Siderurgia": ("Exportação", ["7210"]),
    "Horizonte Autopeças": ("Exportação", ["8708", "8413"]),
    "Nativa Celulose": ("Exportação", ["4703"]),
    "Oeste Grãos": ("Exportação", ["1201"]),
    "Pampa Calçados": ("Exportação", ["6403"]),
    "Raiz Café Especial": ("Exportação", ["0901"]),
}

TRANSPORTADORES = {
    "Marítimo": ["Atlântica Lines", "Cruzeiro do Sul Shipping", "Maré Alta Navegação",
                 "Oceano Azul Carriers", "Vento Leste Marítima"],
    "Aéreo": ["Aerocarga Tropical", "Céu Aberto Cargo", "Rota Expressa Air"],
    "Rodoviário": ["Estrada Real Logística", "Fronteira Transportes"],
}

INCOTERMS = ["FOB", "CIF", "EXW", "FCA", "CFR", "DAP"]
PESO_INCOTERMS = [34, 22, 12, 14, 10, 8]
CANAIS = ["Verde", "Amarelo", "Vermelho", "Cinza"]
PESO_CANAIS = [80, 10, 8, 2]
TRANSITO = {"Marítimo": (22, 45), "Aéreo": (2, 6), "Rodoviário": (3, 9)}
DESEMBARACO = {"Verde": (1, 3), "Amarelo": (3, 7), "Vermelho": (7, 20), "Cinza": (15, 40)}

COLUNAS = [
    "id_processo", "tipo_operacao", "modal", "incoterm", "cliente", "transportador",
    "pais_origem", "local_origem", "pais_destino", "local_destino", "ncm",
    "descricao_produto", "tipo_container", "qtd_containers", "peso_kg",
    "valor_fob_usd", "frete_usd", "seguro_usd", "data_abertura", "data_embarque",
    "data_chegada_prevista", "data_chegada_real", "data_desembaraco", "canal", "status",
]


def _br_data(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


def _br_numero(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")


def _sujar(rng: random.Random, texto: str) -> str:
    """Reproduz inconsistências típicas de digitação em cerca de 6% dos campos."""
    sorteio = rng.random()
    if sorteio < 0.02:
        return texto.upper()
    if sorteio < 0.04:
        return texto.lower()
    if sorteio < 0.06:
        return f" {texto}  "
    return texto


def _escolher_modal(rng: random.Random, pais: str) -> str:
    _, portos, _, fronteira = PAISES[pais]
    opcoes, pesos = ["Aéreo"], [18]
    if portos:
        opcoes.append("Marítimo")
        pesos.append(70)
    if fronteira:
        opcoes.append("Rodoviário")
        pesos.append(45)
    return rng.choices(opcoes, weights=pesos)[0]


def _local_exterior(rng: random.Random, pais: str, modal: str) -> str:
    _, portos, aeroportos, fronteira = PAISES[pais]
    if modal == "Marítimo":
        return rng.choice(portos)
    if modal == "Aéreo":
        return rng.choice(aeroportos)
    return fronteira


def _gerar_processo(rng: random.Random, numero: int) -> dict[str, str]:
    cliente = rng.choice(list(CLIENTES))
    tipo, ncms_do_cliente = CLIENTES[cliente]
    pais = rng.choices(list(PAISES), weights=[p[0] for p in PAISES.values()])[0]
    modal = _escolher_modal(rng, pais)
    local_exterior = _local_exterior(rng, pais, modal)
    local_brasil = rng.choice(PORTOS_BR[modal])

    ncm = rng.choice(ncms_do_cliente)
    descricao, (preco_min, preco_max) = PRODUTOS[ncm]

    if modal == "Marítimo":
        if ncm in REFRIGERADOS:
            tipo_container = "40' Reefer"
        else:
            tipo_container = rng.choice(["20' Dry", "40' Dry", "40' HC"])
        qtd_containers = rng.choices([1, 2, 3, 4, 6, 8, 10], weights=[40, 22, 12, 10, 8, 5, 3])[0]
        peso = qtd_containers * rng.uniform(9000, 24000)
        frete = qtd_containers * rng.uniform(1400, 5200)
    elif modal == "Aéreo":
        tipo_container, qtd_containers = "", 0
        peso = rng.uniform(80, 3500)
        frete = peso * rng.uniform(2.8, 7.5)
    else:
        tipo_container, qtd_containers = "", 0
        peso = rng.uniform(4000, 27000)
        frete = rng.uniform(1800, 6500)

    if preco_max > 50 and modal != "Aéreo":
        peso *= 0.06  # carga de alto valor agregado ocupa volume, não peso
    valor_fob = peso * rng.uniform(preco_min, preco_max)
    seguro = valor_fob * rng.uniform(0.0015, 0.004)

    abertura = INICIO + timedelta(days=rng.randint(0, (FIM - INICIO).days))
    embarque = abertura + timedelta(days=rng.randint(3, 18))
    prevista = embarque + timedelta(days=rng.randint(*TRANSITO[modal]))

    # Atraso: maioria chega no prazo; marítimo atrasa mais que os outros modais.
    chance_atraso = {"Marítimo": 0.42, "Aéreo": 0.18, "Rodoviário": 0.27}[modal]
    if rng.random() < chance_atraso:
        desvio = rng.choices([rng.randint(1, 5), rng.randint(6, 14), rng.randint(15, 30)],
                             weights=[60, 30, 10])[0]
    else:
        desvio = rng.randint(-2, 0)
    chegada_real = prevista + timedelta(days=desvio)

    canal = rng.choices(CANAIS, weights=PESO_CANAIS)[0]
    desembaraco = chegada_real + timedelta(days=rng.randint(*DESEMBARACO[canal]))

    if rng.random() < 0.03:
        status = "Cancelado"
        embarque_out = prevista_out = chegada_out = desembaraco_out = None
        canal_out = ""
    elif chegada_real > DATA_DE_CORTE:
        status = "Em trânsito"
        embarque_out, prevista_out, chegada_out, desembaraco_out = embarque, prevista, None, None
        canal_out = ""
    elif desembaraco > DATA_DE_CORTE:
        status = "Aguardando desembaraço"
        embarque_out, prevista_out, chegada_out, desembaraco_out = (
            embarque, prevista, chegada_real, None)
        canal_out = canal
    else:
        status = "Concluído"
        embarque_out, prevista_out, chegada_out, desembaraco_out = (
            embarque, prevista, chegada_real, desembaraco)
        canal_out = canal

    importacao = tipo == "Importação"
    return {
        "id_processo": f"{'IMP' if importacao else 'EXP'}-{abertura.year}-{numero:05d}",
        "tipo_operacao": tipo,
        "modal": _sujar(rng, modal),
        "incoterm": rng.choices(INCOTERMS, weights=PESO_INCOTERMS)[0],
        "cliente": _sujar(rng, cliente),
        "transportador": rng.choice(TRANSPORTADORES[modal]),
        "pais_origem": pais if importacao else "Brasil",
        "local_origem": local_exterior if importacao else local_brasil,
        "pais_destino": "Brasil" if importacao else pais,
        "local_destino": local_brasil if importacao else local_exterior,
        "ncm": ncm,
        "descricao_produto": descricao,
        "tipo_container": tipo_container,
        "qtd_containers": str(qtd_containers),
        "peso_kg": _br_numero(peso),
        "valor_fob_usd": _br_numero(valor_fob),
        "frete_usd": _br_numero(frete),
        "seguro_usd": _br_numero(seguro),
        "data_abertura": _br_data(abertura),
        "data_embarque": _br_data(embarque_out),
        "data_chegada_prevista": _br_data(prevista_out),
        "data_chegada_real": _br_data(chegada_out),
        "data_desembaraco": _br_data(desembaraco_out),
        "canal": _sujar(rng, canal_out) if canal_out else "",
        "status": status,
    }


def gerar(destino: Path = CSV_BRUTO, total: int = TOTAL, semente: int = SEMENTE) -> Path:
    rng = random.Random(semente)
    linhas = [_gerar_processo(rng, numero) for numero in range(1, total + 1)]
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS, delimiter=";", lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)
    return destino


def main() -> None:
    caminho = gerar()
    print(f"Base gerada: {caminho} ({TOTAL} processos, semente {SEMENTE})")


if __name__ == "__main__":
    main()
