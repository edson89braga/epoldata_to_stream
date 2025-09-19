# src/state_manager.py

import streamlit as st
from . import config

def initialize_state():
    """Inicializa as variáveis no session_state se ainda não existirem."""
    if 'expanders_state' not in st.session_state:
        st.session_state.expanders_state = True # Inicia expandido

    # Define os valores padrão dos filtros no estado da sessão
    # Isso evita conflitos com o parâmetro 'default' dos widgets
    for col, default_value in config.JSON_FILTROS_DEFAULT.items():
        key = f"filter_{col}"
        if key not in st.session_state:
            # Garante que o valor seja sempre uma lista para o multiselect
            st.session_state[key] = [default_value] if isinstance(default_value, str) else default_value

def toggle_expanders_state():
    """Inverte o estado booleano de 'expanders_state'."""
    st.session_state.expanders_state = not st.session_state.expanders_state

def invalidate_excel_file():
    """Define o arquivo Excel no estado da sessão como None."""
    st.session_state.excel_file = None

def clear_filters():
    """Limpa todos os filtros da barra lateral, resetando os widgets."""
    # Filtros são identificados por um prefixo para segurança
    filter_keys = [k for k in st.session_state.keys() if k.startswith("filter_")]
    for key in filter_keys:
        st.session_state[key] = [] # Para multiselect, resetar para lista vazia
    
    # Limpa o filtro de colunas também
    if "multiselect_columns" in st.session_state:
        del st.session_state["multiselect_columns"]
    invalidate_excel_file()



