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
    
    Args:
        df (pd.DataFrame): DataFrame original
        
    Returns:
        pd.DataFrame: DataFrame limpo e compatível
    """
    df_clean = df.copy()
    
    # Tratamento especial para cada coluna
    for col in df_clean.columns:
        # Verificar se a coluna tem valores nulos
        if df_clean[col].isna().all():
            # Se toda a coluna é nula, converter para string
            df_clean[col] = df_clean[col].astype('string')
        elif df_clean[col].dtype == 'object':
            # Para colunas object, tentar identificar o melhor tipo
            try:
                # Tentar converter para numérico primeiro
                numeric_col = pd.to_numeric(df_clean[col], errors='coerce')
                if not numeric_col.isna().all():
                    # Se conseguiu converter alguns valores, manter como numérico
                    df_clean[col] = numeric_col
                else:
                    # Se não conseguiu converter, manter como string
                    df_clean[col] = df_clean[col].fillna('').astype('string')
            except:
                # Em caso de erro, forçar conversão para string
                df_clean[col] = df_clean[col].fillna('').astype('string')
        
        # Tratamento especial para colunas mistas
        elif df_clean[col].dtype.name.startswith('mixed'):
            df_clean[col] = df_clean[col].fillna('').astype('string')
    
    # Substituir valores problemáticos
    for col in df_clean.select_dtypes(include=['object', 'string']).columns:
        df_clean[col] = df_clean[col].fillna('')
        # Converter para string se ainda não for
        if df_clean[col].dtype != 'string':
            df_clean[col] = df_clean[col].astype('string')
    
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
st.set_page_config(page_title="Visualizador de Dados Universal", layout="wide")
st.title("Visualizador de Dados Universal")
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
            
            st.dataframe(display_df, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao exibir dados: {str(e)}")
            st.write("Tentando exibir em formato alternativo...")
            # Fallback: mostrar como texto
            st.text(str(df_clean.head()))
    
    with tab3:
        st.write("### Estatísticas básicas:")
        try:
            # Só calcular estatísticas para colunas numéricas
            numeric_cols = df_original.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                stats_df = df_original[numeric_cols].describe()
                st.dataframe(stats_df, use_container_width=True)
            else:
                st.info("Nenhuma coluna numérica encontrada para estatísticas.")
        except Exception as e:
            st.error(f"Erro ao calcular estatísticas: {str(e)}")
    
    with tab4:
        st.write("### Informações das Colunas:")
        try:
            info_df = create_info_dataframe(df_original)
            st.dataframe(info_df, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao criar tabela de informações: {str(e)}")
    
    # Seção adicional para exploração
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
                st.dataframe(df_clean[selected_columns].head(100), use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao exibir colunas selecionadas: {str(e)}")

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
    """)

# Comando para executar: streamlit run main.py

