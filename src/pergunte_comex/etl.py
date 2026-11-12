"""ETL: lê o CSV bruto, limpa, deriva colunas e grava a tabela `processos` no DuckDB.

Toda a transformação é SQL rodando dentro do DuckDB. Ao final, um conjunto de
validações confere a carga; se alguma falhar, o ETL termina com erro.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from pergunte_comex import BANCO, CSV_BRUTO
from pergunte_comex.esquema import COLUNAS, TABELA

# Texto: tira espaços das pontas e padroniza a caixa pelo valor canônico.
_MODAL = """CASE strip_accents(lower(trim(modal)))
    WHEN 'maritimo' THEN 'Marítimo' WHEN 'aereo' THEN 'Aéreo'
    WHEN 'rodoviario' THEN 'Rodoviário' END"""
_CANAL = """CASE lower(trim(canal))
    WHEN 'verde' THEN 'Verde' WHEN 'amarelo' THEN 'Amarelo'
    WHEN 'vermelho' THEN 'Vermelho' WHEN 'cinza' THEN 'Cinza' END"""


def _numero(coluna: str) -> str:
    return f"CAST(replace({coluna}, ',', '.') AS DOUBLE)"


def _data(coluna: str) -> str:
    return f"CAST(strptime(nullif(trim({coluna}), ''), '%d/%m/%Y') AS DATE)"


SQL_CARGA = f"""
CREATE OR REPLACE TABLE {TABELA} AS
WITH bruto AS (
    SELECT * FROM read_csv(?, delim=';', header=true, all_varchar=true)
),
canonico AS (
    -- o nome "certo" de cada cliente é a grafia mais frequente entre as variações
    SELECT lower(trim(cliente)) AS chave, mode(trim(cliente)) AS cliente
    FROM bruto GROUP BY 1
),
limpo AS (
    SELECT
        trim(id_processo) AS id_processo,
        trim(tipo_operacao) AS tipo_operacao,
        {_MODAL} AS modal,
        trim(incoterm) AS incoterm,
        c.cliente AS cliente,
        trim(transportador) AS transportador,
        trim(pais_origem) AS pais_origem,
        trim(local_origem) AS local_origem,
        trim(pais_destino) AS pais_destino,
        trim(local_destino) AS local_destino,
        trim(ncm) AS ncm,
        trim(descricao_produto) AS descricao_produto,
        nullif(trim(tipo_container), '') AS tipo_container,
        CAST(qtd_containers AS INTEGER) AS qtd_containers,
        {_numero('peso_kg')} AS peso_kg,
        {_numero('valor_fob_usd')} AS valor_fob_usd,
        {_numero('frete_usd')} AS frete_usd,
        {_numero('seguro_usd')} AS seguro_usd,
        {_data('data_abertura')} AS data_abertura,
        {_data('data_embarque')} AS data_embarque,
        {_data('data_chegada_prevista')} AS data_chegada_prevista,
        {_data('data_chegada_real')} AS data_chegada_real,
        {_data('data_desembaraco')} AS data_desembaraco,
        {_CANAL} AS canal,
        trim(status) AS status
    FROM bruto b
    JOIN canonico c ON c.chave = lower(trim(b.cliente))
)
SELECT
    id_processo, tipo_operacao, modal, incoterm, cliente, transportador,
    pais_origem, local_origem, pais_destino, local_destino,
    CASE WHEN tipo_operacao = 'Importação' THEN pais_origem ELSE pais_destino END
        AS pais_parceiro,
    ncm, descricao_produto, tipo_container, qtd_containers, peso_kg,
    valor_fob_usd, frete_usd, seguro_usd,
    round(valor_fob_usd + frete_usd + seguro_usd, 2) AS valor_cif_usd,
    data_abertura, data_embarque, data_chegada_prevista, data_chegada_real,
    data_desembaraco, canal, status,
    CAST(data_chegada_real - data_embarque AS INTEGER) AS dias_transito,
    CAST(data_chegada_real - data_chegada_prevista AS INTEGER) AS dias_atraso,
    (data_chegada_real - data_chegada_prevista) > 0 AS atrasado,
    CAST(data_desembaraco - data_chegada_real AS INTEGER) AS dias_desembaraco
FROM limpo
ORDER BY data_abertura, id_processo
"""

# (descrição, SQL que devolve a quantidade de linhas com problema; o esperado é 0)
VALIDACOES = [
    ("id_processo é único",
     f"SELECT count(*) - count(DISTINCT id_processo) FROM {TABELA}"),
    ("modal foi reconhecido em todas as linhas",
     f"SELECT count(*) FROM {TABELA} WHERE modal IS NULL"),
    ("tipo_operacao só tem Importação e Exportação",
     f"SELECT count(*) FROM {TABELA} WHERE tipo_operacao NOT IN ('Importação', 'Exportação')"),
    ("valores e peso são positivos",
     f"SELECT count(*) FROM {TABELA} WHERE peso_kg <= 0 OR valor_fob_usd <= 0 OR frete_usd <= 0"),
    ("datas seguem a ordem abertura, embarque, chegada, desembaraço",
     f"""SELECT count(*) FROM {TABELA} WHERE data_embarque < data_abertura
         OR data_chegada_real < data_embarque OR data_desembaraco < data_chegada_real"""),
    ("processo concluído tem desembaraço e canal",
     f"""SELECT count(*) FROM {TABELA} WHERE status = 'Concluído'
         AND (data_desembaraco IS NULL OR canal IS NULL)"""),
    ("carga que chegou tem canal reconhecido",
     f"SELECT count(*) FROM {TABELA} WHERE data_chegada_real IS NOT NULL AND canal IS NULL"),
    ("o Brasil está em uma das pontas de todo processo",
     f"SELECT count(*) FROM {TABELA} WHERE 'Brasil' NOT IN (pais_origem, pais_destino)"),
]


class ErroDeValidacao(Exception):
    pass


def validar(con: duckdb.DuckDBPyConnection) -> list[tuple[str, int]]:
    """Roda as validações e devolve (descrição, linhas com problema)."""
    return [(descricao, con.execute(sql).fetchone()[0]) for descricao, sql in VALIDACOES]


def executar(csv_bruto: Path = CSV_BRUTO, banco: Path = BANCO) -> int:
    """Carrega o CSV no DuckDB e devolve a quantidade de linhas gravadas."""
    banco.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(banco)) as con:
        linhas_brutas = con.execute(
            "SELECT count(*) FROM read_csv(?, delim=';', header=true, all_varchar=true)",
            [str(csv_bruto)],
        ).fetchone()[0]
        con.execute(SQL_CARGA, [str(csv_bruto)])
        for nome, (_, descricao) in COLUNAS.items():
            texto = descricao.replace("'", "''")
            con.execute(f"COMMENT ON COLUMN {TABELA}.{nome} IS '{texto}'")

        total = con.execute(f"SELECT count(*) FROM {TABELA}").fetchone()[0]
        resultados = validar(con)

    falhas = [(d, n) for d, n in resultados if n]
    if total != linhas_brutas:
        diferenca = abs(total - linhas_brutas)
        falhas.append((f"carga preserva as {linhas_brutas} linhas do CSV", diferenca))
    for descricao, problemas in resultados:
        print(f"  [{'ok' if not problemas else 'FALHOU'}] {descricao}")
    if falhas:
        detalhe = "; ".join(f"{d} ({n} linhas)" for d, n in falhas)
        raise ErroDeValidacao(f"Validação da carga falhou: {detalhe}")
    return total


def main() -> None:
    print(f"Carregando {CSV_BRUTO.name} em {BANCO.name}")
    total = executar()
    print(f"Tabela `{TABELA}` gravada com {total} linhas")


if __name__ == "__main__":
    main()
