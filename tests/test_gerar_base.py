import csv

from pergunte_comex import CSV_BRUTO, gerar_base


def _ler(caminho):
    with caminho.open(encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def test_base_tem_1000_processos_com_ids_unicos(csv_bruto):
    linhas = _ler(csv_bruto)
    assert len(linhas) == 1000
    assert len({linha["id_processo"] for linha in linhas}) == 1000


def test_geracao_e_reproduzivel(csv_bruto, tmp_path):
    outra = gerar_base.gerar(tmp_path / "outra.csv")
    assert outra.read_bytes() == csv_bruto.read_bytes()


def test_csv_versionado_e_o_que_o_gerador_produz(csv_bruto):
    assert CSV_BRUTO.read_bytes() == csv_bruto.read_bytes(), (
        "dados/processos_comex.csv está diferente do gerador. "
        "Rode: python -m pergunte_comex.gerar_base")


def test_cliente_so_opera_no_seu_tipo_e_com_seus_produtos(csv_bruto):
    for linha in _ler(csv_bruto):
        tipo, ncms = _cliente(linha["cliente"])
        assert linha["tipo_operacao"] == tipo
        assert linha["ncm"] in ncms


def _cliente(texto):
    chave = texto.strip().lower()
    return next(v for k, v in gerar_base.CLIENTES.items() if k.lower() == chave)
