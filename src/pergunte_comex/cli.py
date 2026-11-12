"""Linha de comando: pergunte-comex "Qual modal mais atrasa?" """

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

from pergunte_comex import RAIZ
from pergunte_comex.ia import GeradorClaude, IAIndisponivel
from pergunte_comex.responder import BancoAusente, responder
from pergunte_comex.saida import grafico, tabela
from pergunte_comex.sql_seguro import SQLRecusado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pergunte-comex",
        description="Faça uma pergunta em português sobre a operação de comex.")
    parser.add_argument("pergunta", help="A pergunta, entre aspas")
    parser.add_argument("--grafico", type=Path, default=RAIZ / "saida" / "resposta.png",
                        help="Onde salvar o gráfico (padrão: saida/resposta.png)")
    parser.add_argument("--sem-grafico", action="store_true", help="Não gerar gráfico")
    parser.add_argument("--modelo", help="Modelo da Anthropic a usar")
    args = parser.parse_args(argv)

    try:
        resposta = responder(args.pergunta, GeradorClaude(modelo=args.modelo))
    except (IAIndisponivel, BancoAusente, SQLRecusado) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    except duckdb.Error as erro:
        print(f"Erro: o SQL gerado pela IA não rodou no banco. {erro}", file=sys.stderr)
        return 1

    print(f"SQL gerado:\n{resposta.sql}\n")
    print(tabela(resposta))
    if not args.sem_grafico:
        caminho = grafico(resposta, args.grafico)
        if caminho:
            print(f"\nGráfico salvo em {caminho}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
