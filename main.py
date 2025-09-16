import pandas as pd
import streamlit as st
from rich import print as rprint
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
from typing import Optional, Union
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

def clean_dataframe_for_streamlit(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpa e prepara o DataFrame para ser compatível com o Streamlit/Arrow.
    Implementa limpeza agressiva para resolver problemas de serialização.
    
    Args:
        df (pd.DataFrame): DataFrame original
        
    Returns:
        pd.DataFrame: DataFrame limpo e compatível
    """
    df_clean = df.copy()
    
    # Reset do índice para evitar problemas com índices complexos
    df_clean = df_clean.reset_index(drop=True)
    
    # Tratamento agressivo para cada coluna
    for col in df_clean.columns:
        try:
            df_clean[col] = df_clean[col].fillna('').astype(str).astype('string')
            continue
        
            # Primeiro, tratar valores nulos
            if df_clean[col].isna().all():
                # Se toda a coluna é nula, criar coluna string vazia
                df_clean[col] = pd.Series([''] * len(df_clean), dtype='string')
                continue
            
            # Verificar se é numérica
            if pd.api.types.is_numeric_dtype(df_clean[col]):
                # Se já é numérica, manter mas garantir que não há valores problemáticos
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
                continue
            
            # Para colunas não-numéricas, tentar conversão inteligente
            if df_clean[col].dtype == 'object' or str(df_clean[col].dtype).startswith('mixed'):
                # Tentar primeiro conversão numérica
                try:
                    numeric_test = pd.to_numeric(df_clean[col], errors='coerce')
                    # Se mais de 50% dos valores foram convertidos com sucesso, manter numérico
                    if numeric_test.notna().sum() / len(df_clean) > 0.5:
                        df_clean[col] = numeric_test
                        continue
                except:
                    pass
                
                # Tentar conversão para datetime
                try:
                    datetime_test = pd.to_datetime(df_clean[col], errors='coerce')
                    # Se mais de 50% dos valores foram convertidos, manter datetime
                    if datetime_test.notna().sum() / len(df_clean) > 0.5:
                        df_clean[col] = datetime_test
                        continue
                except:
                    pass
                
                # Se chegou até aqui, converter para string de forma segura
                df_clean[col] = df_clean[col].fillna('').astype(str)
                # Garantir que é string pandas nativa
                df_clean[col] = df_clean[col].astype('string')
            
            else:
                # Para outros tipos, tentar manter o tipo original
                # mas garantir compatibilidade
                if 'datetime' in str(df_clean[col].dtype):
                    continue  # datetime já é compatível
                elif 'bool' in str(df_clean[col].dtype):
                    continue  # boolean já é compatível
                else:
                    # Converter para string como fallback
                    df_clean[col] = df_clean[col].fillna('').astype(str).astype('string')
                    
        except Exception as e:
            # Em caso de qualquer erro, forçar conversão para string
            try:
                df_clean[col] = df_clean[col].fillna('').astype(str).astype('string')
            except:
                # Último recurso: criar coluna string com representação do valor
                df_clean[col] = pd.Series([str(x) if pd.notna(x) else '' for x in df_clean[col]], dtype='string')
    
    # Limpeza final: garantir que não há tipos problemáticos restantes
    for col in df_clean.columns:
        if df_clean[col].dtype == 'object':
            df_clean[col] = df_clean[col].astype('string')
    
    # Verificar se há colunas com nomes problemáticos
    df_clean.columns = [str(col).strip() for col in df_clean.columns]
    
    return df_clean

def print_dataframe_info(df: pd.DataFrame) -> None:
    """
    Imprime informações detalhadas sobre o DataFrame usando rich.
    
    Args:
        df (pd.DataFrame): DataFrame para análise
    """
    # Criando painel com informações básicas
    info_text = f"""
    [bold cyan]Informações do DataFrame:[/bold cyan]
    • Dimensões (linhas, colunas): {df.shape}
    • Total de elementos: {df.size}
    • Memória utilizada: {df.memory_usage().sum() / 1024**2:.2f} MB
    """
    rprint(Panel(info_text, title="DataFrame Info", border_style="cyan"))
    
    # Criando tabela com informações das colunas
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
st.title("Visualizador de Dados")
st.markdown("Suporta arquivos: .parquet, .pkl, .pickle, .csv, .xlsx")

# Campo para inserir o caminho do arquivo
file_path = st.text_input("Digite o caminho do arquivo:", value="C:\\Users\\edson.eab\\Downloads\\df_bi_only_procs.parquet")

if file_path and st.button("Carregar Arquivo"):
    with st.spinner("Carregando arquivo..."):
        # Tentando ler o arquivo quando um caminho for fornecido
        df_original = read_dataframe(file_path)
        
        if df_original is not None:
            # Armazenar o DataFrame original no session state
            st.session_state['df_original'] = df_original
            st.session_state['file_loaded'] = True
            st.success(f"Arquivo carregado com sucesso! Dimensões: {df_original.shape}")

# Verificar se há um arquivo carregado
if 'file_loaded' in st.session_state and st.session_state['file_loaded']:
    df_original = st.session_state['df_original']
    
    # Limpar o DataFrame para compatibilidade com Streamlit
    with st.spinner("Processando dados..."):
        df_clean = clean_dataframe_for_streamlit(df_original)
    
    # Usando rich para imprimir informações detalhadas no terminal
    print_dataframe_info(df_original)
    
    # Criando abas para melhor organização
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Visão Geral", "🔍 Amostra dos Dados", "📈 Estatísticas", "ℹ️ Info das Colunas"])
    
    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Linhas", f"{df_original.shape[0]:,}")
        with col2:
            st.metric("Colunas", df_original.shape[1])
        with col3:
            st.metric("Memória (MB)", f"{df_original.memory_usage().sum() / 1024**2:.2f}")
        
        st.write("### Tipos de Dados")
        dtype_counts = df_original.dtypes.value_counts()
        st.bar_chart(dtype_counts)
    
    with tab2:
        st.write("### Primeiras linhas do DataFrame:")
        try:
            # Mostrar apenas as primeiras colunas se houver muitas
            display_df = df_clean.head(100)
            if len(df_clean.columns) > 20:
                st.warning(f"Exibindo apenas as primeiras 20 colunas de {len(df_clean.columns)} total.")
                display_df = display_df.iloc[:, :20]
            
            st.dataframe(display_df, width='stretch')
        except Exception as e:
            st.error(f"Erro ao exibir dados: {str(e)}")
            st.write("Tentando exibir em formato alternativo...")
            # Fallback: mostrar como texto
            st.text(str(df_clean.head()))
        
        # Seção de opções avançadas apenas nesta aba
        with st.expander("🔧 Opções Avançadas"):
            st.write("### Filtros e Visualizações")
            
            # Seleção de colunas para visualizar
            selected_columns = st.multiselect(
                "Selecione colunas específicas para visualizar:",
                options=list(df_clean.columns),
                default=list(df_clean.columns[:5]) if len(df_clean.columns) >= 5 else list(df_clean.columns)
            )
            
            if selected_columns:
                st.write(f"### Dados das Colunas Selecionadas ({len(selected_columns)} colunas):")
                try:
                    st.dataframe(df_clean[selected_columns].head(100), width='stretch')
                except Exception as e:
                    st.error(f"Erro ao exibir colunas selecionadas: {str(e)}")
                    # Fallback ainda mais seguro
                    st.write("**Primeira linha das colunas selecionadas:**")
                    for col in selected_columns:
                        st.write(f"- **{col}**: {str(df_clean[col].iloc[0]) if len(df_clean) > 0 else 'N/A'}")
            
            # Opção para download dos dados limpos
            if st.button("💾 Baixar dados limpos como CSV"):
                try:
                    csv = df_clean.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name="dados_limpos.csv",
                        mime="text/csv"
                    )
                except Exception as e:
                    st.error(f"Erro ao preparar download: {str(e)}")
    
    with tab3:
        st.write("### Estatísticas básicas:")
        try:
            # Só calcular estatísticas para colunas numéricas
            numeric_cols = df_original.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                stats_df = df_original[numeric_cols].describe()
                st.dataframe(stats_df, width='stretch')
            else:
                st.info("Nenhuma coluna numérica encontrada para estatísticas.")
        except Exception as e:
            st.error(f"Erro ao calcular estatísticas: {str(e)}")
    
    with tab4:
        st.write("### Informações das Colunas:")
        try:
            info_df = create_info_dataframe(df_original)
            st.dataframe(info_df, width='stretch')
        except Exception as e:
            st.error(f"Erro ao criar tabela de informações: {str(e)}")
            # Fallback: mostrar informações básicas
            st.write("**Informações básicas das colunas:**")
            for i, col in enumerate(df_original.columns):
                if i < 10:  # Limitar a 10 primeiras colunas no fallback
                    st.write(f"- **{col}**: {str(df_original[col].dtype)} | Nulos: {df_original[col].isna().sum()}")
                elif i == 10:
                    st.write(f"... e mais {len(df_original.columns) - 10} colunas")
else:
    st.info("👆 Digite o caminho do arquivo acima e clique em 'Carregar Arquivo' para começar.")
    st.markdown("""
    ### Formatos Suportados:
    - **Parquet** (.parquet)
    - **Pickle** (.pkl, .pck, .pickle) 
    - **CSV** (.csv)
    - **Excel** (.xlsx)
    
    ### Recursos:
    - ✅ Visualização de dados compatível com Arrow/Streamlit
    - ✅ Informações detalhadas no terminal via Rich
    - ✅ Estatísticas básicas
    - ✅ Tratamento automático de tipos de dados problemáticos
    - ✅ Interface organizada em abas
    - ✅ Opções avançadas de filtragem
    - ✅ Download de dados limpos
    """)

# Comando para executar: streamlit run main.py

