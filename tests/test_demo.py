import pytest

from pergunte_comex import cli
from pergunte_comex.demo import GeradorDemo, PerguntaForaDoCatalogo, carregar_catalogo
from pergunte_comex.responder import responder


@pytest.mark.parametrize("digitado, id_esperado", [
    ("Qual é o atraso médio em dias por modal?", "atraso-medio-por-modal"),
    ("atraso medio por modal", "atraso-medio-por-modal"),
    ("quantos processos foram cancelados", "cancelados"),
    ("top 3 clientes por valor CIF", "top3-clientes-cif"),
    ("processos em cada canal de parametrização", "processos-por-canal"),
    ("quantos processos estão em trânsito?", "em-transito"),
    ("5", "atraso-medio-por-modal"),
])
def test_reconhece_perguntas_proximas_e_numero_do_menu(digitado, id_esperado):
    assert GeradorDemo().reconhecer(digitado)["id"] == id_esperado


def test_toda_pergunta_do_catalogo_reconhece_a_si_mesma():
    gerador = GeradorDemo()
    for item in carregar_catalogo():
        assert gerador.reconhecer(item["pergunta"])["id"] == item["id"]


@pytest.mark.parametrize("digitado", ["qual a previsão do tempo amanhã?", "oi", "99"])
def test_recusa_pergunta_fora_do_catalogo(digitado):
    with pytest.raises(PerguntaForaDoCatalogo):
        GeradorDemo().gerar_sql(digitado)


def test_demo_responde_de_ponta_a_ponta(banco):
    resposta = responder("atraso medio por modal", GeradorDemo(), banco)
    assert resposta.colunas == ["modal", "atraso_medio_dias"]
    assert {linha[0] for linha in resposta.linhas} == {"Marítimo", "Aéreo", "Rodoviário"}


@pytest.fixture()
def cli_com_banco(banco, monkeypatch):
    monkeypatch.setattr(cli, "BANCO", banco)
    monkeypatch.setattr("pergunte_comex.responder.BANCO", banco)
    monkeypatch.setattr(cli.responder, "__defaults__", (banco,))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_cli_demo_funciona_sem_chave(cli_com_banco, capsys, tmp_path):
    codigo = cli.main(["--demo", "atraso medio por modal", "--grafico", str(tmp_path / "g.png")])
    saida = capsys.readouterr().out
    assert codigo == 0
    assert "Modo demonstração (sem IA)" in saida and "Marítimo" in saida
    assert (tmp_path / "g.png").exists()


def test_cli_sem_chave_aponta_para_o_modo_demo(cli_com_banco, capsys):
    assert cli.main(["Qual modal mais atrasa?"]) == 1
    assert "--demo" in capsys.readouterr().err


def test_cli_menu_interativo(cli_com_banco, capsys, monkeypatch):
    entradas = iter(["3", "pergunta sem sentido algum", "sair"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    assert cli.main(["--demo", "--sem-grafico"]) == 0
    capturado = capsys.readouterr()
    assert "Quantos processos foram cancelados?" in capturado.out
    assert "não reconheceu" in capturado.err


def test_cli_lista_exemplos(capsys):
    assert cli.main(["--exemplos"]) == 0
    assert len(capsys.readouterr().out.strip().splitlines()) == len(carregar_catalogo())
