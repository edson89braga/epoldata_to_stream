# src/gui_components.py
import io
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from . import config
from . import state_manager

def load_custom_css():
    """Carrega CSS customizado para compactar a UI."""
    st.markdown("""
        <style>
            /* Define a largura inicial da barra lateral */
            [data-testid="stSidebar"][aria-collapsed="false"] {
                min-width: 300px !important; /* é necessário para sobrescrever o estilo padrão */
            }

            /* Ajusta a posição vertical das abas */
            div[data-testid="stTabs"] {
                margin-top: -35px;
            }
                
            /* Realça os rótulos das abas (sem fixação) */
            button[data-baseweb="tab"] {
                font-size: 1.1rem !important;
                font-weight: 600 !important;
            }
                
            /* Realça a aba ativa com a cor primária do tema */
            button[data-baseweb="tab"][aria-selected="true"] {
                color: var(--primary-color) !important;
                border-bottom-color: var(--primary-color) !important;
            }

            /* Reduz o espaçamento inferior dos grupos de botões de rádio */
            div[data-testid="stRadio"] {
                margin-bottom: -25px;
            }
        </style>
    """, unsafe_allow_html=True)

def create_header(df: pd.DataFrame):
    """Cria um cabeçalho fixo com título, KPIs e controles globais."""
    with st.container():
        st.title(config.TITULO)            
        # KPIs
        kpi1, kpi2, kpi3 = st.columns(3)
        total_casos = df[config.KEY_COLUMN_PRINCIPAL].nunique()
        casos_em_andamento = df[df['Situação'] == 'Em Andamento'][config.KEY_COLUMN_PRINCIPAL].nunique()
        duracao_media = df[df['Duração Dias'] > 0]['Duração Dias'].mean()

        kpi1.metric("Total de Casos", f"{total_casos:,}".replace(",", "."))
        kpi2.metric("Casos em Andamento", f"{casos_em_andamento:,}".replace(",", "."))
        kpi3.metric("Duração Média (Dias)", f"{duracao_media:.0f}" if not pd.isna(duracao_media) else "N/A")
        
        st.divider()

def display_active_filters():
    """Exibe um resumo dos filtros que foram aplicados na barra lateral."""
    active_filters = []
    for key, value in st.session_state.items():
        if key.startswith("filter_") and value:
            col_name = key.replace("filter_", "")
            # Formata o valor para exibição
            value_str = ", ".join(map(str, value))
            active_filters.append(f"**{col_name}:** `{value_str}`")

    if active_filters:
        with st.expander("Filtros Ativos", expanded=True):
            st.markdown(" &nbsp; | &nbsp; ".join(active_filters))
    else:
        st.info("Nenhum filtro aplicado. Exibindo todos os registros.")

def display_home_tab():
    """Exibe o conteúdo da aba 'Início'."""
    st.header(config.INFO_HEADER)
    st.markdown(config.INFO_MD, unsafe_allow_html=True)

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
    # st.sidebar.header("Filtros")

    df_filtered = df.copy()
    
    # Filtro para selecionar colunas
    all_columns = df.columns.tolist()

    # Filtros principais
    with st.sidebar.expander("Filtros Principais", expanded=True):
        for col in all_columns:
            if col in config.JSON_FILTROS_SECUNDARIOS:
                continue
            
            options = sorted(df[col].dropna().unique())
            selected = st.multiselect(
                f"{col}",
                options=options,
                key=f"filter_{col}", # Adiciona uma key prefixada
                on_change=state_manager.invalidate_excel_file
            )
            if selected:
                df_filtered = df_filtered[df_filtered[col].isin(selected)]

    # Filtros secundários em um expander
    with st.sidebar.expander("Filtros Secundários", expanded=False):
        for col in config.JSON_FILTROS_SECUNDARIOS:
            if col in df.columns:
                options = sorted(df[col].dropna().unique())
                selected = st.multiselect(
                    f"{col}",
                    options=options,
                    default=[],
                    key=f"filter_{col}", # Adiciona uma key prefixada
                    on_change=state_manager.invalidate_excel_file
                )
                if selected:
                    df_filtered = df_filtered[df_filtered[col].isin(selected)]

    st.sidebar.button(
        "🧹 Limpar Todos os Filtros",
        on_click=state_manager.clear_filters, use_container_width=True
    )
    return df_filtered

def display_general_table_tab(df: pd.DataFrame):
    """Exibe o conteúdo da aba 'Tabela Geral'."""
    st.header(f"Visualização Geral dos Dados")
    col1, col2 = st.columns([0.8, 0.2], vertical_alignment="center")
    with col1:
        # Exibe um sumário dos filtros atualmente ativos
        display_active_filters()
    with col2:
        st.metric("Total de Registros Filtrados", f"{len(df):,}".replace(",", "."))
    
    selected_columns = st.multiselect(
        "Selecione as colunas a exibir:",
        options=df.columns.tolist(),
        default=df.columns.tolist(),
        key="multiselect_columns", # Key para o reset
        on_change=state_manager.invalidate_excel_file
    )

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
    
    st.dataframe(df_sorted[selected_columns].head(config.N_LINHAS_VISIVEIS))

    # --- Lógica de Download Sob Demanda ---
    if 'excel_file' not in st.session_state:
        st.session_state.excel_file = None

    def generate_excel():
        st.session_state.excel_file = to_excel(df_sorted[selected_columns])

    st.button("Preparar Download (xlsx)", on_click=generate_excel, use_container_width=True)

    if st.session_state.excel_file is not None:
        st.download_button(
            label="📥 Baixar Arquivo",
            data=st.session_state.excel_file,
            file_name="dados_filtrados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# @st.cache_data # cache estava causando um erro de sincronismo com dataframe
def prepare_agg_data(_df: pd.DataFrame, _col_agg: str) -> pd.DataFrame:
    """
    Prepara e agrega os dados para uma coluna específica.
    """
    df_agg = _df.copy()
    df_agg[_col_agg] = df_agg[_col_agg].fillna("Não Informado")
    df_agg = df_agg[~df_agg[_col_agg].isin(config.NULLS_PLACEHOLDERS_TO_DROP)]
    
    agg_data = df_agg.groupby(_col_agg)[config.KEY_COLUMN_PRINCIPAL].nunique().reset_index()
    agg_data.columns = [_col_agg, 'Contagem']
    total_casos = agg_data['Contagem'].sum()
    
    if total_casos > 0:
        agg_data['Percentual'] = (agg_data['Contagem'] / total_casos * 100)
    else:
        agg_data['Percentual'] = 0
        
    return agg_data

def display_aggregations_tab(df: pd.DataFrame):
    """Exibe o conteúdo da aba 'Agregações'."""
    c1, c2 = st.columns([0.8, 0.2], vertical_alignment="center")
    with c1:
        st.header("Agregações de Dados")
    with c2:
        st.button(
            "Recolher Tudo" if st.session_state.expanders_state else "Expandir Tudo",
            on_click=state_manager.toggle_expanders_state)
        
    st.info("As visualizações de agregação são baseadas nos dados atualmente filtrados. Os gráficos exibem até 15 resultados cada.")

    # --- Barreira de Proteção (Guardrail) ---
    AGGREGATION_THRESHOLD = 50000 
    if len(df) > AGGREGATION_THRESHOLD:
        st.warning(
            f"Muitos registros para visualizar ({len(df):,}). "
            f"Por favor, aplique mais filtros na barra lateral para reduzir o número de registros abaixo de {AGGREGATION_THRESHOLD:,} e habilitar as agregações."
        )
        return # Interrompe a execução da função aqui

    for col_agg in config.LIST_AGREGATION_VIEWS:
        if col_agg not in df.columns:
            st.warning(f"A coluna de agregação '{col_agg}' não foi encontrada nos dados.")
            continue
        
        category_label = col_agg.upper()
        with st.expander(f"Análise por: {category_label}", expanded=st.session_state.expanders_state):
            
            agg_data = prepare_agg_data(df, col_agg)

            def _render_chart_controls(container):
                with container.container():
                    # Controles específicos para o gráfico em um container
                    c1, c2, c3, c4 = st.columns(4, vertical_alignment="center")
                    chart_type = c1.radio("Gráfico Tipo", ["Colunas", "Circular"], key=f"chart_type_{col_agg}", horizontal=True)
                    color_mode = c2.radio("Cor", ["Monocromático", "Multicolor"], key=f"color_mode_{col_agg}", horizontal=True)
                    sort_by_chart = c3.radio("Ordenar por", ["Percentual", col_agg], key=f"sort_chart_{col_agg}", horizontal=True)
                    sort_order_chart = c4.radio("Ordem", ["Decrescente", "Crescente"], key=f"order_chart_{col_agg}", horizontal=True)
                return chart_type, color_mode, sort_by_chart, sort_order_chart
            
            # --- Funções de Renderização ---
            def render_table(container):
                # Ordena os dados para exibição na tabela
                sorted_data = agg_data.sort_values(by="Contagem", ascending=False).reset_index(drop=True)
                container.dataframe(
                    sorted_data, # width=True,
                    column_config={
                        "Percentual": st.column_config.ProgressColumn(
                            "Percentual (%)", format="%.2f%%", min_value=0, max_value=100
                        )
                    }
                )

            def render_chart(container, chart_type, color_mode, sort_by_chart, sort_order_chart):
                
                # A ordenação para pegar o Top 15 e a ordenação para exibição são feitas aqui
                chart_data = agg_data.sort_values(by='Contagem', ascending=False).head(15).sort_values(
                    by=sort_by_chart,
                    ascending=(sort_order_chart == "Crescente")
                )

                color_arg = col_agg if color_mode == "Multicolor" else None

                if chart_type == "Colunas":
                    if color_mode == "Monocromático":
                        # Usa graph_objects para criar uma legenda por barra
                        fig = go.Figure()
                        for index, row in chart_data.iterrows():
                            fig.add_trace(go.Bar(
                                x=[row[col_agg]],
                                y=[row['Contagem']],
                                name=str(row[col_agg]),
                                text=row['Contagem'],
                                textposition='auto',
                                marker_color='rgb(31, 119, 180)' # Cor azul padrão do Plotly
                            ))
                        fig.update_layout(barmode='stack', showlegend=True)
                    
                    else: # Multicolorido
                        fig = px.bar(chart_data, x=col_agg, y='Contagem', text_auto=True, color=col_agg)

                else: # Circular
                    fig = px.pie(
                        chart_data, names=col_agg, values='Contagem', # title=f'Top 15 - {col_agg}',
                        color=color_arg
                    )
                    fig.update_traces(textposition='inside', textinfo='percent+label')

                # Realça os rótulos e fontes do gráfico
                fig.update_layout(
                    font=dict(
                        size=14, # Tamanho base da fonte para o gráfico
                    ),
                    legend_font=dict(
                        size=14 # Tamanho da fonte da legenda
                    ),
                    xaxis_title_font=dict(size=16), # Tamanho da fonte do título do eixo X
                    yaxis_title_font=dict(size=16), # Tamanho da fonte do título do eixo Y
                )
                fig.update_traces(textfont_size=14) # Tamanho da fonte dos rótulos de dados

                # Centraliza a legenda verticalmente para todos os gráficos
                fig.update_layout(legend=dict(yanchor="middle", y=0.5))

                container.plotly_chart(fig, width=True)

            # --- Lógica de Layout Principal ---
            
            # Inicializa variáveis para evitar erros
            chart_type, color_mode, sort_by_chart, sort_order_chart = (None,) * 4
            
            # Renderização do cabeçalho é condicional à view_mode
            # Primeiro, precisamos saber qual é o view_mode
            temp_view_mode_key = f"view_mode_{col_agg}"
            view_mode_selection = st.session_state.get(temp_view_mode_key, "Gráfico") # Pega valor atual ou default

            if view_mode_selection == "Ambos":
                # Layout de cabeçalho com duas colunas
                header_col1, header_col2 = st.columns([0.3, 0.7], vertical_alignment='center', gap="small")
                with header_col1:
                    view_mode = st.radio("Exibição", ["Gráfico", "Tabela", "Ambos"], key=temp_view_mode_key, horizontal=True) # label_visibility="collapsed"
                with header_col2:
                    chart_type, color_mode, sort_by_chart, sort_order_chart = _render_chart_controls(st)
            else:
                # Layout de cabeçalho com uma coluna
                view_mode = st.radio("Exibição", ["Gráfico", "Tabela", "Ambos"], key=temp_view_mode_key, horizontal=True)
            
            st.divider()

            # Lógica de renderização do conteúdo
            if view_mode == "Tabela":
                render_table(st)

            elif view_mode == "Gráfico":
                # Controles são renderizados ANTES do gráfico no mesmo container
                chart_type, color_mode, sort_by_chart, sort_order_chart = _render_chart_controls(st)
                render_chart(st, chart_type, color_mode, sort_by_chart, sort_order_chart)

            elif view_mode == "Ambos":
                # Controles já foram renderizados no cabeçalho
                col_table, col_chart = st.columns([0.5, 0.5], vertical_alignment='center')
                render_table(col_table)
                render_chart(col_chart, chart_type, color_mode, sort_by_chart, sort_order_chart)


