# Pergunte ao Comex

Assistente que responde perguntas em português sobre os dados públicos de comércio exterior do Brasil (Comex Stat).

A ideia: você pergunta em linguagem natural, a IA transforma a pergunta em SQL, a consulta roda em um banco DuckDB carregado por um ETL em Python e a resposta volta com os números e um gráfico. Um conjunto de perguntas de teste roda no GitHub Actions a cada commit para medir se a IA continua acertando.

## Status

Projeto em construção. Este commit inicial só valida a estrutura do repositório.

## Planejado

- ETL em Python dos dados do Comex Stat para DuckDB
- Geração de SQL a partir de perguntas em português
- Respostas com gráfico
- Avaliação automática da IA no GitHub Actions

Desenvolvido por Samuel Reis
