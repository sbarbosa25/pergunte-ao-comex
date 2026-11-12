"""Modo demonstração: responde sem IA e sem chave de API.

Em vez de pedir o SQL a um modelo, procura no catálogo de perguntas da
avaliação a mais parecida com a que foi digitada e usa o SQL de gabarito dela.
Serve para qualquer pessoa experimentar o projeto de ponta a ponta. Não é IA:
só entende perguntas próximas das que estão no catálogo.
"""

from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from pergunte_comex import RAIZ

CATALOGO = RAIZ / "avaliacao" / "perguntas.json"
SEMELHANCA_MINIMA = 0.45

_VAZIAS = {
    "a", "as", "o", "os", "de", "da", "das", "do", "dos", "e", "em", "na", "nas", "no", "nos",
    "que", "qual", "quais", "com", "por", "para", "um", "uma", "foi", "foram", "sao", "tem",
    "teve", "temos", "cada", "sem", "neste", "nesta", "esta", "estao", "leva", "existem",
}


class PerguntaForaDoCatalogo(LookupError):
    pass


def carregar_catalogo(caminho: Path = CATALOGO) -> list[dict]:
    return json.loads(caminho.read_text(encoding="utf-8"))


def _palavras(texto: str) -> list[str]:
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return [p for p in re.findall(r"[a-z0-9]+", sem_acento) if p not in _VAZIAS]


def semelhanca(pergunta: str, referencia: str) -> float:
    """Nota de 0 a 1: metade pelas palavras em comum, metade pela ordem do texto."""
    a, b = _palavras(pergunta), _palavras(referencia)
    if not a or not b:
        return 0.0
    conjunto_a, conjunto_b = set(a), set(b)
    em_comum = len(conjunto_a & conjunto_b) / len(conjunto_a | conjunto_b)
    ordem = SequenceMatcher(None, " ".join(a), " ".join(b)).ratio()
    return (em_comum + ordem) / 2


class GeradorDemo:
    """Segue o mesmo contrato de `GeradorSQL`, mas consulta o catálogo em vez da IA."""

    modelo = "demonstração (sem IA)"

    def __init__(self, catalogo: list[dict] | None = None) -> None:
        self.catalogo = catalogo if catalogo is not None else carregar_catalogo()
        self.reconhecida: str | None = None

    def reconhecer(self, pergunta: str) -> dict:
        texto = pergunta.strip()
        if texto.isdigit() and 1 <= int(texto) <= len(self.catalogo):
            return self.catalogo[int(texto) - 1]
        melhor = max(self.catalogo, key=lambda item: semelhanca(texto, item["pergunta"]))
        if semelhanca(texto, melhor["pergunta"]) < SEMELHANCA_MINIMA:
            raise PerguntaForaDoCatalogo(
                "O modo demonstração não reconheceu essa pergunta. Ele só responde "
                "perguntas próximas das que estão no catálogo (veja com --exemplos). "
                "Para perguntas livres, configure ANTHROPIC_API_KEY e rode sem --demo.")
        return melhor

    def gerar_sql(self, pergunta: str) -> str:
        item = self.reconhecer(pergunta)
        self.reconhecida = item["pergunta"]
        return item["sql_gabarito"]
