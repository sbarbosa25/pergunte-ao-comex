import pytest

from pergunte_comex.responder import consultar
from pergunte_comex.sql_seguro import SQLRecusado, validar


@pytest.mark.parametrize("texto, esperado", [
    ("SELECT 1", "SELECT 1"),
    ("```sql\nSELECT 1;\n```", "SELECT 1"),
    ("with a as (select 1) select * from a -- comentário", "with a as (select 1) select * from a"),
    ("select 'drop; update' as texto", "select 'drop; update' as texto"),
    ("select replace(cliente, 'a', 'b') from processos",
     "select replace(cliente, 'a', 'b') from processos"),
])
def test_aceita_consultas(texto, esperado):
    assert validar(texto) == esperado


@pytest.mark.parametrize("texto", [
    "",
    "DROP TABLE processos",
    "select * from processos; drop table processos",
    "UPDATE processos SET status = 'x'",
    "with a as (select 1) delete from processos",
    "COPY processos TO 'saida.csv'",
    "select * from read_csv('/etc/passwd')",
    "ATTACH 'outro.duckdb'",
    "A resposta é 42.",
])
def test_recusa_o_que_nao_e_consulta(texto):
    with pytest.raises(SQLRecusado):
        validar(texto)


def test_consulta_nao_le_arquivo_do_disco(banco, tmp_path):
    segredo = tmp_path / "segredo.csv"
    segredo.write_text("a\n1\n", encoding="utf-8")
    with pytest.raises(Exception, match="(?i)does not exist|disabled|permission"):
        consultar(f"select * from '{segredo}'", banco)


def test_conexao_e_somente_leitura(banco):
    colunas, linhas = consultar("select count(*) as n from processos", banco)
    assert (colunas, linhas) == (["n"], [(1000,)])
