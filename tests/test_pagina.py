import json
import re

from pergunte_comex import pagina
from pergunte_comex.demo import carregar_catalogo


def _dados_embutidos(html):
    achado = re.search(r"const DADOS = (\[.*?\]);\nconst VAZIAS", html, re.S)
    return json.loads(achado.group(1).replace("<\\/", "</"))


def test_pagina_embute_todas_as_perguntas_com_resultado(banco, tmp_path):
    destino = pagina.gerar(tmp_path / "site" / "index.html", banco)
    html = destino.read_text(encoding="utf-8")
    assert pagina.MARCADOR not in html
    dados = _dados_embutidos(html)
    assert [d["id"] for d in dados] == [p["id"] for p in carregar_catalogo()]
    for item in dados:
        assert item["linhas"], item["id"]
        assert len(item["colunas"]) == len(item["tipos"]) == len(item["linhas"][0])


def test_tipos_das_colunas(banco):
    dados = {d["id"]: d for d in pagina.montar_dados(banco)}
    assert dados["atraso-medio-por-modal"]["tipos"] == ["texto", "numero"]
    meses = dados["processos-abertos-por-mes-2026"]
    assert meses["tipos"] == ["data", "numero"]
    assert meses["linhas"][0][0] == "2026-01-01"


def test_pagina_avisa_que_nao_usa_ia_e_nao_depende_de_rede(banco, tmp_path):
    html = pagina.gerar(tmp_path / "index.html", banco).read_text(encoding="utf-8")
    assert "demonstração sem IA" in html
    externos = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
    assert externos == ["https://github.com/sbarbosa25/pergunte-ao-comex"]
