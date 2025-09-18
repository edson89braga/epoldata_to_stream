# src/gui_components.py
import io
import streamlit as st
import pandas as pd
import plotly.express as px
from . import config

@st.cache_data
def to_excel(df: pd.DataFrame) -> bytes:
    """Converte um DataFrame para um arquivo Excel em memória."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    return output.getvalue()

def create_sidebar(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Cria a barra lateral de filtros e retorna o DataFrame filtrado
    e as colunas selecionadas para exibição.
    """
    st.sidebar.header("Filtros")
    
    df_filtered = df.copy()
    
    # Filtro para selecionar colunas
    all_columns = df.columns.tolist()
    selected_columns = st.sidebar.multiselect(
        "Selecione as colunas para exibir:",
        options=all_columns,
        default=all_columns
    )

    # Filtros principais
    st.sidebar.subheader("Filtros Principais")
    for col in all_columns:
        if col in config.JSON_FILTROS_SECUNDARIOS:
            continue

        default_value = []
        if col in config.JSON_FILTROS_DEFAULT:
            default_value = config.JSON_FILTROS_DEFAULT[col]
        
        options = sorted(df[col].dropna().unique())
        selected = st.sidebar.multiselect(
            f"Filtrar {col}",
            options=options,
            default=default_value
        )
        if selected:
            df_filtered = df_filtered[df_filtered[col].isin(selected)]

    # Filtros secundários em um expander
    with st.sidebar.expander("Filtros Secundários", expanded=False):
        for col in config.JSON_FILTROS_SECUNDARIOS:
            if col in df.columns:
                options = sorted(df[col].dropna().unique())
                selected = st.multiselect(
                    f"Filtrar {col}",
                    options=options,
                    default=[]
                )
                if selected:
                    df_filtered = df_filtered[df_filtered[col].isin(selected)]
    
    return df_filtered, selected_columns if selected_columns else all_columns

def display_general_table_tab(df: pd.DataFrame, selected_columns: list[str]):
    """Exibe o conteúdo da aba 'Tabela Geral'."""
    st.header(f"Visualização Geral dos Dados")
    st.metric("Total de Registros Encontrados", f"{len(df):,}".replace(",", "."))

    col1, col2, col3 = st.columns([0.4, 0.3, 0.3])
    with col1:
        sort_col = st.selectbox(
            "Ordenar por:",
            options=df.columns,
            index=list(df.columns).index(config.KEY_COLUMN_PRINCIPAL) if config.KEY_COLUMN_PRINCIPAL in df.columns else 0
        )
    with col2:
        sort_order = st.radio(
            "Ordem:",
            options=["Crescente", "Decrescente"],
            horizontal=True
        )
    
    is_ascending = sort_order == "Crescente"
    df_sorted = df.sort_values(by=sort_col, ascending=is_ascending)
    
    st.info(f"Exibindo os {config.N_LINHAS_VISIVEIS} primeiros registros da tabela ordenada.")

    st.dataframe(
        df_sorted[selected_columns].head(config.N_LINHAS_VISIVEIS),
    )
    
    excel_file = to_excel(df_sorted[selected_columns])
    st.download_button(
        label="📥 Download (XLSX)",
        data=excel_file,
        file_name="dados_filtrados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def display_aggregations_tab(df: pd.DataFrame):
    """Exibe o conteúdo da aba 'Agregações'."""
    st.header("Agregações por Categoria")
    st.info(f"Exibindo até 15 Colunas por gráfico.")
    for col_agg in config.LIST_AGREGATION_VIEWS:
        if col_agg not in df.columns:
            st.warning(f"A coluna de agregação '{col_agg}' não foi encontrada nos dados.")
            continue

        with st.expander(f"Análise por: {col_agg}", expanded=True):
            # Prepara os dados para agregação
            df_agg = df.copy()
            df_agg[col_agg] = df_agg[col_agg].fillna("Não Informado")
            df_agg = df_agg[~df_agg[col_agg].isin(config.NULLS_PLACEHOLDERS_TO_DROP)]

            # Lógica de agregação
            agg_data = df_agg.groupby(col_agg)[config.KEY_COLUMN_PRINCIPAL].nunique().reset_index()
            agg_data.columns = [col_agg, 'Contagem']
            total_casos = agg_data['Contagem'].sum()
            agg_data['Percentual'] = (agg_data['Contagem'] / total_casos * 100)
           
            # Exibição
            col_table, col_chart = st.columns([0.5, 0.5], vertical_alignment='center')
            with col_table:
                st.dataframe(
                    agg_data,
                    column_config={
                        "Percentual": st.column_config.ProgressColumn(
                            "Percentual (%)", format="%.2f%%", min_value=0, max_value=100
                        )
                    }
                )

            with col_chart:
                # Controles de ordenação específicos para o gráfico em um container
                with st.container():
                    ctrl_cols = st.columns((1, 0.7, 1.3), vertical_alignment='center')
                    ctrl_cols[0].markdown("**Ordenação do Gráfico**")
                    sort_order_chart = ctrl_cols[1].radio(
                        "Ordem", ["Decrescente", "Crescente"], key=f"order_chart_{col_agg}", horizontal=True, label_visibility="collapsed"
                    )
                    sort_by_chart = ctrl_cols[2].radio(
                        "Ordenar por", ["Percentual", col_agg], key=f"sort_chart_{col_agg}", horizontal=True, label_visibility="collapsed"
                    )

                # Garante que o gráfico sempre mostre o Top 15 com base na contagem
                top_15_data = agg_data.sort_values(by='Contagem', ascending=False).head(15)
                
                # Aplica a ordenação dos controles ao subconjunto Top 15
                chart_data = top_15_data.sort_values(
                    by=sort_by_chart,
                    ascending=(sort_order_chart == "Crescente")
                )

                fig = px.bar(
                    chart_data, 
                    x=col_agg,
                    y='Contagem',
                    #title=f'Top 15 - {col_agg}',
                    text_auto=True
                )
                st.plotly_chart(fig)

