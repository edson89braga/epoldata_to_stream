# src/state_manager.py

import streamlit as st
from . import config

def initialize_state():
    """Inicializa as variáveis no session_state se ainda não existirem."""
    if 'expanders_state' not in st.session_state:
        st.session_state.expanders_state = True # Inicia expandido
    if 'alerts_expanders_state' not in st.session_state:
        st.session_state.alerts_expanders_state = True # Estado para a aba de alertas        

    # Define os valores padrão dos filtros no estado da sessão
    # Isso evita conflitos com o parâmetro 'default' dos widgets
    for col, default_value in config.JSON_FILTROS_DEFAULT.items():
        key = f"filter_{col}"
        if key not in st.session_state:
            # Garante que o valor seja sempre uma lista para o multiselect
            st.session_state[key] = [default_value] if isinstance(default_value, str) else default_value

    # Inicializa listas para as análises dinâmicas
    if 'extra_aggregation_cols' not in st.session_state:
        st.session_state.extra_aggregation_cols = []
    if 'extra_crosstabs' not in st.session_state:
        st.session_state.extra_crosstabs = []
    if 'extra_timeseries' not in st.session_state:
        st.session_state.extra_timeseries = []
    
    # Contador para garantir chaves únicas para widgets dinâmicos
    if 'widget_id_counter' not in st.session_state:
        st.session_state.widget_id_counter = 0

def toggle_expanders_state():
    """Inverte o estado booleano de 'expanders_state'."""
    st.session_state.expanders_state = not st.session_state.expanders_state

def toggle_alerts_expanders_state():
    """Inverte o estado booleano de 'alerts_expanders_state'."""
    st.session_state.alerts_expanders_state = not st.session_state.alerts_expanders_state

def invalidate_excel_file():
    """Define o arquivo Excel no estado da sessão como None."""
    st.session_state.excel_file = None

def clear_filters(all_columns: list = None):
    """Limpa todos os filtros da barra lateral, resetando os widgets."""
    # Filtros são identificados por um prefixo para segurança
    filter_keys = [k for k in st.session_state.keys() if k.startswith("filter_")]
    for key in filter_keys:
        st.session_state[key] = [] # Para multiselect, resetar para lista vazia
    
    # Reseta o filtro de colunas para 'all' se a lista for fornecida
    if "multiselect_columns" in st.session_state:
        if all_columns is not None:
            st.session_state["multiselect_columns"] = all_columns
        else:
            del st.session_state["multiselect_columns"]

    invalidate_excel_file()

# --- Funções para Gerenciar Análises Dinâmicas ---

def add_extra_analysis(analysis_type: str, config: dict = None):
    """Adiciona uma nova análise a uma das listas no session_state."""
    st.session_state.widget_id_counter += 1
    
    if analysis_type == 'aggregation':
        st.session_state.extra_aggregation_cols.append(config['col'])
    
    elif analysis_type == 'crosstab':
        new_crosstab = {'id': st.session_state.widget_id_counter}
        st.session_state.extra_crosstabs.append(new_crosstab)
        
    elif analysis_type == 'timeseries':
        new_timeseries = {'id': st.session_state.widget_id_counter}
        st.session_state.extra_timeseries.append(new_timeseries)

def remove_extra_analysis(analysis_type: str, item_identifier):
    """Remove uma análise de uma das listas no session_state."""
    if analysis_type == 'aggregation':
        st.session_state.extra_aggregation_cols.remove(item_identifier)
    elif analysis_type == 'crosstab':
        state_list = st.session_state['extra_crosstabs']
        st.session_state['extra_crosstabs'] = [item for item in state_list if item['id'] != item_identifier]
    elif analysis_type == 'timeseries':
        state_list = st.session_state['extra_timeseries']
        st.session_state['extra_timeseries'] = [item for item in state_list if item['id'] != item_identifier]

