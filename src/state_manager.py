# src/state_manager.py

import streamlit as st

def initialize_state():
    """Inicializa as variáveis no session_state se ainda não existirem."""
    if 'expanders_state' not in st.session_state:
        st.session_state.expanders_state = True # Inicia expandido

def toggle_expanders_state():
    """Inverte o estado booleano de 'expanders_state'."""
    st.session_state.expanders_state = not st.session_state.expanders_state

