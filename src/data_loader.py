# src/data_loader.py

import pandas as pd
import streamlit as st
from . import config

@st.cache_data
def load_data() -> pd.DataFrame:
    """
    Carrega o DataFrame a partir do arquivo Parquet especificado na configuração.
    Utiliza o cache do Streamlit para evitar recarregamentos desnecessários.
    """
    try:
        df = pd.read_parquet(config.PATH_DF_TRATADO_PARQUET)
        return df
    except FileNotFoundError:
        st.error(f"Arquivo não encontrado em: {config.PATH_DF_TRATADO_PARQUET}")
        return pd.DataFrame()
    

