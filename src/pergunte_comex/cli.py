"""Linha de comando.

  pergunte-comex "Qual modal mais atrasa?"     pergunta livre, respondida pela IA
  pergunte-comex --demo "atraso por modal"     sem IA e sem chave, usa o catálogo
  pergunte-comex --demo                        menu interativo do modo demonstração
  pergunte-comex --exemplos                    lista as perguntas do catálogo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

from pergunte_comex import BANCO, RAIZ, etl
from pergunte_comex.demo import GeradorDemo, PerguntaForaDoCatalogo, carregar_catalogo
from pergunte_comex.ia import GeradorClaude, GeradorSQL, IAIndisponivel
from pergunte_comex.responder import LimiteExcedido, responder
from pergunte_comex.saida import grafico, tabela
from pergunte_comex.sql_seguro import SQLRecusado


def _preparar_banco() -> None:
    if not BANCO.exists():
        print("Primeira execução: carregando a base de exemplo no DuckDB.")
        etl.executar()
        print()


def _listar_exemplos() -> None:
    for numero, item in enumerate(carregar_catalogo(), start=1):
        print(f"{numero:>2}. {item['pergunta']}")


def _responder(pergunta: str, gerador: GeradorSQL, destino_grafico: Path | None) -> int:
    try:
        resposta = responder(pergunta, gerador)
    except (PerguntaForaDoCatalogo, SQLRecusado, LimiteExcedido) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    except duckdb.Error as erro:
        print(f"Erro: o SQL gerado não rodou no banco. {erro}", file=sys.stderr)
        return 1

    if isinstance(gerador, GeradorDemo):
        print(f"Modo demonstração (sem IA). Pergunta reconhecida: {gerador.reconhecida}\n")
        resposta.pergunta = gerador.reconhecida or pergunta
    print(f"SQL:\n{resposta.sql}\n")
    print(tabela(resposta))
    if destino_grafico:
        caminho = grafico(resposta, destino_grafico)
        if caminho:
            print(f"\nGráfico salvo em {caminho}")
    return 0


def _menu(gerador: GeradorDemo, destino_grafico: Path | None) -> int:
    print("Modo demonstração: digite o número de uma pergunta, escreva a sua ou 'sair'.\n")
    _listar_exemplos()
    while True:
        try:
            entrada = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if entrada.lower() in {"sair", "s", "q", "exit"}:
            return 0
        if entrada:
            print()
            _responder(entrada, gerador, destino_grafico)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pergunte-comex",
        description="Faça uma pergunta em português sobre a operação de comex.")
    parser.add_argument("pergunta", nargs="?", help="A pergunta, entre aspas")
    parser.add_argument("--demo", action="store_true",
                        help="Responde sem IA e sem chave, a partir do catálogo de perguntas")
    parser.add_argument("--exemplos", action="store_true",
                        help="Lista as perguntas do catálogo e sai")
    parser.add_argument("--grafico", type=Path, default=RAIZ / "saida" / "resposta.png",
                        help="Onde salvar o gráfico (padrão: saida/resposta.png)")
    parser.add_argument("--sem-grafico", action="store_true", help="Não gerar gráfico")
    parser.add_argument("--modelo", help="Modelo da Anthropic a usar")
    args = parser.parse_args(argv)
    destino_grafico = None if args.sem_grafico else args.grafico

    if args.exemplos:
        _listar_exemplos()
        return 0
    if not args.pergunta and not args.demo:
        parser.error("informe a pergunta, ou use --demo para o menu de demonstração")

    try:
        _preparar_banco()
    except etl.ErroDeValidacao as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    if args.demo:
        gerador = GeradorDemo()
        if args.pergunta:
            return _responder(args.pergunta, gerador, destino_grafico)
        return _menu(gerador, destino_grafico)

    try:
        gerador_ia = GeradorClaude(modelo=args.modelo)
    except IAIndisponivel as erro:
        print(f"Erro: {erro}\nPara testar sem chave, use o modo demonstração: "
              "pergunte-comex --demo", file=sys.stderr)
        return 1
    return _responder(args.pergunta, gerador_ia, destino_grafico)


if __name__ == "__main__":
    sys.exit(main())
