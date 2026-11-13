"""Junta as peças: pergunta, SQL gerado pela IA, trava de segurança e consulta."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

import duckdb

from pergunte_comex import BANCO
from pergunte_comex.ia import GeradorSQL
from pergunte_comex.sql_seguro import validar

# Quarta barreira: custo. Um SELECT válido ainda pode sair caro (um produto
# cartesiano, por exemplo), então a consulta tem teto de linhas, tempo, memória
# e disco. O teto de disco importa: quando a memória acaba, o DuckDB passa a
# gravar em arquivos temporários, e sem limite uma ordenação grande enche o disco.
MAX_LINHAS = 10_000
TEMPO_MAXIMO_S = 10.0
MEMORIA_MAXIMA = "512MB"
DISCO_TEMPORARIO_MAXIMO = "1GB"


@dataclass
class Resposta:
    pergunta: str
    sql: str
    colunas: list[str]
    linhas: list[tuple]


class BancoAusente(FileNotFoundError):
    pass


class LimiteExcedido(RuntimeError):
    """A consulta passou do teto de linhas, de tempo ou de memória."""


def consultar(
    sql: str,
    banco: Path = BANCO,
    *,
    max_linhas: int = MAX_LINHAS,
    tempo_maximo_s: float = TEMPO_MAXIMO_S,
) -> tuple[list[str], list[tuple]]:
    """Valida o SQL e executa em conexão somente leitura, com teto de custo."""
    sql = validar(sql)
    if not banco.exists():
        raise BancoAusente(
            f"Banco {banco} não encontrado. Rode antes: python -m pergunte_comex.etl")
    with duckdb.connect(str(banco), read_only=True) as con:
        con.execute(f"SET memory_limit = '{MEMORIA_MAXIMA}'")
        con.execute(f"SET max_temp_directory_size = '{DISCO_TEMPORARIO_MAXIMO}'")
        # terceira barreira: a consulta não enxerga arquivos nem rede, só o banco
        con.execute("SET enable_external_access = false")

        # O temporizador cobre a execução e a leitura do resultado.
        temporizador = threading.Timer(tempo_maximo_s, con.interrupt)
        temporizador.daemon = True
        temporizador.start()
        try:
            cursor = con.execute(sql)
            colunas = [c[0] for c in cursor.description]
            # Lê uma linha além do teto só para saber se o resultado passou dele.
            linhas = cursor.fetchmany(max_linhas + 1)
        except duckdb.InterruptException as erro:
            raise LimiteExcedido(
                f"A consulta foi interrompida por passar de {tempo_maximo_s:g} segundos."
            ) from erro
        except duckdb.OutOfMemoryException as erro:
            raise LimiteExcedido(
                f"A consulta foi interrompida por passar do teto de memória "
                f"({MEMORIA_MAXIMA}) e de disco temporário ({DISCO_TEMPORARIO_MAXIMO})."
            ) from erro
        finally:
            temporizador.cancel()

    if len(linhas) > max_linhas:
        raise LimiteExcedido(
            f"A consulta retornaria mais de {max_linhas} linhas. "
            "Refine a pergunta com um filtro, um agrupamento ou um limite.")
    return colunas, linhas


def responder(pergunta: str, gerador: GeradorSQL, banco: Path = BANCO) -> Resposta:
    sql = validar(gerador.gerar_sql(pergunta))
    colunas, linhas = consultar(sql, banco)
    return Resposta(pergunta=pergunta, sql=sql, colunas=colunas, linhas=linhas)
