# src/config.py

from datetime import date
from typing import Dict, List, Set, Union

# --- Paths and Constants ---
DATA_CORTE_ORIGINAL: date = date(2025, 11, 10)

data_str = DATA_CORTE_ORIGINAL.strftime("%d-%m-%Y")
data_str2 = DATA_CORTE_ORIGINAL.strftime("%d/%m/%Y")
base_name = f"Casos_SP_{data_str}"

PATH_DF_TRATADO_PARQUET: str = f"data/{base_name}_Tratado.parquet"
KEY_COLUMN_PRINCIPAL: str = 'Caso Id'
N_LINHAS_VISIVEIS: int = 200

TITULO = "Dashboard de Análise de Casos Sob Alerta"
# TITULO = "Dashboard de Análise de Casos"

INFO_HEADER = "Bem-vindo ao Dashboard de Análise de Casos sob Alerta"
INFO_MD = f"""
    Este painel interativo foi projetado para explorar e analisar os dados de casos, permitindo desde uma visão geral até diagnósticos detalhados.
    
    **Filtros de corte na base ePol-BI:**
    - UF: SP
    - Situação: 'Em Andamento'
    - Data de extração: **{data_str2}**
    ---

    Utilize os **filtros na barra lateral** para segmentar os dados em todas as abas de análise. Cada aba oferece uma perspectiva diferente:
    - **📋 Tabela Geral**: Visualização dos dados brutos filtrados, selecione colunas, ordene e opcionalmente faça o download em formato Excel.
    <br><br>
    - **🔎 Análise de Alertas**: Ferramenta para diagnóstico e análise sobre os índices de qualidade (Alertas).
        - **Análise da situação atual:** Com a data-corte original, visualiza-se a distribuição de alertas por tipo ou por delegacia/responsável.
        - **Análise prognóstica:** Selecionando uma data futura no seletor de data-corte, a aplicação recalcula dinamicamente quais casos passarão a ter alertas. Ideal para planejamento e atuação preventiva.
    <br><br>     
    - **📈 Agregações**: Explore a distribuição dos casos por categorias como Tipo de Processo, Delegacia, Matéria, entre outras.
    - **🔗 Análise Cruzada**: Investigue a relação entre duas variáveis categóricas através de um mapa de calor interativo.
    - **⏳ Série Temporal**: Acompanhe a evolução do número de casos ao longo do tempo, com base em diferentes colunas de data.
    """ 

# - Sistema de tramitação: ePol

# --- Data Cleaning ---
NULLS_PLACEHOLDERS_TO_DROP: List[str] = ['-', '', 'None', '<NA>', 'nan', 'nat', 'undefined']

# --- UI Defaults ---
JSON_FILTROS_DEFAULT: Dict[str, Union[str, List[str]]] = {
    'Situação': "Em Andamento",
    'Unidade UF': 'SP',
} # 'Lotação Sigla': 'SR/PF/SP',

LIST_FILTROS_SECUNDARIOS: List[str] = [
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
    'Proc. Lei Artigo', 
    'Proc. Lei Artigo Isolado', 
]

LIST_AGREGATION_VIEWS: Set[str] = [
    'Tipo', 
    'Delegacia', 
    #'Documento de Origem', 
    #'Órgão de Origem', 
    #'Órgão Vítima', 
    #'Área de Atribuição', 
    #'Proc. Lei',
    #'Lei-Artigo',
    # 'Tipo Penal', 
    #'Matéria Prometheus', 
]

LIST_COLS_TO_EXPLODE = [
    'Tipo Penal', 'Lei-Artigo', 'Proc. Lei',
    'Tipo Alerta', 'Tipo Saneamento',
]

# --- Colunas para Análise de Alertas ---
COL_ALERTA = "Tipo Alerta"
COL_SANEAMENTO = "Tipo Saneamento"
COL_DELEGACIA = "Delegacia"
COL_LOTACAO = "Lotação Sigla"
COL_DELEGADO = "Delegado Atual"
COL_ESCRIVAO = "Escrivão"

DEFAULT_INDEX_ANALISE_CRUZADA = (0, 6) # Tipo e Delegacia
DEFAULT_INDEX_DATA_ANALISE_TEMPORAL = 5 # Data Instauração