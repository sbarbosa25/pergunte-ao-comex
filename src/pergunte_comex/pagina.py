"""Gera a página de demonstração: um HTML único, sem servidor e sem IA.

Roda o SQL de gabarito de cada pergunta do catálogo no DuckDB e embute os
resultados no HTML. A página publicada no GitHub Pages é este arquivo.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from pergunte_comex import BANCO, RAIZ, etl
from pergunte_comex.demo import carregar_catalogo
from pergunte_comex.responder import consultar

MODELO = Path(__file__).with_name("modelos") / "pagina.html"
DESTINO = RAIZ / "site" / "index.html"
MARCADOR = "/*DADOS*/"


def _tipo(valores: list[object]) -> str:
    presentes = [v for v in valores if v is not None]
    if presentes and all(isinstance(v, (date, datetime)) for v in presentes):
        return "data"
    if presentes and all(
        isinstance(v, (int, float, Decimal)) and not isinstance(v, bool) for v in presentes
    ):
        return "numero"
    return "texto"


def _serializar(valor: object) -> object:
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    return valor


def montar_dados(banco: Path = BANCO) -> list[dict]:
    dados = []
    for item in carregar_catalogo():
        colunas, linhas = consultar(item["sql_gabarito"], banco)
        tipos = [_tipo([linha[i] for linha in linhas]) for i in range(len(colunas))]
        dados.append({
            "id": item["id"],
            "pergunta": item["pergunta"],
            "sql": item["sql_gabarito"],
            "colunas": colunas,
            "tipos": tipos,
            "linhas": [[_serializar(v) for v in linha] for linha in linhas],
        })
    return dados


def gerar(destino: Path = DESTINO, banco: Path = BANCO) -> Path:
    modelo = MODELO.read_text(encoding="utf-8")
    if MARCADOR not in modelo:
        raise ValueError(f"O modelo {MODELO.name} não tem o marcador {MARCADOR}")
    # "</" escapado para o JSON não conseguir fechar a tag <script> da página
    conteudo = json.dumps(montar_dados(banco), ensure_ascii=False).replace("</", "<\\/")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(modelo.replace(MARCADOR, conteudo), encoding="utf-8")
    return destino


def main() -> None:
    if not BANCO.exists():
        etl.executar()
    print(f"Página gerada: {gerar()}")


if __name__ == "__main__":
    main()
