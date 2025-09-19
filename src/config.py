# src/config.py

from typing import Dict, List, Set, Union

# --- Paths and Constants ---
PATH_DF_TRATADO_PARQUET: str = r"C:\\Users\\edson.eab\\Downloads\\Casos_SRSP_16-09-2025_Tratado.parquet"
KEY_COLUMN_PRINCIPAL: str = 'Caso Id'
N_LINHAS_VISIVEIS: int = 100

TITULO = "Dashboard de Análise de Casos"

INFO_HEADER = "Bem-vindo ao Dashboard de Análise de Casos"
INFO_MD = """
    Este painel interativo foi projetado para explorar e analisar os dados referentes a <u>Casos em tramitação no sistema ePol vinculados ao estado de SP</u>.
    
    Data de corte: **16/09/2025**

    Utilize os filtros na barra lateral para segmentar os dados de acordo com seu interesse.
    - **Tabela Geral**: Visualize os dados brutos filtrados e faça o download em formato Excel.
    - **Agregações**: Explore distribuições e contagens por diferentes categorias.

    """

# --- Data Cleaning ---
NULLS_PLACEHOLDERS_TO_DROP: List[str] = ['-', '', 'None', '<NA>', 'nan', 'nat', 'undefined']

# --- UI Defaults ---
JSON_FILTROS_DEFAULT: Dict[str, Union[str, List[str]]] = {
    'Situação': "Em Andamento",
    'Unidade UF': 'SP',
    'Lotação Sigla': 'SR/PF/SP',
}

JSON_FILTROS_SECUNDARIOS: List[str] = [
    'Caso Id', 'Número do Processo',
    'Data Fato', 
    'Data Recebimento', 
    'Data Cadastro', 
    'Data Parecer', 
    'Data Distribuição', 
    'Data Instauração', 
    'Data Relatório', 
    'Data Encerrado', 
    'Duração Dias', 
    'Última Movimentação',
]

LIST_AGREGATION_VIEWS: Set[str] = [
    'Tipo', 
    'Delegacia', 
    'Tipo Documento', 
    'Origem Documento', 
    'Órgão/Vítima', 
    'Área de Atribuição', 
    'Tipo Penal', 
    'Matéria Prometheus', 
]