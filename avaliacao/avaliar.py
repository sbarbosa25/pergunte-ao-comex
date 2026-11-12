"""Avaliação automática: a IA acerta as perguntas?

Cada pergunta de `perguntas.json` tem um SQL de gabarito escrito à mão. A
avaliação pede o SQL para a IA, roda os dois no mesmo banco e compara os
resultados. O que conta é a resposta, não o texto do SQL: nomes de colunas,
ordem das colunas e ordem das linhas não importam.

Modos:
  python -m avaliacao.avaliar --gabarito   confere se todo gabarito roda e retorna
                                           dados (não usa IA, roda em qualquer commit)
  python -m avaliacao.avaliar --ia         avalia a IA (precisa de ANTHROPIC_API_KEY)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from pergunte_comex import BANCO, RAIZ
from pergunte_comex.ia import GeradorSQL
from pergunte_comex.responder import consultar

PERGUNTAS = Path(__file__).with_name("perguntas.json")
RELATORIO = RAIZ / "saida" / "avaliacao.md"
ACERTO_MINIMO = 0.8


@dataclass
class Resultado:
    id: str
    pergunta: str
    acertou: bool
    sql_ia: str
    detalhe: str = ""


def carregar_perguntas(caminho: Path = PERGUNTAS) -> list[dict]:
    return json.loads(caminho.read_text(encoding="utf-8"))


def _normalizar_valor(valor: object) -> str:
    if valor is None:
        return "∅"
    if isinstance(valor, bool):
        return str(valor)
    if isinstance(valor, (int, float, Decimal)):
        return f"{round(float(valor), 2):.2f}"
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor).strip()


def normalizar(linhas: list[tuple]) -> list[tuple[str, ...]]:
    """Deixa o resultado comparável: ignora ordem das linhas e das colunas."""
    return sorted(tuple(sorted(_normalizar_valor(v) for v in linha)) for linha in linhas)


def mesmo_resultado(obtido: list[tuple], esperado: list[tuple]) -> bool:
    return normalizar(obtido) == normalizar(esperado)


def conferir_gabarito(banco: Path = BANCO) -> list[str]:
    """Devolve a lista de problemas encontrados nos gabaritos (vazia se tudo certo)."""
    problemas = []
    ids = set()
    for item in carregar_perguntas():
        if item["id"] in ids:
            problemas.append(f"{item['id']}: id repetido")
        ids.add(item["id"])
        try:
            _, linhas = consultar(item["sql_gabarito"], banco)
        except Exception as erro:  # noqa: BLE001 - qualquer falha do gabarito é um problema
            problemas.append(f"{item['id']}: gabarito não roda ({erro})")
            continue
        if not linhas or all(v is None for v in linhas[0]):
            problemas.append(f"{item['id']}: gabarito não retorna dados")
    return problemas


def avaliar(gerador: GeradorSQL, banco: Path = BANCO) -> list[Resultado]:
    resultados = []
    for item in carregar_perguntas():
        _, esperado = consultar(item["sql_gabarito"], banco)
        sql_ia = ""
        try:
            sql_ia = gerador.gerar_sql(item["pergunta"])
            _, obtido = consultar(sql_ia, banco)
        except Exception as erro:  # noqa: BLE001 - erro da IA conta como resposta errada
            resultados.append(Resultado(item["id"], item["pergunta"], False, sql_ia,
                                        f"{type(erro).__name__}: {erro}"))
            continue
        acertou = mesmo_resultado(obtido, esperado)
        detalhe = "" if acertou else (
            f"esperado {len(esperado)} linha(s), obtido {len(obtido)}; "
            f"primeira esperada {esperado[0]}, primeira obtida {obtido[0] if obtido else None}")
        resultados.append(Resultado(item["id"], item["pergunta"], acertou, sql_ia, detalhe))
    return resultados


def taxa_de_acerto(resultados: list[Resultado]) -> float:
    return sum(r.acertou for r in resultados) / len(resultados) if resultados else 0.0


def relatorio(resultados: list[Resultado], modelo: str) -> str:
    acertos = sum(r.acertou for r in resultados)
    linhas = [
        "# Avaliação da IA",
        "",
        f"Modelo: `{modelo}`",
        "",
        f"Acertos: **{acertos} de {len(resultados)}** ({taxa_de_acerto(resultados):.0%})",
        "",
        "| Pergunta | Resultado |",
        "| --- | --- |",
    ]
    linhas += [f"| {r.pergunta} | {'acertou' if r.acertou else 'errou'} |" for r in resultados]
    erros = [r for r in resultados if not r.acertou]
    if erros:
        linhas += ["", "## Erros", ""]
        for r in erros:
            linhas += [f"### {r.id}", "", r.pergunta, "", "```sql", r.sql_ia.strip() or "(vazio)",
                       "```", "", r.detalhe, ""]
    return "\n".join(linhas) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument("--gabarito", action="store_true", help="Confere os gabaritos, sem IA")
    modo.add_argument("--ia", action="store_true", help="Avalia a IA")
    parser.add_argument("--minimo", type=float, default=ACERTO_MINIMO,
                        help=f"Taxa mínima de acerto para passar (padrão {ACERTO_MINIMO})")
    args = parser.parse_args(argv)

    if args.gabarito:
        problemas = conferir_gabarito()
        for problema in problemas:
            print(f"  [FALHOU] {problema}")
        total = len(carregar_perguntas())
        print(f"Gabaritos conferidos: {total - len(problemas)} de {total} em ordem")
        return 1 if problemas else 0

    from pergunte_comex.ia import GeradorClaude

    gerador = GeradorClaude()
    resultados = avaliar(gerador)
    texto = relatorio(resultados, gerador.modelo)
    RELATORIO.parent.mkdir(parents=True, exist_ok=True)
    RELATORIO.write_text(texto, encoding="utf-8")
    print(texto)
    taxa = taxa_de_acerto(resultados)
    if taxa < args.minimo:
        print(f"Reprovado: acerto de {taxa:.0%} abaixo do mínimo de {args.minimo:.0%}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
