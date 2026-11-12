"""Transforma uma pergunta em português em SQL para o DuckDB.

`GeradorSQL` é o contrato. `GeradorClaude` é a implementação que chama a API da
Anthropic. Os testes e a avaliação usam geradores falsos que seguem o mesmo
contrato, então nada além deste arquivo precisa conhecer o provedor de IA.
"""

from __future__ import annotations

import os
from typing import Protocol

from pergunte_comex.esquema import TABELA, descricao_para_ia

MODELO_PADRAO = "claude-sonnet-5-5"

INSTRUCOES = f"""Você é um analista de dados de comércio exterior. Sua tarefa é traduzir \
a pergunta do usuário em uma única consulta SQL para o DuckDB.

{descricao_para_ia()}

Regras:
- Responda apenas com o SQL, sem explicação e sem bloco de código markdown.
- Use somente SELECT (ou WITH ... SELECT) sobre a tabela `{TABELA}`.
- Use os valores de texto exatamente como aparecem na descrição das colunas, \
com acentos e inicial maiúscula.
- Processos com status 'Cancelado' não entram em contagens, somas e médias, a \
menos que a pergunta fale em cancelamentos.
- Métricas de atraso e de prazo só consideram processos em que a coluna usada \
não é nula.
- Dê nomes claros em português para as colunas calculadas.
- Arredonde valores monetários e médias para 2 casas decimais.
- Em rankings, ordene do maior para o menor e use LIMIT quando a pergunta \
pedir uma quantidade."""


class GeradorSQL(Protocol):
    def gerar_sql(self, pergunta: str) -> str: ...


class IAIndisponivel(RuntimeError):
    pass


class GeradorClaude:
    def __init__(self, modelo: str | None = None, chave: str | None = None) -> None:
        self.modelo = modelo or os.environ.get("PERGUNTE_COMEX_MODELO", MODELO_PADRAO)
        chave = chave or os.environ.get("ANTHROPIC_API_KEY")
        if not chave:
            raise IAIndisponivel(
                "Defina a variável de ambiente ANTHROPIC_API_KEY para usar a IA.")
        import anthropic  # importado aqui para os testes rodarem sem o pacote configurado

        self._cliente = anthropic.Anthropic(api_key=chave)

    def gerar_sql(self, pergunta: str) -> str:
        resposta = self._cliente.messages.create(
            model=self.modelo,
            max_tokens=1024,
            system=INSTRUCOES,
            messages=[{"role": "user", "content": pergunta}],
        )
        return "".join(bloco.text for bloco in resposta.content if bloco.type == "text")
