import numpy as np
import pandas as pd
import streamlit as st

from data_processing import (
    apply_column_types,
    create_info_dataframe,
    detect_column_types,
    print_dataframe_info,
    read_dataframe,
    sanitize_for_streamlit,
)

# Variáveis hardcoded:
start_file = "C:\\Users\\edson.eab\\Downloads\\Casos_SRSP_16-09-2025-Filtrado.parquet"
placeholders_to_drop = ['-', '', 'None', '<NA>', 'nan', 'undefined']

filter_cols = ['Proc. Tipo', 'Proc. Situação', 'Situação Sigla', 'Proc. Delegacia'] # TODO: Na verdade, todas colunas devem ser filtro, em vez desta lista apenas.

area_cols = [
    'Proc. Tipo Documento', 'Proc. Origem Documento', 
    'Proc. Área de Atribuição', 'Proc. Tipo Penal', 
    'Proc. Incidência Penal Principal',
    'Proc. Tratamento Especial', 'Matéria Registro Especial'
]

coluna_com_listas = 'Proc. Tipo Penal'

# ---

# Configuração da página Streamlit
st.set_page_config(page_title="Visualizador de Dados", layout="wide")
st.title("🔍 Visualizador de Dados")
st.markdown("Suporta arquivos: .parquet, .pkl, .pickle, .csv, .xlsx")

# Campo para inserir o caminho do arquivo
file_path = st.text_input(
    "📁 Digite o caminho do arquivo:",
    value=start_file,
    help="Caminho completo para o arquivo de dados",
)

# Inicializar session state
if "df_original" not in st.session_state:
    st.session_state["df_original"] = None
if "column_info" not in st.session_state:
    st.session_state["column_info"] = None
if "file_loaded" not in st.session_state:
    st.session_state["file_loaded"] = False
if "types_configured" not in st.session_state:
    st.session_state["types_configured"] = False
if "df_final" not in st.session_state:
    st.session_state["df_final"] = None

# Botão para carregar arquivo
if st.button("📥 Carregar Arquivo"):
    with st.spinner("Carregando arquivo..."):
        df_original = read_dataframe(file_path)

        if df_original is not None:
            st.session_state["df_original"] = df_original
            st.session_state["file_loaded"] = True
            st.session_state["types_configured"] = False  # Reset configuração de tipos
            st.success(f"✅ Arquivo carregado! Dimensões: {df_original.shape}")

            # Analisar tipos de colunas
            with st.spinner("Analisando tipos de dados..."):
                column_info = detect_column_types(df_original)
                st.session_state["column_info"] = column_info

            st.rerun()

# Se os tipos foram configurados, mostrar os dados
if st.session_state["types_configured"] and st.session_state["df_final"] is not None:
    df_original = st.session_state["df_original"]
    df_final = st.session_state["df_final"]

    st.markdown("---")

    # Usar rich para imprimir informações detalhadas no terminal
    print_dataframe_info(df_final)

    # Criando abas para melhor organização
    tab2, tab3, tab4, tab1, tab5 = st.tabs(
        ["🔍 Amostra dos Dados", "📈 Estatísticas", "ℹ️ Info das Colunas", "📊 Visão Geral", "🗂️ Análise por Área"]
    )

    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Linhas", f"{df_final.shape[0]:,}")
        with col2:
            st.metric("Colunas", df_final.shape[1])
        with col3:
            st.metric("Memória (MB)", f"{df_final.memory_usage().sum() / 1024**2:.2f}")

        st.markdown("### 📋 Tipos de Dados Finais")
        dtype_counts = df_final.dtypes.value_counts()
        
        # O índice de dtype_counts contém objetos de tipo (ex: dtype('int64')),
        # que não são serializáveis pelo Arrow. Convertê-los para string resolve.
        dtype_counts.index = dtype_counts.index.map(str)
        st.bar_chart(dtype_counts)

        # Comparação antes/depois
        st.markdown("### 🔄 Comparação de Tipos")
        comparison_data = []
        for col in df_final.columns:
            comparison_data.append(
                {
                    "Coluna": col,
                    "Tipo Original": str(df_original[col].dtype),
                    "Tipo Final": str(df_final[col].dtype),
                    "Mudou": "✅"
                    if str(df_original[col].dtype) != str(df_final[col].dtype)
                    else "➖",
                }
            )

        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(sanitize_for_streamlit(comparison_df))

        # Botão para reconfigurar tipos
        if st.button("⚙️ Reconfigurar Tipos de Dados"):
            st.session_state["types_configured"] = False
            st.rerun()

    with tab2:
        st.markdown("### 📥 Filtros e Amostra dos Dados")
        
        # DataFrame a ser filtrado
        filtered_df = df_final.copy()
        
        # Seção de filtros
        with st.expander("🔍 Aplicar Filtros"):
            selections = {}

            for col_name in filter_cols:
                if col_name in filtered_df.columns:
                    options = sorted(filtered_df[col_name].dropna().unique())
                    selections[col_name] = st.multiselect(
                        f"Filtrar por **{col_name}**:",
                        options=options,
                        default=[]
                    )
        
            # Aplicar filtros
            for col_name, selected_values in selections.items():
                if selected_values:
                    filtered_df = filtered_df[filtered_df[col_name].isin(selected_values)]

        # Exibir métrica de resultados
        st.info(f"Mostrando **{len(filtered_df):,}** de **{len(df_final):,}** registros.")
                
        st.markdown("### Primeiras linhas do DataFrame:")
        try:
            display_df = filtered_df.head(100)
            if len(filtered_df.columns) > 30:
                st.warning(
                    f"Exibindo apenas as primeiras 30 colunas de {len(filtered_df.columns)} total."
                )
                display_df = display_df.iloc[:, :30]

            st.dataframe(sanitize_for_streamlit(display_df))
        except Exception as e:
            st.error(f"Erro ao exibir dados: {str(e)}")
            st.markdown("**Tentativa alternativa - Informações básicas:**")
            for col in filtered_df.columns[:5]:
                st.write(
                    f"**{col}**: {filtered_df[col].dtype} - Exemplo: {filtered_df[col].iloc[0] if len(filtered_df) > 0 else 'N/A'}"
                )

        # Opções avançadas apenas nesta aba
        with st.expander("🔧 Opções Avançadas"):
            st.markdown("### 🎛️ Filtros e Visualizações")

            selected_columns = st.multiselect(
                "Selecione colunas específicas para visualizar:",
                options=list(filtered_df.columns),
                default=list(filtered_df.columns[:5])
                if len(filtered_df.columns) >= 5
                else list(filtered_df.columns),
            )

            if selected_columns:
                st.markdown(
                    f"### 📋 Dados das Colunas Selecionadas ({len(selected_columns)} colunas):"
                )
                try:
                    st.dataframe(sanitize_for_streamlit(filtered_df[selected_columns].head(100)))
                except Exception as e:
                    st.error(f"Erro ao exibir colunas selecionadas: {str(e)}")

            # Download dos dados processados
            st.markdown("### 💾 Download")
            col1, col2 = st.columns(2)

            with col1:
                if st.button("📥 Baixar como CSV"):
                    try:
                        csv = filtered_df.to_csv(index=False)
                        st.download_button(
                            label="⬇️ Download CSV",
                            data=csv,
                            file_name="dados_processados.csv",
                            mime="text/csv",
                        )
                        st.success("CSV preparado para download!")
                    except Exception as e:
                        st.error(f"Erro ao preparar CSV: {str(e)}")

            with col2:
                if st.button("📥 Baixar como Parquet"):
                    try:
                        # Converter para parquet em bytes
                        parquet_buffer = filtered_df.to_parquet(index=False)
                        st.download_button(
                            label="⬇️ Download Parquet",
                            data=parquet_buffer,
                            file_name="dados_processados.parquet",
                            mime="application/octet-stream",
                        )
                        st.success("Parquet preparado para download!")
                    except Exception as e:
                        st.error(f"Erro ao preparar Parquet: {str(e)}")

    with tab3:
        st.markdown("### 📊 Estatísticas básicas:")
        try:
            numeric_cols = df_final.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                stats_df = df_final[numeric_cols].describe()

                st.dataframe(sanitize_for_streamlit(stats_df))

                # Estatísticas adicionais
                st.markdown("### 📈 Informações Numéricas Adicionais")
                for col in numeric_cols[:5]:  # Limitar a 5 colunas
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric(f"{col} - Média", f"{df_final[col].mean():.2f}")
                    with col2:
                        st.metric(f"{col} - Mediana", f"{df_final[col].median():.2f}")
                    with col3:
                        st.metric(f"{col} - Mín", f"{df_final[col].min():.2f}")
                    with col4:
                        st.metric(f"{col} - Máx", f"{df_final[col].max():.2f}")
            else:
                st.info("Nenhuma coluna numérica encontrada para estatísticas.")

            # Estatísticas para colunas datetime
            datetime_cols = df_final.select_dtypes(include=["datetime64"]).columns
            if len(datetime_cols) > 0:
                st.markdown("### 📅 Informações de Data/Hora")
                for col in datetime_cols:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            f"{col} - Mais Antiga",
                            str(df_final[col].min().date())
                            if pd.notna(df_final[col].min())
                            else "N/A",
                        )
                    with col2:
                        st.metric(
                            f"{col} - Mais Recente",
                            str(df_final[col].max().date())
                            if pd.notna(df_final[col].max())
                            else "N/A",
                        )

        except Exception as e:
            st.error(f"Erro ao calcular estatísticas: {str(e)}")

    with tab4:
        st.markdown("### ℹ️ Informações das Colunas:")
        try:
            info_df = create_info_dataframe(df_final)
            st.dataframe(sanitize_for_streamlit(info_df))
        except Exception as e:
            st.error(f"Erro ao criar tabela de informações: {str(e)}")
            st.markdown("**Informações básicas das colunas:**")
            for i, col in enumerate(df_final.columns):
                if i < 10:
                    st.write(
                        f"- **{col}**: {str(df_final[col].dtype)} | Nulos: {df_final[col].isna().sum()}"
                    )
                elif i == 10:
                    st.write(f"... e mais {len(df_final.columns) - 10} colunas")

    with tab5:
        st.markdown("### 🗂️ Análise por Área Associada")
        st.markdown("Distribuição de valores para colunas relacionadas à área.")

        for col_name in area_cols:
            if col_name in df_final.columns:
                st.markdown(f"---")
                st.markdown(f"#### Distribuição por: `{col_name}`")                

                # Cria uma cópia da série para análise
                series_to_analyze = df_final[col_name].copy()

                # Lógica especial para se contiver listas (ou strings de listas)
                if col_name == coluna_com_listas:
                    # Converte strings que parecem listas de volta para listas
                    # Isso corrige o problema se o tipo foi configurado como string
                    is_stringified_list = series_to_analyze.dropna().apply(
                        lambda x: isinstance(x, str) and x.startswith('[') and x.endswith(']')
                    ).any()

                    if is_stringified_list:
                        import ast
                        st.info("Detectamos strings de listas e as convertemos para análise.")
                        series_to_analyze = series_to_analyze.apply(
                            lambda x: ast.literal_eval(x) if (isinstance(x, str) and x.startswith('[')) else x
                        )

                    # Verifica se a coluna agora contém listas e a "explode"
                    if series_to_analyze.dropna().apply(isinstance, args=(list,)).any():
                        st.info("Esta coluna foi 'explodida' para contar cada tipo penal individualmente.")
                        series_to_analyze = series_to_analyze.explode()

                # Calcula a contagem de valores
                value_counts = series_to_analyze.value_counts().reset_index()
                value_counts.columns = [col_name, 'Contagem']

                # Para o gráfico, usamos nomes de coluna genéricos e consistentes
                # para evitar que o Streamlit se confunda em cada iteração do loop.
                chart_data = value_counts.copy()
                chart_data.columns = ['Categoria', 'Contagem']

                # Prepara dados para o gráfico, removendo valores nulos/placeholders comuns
                chart_data['Categoria'] = chart_data['Categoria'].astype(str) # Garante que tudo é string para comparação
                chart_data = chart_data[~chart_data['Categoria'].isin(placeholders_to_drop)]

                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown("**Contagem Total (incluindo nulos)**")
                    st.dataframe(value_counts)
                with col2:
                    st.markdown("**Top 15 Valores Válidos**")
                    st.bar_chart(chart_data.head(15), x='Categoria', y='Contagem')
            else:
                st.warning(f"A coluna '{col_name}' não foi encontrada no DataFrame.")

# Se o arquivo foi carregado, mas os tipos não configurados, mostrar a tela de configuração
elif st.session_state["file_loaded"]:
    st.markdown("---")
    st.subheader("⚙️ Configuração de Tipos de Dados")
    st.markdown("Configure como cada coluna deve ser tratada:")

    column_info = st.session_state["column_info"]
    df_original = st.session_state["df_original"]

    # Criar formulário para configuração de tipos
    with st.form("column_types_form"):
        type_mapping = {}

        # Criar colunas para o layout
        cols_per_row = 1
        columns = list(column_info.keys())

        for i in range(0, len(columns), cols_per_row):
            row_cols = st.columns(cols_per_row)

            for j, col_name in enumerate(columns[i : i + cols_per_row]):
                if j < len(row_cols):
                    with row_cols[j]:
                        info = column_info[col_name]

                        # Criar sugestão baseada na análise
                        if info["can_be_numeric"] and info["numeric_success_rate"] > 90:
                            suggested = "numeric"
                        elif (
                            info["can_be_datetime"]
                            and info["datetime_success_rate"] > 90
                        ):
                            suggested = "datetime"
                        else:
                            suggested = "string"

                        # Informações da coluna
                        st.markdown(f"**{col_name}**")
                        st.caption(
                            f"Tipo atual: {info['original_dtype']} | "
                            f"Nulos: {info['null_count']} | "
                            f"Únicos: {info['unique_count']}"
                        )

                        if info["sample_values"]:
                            st.caption(
                                f"Amostras: {', '.join(info['sample_values'][:3])}"
                            )

                        # Mostrar taxas de sucesso se relevantes
                        if info["numeric_success_rate"] > 0:
                            st.caption(
                                f"🔢 Numérico: {info['numeric_success_rate']:.1f}% sucesso"
                            )
                        if info["datetime_success_rate"] > 0:
                            st.caption(
                                f"📅 Data: {info['datetime_success_rate']:.1f}% sucesso"
                            )

                        # Seletor de tipo
                        type_options = ["string", "numeric", "datetime", "boolean"]
                        selected_type = st.selectbox(
                            f"Tipo para {col_name}:",
                            options=type_options,
                            index=type_options.index(suggested),
                            key=f"type_{col_name}",
                            label_visibility="collapsed",
                        )

                        type_mapping[col_name] = selected_type
                        st.markdown("---")

        # Botões do formulário no fim da view
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            apply_types = st.form_submit_button("✅ Aplicar Tipos")
        with col2:
            auto_detect = st.form_submit_button("🤖 Auto-detectar")
        with col3:
            all_string = st.form_submit_button("📝 Tudo como String")

    # Processar escolha do usuário
    if apply_types:
        with st.spinner("Aplicando tipos de dados..."):
            df_final, conversion_log = apply_column_types(df_original, type_mapping)
            st.session_state["df_final"] = df_final
            st.session_state["types_configured"] = True
            
            # Mostrar log de conversão
            st.success("✅ Tipos aplicados com sucesso!")
            with st.expander("📋 Log de Conversões"):
                for log_entry in conversion_log:
                    st.write(log_entry)

        st.rerun()

    elif auto_detect:
        # Auto-detectar baseado nas taxas de sucesso
        auto_mapping = {}
        for col_name, info in column_info.items():
            if info["can_be_numeric"] and info["numeric_success_rate"] > 80:
                auto_mapping[col_name] = "numeric"
            elif info["can_be_datetime"] and info["datetime_success_rate"] > 80:
                auto_mapping[col_name] = "datetime"
            else:
                auto_mapping[col_name] = "string"

        with st.spinner("Aplicando detecção automática..."):
            df_final, conversion_log = apply_column_types(df_original, auto_mapping)
            st.session_state["df_final"] = df_final
            st.session_state["types_configured"] = True

            st.success("✅ Detecção automática aplicada!")
            with st.expander("📋 Log de Conversões"):
                for log_entry in conversion_log:
                    st.write(log_entry)

        st.rerun()

    elif all_string:
        # Converter tudo para string
        string_mapping = {col: "string" for col in column_info.keys()}

        with st.spinner("Convertendo tudo para string..."):
            df_final, conversion_log = apply_column_types(df_original, string_mapping)
            st.session_state["df_final"] = df_final
            st.session_state["types_configured"] = True

            st.success("✅ Todas as colunas convertidas para string!")

        st.rerun()

# Tela inicial
else:
    st.info("👆 Digite o caminho do arquivo acima e clique em 'Carregar Arquivo' para começar.")

    st.markdown(
        """
        ### 📋 Formatos Suportados:
        - **Parquet** (.parquet) - Recomendado para grandes datasets
        - **Pickle** (.pkl, .pck, .pickle) - Preserva tipos Python
        - **CSV** (.csv) - Formato universal
        - **Excel** (.xlsx) - Planilhas Microsoft
        
        ### Recursos:
        - 🎯 **Configuração interativa de tipos** - Você escolhe como tratar cada coluna
        - 🤖 **Detecção automática inteligente** - Sugestões baseadas em análise estatística  
        - 📊 **Visualização compatível** com Arrow/Streamlit
        - 🖥️ **Informações detalhadas** no terminal via Rich
        - 📈 **Estatísticas abrangentes** incluindo dados temporais
        - 🔧 **Interface organizada** em abas com opções avançadas
        - 💾 **Download** em CSV e Parquet
        - 🔄 **Comparação antes/depois** da configuração de tipos
        
        ### Como Usar:
        1. **Carregue** seu arquivo usando o botão acima
        2. **Configure** os tipos de cada coluna conforme sua necessidade
        3. **Explore** os dados nas diferentes abas
        4. **Baixe** os dados processados quando necessário
        """
    )