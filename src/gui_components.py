# src/gui_components.py
import io, ast, numpy as np
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta, date
from . import config
from . import state_manager

# Vamos remover as 3 primeiras cores, começando do índice 3
escala_azul_truncada = px.colors.sequential.Blues[3:]

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
    """
    Converte um DataFrame para um arquivo Excel em memória, aplicando uma largura
    de coluna padrão para melhor visualização.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
        
        # Acessa a planilha para ajustar a largura das colunas
        worksheet = writer.sheets['Dados']
        for column_cells in worksheet.columns:
            # Define a largura da coluna para 30
            worksheet.column_dimensions[column_cells[0].column_letter].width =30
            
    return output.getvalue()

def prepare_explodable_data(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
    """
    Prepara uma coluna "explodível", tratando strings de listas e removendo nulos,
    antes de expandir o DataFrame.
    """
    df_copy = df.copy()

    # 1. Substitui placeholders nulos por np.nan para facilitar a remoção
    df_copy[col_name] = df_copy[col_name].replace(config.NULLS_PLACEHOLDERS_TO_DROP, np.nan)
    df_processed = df_copy.dropna(subset=[col_name])

    if df_processed.empty:
        return pd.DataFrame(columns=df.columns)

    # 2. Converte strings que parecem listas (ex: "['a', 'b']") em objetos de lista
    series_to_analyze = df_processed[col_name]
    is_stringified_list = series_to_analyze.apply(
        lambda x: isinstance(x, str) and x.startswith('[') and x.endswith(']')
    ).any()

    if is_stringified_list:
        series_to_analyze = series_to_analyze.apply(
            lambda x: ast.literal_eval(x) if (isinstance(x, str) and x.startswith('[')) else x
        )
        df_processed[col_name] = series_to_analyze

    # 3. Explode o DataFrame e remove linhas onde a lista estava vazia
    df_exploded = df_processed.explode(col_name)
    return df_exploded.dropna(subset=[col_name])

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
    
    with st.expander("Colunas em exibição", expanded=False):
        selected_columns = st.multiselect(
            "Selecione as colunas a exibir na tabela geral abaixo:",
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
            on_click=state_manager.toggle_expanders_state, key="toggle_expand_aggregations")
        
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
                chart_data = agg_data.sort_values(by='Contagem', ascending=False)

                color_arg = col_agg if color_mode == "Multicolor" else None

                if chart_type == "Colunas":
                    # Para gráfico de colunas, simplesmente pegamos o top 15
                    chart_data = chart_data.head(15).sort_values(
                        by=sort_by_chart,
                        ascending=(sort_order_chart == "Crescente")
                    )                    
                    fig = _create_bar_chart(chart_data, col_agg, color_mode)

                else: # Circular
                    # Para pizza, consolidamos os itens menores em "Outros" para manter a proporção correta
                    if len(chart_data) > 15:
                        top_data = chart_data.head(14)
                        others_sum = chart_data.iloc[14:]['Contagem'].sum()
                        others_row = pd.DataFrame([{col_agg: 'Outros', 'Contagem': others_sum}])
                        chart_data = pd.concat([top_data, others_row], ignore_index=True)                    
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
    with st.expander("Adicionar NOVO Gráfico de Análise", expanded=True):
        available_cols = [col for col in df.select_dtypes(include=['object', 'category']).columns if col not in all_cols_to_render + [config.KEY_COLUMN_PRINCIPAL]]
        
        with st.form(key="add_aggregation_form"):
            add_col1, add_col2 = st.columns([0.8, 0.2], vertical_alignment="bottom")
            with add_col1:
                new_col_to_add = st.selectbox(
                    "Selecione uma nova coluna para analisar:", 
                    available_cols, 
                    key="new_agg_col_select",
                    disabled=not available_cols # Desabilita se não houver colunas
                )
            with add_col2:
                submitted = st.form_submit_button(
                    "➕ Adicionar", 
                    use_container_width=True,
                    disabled=not available_cols
                )
            
            if submitted and new_col_to_add:
                state_manager.add_extra_analysis('aggregation', {'col': new_col_to_add})
                st.rerun()

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

@st.cache_data
def calculate_dynamic_alerts(_df: pd.DataFrame, target_date: date) -> pd.DataFrame:
    """
    Calcula dinamicamente os alertas para um DataFrame com base em uma data-alvo.
    O resultado é CUMULATIVO: inclui tanto os casos que já tinham o alerta na
    data-base original quanto os que passarão a tê-lo na data-alvo.
    """
    df = _df.copy()
    target_datetime = pd.to_datetime(target_date)

    # Dicionário de Fórmulas. Mapeia o nome do alerta a uma função lambda que retorna uma máscara booleana.
    # As colunas usadas aqui devem ser as que existem no DataFrame FINAL (após renomeação).
    alert_formulas = {
        'NCV Pendente Parecer > 15 dias': lambda d: (d['Tipo'] == 'NCV') & (d['Situação'] == 'Aguardando Parecer') & ((target_datetime - d['Data Parecer']).dt.days > 15),
        'NC Pendente Parecer > 15 dias': lambda d: (d['Tipo'] == 'NC') & (d['Situação'] == 'Aguardando Parecer') & ((target_datetime - d['Data Cadastro']).dt.days > 15),
        'NC Pendente Instauração > 30 dias': lambda d: (d['Tipo'] == 'NC') & (d['Situação'] == 'Aguardando Instauração') & ((target_datetime - d['Data Parecer']).dt.days > 30),
        'CP Vencido > 10 dias': lambda d: (d['Tipo'] == 'CP') & ((target_datetime - d['Data Vencimento']).dt.days >= 11),
        'TC Vencido > 10 dias': lambda d: (d['Tipo'] == 'TC') & ((target_datetime - d['Data Vencimento']).dt.days >= 11),
        'RE Vencido > 10 dias': lambda d: (d['Tipo'] == 'RE') & ((target_datetime - d['Data Vencimento']).dt.days >= 11),
        'MP Vencido > 10 dias': lambda d: (d['Tipo'] == 'MP') & ((target_datetime - d['Data Vencimento']).dt.days >= 11),
        'NCV Vencido > 90 dias': lambda d: (d['Tipo'] == 'NCV') & ((target_datetime - d['Data Vencimento']).dt.days >= 91),
        'NC Vencido > 90 dias': lambda d: (d['Tipo'] == 'NC') & ((target_datetime - d['Data Vencimento']).dt.days >= 91),
        'IPL Vencido > 10 dias': lambda d: (d['Tipo'] == 'IPL') & ((target_datetime - d['Data Vencimento']).dt.days >= 11) & (~d['Situação'].isin(['Apreciação', 'Pedido de Baixa'])),
        'IPL Cota Duração > 1 ano': lambda d: (d['Tipo'] == 'IPL') & (d['Data Cota'] < (target_datetime - pd.DateOffset(years=1))), 
        'IPL Duração > 3 anos': lambda d: (d['Tipo'] == 'IPL') & (d['Data Instauração'] < (target_datetime - pd.DateOffset(years=3))),
        'IPL Duração > 5 anos': lambda d: (d['Tipo'] == 'IPL') & (d['Data Instauração'] < (target_datetime - pd.DateOffset(years=5))),
        'TC Duração > 90 dias': lambda d: (d['Tipo'] == 'TC') & (d['Data Instauração'] < (target_datetime - pd.DateOffset(days=90))),
    }
    
    # Inicializa a coluna de alertas simulados com listas vazias
    simulated_alerts_col = 'Alertas Simulados'
    df[simulated_alerts_col] = [[] for _ in range(len(df))]

    # Aplica cada fórmula e preenche a lista de alertas para as linhas correspondentes
    for alert_name, formula_func in alert_formulas.items():
        if alert_name == 'IPL Cota Duração > 1 ano' and 'Data Cota' not in df.columns:
            continue

        # Garante que a operação de data não falhe em colunas com NaT
        # Criamos a máscara apenas em dados não nulos para as colunas de data relevantes
        relevant_date_cols = [col for col in ['Data Parecer', 'Data Cadastro', 'Data Vencimento', 'Data Cota', 'Data Instauração'] if col in df.columns and formula_func.__code__.co_names.__contains__(col)]
        
        # Previne erro com colunas de data que possam estar ausentes
        if not all(col in df.columns for col in relevant_date_cols): continue
            
        subset = df.dropna(subset=relevant_date_cols)
        if not subset.empty:
            # 1. Identifica os casos que TERÃO o alerta na data-alvo (simulação)
            mask_futuro = formula_func(subset)
            indices_futuros = subset[mask_futuro].index

            # 2. Identifica os casos que JÁ TÊM o alerta na data-base original
            # A função `has_alert` lida com células que podem ser listas ou nulas
            def has_alert(alert_list):
                return isinstance(alert_list, list) and alert_name in alert_list
            
            mask_atual = df[config.COL_ALERTA].apply(has_alert)
            indices_atuais = df[mask_atual].index

            # 3. Combina os dois grupos de casos, removendo duplicatas
            # O método .union() de índices do Pandas é perfeito para isso
            indices_combinados = indices_atuais.union(indices_futuros)

            # 4. Atualiza a lista de alertas para todos os casos do grupo combinado
            if not indices_combinados.empty:
                df.loc[indices_combinados, simulated_alerts_col] = df.loc[indices_combinados, simulated_alerts_col].apply(lambda x: x + [alert_name])

    return df

def _render_aggregation_chart(
    is_simulation_mode: bool,
    df_alerted: pd.DataFrame, 
    df_universe: pd.DataFrame,
    group_by_col: str, 
    alert_col: str,
    key_suffix: str,
    title: str,
    filters: dict = None,
    opt_visualization: bool = True,
    secondary_group_by_col: str = None,
    secondary_group_by_label: str = None):    
    """Função reutilizável para renderizar os gráficos de agregação de alertas."""

    # --- 1. Pré-cálculo de dependências a partir do st.session_state ---
    # Isso permite reordenar os componentes visualmente, respeitando a lógica.
    person_filter_key = f"alert_filter_{key_suffix}_{group_by_col}"

    # --- 2. Controles de Visualização (Ordem Visual: 1) ---
    num_cols = len(filters) + 1 if opt_visualization else len(filters)
    filter_cols = st.columns(num_cols, vertical_alignment='top') if num_cols > 0 else []
    if secondary_group_by_col:
        num_cols += 1
        filter_cols = st.columns(num_cols, vertical_alignment='bottom', gap="large") if num_cols > 0 else []
    
    view_options = ["Contagem Absoluta"]
    if not is_simulation_mode:
        view_options.append("Visão Percentual")
    
    with filter_cols[-1]:
        if opt_visualization:
            view_type = st.radio("Visualização", view_options, key=f"view_{key_suffix}", horizontal=True)
        else:
            view_type = "Visualização"

    # Lógica para o checkbox de agrupamento secundário
    use_secondary = False
    if secondary_group_by_col:
        with filter_cols[1]: # 2ª Coluna para o checkbox; # TODO: verificar se prejudicará outros gráficos que não o 'alertas por '
            use_secondary = st.checkbox(secondary_group_by_label, key=f"toggle_secondary_group_{key_suffix}")
 
    current_group_by_col = secondary_group_by_col if use_secondary else group_by_col

    # --- 3. Filtros Específicos do Gráfico (Ordem Visual: 2) ---
    selected_filters = {}
    for i, (filter_name, filter_options) in enumerate(filters.items()):
        with filter_cols[i]:
            options = ["Todas"] + sorted(filter_options.dropna().unique().tolist())
            selected_filters[filter_name] = st.selectbox(f"Filtrar por {filter_name}", options, key=f"alert_filter_{key_suffix}_{filter_name}")

    # --- 4. KPIs e Denominador Dinâmico (Ordem Visual: 3) ---
    df_universe_filtered = df_universe.copy()
    for col, value in selected_filters.items():
        if value != "Todas" and col in df_universe_filtered.columns:
            df_universe_filtered = df_universe_filtered[df_universe_filtered[col] == value]

    # Aplica todos os filtros selecionados no gráfico ao dataframe de alertas
    df_filtered = df_alerted.copy()
    for col, value in selected_filters.items():
        if value != "Todas":
            df_filtered = df_filtered[df_filtered[col] == value]
 
    is_person_selected = (
        group_by_col in [config.COL_DELEGADO, config.COL_ESCRIVAO] and
        selected_filters.get(group_by_col, "Todas") != "Todas"
    )

    if is_person_selected:
        selected_person = selected_filters[group_by_col]
        
        kpi1, kpi2 = st.columns(2)
        # O KPI de total de alertas agora é calculado sobre o dataframe já filtrado
        total_alerts_person = df_filtered[config.KEY_COLUMN_PRINCIPAL].nunique()
        kpi1.metric(f"Total de Casos c/ Alertas ({selected_person})", f"{total_alerts_person:,}")        

        # O denominador para o KPI também deve ser dinâmico
        if not is_simulation_mode:
            # Filtra o universo para a pessoa E os outros filtros (ex: delegacia)
            total_cases_person = df_universe_filtered[config.KEY_COLUMN_PRINCIPAL].nunique()
            percent_alerted = (total_alerts_person / total_cases_person * 100) if total_cases_person > 0 else 0
            help_text = f"Calculado como: {total_alerts_person} (casos com alerta) / {total_cases_person} (casos totais do responsável)"
            kpi2.metric(f"% de Casos c/ Alerta ({selected_person})", f"{percent_alerted:.2f}%", help=help_text)
    
    # --- 5. Lógica de Agregação e Visualização Dinâmica ---
    if is_person_selected:
        effective_group_by_col = alert_col
        effective_title = f"Distribuição de Alertas para {selected_filters.get(current_group_by_col, '')}"
    else:
        effective_group_by_col = current_group_by_col
        effective_title = title.replace(group_by_col, current_group_by_col) # Título dinâmico
    
    if not df_filtered.empty:
        agg_data = df_filtered.groupby(effective_group_by_col)[config.KEY_COLUMN_PRINCIPAL].nunique().reset_index()
        agg_data.rename(columns={config.KEY_COLUMN_PRINCIPAL: 'Contagem'}, inplace=True)
    else:
        agg_data = pd.DataFrame(columns=[effective_group_by_col, 'Contagem'])

    # --- 6. Lógica de Cálculo e Ordenação ---
    y_col, text_col, y_title, sort_by_col = ('Contagem', 'Contagem', f"Nº de Casos por {effective_group_by_col}", 'Contagem')
    custom_data_cols = ['Contagem']
    hovertemplate = '<b>%{x}</b><br>Nº de Casos: %{y}<extra></extra>' # <extra> remove a caixa secundária do hover    
    
    if view_type == "Visão Percentual" and not is_simulation_mode:
        denominator = None
        if is_person_selected:
            # O denominador é o total de casos da pessoa selecionada, respeitando os outros filtros
            denominator = df_universe_filtered[config.KEY_COLUMN_PRINCIPAL].nunique()
        else:
            # Lógica anterior para os outros gráficos
            df_denominator_base = df_universe.copy()
            for f_col, f_val in selected_filters.items():
                if f_val != "Todas" and f_col != alert_col: # Ignora o filtro de alerta para o total
                    df_denominator_base = df_denominator_base[df_denominator_base[f_col] == f_val]

            if current_group_by_col == alert_col: # Gráfico de Tipos de Alerta
                denominator = df_denominator_base[config.KEY_COLUMN_PRINCIPAL].nunique()
            else: # Gráfico de Delegacia
                denominator = df_denominator_base.groupby(effective_group_by_col)[config.KEY_COLUMN_PRINCIPAL].nunique()

        if denominator is not None:
            if isinstance(denominator, pd.Series):
                agg_data = agg_data.merge(denominator.rename('Total Casos'), how='left', left_on=effective_group_by_col, right_index=True)
            elif isinstance(denominator, (int, float)):
                agg_data['Total Casos'] = denominator

        if 'Total Casos' in agg_data.columns:
            agg_data['Percentual'] = (agg_data['Contagem'] / agg_data['Total Casos'] * 100)
            y_col, text_col = ('Percentual', 'Percentual')
            # hover_data =  ['Contagem', 'Total Casos'],
            y_title, sort_by_col = (f"% de Casos com Alerta por {effective_group_by_col}", 'Percentual')
            custom_data_cols = ['Contagem', 'Total Casos']
            hovertemplate = '<b>%{x}</b><br>Percentual: %{y:.2f}%<br>Casos com Alerta: %{customdata[0]} de %{customdata[1]}<extra></extra>'            
    
    agg_data = agg_data.sort_values(by=sort_by_col, ascending=False).head(20)

    # --- 7. Renderização do Gráfico (Ordem Visual: 4) ---
    if not agg_data.empty:        
        fig = px.bar(
            agg_data, 
            x=effective_group_by_col, 
            y=y_col, 
            color=y_col, 
            color_continuous_scale=escala_azul_truncada, 
            # template = 'plotly_dark',
            text=text_col, # title=effective_title
            # hover_data=hover_data,
            custom_data=custom_data_cols,
            # labels={effective_group_by_col: effective_group_by_col} # y_col: y_title
            labels={effective_group_by_col: "", "Contagem": ""} # Remove os títulos dos eixos; ou usa fig.update_layout(xaxis_title=None, yaxis_title=None)
        )
        # Define o formato do texto com base na coluna que está sendo plotada
        text_template = '%{text:.2f}%' if y_col == 'Percentual' else '%{text}'
        fig.update_traces(texttemplate=text_template, textposition='auto', hovertemplate=hovertemplate)
        
        fig.update_layout( font=dict(size=14), hoverlabel=dict(font=dict(size=16)) )
        fig.update_layout(yaxis_title=None)

        st.plotly_chart(fig, use_container_width=True)

        # --- 8. Botão de Exportação ---
        excel_data = to_excel(df_filtered)
        st.download_button(
            label="📥 Exportar Dados Analíticos Filtrados (xlsx)",
            data=excel_data,
            file_name=f"{key_suffix}_casos_filtrados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_filtered_{key_suffix}",
            use_container_width=True
        )
    else:
        st.info("Nenhum dado para exibir com os filtros selecionados.")

def display_alerts_analysis_tab(df: pd.DataFrame):
    """Exibe a aba de Análise de Alertas e Simulações."""
    c1, c2 = st.columns([0.8, 0.2], vertical_alignment="center")
    with c1:
        st.header("Análise e Simulação de Alertas")
    with c2:
        st.button(
            "Recolher Tudo" if st.session_state.alerts_expanders_state else "Expandir Tudo",
            on_click=state_manager.toggle_alerts_expanders_state, key="toggle_expand_alerts")    

    # --- 1. Controle Principal (Seletor de Data) ---
    target_date = st.date_input(
        "Selecione a Data-Corte para Análise",
        value=config.DATA_CORTE_ORIGINAL,
        min_value=config.DATA_CORTE_ORIGINAL,
        help="Selecione a data original para análise ou uma data futura para simulação."
    )
    is_simulation_mode = target_date > config.DATA_CORTE_ORIGINAL

    # --- 2. Preparação dos Dados com base no modo ---
    denominator_data = {}
    if is_simulation_mode:
        st.info(f"Modo Simulação ativado para a data {target_date.strftime('%d/%m/%Y')}. Os cálculos de percentual e a análise de saneamentos estão desabilitados.")
        with st.spinner("Calculando alertas simulados..."):
            df_analysis = calculate_dynamic_alerts(df, target_date)
        alert_col = 'Alertas Simulados'
        df_analysis = df_analysis[df_analysis[alert_col].apply(len) > 0] # Filtra casos sem alertas simulados
    else:
        st.info(f"Modo Análise com dados de {config.DATA_CORTE_ORIGINAL.strftime('%d/%m/%Y')}.")
        df_analysis = df.copy()
        alert_col = config.COL_ALERTA
        # Prepara denominadores para cálculos de percentual
    
    # Prepara e explode o dataframe de análise, tratando strings de listas e removendo nulos.
    df_exploded = prepare_explodable_data(df_analysis, alert_col)

    st.divider()

    # --- 3. Renderização dos Gráficos em Expanders ---
    with st.expander("Cruzamento: Delegacia vs. Tipo de Alerta", expanded=st.session_state.alerts_expanders_state):
        if not df_exploded.empty:
            crosstab_df = pd.crosstab(df_exploded[alert_col], df_exploded[config.COL_DELEGACIA])
            fig = px.imshow(crosstab_df, text_auto=True, aspect="auto",
                            #labels=dict(x=f"<b>{config.COL_DELEGACIA}</b>", y=f"<b>{alert_col}</b>", color="Contagem"),
                            labels=dict(x="", y="", color="Contagem"),
                            color_continuous_scale=px.colors.sequential.Blues)
            fig.update_xaxes(side="top")
            fig.update_layout( font=dict(size=12), hoverlabel=dict(font=dict(size=16)) )
            st.plotly_chart(fig, use_container_width=True)
            
            excel_crosstab = to_excel(crosstab_df.reset_index())
            st.download_button("📥 Exportar Tabela Cruzada (xlsx)", excel_crosstab, "crosstab_alertas.xlsx", use_container_width=True)
        else:
            st.info("Nenhum alerta para exibir.")

    with st.expander("Análise por: TIPO ALERTA", expanded=st.session_state.alerts_expanders_state):
        _render_aggregation_chart(
            is_simulation_mode,
            df_alerted=df_exploded, df_universe=df, group_by_col=alert_col, alert_col=alert_col, key_suffix="tipo_alerta",
            title="Contagem de Casos por Tipo de Alerta",
            filters={config.COL_DELEGACIA: df[config.COL_DELEGACIA]}
        )

    with st.expander("Análise por: DELEGACIA / LOTAÇÃO", expanded=st.session_state.alerts_expanders_state):
        _render_aggregation_chart(
            is_simulation_mode,
            df_alerted=df_exploded, df_universe=df, group_by_col=config.COL_DELEGACIA, alert_col=alert_col, key_suffix="delegacia_lotacao",
            title=f"Contagem de Casos com Alerta por {config.COL_DELEGACIA}",
            filters={alert_col: df_exploded[alert_col]},
            secondary_group_by_col=config.COL_LOTACAO,
            secondary_group_by_label="Agrupar por Lotação"            
        )
    with st.expander("Análise por: DELEGADO(A)", expanded=st.session_state.alerts_expanders_state):
        _render_aggregation_chart(
            is_simulation_mode,
            df_alerted=df_exploded, df_universe=df, group_by_col=config.COL_DELEGADO, alert_col=alert_col, key_suffix="delegado",
            title="Contagem de Casos com Alerta por Delegado",
            filters={config.COL_DELEGACIA: df[config.COL_DELEGACIA], alert_col: df_exploded[alert_col], config.COL_DELEGADO: df[config.COL_DELEGADO]}
        )

    with st.expander("Análise por: ESCRIVÃO(Ã)", expanded=st.session_state.alerts_expanders_state):
        _render_aggregation_chart(
            is_simulation_mode,
            df_alerted=df_exploded, df_universe=df, group_by_col=config.COL_ESCRIVAO, alert_col=alert_col, key_suffix="escrivao",
            title="Contagem de Casos com Alerta por Escrivão",
            filters={config.COL_DELEGACIA: df[config.COL_DELEGACIA], alert_col: df_exploded[alert_col], config.COL_ESCRIVAO: df[config.COL_ESCRIVAO]},
        )

    if not is_simulation_mode:
        with st.expander("Análise por: TIPO SANEAMENTO", expanded=st.session_state.alerts_expanders_state):
            df_saneamento_exploded = prepare_explodable_data(df, config.COL_SANEAMENTO)
            _render_aggregation_chart(
                is_simulation_mode,
                df_alerted=df_saneamento_exploded, df_universe=df, group_by_col=config.COL_SANEAMENTO, alert_col=config.COL_SANEAMENTO, key_suffix="saneamento",
                title="Contagem de Casos por Tipo de Saneamento",
                filters={
                    config.COL_DELEGACIA: df[config.COL_DELEGACIA],
                    config.COL_DELEGADO: df[config.COL_DELEGADO],
                    config.COL_ESCRIVAO: df[config.COL_ESCRIVAO]
                },
                opt_visualization=False
            )

