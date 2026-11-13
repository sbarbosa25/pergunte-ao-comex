"""Quarta barreira: um SELECT válido não pode custar o que quiser."""

import time

import pytest

from avaliacao import avaliar
from pergunte_comex import cli, responder
from pergunte_comex.responder import LimiteExcedido, consultar
from pergunte_comex.sql_seguro import validar

CARTESIANO_LINHAS = "SELECT a.id_processo, b.id_processo FROM processos a, processos b"
CARTESIANO_TEMPO = "SELECT count(*) FROM processos a, processos b, processos c, processos d"


def test_produto_cartesiano_passa_pela_validacao_de_sql():
    # É exatamente por isso que a barreira de custo existe.
    assert validar(CARTESIANO_LINHAS) == CARTESIANO_LINHAS
    assert validar(CARTESIANO_TEMPO) == CARTESIANO_TEMPO


def test_resultado_grande_demais_e_recusado_sem_ler_tudo(banco):
    inicio = time.monotonic()
    with pytest.raises(LimiteExcedido, match="mais de 10000 linhas"):
        consultar(CARTESIANO_LINHAS, banco)  # 1.000.000 de linhas
    assert time.monotonic() - inicio < 5


def test_consulta_demorada_e_interrompida_pelo_temporizador(banco):
    inicio = time.monotonic()
    with pytest.raises(LimiteExcedido, match="segundos"):
        consultar(CARTESIANO_TEMPO, banco, tempo_maximo_s=0.5)  # 10^12 combinações
    assert time.monotonic() - inicio < 5


def test_banco_continua_utilizavel_depois_de_uma_interrupcao(banco):
    with pytest.raises(LimiteExcedido):
        consultar(CARTESIANO_TEMPO, banco, tempo_maximo_s=0.3)
    assert consultar("SELECT count(*) FROM processos", banco)[1] == [(1000,)]


def test_resultado_no_limite_exato_e_aceito(banco):
    colunas, linhas = consultar("SELECT id_processo FROM processos", banco, max_linhas=1000)
    assert len(linhas) == 1000
    with pytest.raises(LimiteExcedido):
        consultar("SELECT id_processo FROM processos", banco, max_linhas=999)


def test_teto_de_memoria_esta_aplicado_na_conexao(banco):
    _, linhas = consultar(
        "SELECT current_setting('memory_limit'), current_setting('max_temp_directory_size')",
        banco)
    memoria, disco = linhas[0]
    assert memoria.endswith("MiB") and float(memoria.split()[0]) < 600
    assert disco.endswith("MiB") and float(disco.split()[0]) < 1100


def test_ordenacao_gigante_para_no_teto_de_memoria_e_disco(banco, monkeypatch):
    # Sem teto de disco, esta consulta grava dezenas de GB em arquivos temporários.
    monkeypatch.setattr(responder, "MEMORIA_MAXIMA", "64MB")
    monkeypatch.setattr(responder, "DISCO_TEMPORARIO_MAXIMO", "64MB")
    sql = ("SELECT a.id_processo, b.id_processo, c.cliente "
           "FROM processos a, processos b, processos c ORDER BY random()")
    inicio = time.monotonic()
    with pytest.raises(LimiteExcedido, match="memória"):
        consultar(sql, banco, tempo_maximo_s=30)
    assert time.monotonic() - inicio < 15
    temporarios = banco.with_name(banco.name + ".tmp")
    assert not temporarios.exists() or not any(temporarios.iterdir())


def test_avaliacao_conta_consulta_cara_como_resposta_errada(banco):
    class GeradorCaro:
        def gerar_sql(self, pergunta):
            return CARTESIANO_LINHAS

    resultados = avaliar.avaliar(GeradorCaro(), banco)
    assert avaliar.taxa_de_acerto(resultados) == 0.0
    assert all("LimiteExcedido" in r.detalhe for r in resultados)


def test_cli_explica_o_limite_em_vez_de_travar(banco, monkeypatch, capsys):
    monkeypatch.setattr(cli, "BANCO", banco)
    monkeypatch.setattr(cli.responder, "__defaults__", (banco,))

    class GeradorCaro:
        def gerar_sql(self, pergunta):
            return CARTESIANO_LINHAS

    assert cli._responder("liste tudo cruzado com tudo", GeradorCaro(), None) == 1
    assert "mais de 10000 linhas" in capsys.readouterr().err
