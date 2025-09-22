# src/gui_components.py
import io, ast
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
            if col in config.LIST_FILTROS_SECUNDARIOS:
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
        for col in config.LIST_FILTROS_SECUNDARIOS:
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
        on_click=state_manager.clear_filters, use_container_width=True,
        args=(df.columns.tolist(),), # Passa a lista de colunas para a função de reset
    )
    return df_filtered

def display_general_table_tab(df: pd.DataFrame):
    """Exibe o conteúdo da aba 'Tabela Geral'."""
    st.header(f"Visualização Geral dos Dados")
    col1_i, col2_i = st.columns([0.8, 0.2], vertical_alignment="center")
    with col1_i:
        # Exibe um sumário dos filtros atualmente ativos
        display_active_filters()
    with col2_i:
        st.metric("Total de Registros Filtrados", f"{len(df):,}".replace(",", "."))
    
    selected_columns = st.multiselect(
        "Selecione as colunas a exibir:",
        options=df.columns.tolist(),
        default=df.columns.tolist(),
        key="multiselect_columns", # Key para o reset
        on_change=state_manager.invalidate_excel_file
    )

    col1, col2 = st.columns(2) # [0.4, 0.3, 0.3])
    with col1:
        sort_col = st.selectbox(
            "Ordenar por:",
            options=selected_columns if selected_columns else df.columns.tolist(),
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

    # --- Lógica Especial para Colunas com Listas (Explode) ---
    if _col_agg in config.LIST_COLS_TO_EXPLODE:
        series_to_analyze = df_agg[_col_agg]

        # 1. Converte strings que parecem listas (ex: "['a', 'b']") em objetos de lista
        is_stringified_list = series_to_analyze.dropna().apply(
            lambda x: isinstance(x, str) and x.startswith('[') and x.endswith(']')
        ).any()

        if is_stringified_list:
            # Usa ast.literal_eval que é seguro para esta conversão
            series_to_analyze = series_to_analyze.apply(
                lambda x: ast.literal_eval(x) if (isinstance(x, str) and x.startswith('[')) else x
            )
            df_agg[_col_agg] = series_to_analyze

        # 2. Se a coluna contém listas, "explode" o DataFrame
        is_exploded_list = series_to_analyze.dropna().apply(isinstance, args=(list,)).any()
        if is_exploded_list:
            df_agg = df_agg.explode(_col_agg)
        
        if is_stringified_list and is_exploded_list:
            st.info(f"Convertendo strings de listas para análise e expandindo para contar cada item individualmente.")
        elif is_stringified_list and not is_exploded_list:
            st.info(f"Convertendo strings de listas para análise.")
        elif is_exploded_list:
            st.info(f"Expandindo listas para contar cada item individualmente.")

    # df_agg = df_agg[~df_agg[_col_agg].isin(config.NULLS_PLACEHOLDERS_TO_DROP)]

    # Unifica todos os valores nulos e placeholders (ex: '-', '', <NA>) sob a mesma categoria
    df_agg[_col_agg] = df_agg[_col_agg].replace(config.NULLS_PLACEHOLDERS_TO_DROP, "Sem Registro").fillna("Sem Registro")
    
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
            f"Por favor, aplique mais filtros na barra lateral para reduzir o número de registros abaixo de {AGGREGATION_THRESHOLD:,}"
             " e habilitar as agregações."
        )
        return # Interrompe a execução da função aqui

    # Renderiza tanto as agregações padrão quanto as extras
    all_cols_to_render = config.LIST_AGREGATION_VIEWS + st.session_state.extra_aggregation_cols
    
    for col_agg in all_cols_to_render:
        if col_agg not in df.columns:
            st.warning(f"A coluna de agregação '{col_agg}' não foi encontrada nos dados.")
            continue
        
        category_label = col_agg.upper()
        container = st.expander(f"Análise por: {category_label}", expanded=st.session_state.expanders_state)
        with container:
            
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

            def _create_bar_chart(data, col_agg, color_mode):
                if color_mode == "Monocromático":
                    fig = go.Figure()
                    # Define a ordem de exibição das barras (crescente)
                    ascending_category_order = data[col_agg].tolist()

                    # Itera em ordem reversa (decrescente) para popular a legenda corretamente
                    for index, row in data.iloc[::-1].iterrows():
                        fig.add_trace(go.Bar(
                            x=[row[col_agg]],
                            y=[row['Contagem']],
                            name=str(row[col_agg]),
                            text=f"{row['Contagem']}",
                            textposition='auto',
                            marker_color='rgb(31, 119, 180)'
                        ))
                    
                    fig.update_layout(legend=dict(yanchor="middle", y=0.5, traceorder="reversed"))

                    # Força a ordem de exibição no eixo X
                    fig.update_xaxes(categoryorder='array', categoryarray=ascending_category_order)
                    # fig.update_layout(barmode='stack', showlegend=True)

                else: # Multicolorido
                    fig = px.bar(data, x=col_agg, y='Contagem', color=col_agg, text_auto=True)
                return fig

            def _create_pie_chart(data, col_agg, color_arg):
                fig = px.pie(data, names=col_agg, values='Contagem', color=color_arg)
                fig.update_traces(textposition='inside', textinfo='percent+label')
                return fig

            def render_chart(container, chart_type, color_mode, sort_by_chart, sort_order_chart):
                
                # A ordenação para pegar o Top 15 e a ordenação para exibição são feitas aqui
                chart_data = agg_data.sort_values(by='Contagem', ascending=False).head(15).sort_values(
                    by=sort_by_chart,
                    ascending=(sort_order_chart == "Crescente")
                )

                color_arg = col_agg if color_mode == "Multicolor" else None

                if chart_type == "Colunas":
                    fig = _create_bar_chart(chart_data, col_agg, color_mode)

                else: # Circular
                    fig = _create_pie_chart(chart_data, col_agg, color_arg)

                # Realça os rótulos e fontes do gráfico
                fig.update_layout(
                    legend_title_text=None, # Remove o título da legenda
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

                # Centraliza a legenda
                fig.update_layout(legend=dict(yanchor="middle", y=0.5))

                container.plotly_chart(fig, width=True, key=f"chart_{col_agg}")

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

            # Adiciona botão de remover para análises extras
            if col_agg in st.session_state.extra_aggregation_cols:
                st.button(
                    "❌ Remover Análise", 
                    key=f"remove_agg_{col_agg}",
                    on_click=state_manager.remove_extra_analysis,
                    args=('aggregation', col_agg),
                    use_container_width=True
                )

    st.divider()
    # --- UI para Adicionar Nova Agregação ---
    st.subheader("Adicionar Nova Análise de Agregação")
    available_cols = [col for col in df.select_dtypes(include=['object', 'category']).columns if col not in all_cols_to_render + [config.KEY_COLUMN_PRINCIPAL]]
    
    add_col1, add_col2 = st.columns([0.8, 0.2], vertical_alignment="bottom")
    new_col_to_add = add_col1.selectbox("Selecione uma nova coluna para analisar:", available_cols, key="new_agg_col_select")
    add_col2.button(
        "➕ Adicionar", 
        key="add_agg_button",
        on_click=state_manager.add_extra_analysis,
        args=('aggregation', {'col': new_col_to_add}),
        use_container_width=True
    )

def display_crosstab_tab(df: pd.DataFrame):
    """
    Exibe a aba de Análise Cruzada, permitindo a comparação entre duas
    variáveis categóricas através de uma tabela de contingência e um mapa de calor.
    """
    st.header("Análise Cruzada de Variáveis")
    st.markdown("Selecione duas variáveis categóricas para analisar a frequência e a relação entre elas.")

    # Identifica colunas categóricas com baixa cardinalidade para uma boa visualização
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    low_cardinality_cols = [col for col in categorical_cols if df[col].nunique() <= 50]
    
    high_cardinality_cols = set(categorical_cols) - set(low_cardinality_cols)
    if high_cardinality_cols:
        st.info(f"As seguintes colunas foram omitidas por terem muitos valores únicos (>50): {', '.join(sorted(list(high_cardinality_cols)))}")

    if len(low_cardinality_cols) < 2:
        st.warning("Não há variáveis categóricas suficientes para realizar uma análise cruzada.")
        return

    def render_crosstab_instance(instance_id=None):
        key_suffix = f"_{instance_id}" if instance_id else "_main"
        
        col1_selection, col2_selection = st.columns(2)
        with col1_selection:
            col1 = st.selectbox("Selecione a variável para as Linhas:", low_cardinality_cols, index=config.DEFAULT_INDEX_ANALISE_CRUZADA[0], key=f"crosstab_col1{key_suffix}")
        with col2_selection:
            col2 = st.selectbox("Selecione a variável para as Colunas:", low_cardinality_cols, index=config.DEFAULT_INDEX_ANALISE_CRUZADA[1], key=f"crosstab_col2{key_suffix}")

        if col1 == col2:
            st.error("Por favor, selecione duas variáveis diferentes.", icon="🚨")
            return

        with st.expander("Filtros Adicionais"):
            # st.subheader("Filtros Adicionais")
            st.markdown("Refine os dados incluídos na análise selecionando os valores de cada variável.")
        
            filt_col1, filt_col2 = st.columns(2)
            with filt_col1:
                # Filtro para os valores da primeira variável
                unique_vals1 = sorted(df[col1].dropna().unique())
                selected_vals1 = st.multiselect(
                    f"Valores a incluir de **{col1}**:",
                    options=unique_vals1,
                    default=unique_vals1,
                    key=f"crosstab_ms_col1{key_suffix}"
                )

            with filt_col2:
                # Filtro para os valores da segunda variável
                unique_vals2 = sorted(df[col2].dropna().unique())
                selected_vals2 = st.multiselect(
                    f"Valores a incluir de **{col2}**:",
                    options=unique_vals2,
                    default=unique_vals2,
                    key=f"crosstab_ms_col2{key_suffix}"
                )

        st.divider()
        
        df_crosstab = df[df[col1].isin(selected_vals1) & df[col2].isin(selected_vals2)]
        try:
            crosstab_df = pd.crosstab(df_crosstab[col1], df_crosstab[col2])
            # Cria o mapa de calor (heatmap) com Plotly
            fig = px.imshow(
                crosstab_df,
                text_auto=True,
                aspect="auto",
                # title=f"Mapa de Calor: Relação entre {col1} e {col2}",
                labels=dict(x=f"<b>{col2}</b>", y=f"<b>{col1}</b>", color="Contagem"),
                color_continuous_scale=px.colors.sequential.Blues
            )
            
            fig.update_xaxes(side="top")
            fig.update_layout(font=dict(size=14))
            st.plotly_chart(fig, use_container_width=True, key=f"crosstab_chart{key_suffix}")

            with st.expander("Ver Tabela de Frequência Detalhada"):
                st.dataframe(crosstab_df, use_container_width=True)

        except Exception as e:
            st.error(f"Ocorreu um erro ao gerar a análise cruzada: {e}")
        
        if instance_id:
            st.button(
                "❌ Remover Análise", 
                key=f"remove_crosstab_{instance_id}",
                on_click=state_manager.remove_extra_analysis,
                args=('crosstab', instance_id),
                use_container_width=True
            )

    # Renderiza a análise principal
    render_crosstab_instance()

    # Renderiza as análises extras
    for item in st.session_state.extra_crosstabs:
        st.divider()
        render_crosstab_instance(instance_id=item['id'])

    st.divider()
    st.button(
        "➕ Adicionar Nova Análise Cruzada",
        on_click=state_manager.add_extra_analysis,
        args=('crosstab',),
        use_container_width=True
    )
 

def display_timeseries_tab(df: pd.DataFrame):
    """
    Exibe a aba de Análise de Série Temporal, permitindo visualizar a
    contagem de casos ao longo do tempo com base em uma coluna de data.
    """
    st.header("Análise de Série Temporal")
    st.markdown("Analise a distribuição de casos ao longo do tempo com base em diferentes granularidades.")

    # Identifica colunas de data/datetime no DataFrame
    date_cols = df.select_dtypes(include=['datetime64[ns]', 'datetime']).columns.tolist()

    # --- Filtra colunas de segmentação por cardinalidade ---
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    CARDINALITY_LIMIT = 30 # Mesmo limite da Análise Cruzada para consistência
    
    low_cardinality_cols = [col for col in categorical_cols if df[col].nunique() <= CARDINALITY_LIMIT]
    high_cardinality_cols = set(categorical_cols) - set(low_cardinality_cols)
    
    segmentation_options = ["Nenhum (Total Geral)"] + sorted(low_cardinality_cols)

    if not date_cols:
        st.warning("Nenhuma coluna de data foi encontrada nos dados para realizar a análise temporal.")
        return

    def render_timeseries_instance(instance_id=None):
        key_suffix = f"_{instance_id}" if instance_id else "_main"

        col1_selection, col2_selection, col3_selection = st.columns(3)

        with col1_selection:
            date_col = st.selectbox("Selecione a coluna de data para análise:", date_cols, key=f"ts_date_col{key_suffix}", index=config.DEFAULT_INDEX_DATA_ANALISE_TEMPORAL)
        
        with col2_selection:
            granularity = st.selectbox(
                "Selecione a granularidade do tempo:",
                ['Ano', 'Trimestre', 'Mês', 'Semana', 'Dia'],
                key=f"ts_granularity{key_suffix}"
            )

        with col3_selection:
            segment_col = st.selectbox("Segmentar por (opcional):", segmentation_options, 
                                    help=f"Apenas colunas com até {CARDINALITY_LIMIT} valores únicos são exibidas.",
                                    key=f"ts_segment_col{key_suffix}")

        st.divider()

        try:
            granularity_map = {
                'Ano': 'Y', 'Trimestre': 'Q', 'Mês': 'M', 'Semana': 'W', 'Dia': 'D'
            }
            resample_code = granularity_map[granularity]

            # --- Prepara o DataFrame dinamicamente com as colunas necessárias ---
            cols_to_keep = [date_col, config.KEY_COLUMN_PRINCIPAL]
            if segment_col != "Nenhum (Total Geral)":
                cols_to_keep.append(segment_col)
            
            # Garante que a lista de colunas seja única para evitar erros
            unique_cols = list(set(cols_to_keep))
            df_time = df[unique_cols].copy()
            df_time = df_time.dropna(subset=cols_to_keep) # Remove linhas sem data ou segmento

            if df_time.empty:
                st.info("Não há dados válidos na coluna de data selecionada para o período filtrado.")
                return

            if segment_col == "Nenhum (Total Geral)":
                # Usa .agg() para uma saída consistente
                time_series_data = df_time.groupby(pd.Grouper(key=date_col, freq=resample_code)).agg(
                    Contagem_de_Casos=(config.KEY_COLUMN_PRINCIPAL, 'nunique')
                ).reset_index().rename(columns={date_col: 'Período'})
                y_col = 'Contagem_de_Casos'
                color_arg = None
                title = f"Evolução de Casos por {granularity} ({date_col})"
            else:
                # Usa .agg() para uma saída consistente
                time_series_data = df_time.groupby([pd.Grouper(key=date_col, freq=resample_code), segment_col]).agg(
                    Contagem_de_Casos=(config.KEY_COLUMN_PRINCIPAL, 'nunique')
                ).reset_index().rename(columns={date_col: 'Período'})
                y_col = 'Contagem_de_Casos'
                color_arg = segment_col
                title = f"Evolução de Casos por {granularity} ({date_col}), segmentado por {segment_col}"

            # Cria o gráfico de linha com Plotly
            fig = px.line(
                time_series_data,
                x='Período',
                y=y_col,
                color=color_arg,
                title=title,
                markers=True,
                labels={'Período': f'Período ({granularity})', y_col: 'Número de Casos Únicos'}
            )
            
            fig.update_layout(font=dict(size=14))
            st.plotly_chart(fig, use_container_width=True, key=f"timeseries_chart{key_suffix}")

            with st.expander("Ver Dados da Série Temporal Detalhadamente"):
                st.dataframe(time_series_data, use_container_width=True)

        except Exception as e:
            st.error(f"Ocorreu um erro ao gerar a análise de série temporal: {e}")

        if instance_id:
            st.button(
                "❌ Remover Análise", 
                key=f"remove_timeseries_{instance_id}",
                on_click=state_manager.remove_extra_analysis,
                args=('timeseries', instance_id),
                use_container_width=True
            )

    # Renderiza a análise principal
    render_timeseries_instance()

    # Renderiza as análises extras
    for item in st.session_state.extra_timeseries:
        st.divider()
        render_timeseries_instance(instance_id=item['id'])

    st.divider()
    st.button(
        "➕ Adicionar Nova Análise Temporal",
        on_click=state_manager.add_extra_analysis,
        args=('timeseries',),
        use_container_width=True
    )

