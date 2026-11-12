"""Junta as peças: pergunta, SQL gerado pela IA, trava de segurança e consulta."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb

from pergunte_comex import BANCO
from pergunte_comex.ia import GeradorSQL
from pergunte_comex.sql_seguro import validar


@dataclass
class Resposta:
    pergunta: str
    sql: str
    colunas: list[str]
    linhas: list[tuple]


class BancoAusente(FileNotFoundError):
    pass


def consultar(sql: str, banco: Path = BANCO) -> tuple[list[str], list[tuple]]:
    """Valida o SQL e executa em conexão somente leitura."""
    sql = validar(sql)
    if not banco.exists():
        raise BancoAusente(
            f"Banco {banco} não encontrado. Rode antes: python -m pergunte_comex.etl")
    with duckdb.connect(str(banco), read_only=True) as con:
        # terceira barreira: a consulta não enxerga arquivos nem rede, só o banco
        con.execute("SET enable_external_access = false")
        cursor = con.execute(sql)
        colunas = [c[0] for c in cursor.description]
        return colunas, cursor.fetchall()


def responder(pergunta: str, gerador: GeradorSQL, banco: Path = BANCO) -> Resposta:
    sql = validar(gerador.gerar_sql(pergunta))
    colunas, linhas = consultar(sql, banco)
    return Resposta(pergunta=pergunta, sql=sql, colunas=colunas, linhas=linhas)
