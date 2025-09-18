# app.py
import streamlit as st
from src import data_loader, gui_components, state_manager

st.set_page_config(layout="wide", page_title="Análise de Casos")

def main():
    """Função principal que executa a aplicação Streamlit."""

    # st.title("Dashboard de Análise de Casos")

    # Inicializa o estado da sessão
    state_manager.initialize_state()

    # Carrega os dados usando o módulo de data loader
    df_tratado = data_loader.load_data()

    if df_tratado.empty:
        st.warning("Não foi possível carregar os dados. Verifique o caminho do arquivo.")
        return

    # A sidebar agora retorna o dataframe filtrado e as colunas a serem exibidas
    df_filtered, selected_columns = gui_components.create_sidebar(df_tratado)

    # Cria o cabeçalho fixo com título e KPIs
    # gui_components.create_header(df_filtered)

    # Cria as abas principais da aplicação
    tab_inicio, tab_geral, tab_agregacoes = st.tabs([
        "Início", "Tabela Geral", "Agregações"
    ])

    with tab_inicio:
        gui_components.display_home_tab()

    with tab_geral:
        # Passa o DF filtrado e as colunas selecionadas
        gui_components.display_general_table_tab(df_filtered, selected_columns)

    with tab_agregacoes:
        # A aba de agregações opera sobre os dados já filtrados
        gui_components.display_aggregations_tab(df_filtered)

if __name__ == "__main__":
    main()

# >>> streamlit run app.py
