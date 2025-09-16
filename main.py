import pandas as pd
import streamlit as st
from rich import print as rprint
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
from typing import Optional, Union, Dict, List
import os
import numpy as np

def read_dataframe(file_path: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Lê um arquivo de dados em vários formatos e retorna um DataFrame do pandas.
    
    Args:
        file_path (str, optional): Caminho do arquivo. Se None, solicita input do usuário.
        
    Returns:
        pd.DataFrame: DataFrame contendo os dados do arquivo ou None se houver erro
    """
    if file_path is None:
        file_path = input("Digite o caminho completo do arquivo: ").strip()
    
    if not os.path.exists(file_path):
        rprint("[red]Erro: Arquivo não encontrado![/red]")
        return None
    
    file_extension = Path(file_path).suffix.lower()
    
    try:
        df = None
        if file_extension == '.parquet':
            df = pd.read_parquet(file_path)
        elif file_extension in ('.pkl', '.pck') or file_extension == '.pickle':
            df = pd.read_pickle(file_path)
        elif file_extension == '.csv':
            df = pd.read_csv(file_path)
        elif file_extension == '.xlsx':
            df = pd.read_excel(file_path)
        else:
            rprint(f"[yellow]Formato de arquivo não suportado: {file_extension}[/yellow]")
            rprint("[yellow]Formatos suportados: .parquet, .pkl, .pickle, .csv, .xlsx[/yellow]")
            return None
        
        return df
    
    except Exception as e:
        rprint(f"[red]Erro ao ler o arquivo: {str(e)}[/red]")
        return None

def detect_column_types(df: pd.DataFrame) -> Dict[str, Dict]:
    """
    Detecta possíveis tipos para cada coluna e fornece estatísticas.
    
    Args:
        df (pd.DataFrame): DataFrame para análise
        
    Returns:
        Dict: Informações sobre cada coluna
    """
    column_info = {}
    
    for col in df.columns:
        info = {
            'original_dtype': str(df[col].dtype),
            'null_count': df[col].isna().sum(),
            'null_percent': (df[col].isna().sum() / len(df)) * 100,
            'unique_count': df[col].nunique(),
            'sample_values': [],
            'can_be_numeric': False,
            'can_be_datetime': False,
            'numeric_success_rate': 0,
            'datetime_success_rate': 0
        }
        
        # Pegar amostra de valores não-nulos
        non_null_values = df[col].dropna()
        if len(non_null_values) > 0:
            sample_size = min(5, len(non_null_values))
            info['sample_values'] = [str(x) for x in non_null_values.head(sample_size).tolist()]
        
        # Testar conversão numérica
        if len(non_null_values) > 0:
            try:
                numeric_converted = pd.to_numeric(non_null_values, errors='coerce')
                numeric_success = numeric_converted.notna().sum()
                info['numeric_success_rate'] = (numeric_success / len(non_null_values)) * 100
                info['can_be_numeric'] = info['numeric_success_rate'] > 70  # 70% de sucesso
            except:
                pass
        
        # Testar conversão datetime (apenas se não for muito numérica)
        if len(non_null_values) > 0 and info['numeric_success_rate'] < 50:
            try:
                # Tentar apenas uma amostra para evitar warnings excessivos
                sample_for_date = non_null_values.head(min(100, len(non_null_values)))
                datetime_converted = pd.to_datetime(sample_for_date, errors='coerce')
                datetime_success = datetime_converted.notna().sum()
                info['datetime_success_rate'] = (datetime_success / len(sample_for_date)) * 100
                info['can_be_datetime'] = info['datetime_success_rate'] > 70  # 70% de sucesso
            except:
                pass
        
        column_info[col] = info
    
    return column_info

def apply_column_types(df: pd.DataFrame, type_mapping: Dict[str, str]) -> pd.DataFrame:
    """
    Aplica os tipos de dados especificados pelo usuário.
    
    Args:
        df (pd.DataFrame): DataFrame original
        type_mapping (Dict[str, str]): Mapeamento coluna -> tipo desejado
        
    Returns:
        pd.DataFrame: DataFrame com tipos aplicados
    """
    df_typed = df.copy()
    
    # Reset do índice para evitar problemas
    df_typed = df_typed.reset_index(drop=True)
    
    conversion_log = []
    
    for col, target_type in type_mapping.items():
        if col not in df_typed.columns:
            continue
            
        try:
            original_nulls = df_typed[col].isna().sum()
            
            if target_type == 'string':
                df_typed[col] = df_typed[col].fillna('').astype(str).astype('string')
                conversion_log.append(f"✅ {col}: convertido para string")
                
            elif target_type == 'numeric':
                df_typed[col] = pd.to_numeric(df_typed[col], errors='coerce')
                new_nulls = df_typed[col].isna().sum()
                lost_values = new_nulls - original_nulls
                if lost_values > 0:
                    conversion_log.append(f"⚠️ {col}: convertido para numérico ({lost_values} valores perdidos)")
                else:
                    conversion_log.append(f"✅ {col}: convertido para numérico")
                    
            elif target_type == 'datetime':
                df_typed[col] = pd.to_datetime(df_typed[col], errors='coerce')
                new_nulls = df_typed[col].isna().sum()
                lost_values = new_nulls - original_nulls
                if lost_values > 0:
                    conversion_log.append(f"⚠️ {col}: convertido para datetime ({lost_values} valores perdidos)")
                else:
                    conversion_log.append(f"✅ {col}: convertido para datetime")
                    
            elif target_type == 'boolean':
                # Tentar conversão inteligente para boolean
                bool_map = {'true': True, 'false': False, '1': True, '0': False, 
                           'yes': True, 'no': False, 'sim': True, 'nao': False}
                df_typed[col] = df_typed[col].astype(str).str.lower().map(bool_map)
                df_typed[col] = df_typed[col].astype('boolean')
                conversion_log.append(f"✅ {col}: convertido para boolean")
                
        except Exception as e:
            # Em caso de erro, manter como string
            df_typed[col] = df_typed[col].fillna('').astype(str).astype('string')
            conversion_log.append(f"❌ {col}: erro na conversão, mantido como string - {str(e)}")
    
    return df_typed, conversion_log

def print_dataframe_info(df: pd.DataFrame) -> None:
    """
    Imprime informações detalhadas sobre o DataFrame usando rich.
    
    Args:
        df (pd.DataFrame): DataFrame para análise
    """
    info_text = f"""
    [bold cyan]Informações do DataFrame:[/bold cyan]
    • Dimensões (linhas, colunas): {df.shape}
    • Total de elementos: {df.size}
    • Memória utilizada: {df.memory_usage().sum() / 1024**2:.2f} MB
    """
    rprint(Panel(info_text, title="DataFrame Info", border_style="cyan"))
    
    table = Table(title="Detalhes das Colunas")
    table.add_column("Nome da Coluna", style="cyan")
    table.add_column("Tipo de Dado", style="magenta")
    table.add_column("Valores Nulos", style="yellow")
    table.add_column("Valores Únicos", style="green")
    
    for col in df.columns:
        n_unique = df[col].nunique()
        null_count = df[col].isna().sum()
        null_percent = (null_count/len(df))*100 if len(df) > 0 else 0
        
        table.add_row(
            str(col),
            str(df[col].dtype),
            f"{null_count} ({null_percent:.1f}%)",
            str(n_unique)
        )
    
    rprint(table)

def create_info_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria um DataFrame com informações sobre as colunas que é compatível com Streamlit.
    """
    info_data = []
    for col in df.columns:
        null_count = df[col].isna().sum()
        null_percent = (null_count/len(df))*100 if len(df) > 0 else 0
        unique_count = df[col].nunique()
        
        info_data.append({
            'Coluna': str(col),
            'Tipo': str(df[col].dtype),
            'Valores Nulos': f"{null_count} ({null_percent:.1f}%)",
            'Valores Únicos': unique_count
        })
    
    return pd.DataFrame(info_data)

# Configuração da página Streamlit
st.set_page_config(page_title="Visualizador de Dados", layout="wide")
st.title("🔍 Visualizador de Dados")
st.markdown("Suporta arquivos: .parquet, .pkl, .pickle, .csv, .xlsx")

# Campo para inserir o caminho do arquivo
file_path = st.text_input(
    "📁 Digite o caminho do arquivo:", 
    value="C:\\Users\\edson.eab\\Downloads\\df_bi_only_procs.parquet",
    help="Caminho completo para o arquivo de dados"
)

# Inicializar session state
if 'df_original' not in st.session_state:
    st.session_state['df_original'] = None
if 'column_info' not in st.session_state:
    st.session_state['column_info'] = None
if 'file_loaded' not in st.session_state:
    st.session_state['file_loaded'] = False
if 'types_configured' not in st.session_state:
    st.session_state['types_configured'] = False
if 'df_final' not in st.session_state:
    st.session_state['df_final'] = None

# Botão para carregar arquivo
if st.button("📥 Carregar Arquivo"):
    with st.spinner("Carregando arquivo..."):
        df_original = read_dataframe(file_path)
        
        if df_original is not None:
            st.session_state['df_original'] = df_original
            st.session_state['file_loaded'] = True
            st.session_state['types_configured'] = False  # Reset configuração de tipos
            st.success(f"✅ Arquivo carregado! Dimensões: {df_original.shape}")
            
            # Analisar tipos de colunas
            with st.spinner("Analisando tipos de dados..."):
                column_info = detect_column_types(df_original)
                st.session_state['column_info'] = column_info
            
            st.rerun()

# Se arquivo foi carregado, mostrar configuração de tipos
if st.session_state['file_loaded'] and not st.session_state['types_configured']:
    st.markdown("---")
    st.subheader("⚙️ Configuração de Tipos de Dados")
    st.markdown("Configure como cada coluna deve ser tratada:")
    
    column_info = st.session_state['column_info']
    df_original = st.session_state['df_original']
    
    # Criar formulário para configuração de tipos
    with st.form("column_types_form"):
        type_mapping = {}
        
        # Criar colunas para o layout
        cols_per_row = 1
        columns = list(column_info.keys())
        
        for i in range(0, len(columns), cols_per_row):
            row_cols = st.columns(cols_per_row)
            
            for j, col_name in enumerate(columns[i:i+cols_per_row]):
                if j < len(row_cols):
                    with row_cols[j]:
                        info = column_info[col_name]
                        
                        # Criar sugestão baseada na análise
                        if info['can_be_numeric'] and info['numeric_success_rate'] > 90:
                            suggested = 'numeric'
                        elif info['can_be_datetime'] and info['datetime_success_rate'] > 90:
                            suggested = 'datetime'
                        else:
                            suggested = 'string'
                        
                        # Informações da coluna
                        st.markdown(f"**{col_name}**")
                        st.caption(f"Tipo atual: {info['original_dtype']} | "
                                 f"Nulos: {info['null_count']} | "
                                 f"Únicos: {info['unique_count']}")
                        
                        if info['sample_values']:
                            st.caption(f"Amostras: {', '.join(info['sample_values'][:3])}")
                        
                        # Mostrar taxas de sucesso se relevantes
                        if info['numeric_success_rate'] > 0:
                            st.caption(f"🔢 Numérico: {info['numeric_success_rate']:.1f}% sucesso")
                        if info['datetime_success_rate'] > 0:
                            st.caption(f"📅 Data: {info['datetime_success_rate']:.1f}% sucesso")
                        
                        # Seletor de tipo
                        type_options = ['string', 'numeric', 'datetime', 'boolean']
                        selected_type = st.selectbox(
                            f"Tipo para {col_name}:",
                            options=type_options,
                            index=type_options.index(suggested),
                            key=f"type_{col_name}",
                            label_visibility="collapsed"
                        )
                        
                        type_mapping[col_name] = selected_type
                        st.markdown("---")
        
        # Botões do formulário
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
            st.session_state['df_final'] = df_final
            st.session_state['types_configured'] = True
            
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
            if info['can_be_numeric'] and info['numeric_success_rate'] > 80:
                auto_mapping[col_name] = 'numeric'
            elif info['can_be_datetime'] and info['datetime_success_rate'] > 80:
                auto_mapping[col_name] = 'datetime'
            else:
                auto_mapping[col_name] = 'string'
        
        with st.spinner("Aplicando detecção automática..."):
            df_final, conversion_log = apply_column_types(df_original, auto_mapping)
            st.session_state['df_final'] = df_final
            st.session_state['types_configured'] = True
            
            st.success("✅ Detecção automática aplicada!")
            with st.expander("📋 Log de Conversões"):
                for log_entry in conversion_log:
                    st.write(log_entry)
        
        st.rerun()
    
    elif all_string:
        # Converter tudo para string
        string_mapping = {col: 'string' for col in column_info.keys()}
        
        with st.spinner("Convertendo tudo para string..."):
            df_final, conversion_log = apply_column_types(df_original, string_mapping)
            st.session_state['df_final'] = df_final
            st.session_state['types_configured'] = True
            
            st.success("✅ Todas as colunas convertidas para string!")
        
        st.rerun()

# Se os tipos foram configurados, mostrar os dados
if st.session_state['types_configured'] and st.session_state['df_final'] is not None:
    df_original = st.session_state['df_original']
    df_final = st.session_state['df_final']
    
    st.markdown("---")
    
    # Usar rich para imprimir informações detalhadas no terminal
    print_dataframe_info(df_final)
    
    # Criando abas para melhor organização
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Visão Geral", "🔍 Amostra dos Dados", "📈 Estatísticas", "ℹ️ Info das Colunas"])
    
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
        st.bar_chart(dtype_counts)
        
        # Comparação antes/depois
        st.markdown("### 🔄 Comparação de Tipos")
        comparison_data = []
        for col in df_final.columns:
            comparison_data.append({
                'Coluna': col,
                'Tipo Original': str(df_original[col].dtype),
                'Tipo Final': str(df_final[col].dtype),
                'Mudou': '✅' if str(df_original[col].dtype) != str(df_final[col].dtype) else '➖'
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, width='stretch')
        
        # Botão para reconfigurar tipos
        if st.button("⚙️ Reconfigurar Tipos de Dados"):
            st.session_state['types_configured'] = False
            st.rerun()
            
    with tab2:
        st.markdown("### Primeiras linhas do DataFrame:")
        try:
            display_df = df_final.head(100)
            if len(df_final.columns) > 20:
                st.warning(f"Exibindo apenas as primeiras 20 colunas de {len(df_final.columns)} total.")
                display_df = display_df.iloc[:, :20]
            
            st.dataframe(display_df, width='stretch')
        except Exception as e:
            st.error(f"Erro ao exibir dados: {str(e)}")
            st.markdown("**Tentativa alternativa - Informações básicas:**")
            for col in df_final.columns[:5]:
                st.write(f"**{col}**: {df_final[col].dtype} - Exemplo: {df_final[col].iloc[0] if len(df_final) > 0 else 'N/A'}")
        
        # Opções avançadas apenas nesta aba
        with st.expander("🔧 Opções Avançadas"):
            st.markdown("### 🎛️ Filtros e Visualizações")
            
            selected_columns = st.multiselect(
                "Selecione colunas específicas para visualizar:",
                options=list(df_final.columns),
                default=list(df_final.columns[:5]) if len(df_final.columns) >= 5 else list(df_final.columns)
            )
            
            if selected_columns:
                st.markdown(f"### 📋 Dados das Colunas Selecionadas ({len(selected_columns)} colunas):")
                try:
                    st.dataframe(df_final[selected_columns].head(100), width='stretch')
                except Exception as e:
                    st.error(f"Erro ao exibir colunas selecionadas: {str(e)}")
            
            # Download dos dados processados
            st.markdown("### 💾 Download")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📥 Baixar como CSV"):
                    try:
                        csv = df_final.to_csv(index=False)
                        st.download_button(
                            label="⬇️ Download CSV",
                            data=csv,
                            file_name="dados_processados.csv",
                            mime="text/csv"
                        )
                        st.success("CSV preparado para download!")
                    except Exception as e:
                        st.error(f"Erro ao preparar CSV: {str(e)}")
            
            with col2:
                if st.button("📥 Baixar como Parquet"):
                    try:
                        # Converter para parquet em bytes
                        parquet_buffer = df_final.to_parquet(index=False)
                        st.download_button(
                            label="⬇️ Download Parquet",
                            data=parquet_buffer,
                            file_name="dados_processados.parquet",
                            mime="application/octet-stream"
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
                st.dataframe(stats_df, width='stretch')
                
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
            datetime_cols = df_final.select_dtypes(include=['datetime64']).columns
            if len(datetime_cols) > 0:
                st.markdown("### 📅 Informações de Data/Hora")
                for col in datetime_cols:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(f"{col} - Mais Antiga", str(df_final[col].min().date()) if pd.notna(df_final[col].min()) else "N/A")
                    with col2:
                        st.metric(f"{col} - Mais Recente", str(df_final[col].max().date()) if pd.notna(df_final[col].max()) else "N/A")
                        
        except Exception as e:
            st.error(f"Erro ao calcular estatísticas: {str(e)}")
    
    with tab4:
        st.markdown("### ℹ️ Informações das Colunas:")
        try:
            info_df = create_info_dataframe(df_final)
            st.dataframe(info_df, width='stretch')
        except Exception as e:
            st.error(f"Erro ao criar tabela de informações: {str(e)}")
            st.markdown("**Informações básicas das colunas:**")
            for i, col in enumerate(df_final.columns):
                if i < 10:
                    st.write(f"- **{col}**: {str(df_final[col].dtype)} | Nulos: {df_final[col].isna().sum()}")
                elif i == 10:
                    st.write(f"... e mais {len(df_final.columns) - 10} colunas")

else:
    # Tela inicial
    if not st.session_state['file_loaded']:
        st.info("👆 Digite o caminho do arquivo acima e clique em 'Carregar Arquivo' para começar.")
        
        st.markdown("""
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
        """)

# Comando para executar: streamlit run main.py
