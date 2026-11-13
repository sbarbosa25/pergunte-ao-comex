"""Trava de segurança para o SQL escrito pela IA.

A IA só pode consultar. Três barreiras garantem isso: esta validação, que
aceita apenas um SELECT (ou WITH ... SELECT); a conexão com o banco, aberta em
modo somente leitura; e o acesso externo do DuckDB desligado na hora da
consulta, para que nenhum SQL consiga ler arquivos do disco. Uma quarta
barreira, em responder.py, limita o custo da consulta (linhas, tempo e memória).
"""

from __future__ import annotations

import re

PROIBIDAS = (
    "insert", "update", "delete", "drop", "alter", "create", "truncate",
    "attach", "detach", "copy", "export", "import", "install", "load", "pragma",
    "call", "set", "reset", "checkpoint", "vacuum",
)
FUNCOES_DE_ARQUIVO = re.compile(
    r"\b(read_\w+|glob|parquet_\w+|sniff_csv|getenv|query|query_table)\s*\(", re.I)
_CERCA = re.compile(r"^```(?:sql)?\s*(.*?)\s*```$", re.S | re.I)
_COMENTARIO = re.compile(r"--[^\n]*|/\*.*?\*/", re.S)
_LITERAL = re.compile(r"'(?:[^']|'')*'")


class SQLRecusado(ValueError):
    pass


def limpar(texto: str) -> str:
    """Remove cerca de código markdown, comentários e ponto e vírgula final."""
    sql = texto.strip()
    cerca = _CERCA.match(sql)
    if cerca:
        sql = cerca.group(1)
    sql = _COMENTARIO.sub(" ", sql).strip()
    return sql.rstrip(";").strip()


def validar(texto: str) -> str:
    """Devolve o SQL limpo ou levanta SQLRecusado explicando o motivo."""
    sql = limpar(texto)
    if not sql:
        raise SQLRecusado("A IA não devolveu nenhum SQL.")

    sem_literais = _LITERAL.sub("''", sql)
    if ";" in sem_literais:
        raise SQLRecusado("Só é permitido um comando por consulta.")
    if not re.match(r"(?i)^(select|with)\b", sem_literais):
        raise SQLRecusado("Só são permitidas consultas SELECT.")
    for palavra in PROIBIDAS:
        if re.search(rf"(?i)\b{palavra}\b", sem_literais):
            raise SQLRecusado(f"Comando não permitido em consulta: {palavra.upper()}.")
    if FUNCOES_DE_ARQUIVO.search(sem_literais):
        raise SQLRecusado("A consulta não pode ler arquivos nem variáveis do sistema.")
    return sql
