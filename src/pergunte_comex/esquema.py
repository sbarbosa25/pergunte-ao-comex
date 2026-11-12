"""Dicionário de dados da tabela `processos`.

É a única fonte da descrição das colunas: o ETL usa para comentar a tabela e a
IA recebe este texto como contexto para escrever o SQL.
"""

TABELA = "processos"

COLUNAS: dict[str, tuple[str, str]] = {
    "id_processo": ("VARCHAR", "Identificador do processo, ex.: IMP-2026-00002"),
    "tipo_operacao": ("VARCHAR", "'Importação' ou 'Exportação'"),
    "modal": ("VARCHAR", "'Marítimo', 'Aéreo' ou 'Rodoviário'"),
    "incoterm": ("VARCHAR", "FOB, CIF, EXW, FCA, CFR ou DAP"),
    "cliente": ("VARCHAR", "Nome do cliente (empresa fictícia)"),
    "transportador": ("VARCHAR", "Armador, companhia aérea ou transportadora rodoviária"),
    "pais_origem": ("VARCHAR", "País de origem; 'Brasil' nas exportações"),
    "local_origem": ("VARCHAR", "Porto, aeroporto ou fronteira de origem"),
    "pais_destino": ("VARCHAR", "País de destino; 'Brasil' nas importações"),
    "local_destino": ("VARCHAR", "Porto, aeroporto ou fronteira de destino"),
    "pais_parceiro": ("VARCHAR", "País estrangeiro do processo (origem na importação, "
                                 "destino na exportação)"),
    "ncm": ("VARCHAR", "Posição NCM do produto, 4 dígitos"),
    "descricao_produto": ("VARCHAR", "Descrição do produto"),
    "tipo_container": ("VARCHAR", "Tipo de container; nulo fora do modal marítimo"),
    "qtd_containers": ("INTEGER", "Quantidade de containers; 0 fora do modal marítimo"),
    "peso_kg": ("DOUBLE", "Peso bruto em kg"),
    "valor_fob_usd": ("DOUBLE", "Valor FOB da mercadoria em dólares"),
    "frete_usd": ("DOUBLE", "Frete internacional em dólares"),
    "seguro_usd": ("DOUBLE", "Seguro internacional em dólares"),
    "valor_cif_usd": ("DOUBLE", "FOB + frete + seguro, em dólares"),
    "data_abertura": ("DATE", "Data de abertura do processo"),
    "data_embarque": ("DATE", "Data de embarque; nula em processos cancelados"),
    "data_chegada_prevista": ("DATE", "Previsão de chegada (ETA)"),
    "data_chegada_real": ("DATE", "Chegada efetiva; nula se a carga ainda não chegou"),
    "data_desembaraco": ("DATE", "Desembaraço aduaneiro; nula se ainda não desembaraçado"),
    "canal": ("VARCHAR", "Canal de parametrização: 'Verde', 'Amarelo', 'Vermelho' ou "
                         "'Cinza'; nulo se a carga ainda não chegou"),
    "status": ("VARCHAR", "'Concluído', 'Em trânsito', 'Aguardando desembaraço' ou 'Cancelado'"),
    "dias_transito": ("INTEGER", "Dias entre embarque e chegada real"),
    "dias_atraso": ("INTEGER", "Chegada real menos chegada prevista, em dias; negativo ou "
                               "zero significa no prazo; nulo se ainda não chegou"),
    "atrasado": ("BOOLEAN", "Verdadeiro quando dias_atraso > 0; nulo se ainda não chegou"),
    "dias_desembaraco": ("INTEGER", "Dias entre chegada real e desembaraço"),
}


def descricao_para_ia() -> str:
    linhas = [f"Tabela `{TABELA}` (uma linha por processo de comércio exterior):"]
    for nome, (tipo, descricao) in COLUNAS.items():
        linhas.append(f"- {nome} ({tipo}): {descricao}")
    return "\n".join(linhas)
