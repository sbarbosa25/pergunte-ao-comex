from datetime import date

from avaliacao import avaliar
from pergunte_comex.responder import Resposta, responder
from pergunte_comex.saida import grafico, tabela


class GeradorFixo:
    """Faz o papel da IA nos testes: devolve sempre o SQL combinado."""

    def __init__(self, sql):
        self.sql = sql

    def gerar_sql(self, pergunta):
        return self.sql(pergunta) if callable(self.sql) else self.sql


def test_responder_valida_e_executa(banco):
    gerador = GeradorFixo("```sql\nSELECT modal, count(*) AS processos FROM processos "
                          "GROUP BY modal ORDER BY processos DESC;\n```")
    resposta = responder("Quantos processos por modal?", gerador, banco)
    assert resposta.colunas == ["modal", "processos"]
    assert resposta.linhas[0][0] == "Marítimo"
    assert sum(linha[1] for linha in resposta.linhas) == 1000


def test_tabela_e_grafico(tmp_path):
    resposta = Resposta("Valor por modal", "select", ["modal", "valor"],
                        [("Marítimo", 1234567.5), ("Aéreo", 890.0)])
    texto = tabela(resposta)
    assert "1.234.567,50" in texto and "Marítimo" in texto
    assert grafico(resposta, tmp_path / "g.png").stat().st_size > 0

    serie = Resposta("Por mês", "select", ["mes", "n"],
                     [(date(2026, 1, 1), 3), (date(2026, 2, 1), 5)])
    assert grafico(serie, tmp_path / "s.png").exists()

    numero_unico = Resposta("Total", "select", ["n"], [(1000,)])
    assert grafico(numero_unico, tmp_path / "n.png") is None


def test_comparacao_ignora_ordem_nomes_e_arredondamento():
    esperado = [("Marítimo", 2.42), ("Aéreo", -0.02)]
    assert avaliar.mesmo_resultado([(-0.0200001, "Aéreo"), (2.419999, "Marítimo")], esperado)
    assert not avaliar.mesmo_resultado([("Marítimo", 2.42)], esperado)
    assert not avaliar.mesmo_resultado([("Marítimo", 9.99), ("Aéreo", -0.02)], esperado)


def test_gabaritos_rodam_e_retornam_dados(banco):
    assert avaliar.conferir_gabarito(banco) == []
    assert len(avaliar.carregar_perguntas()) >= 15


def test_avaliacao_da_100_para_quem_responde_o_gabarito(banco):
    gabarito = {p["pergunta"]: p["sql_gabarito"] for p in avaliar.carregar_perguntas()}
    resultados = avaliar.avaliar(GeradorFixo(lambda pergunta: gabarito[pergunta]), banco)
    assert avaliar.taxa_de_acerto(resultados) == 1.0


def test_avaliacao_conta_erro_e_sql_invalido_como_resposta_errada(banco):
    resultados = avaliar.avaliar(GeradorFixo("SELECT 1"), banco)
    assert avaliar.taxa_de_acerto(resultados) == 0.0
    quebrado = avaliar.avaliar(GeradorFixo("DROP TABLE processos"), banco)
    assert all("SQLRecusado" in r.detalhe for r in quebrado)
    assert "errou" in avaliar.relatorio(quebrado, "modelo-teste")
