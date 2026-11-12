import duckdb
import pytest

from pergunte_comex import etl
from pergunte_comex.esquema import COLUNAS


@pytest.fixture()
def con(banco):
    with duckdb.connect(str(banco), read_only=True) as conexao:
        yield conexao


def test_carga_preserva_as_1000_linhas(con):
    assert con.execute("SELECT count(*) FROM processos").fetchone()[0] == 1000


def test_colunas_batem_com_o_dicionario_de_dados(con):
    descricao = con.execute("DESCRIBE processos").fetchall()
    assert [(c[0], c[1]) for c in descricao] == [(n, t) for n, (t, _) in COLUNAS.items()]


def test_texto_sujo_foi_padronizado(con):
    modais = {r[0] for r in con.execute("SELECT DISTINCT modal FROM processos").fetchall()}
    assert modais == {"Marítimo", "Aéreo", "Rodoviário"}
    canais = {r[0] for r in con.execute("SELECT DISTINCT canal FROM processos").fetchall()}
    assert canais == {"Verde", "Amarelo", "Vermelho", "Cinza", None}
    clientes = con.execute("SELECT count(DISTINCT cliente) FROM processos").fetchone()[0]
    assert clientes == 19


def test_colunas_derivadas(con):
    erradas = con.execute("""
        SELECT count(*) FROM processos
        WHERE abs(valor_cif_usd - (valor_fob_usd + frete_usd + seguro_usd)) > 0.01
           OR dias_atraso IS DISTINCT FROM
              CAST(data_chegada_real - data_chegada_prevista AS INTEGER)
           OR atrasado IS DISTINCT FROM (dias_atraso > 0)
           OR pais_parceiro = 'Brasil'
    """).fetchone()[0]
    assert erradas == 0


def test_todas_as_validacoes_passam(con):
    assert [d for d, problemas in etl.validar(con) if problemas] == []


def test_validacao_barra_csv_com_id_repetido(csv_bruto, tmp_path):
    linhas = csv_bruto.read_text(encoding="utf-8").splitlines()
    ruim = tmp_path / "ruim.csv"
    ruim.write_text("\n".join(linhas + [linhas[1]]) + "\n", encoding="utf-8")
    with pytest.raises(etl.ErroDeValidacao, match="id_processo é único"):
        etl.executar(ruim, tmp_path / "ruim.duckdb")
