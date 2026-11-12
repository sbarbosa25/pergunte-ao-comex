"""Apresentação do resultado: tabela no terminal e gráfico em PNG."""

from __future__ import annotations

from datetime import date
from numbers import Number
from pathlib import Path

from pergunte_comex.responder import Resposta

MAX_LINHAS_TABELA = 30
MAX_BARRAS = 20


def _formatar(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "sim" if valor else "não"
    if isinstance(valor, float):
        inteiro, _, decimal = f"{valor:,.2f}".partition(".")
        return f"{inteiro.replace(',', '.')},{decimal}"
    if isinstance(valor, int):
        return f"{valor:,}".replace(",", ".")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return str(valor)


def _numerico(valor: object) -> bool:
    return isinstance(valor, Number) and not isinstance(valor, bool)


def tabela(resposta: Resposta) -> str:
    if not resposta.linhas:
        return "A consulta não retornou nenhuma linha."
    linhas = [[_formatar(v) for v in linha] for linha in resposta.linhas[:MAX_LINHAS_TABELA]]
    larguras = [max(len(c), *(len(linha[i]) for linha in linhas))
                for i, c in enumerate(resposta.colunas)]
    a_direita = [all(_numerico(linha[i]) or linha[i] is None for linha in resposta.linhas)
                 for i in range(len(resposta.colunas))]

    def montar(celulas: list[str]) -> str:
        return "  ".join(c.rjust(larg) if direita else c.ljust(larg)
                         for c, larg, direita in zip(celulas, larguras, a_direita, strict=True))

    partes = [montar(resposta.colunas), "  ".join("-" * larg for larg in larguras)]
    partes += [montar(linha) for linha in linhas]
    if len(resposta.linhas) > MAX_LINHAS_TABELA:
        partes.append(f"... e mais {len(resposta.linhas) - MAX_LINHAS_TABELA} linhas")
    return "\n".join(partes)


def grafico(resposta: Resposta, destino: Path) -> Path | None:
    """Desenha o resultado quando ele tem uma categoria (ou data) e uma medida.

    Devolve o caminho do PNG, ou None quando o resultado não cabe em um gráfico
    simples (um número só, várias medidas, texto livre).
    """
    if len(resposta.colunas) != 2 or not 2 <= len(resposta.linhas) <= 200:
        return None
    rotulos = [linha[0] for linha in resposta.linhas]
    valores = [linha[1] for linha in resposta.linhas]
    if not all(_numerico(v) for v in valores) or any(r is None for r in rotulos):
        return None

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    serie_temporal = all(isinstance(r, date) for r in rotulos)
    fig, eixo = plt.subplots(figsize=(9, 5))
    if serie_temporal:
        pares = sorted(zip(rotulos, valores, strict=True))
        eixo.plot([p[0] for p in pares], [p[1] for p in pares], color="#1f6f8b", linewidth=2)
        fig.autofmt_xdate()
    else:
        rotulos, valores = rotulos[:MAX_BARRAS], valores[:MAX_BARRAS]
        eixo.barh([str(r) for r in rotulos][::-1], valores[::-1], color="#1f6f8b")
    eixo.set_title(resposta.pergunta, fontsize=12, loc="left")
    eixo.set_xlabel(resposta.colunas[0] if serie_temporal else resposta.colunas[1])
    eixo.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino, dpi=150)
    plt.close(fig)
    return destino
