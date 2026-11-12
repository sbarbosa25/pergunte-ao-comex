import pytest

from pergunte_comex import etl, gerar_base


@pytest.fixture(scope="session")
def csv_bruto(tmp_path_factory):
    return gerar_base.gerar(tmp_path_factory.mktemp("dados") / "processos.csv")


@pytest.fixture(scope="session")
def banco(csv_bruto, tmp_path_factory):
    caminho = tmp_path_factory.mktemp("banco") / "comex.duckdb"
    etl.executar(csv_bruto, caminho)
    return caminho
