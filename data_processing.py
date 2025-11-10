import os, json
from time import perf_counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from rich import print
from rich.panel import Panel
from rich.table import Table

def timer_decorator(func):
    def wrapper_timer(*args, **kwargs):
        start_time = perf_counter()
        value = func(*args, **kwargs)
        end_time = perf_counter()
        print(f"\nTempo de execução da função {func.__name__}: {round(end_time - start_time, 2)} segundos")
        return value
    return wrapper_timer

# === 

@timer_decorator
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
        print("[red]Erro: Arquivo não encontrado![/red]")
        return None

    file_extension = Path(file_path).suffix.lower()

    try:
        df = None
        if file_extension == ".parquet":
            df = pd.read_parquet(file_path)
        elif file_extension in (".pkl", ".pck") or file_extension == ".pickle":
            df = pd.read_pickle(file_path)
        elif file_extension == ".csv":
            df = pd.read_csv(file_path)
        elif file_extension == ".xlsx":
            df = pd.read_excel(file_path)
        else:
            print(f"[yellow]Formato de arquivo não suportado: {file_extension}[/yellow]")
            print("[yellow]Formatos suportados: .parquet, .pkl, .pickle, .csv, .xlsx[/yellow]")
            return None

        return df

    except Exception as e:
        print(f"[red]Erro ao ler o arquivo: {str(e)}[/red]")
        return None
    
def sanitize_for_streamlit(df: pd.DataFrame) -> pd.DataFrame:
    """
    Usar essa função somente se o dataframe estiver apresentando problemas de compatibilidade com Streamlit.

    Higieniza um DataFrame para exibição segura no Streamlit.
    1. Reseta o índice para evitar erros de serialização do índice.
    2. Converte colunas 'object' com tipos complexos (listas, dicts) para strings JSON.
    """
    df_sanitized = df.copy()

    # Etapa 1: Resetar o índice APENAS se não for um RangeIndex padrão.
    # Isso corrige o problema do .describe() sem afetar outros dataframes.
    if not isinstance(df_sanitized.index, pd.RangeIndex):
        df_sanitized = df_sanitized.reset_index()

    # Etapa 2: Higienizar colunas de objeto.
    for col in df_sanitized.select_dtypes(include=['object']).columns:
        # Define uma função de conversão segura para aplicar a cada célula.
        def safe_converter(x):
            if isinstance(x, (dict, list, tuple, set)):
                try:
                    return json.dumps(x, default=str)
                except (TypeError, ValueError):
                    return str(x)
            return str(x) if pd.notna(x) else None

        df_sanitized[col] = df_sanitized[col].apply(safe_converter)
    
    return df_sanitized

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
        # Lida com tipos não "hashable" (como listas/arrays) que quebram o .nunique()
        try:
            unique_count = df[col].nunique()
        except TypeError:
            unique_count = -1  # Indica que a contagem de únicos não é aplicável

        info = {
            "original_dtype": str(df[col].dtype),
            "null_count": df[col].isna().sum(),
            "null_percent": (df[col].isna().sum() / len(df)) * 100,
            "unique_count": unique_count,
            "sample_values": [],
            "can_be_numeric": False,
            "can_be_datetime": False,
            "numeric_success_rate": 0,
            "datetime_success_rate": 0,
        }

        # Pegar amostra de valores não-nulos
        non_null_values = df[col].dropna()
        if len(non_null_values) > 0:
            sample_size = min(5, len(non_null_values))
            info["sample_values"] = [
                str(x) for x in non_null_values.head(sample_size).tolist()
            ]

        # Testar conversão numérica
        if len(non_null_values) > 0:
            try:
                numeric_converted = pd.to_numeric(non_null_values, errors="coerce")
                numeric_success = numeric_converted.notna().sum()
                info["numeric_success_rate"] = (
                    numeric_success / len(non_null_values)
                ) * 100
                info["can_be_numeric"] = info["numeric_success_rate"] > 70  # 70% de sucesso
            except:
                pass

        # Testar conversão datetime (apenas se não for muito numérica)
        if len(non_null_values) > 0 and info["numeric_success_rate"] < 50:
            try:
                # Tentar apenas uma amostra para evitar warnings excessivos
                sample_for_date = non_null_values.head(min(100, len(non_null_values)))
                datetime_converted = pd.to_datetime(sample_for_date, errors="coerce")
                datetime_success = datetime_converted.notna().sum()
                info["datetime_success_rate"] = (
                    datetime_success / len(sample_for_date)
                ) * 100
                info["can_be_datetime"] = (
                    info["datetime_success_rate"] > 70
                )  # 70% de sucesso
            except:
                pass

        column_info[col] = info

    return column_info

def apply_column_types(
    df: pd.DataFrame, type_mapping: Dict[str, str]
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Aplica os tipos de dados especificados pelo usuário.

    Args:
        df (pd.DataFrame): DataFrame original
        type_mapping (Dict[str, str]): Mapeamento coluna -> tipo desejado

    Returns:
        Tuple[pd.DataFrame, List[str]]: DataFrame com tipos aplicados e log de conversão
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

            if target_type == "string":
                # Usar .apply(str) é mais robusto para garantir que todos os elementos virem strings
                df_typed[col] = df_typed[col].fillna("").apply(str)
                conversion_log.append(f"✅ {col}: convertido para string")

            elif target_type == "numeric":
                df_typed[col] = pd.to_numeric(df_typed[col], errors="coerce")
                new_nulls = df_typed[col].isna().sum()
                lost_values = new_nulls - original_nulls
                if lost_values > 0:
                    conversion_log.append(
                        f"⚠️ {col}: convertido para numérico ({lost_values} valores perdidos)"
                    )
                else:
                    conversion_log.append(f"✅ {col}: convertido para numérico")

            elif target_type == "datetime":
                df_typed[col] = pd.to_datetime(df_typed[col], errors="coerce")
                new_nulls = df_typed[col].isna().sum()
                lost_values = new_nulls - original_nulls
                if lost_values > 0:
                    conversion_log.append(
                        f"⚠️ {col}: convertido para datetime ({lost_values} valores perdidos)"
                    )
                else:
                    conversion_log.append(f"✅ {col}: convertido para datetime")

            elif target_type == "boolean":
                # Tentar conversão inteligente para boolean
                bool_map = {
                    "true": True,
                    "false": False,
                    "1": True,
                    "0": False,
                    "yes": True,
                    "no": False,
                    "sim": True,
                    "nao": False,
                }
                # O tipo 'boolean' do pandas pode causar problemas; converter para 'object' com bools
                series_lower = df_typed[col].astype(str).str.lower()
                df_typed[col] = series_lower.map(bool_map)
                conversion_log.append(f"✅ {col}: convertido para boolean")

        except Exception as e:
            # Em caso de erro, manter como string compatível
            df_typed[col] = df_typed[col].fillna("").apply(str)
            conversion_log.append(
                f"❌ {col}: erro na conversão, mantido como string - {str(e)}"
            )

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
    print(Panel(info_text, title="DataFrame Info", border_style="cyan"))

    table = Table(title="Detalhes das Colunas")
    table.add_column("Nome da Coluna", style="cyan")
    table.add_column("Tipo de Dado", style="magenta")
    table.add_column("Valores Nulos", style="yellow")
    table.add_column("Valores Únicos", style="green")

    for col in df.columns:
        n_unique = df[col].nunique()
        null_count = df[col].isna().sum()
        null_percent = (null_count / len(df)) * 100 if len(df) > 0 else 0

        table.add_row(
            str(col),
            str(df[col].dtype),
            f"{null_count} ({null_percent:.1f}%)",
            str(n_unique),
        )

    print(table)

def create_info_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria um DataFrame com informações sobre as colunas que é compatível com Streamlit.
    """
    info_data = []
    for col in df.columns:
        null_count = df[col].isna().sum()
        null_percent = (null_count / len(df)) * 100 if len(df) > 0 else 0
        unique_count = df[col].nunique()

        info_data.append(
            {
                "Coluna": str(col),
                "Tipo": str(df[col].dtype),
                "Valores Nulos": f"{null_count} ({null_percent:.1f}%)",
                "Valores Únicos": unique_count,
            }
        )

    return pd.DataFrame(info_data)

def diagnose_object_columns(df: pd.DataFrame, verbose: bool = True) -> Dict[str, Dict[str, Any]]:
    """Diagnostica tipos problemáticos em colunas object"""
    object_cols = df.select_dtypes(include=['object']).columns
    diagnosis = {}

    for col in object_cols:
        type_counts = {}
        problematic_counts = {}
        samples = {}

        # Usar .apply() é mais seguro para tipos mistos
        unique_types = df[col].dropna().apply(lambda x: type(x).__name__).value_counts()
        type_counts = unique_types.to_dict()

        # Identifica tipos problemáticos para Arrow
        problematic_types = [t for t in type_counts if t in ['list', 'dict', 'tuple', 'set']]
        if problematic_types:
            for pt in problematic_types:
                problematic_counts[pt] = type_counts[pt]
                try:
                    # Encontra a primeira ocorrência do tipo problemático
                    first_occurrence = df[col].dropna().apply(lambda x: isinstance(x, eval(pt))).idxmax()
                    samples[pt] = {'index': first_occurrence, 'value': df.at[first_occurrence, col]}
                except:
                    samples[pt] = {'index': 'N/A', 'value': 'Could not retrieve sample'}

        diagnosis[col] = {
            'unique_types': type_counts,
            'problematic_types': problematic_counts,
            'sample_values': samples,
            'has_problems': len(problematic_counts) > 0
        }

    return diagnosis

# === Outras funções utilitárias ===

@timer_decorator
def obfuscate_name_columns(df: pd.DataFrame, column_names: Union[str, List[str]]) -> pd.DataFrame:
    """
    Ofusca os nomes em uma ou mais colunas de um DataFrame.

    A transformação segue a regra: primeiro nome em maiúsculas, seguido pelas
    iniciais maiúsculas dos sobrenomes.
    Exemplo: "Carlos Paiva Neto Braga" -> "CARLOS PNB"

    Args:
        df (pd.DataFrame): O DataFrame a ser modificado.
        column_names (Union[str, List[str]]): O nome da coluna ou uma lista de
            nomes de colunas contendo os nomes completos.

    Returns:
        pd.DataFrame: Um novo DataFrame com as colunas de nomes ofuscadas.
        
    Raises:
        ValueError: Se alguma das colunas especificadas não existir no DataFrame.
    """
    if isinstance(column_names, str):
        column_names = [column_names]

    for col_name in column_names:
        if col_name not in df.columns:
            raise ValueError(f"A coluna '{col_name}' não foi encontrada no DataFrame.")

    df_obfuscated = df.copy()

    def _obfuscate_name(name: str) -> str:
        """Função auxiliar para transformar um único nome."""
        if pd.isna(name) or not isinstance(name, str) or not name.strip():
            return name  # Retorna o valor original se for nulo, não-string ou vazio

        parts = name.strip().split()
        if len(parts) == 1:
            return parts[0].upper()

        first_name = parts[0].upper()
        initials = "".join([part[0].upper() for part in parts[1:]])

        return f"{first_name} {initials}"

    for col_name in column_names:
        df_obfuscated[col_name] = df_obfuscated[col_name].apply(_obfuscate_name)
    
    print(f"\nColunas {', '.join(column_names)} ofuscadas com sucesso.")
    return df_obfuscated

@timer_decorator
def convert_spreadsheet_to_parquet(
    input_path: str, output_path: Optional[str] = None
) -> Optional[str]:
    """
    Lê uma planilha (CSV ou Excel), converte para DataFrame e salva como Parquet.

    Args:
        input_path (str): Caminho do arquivo de entrada (.csv ou .xlsx).
        output_path (str, optional): Caminho do arquivo de saída .parquet.
            Se não for fornecido, será salvo no mesmo diretório com o mesmo nome
            e extensão .parquet.

    Returns:
        Optional[str]: O caminho do arquivo Parquet criado ou None em caso de erro.
    """
    if not os.path.exists(input_path):
        print(f"\nErro: Arquivo de entrada não encontrado em '{input_path}'")
        return None

    input_file = Path(input_path)
    file_extension = input_file.suffix.lower()

    try:
        if file_extension == ".csv":
            df = pd.read_csv(input_path)
        elif file_extension == ".xlsx":
            df = pd.read_excel(input_path)
        else:
            print(f"\nErro: Formato de arquivo '{file_extension}' não suportado. Use .csv ou .xlsx.")
            return None

        # Adicionado: Tenta converter colunas 'object' que se parecem com datas
        # para o tipo datetime64, que é compatível com Parquet (pyarrow).
        for col in df.select_dtypes(include=['object']).columns:
            # Usar `errors='coerce'` transforma valores inválidos em NaT.
            # Isso garante que a coluna se torne do tipo datetime64, resolvendo o erro.
            temp_series = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
            
            # Apenas substitui a coluna original se a conversão foi bem-sucedida
            # para pelo menos um valor, evitando destruir colunas de texto.
            if temp_series.notna().any():
                df[col] = temp_series

        if output_path is None:
            output_path = str(input_file.with_suffix(".parquet"))

        df.to_parquet(output_path, index=False)
        print(f"\nSucesso! Arquivo (DF_shape:{df.shape}) salvo em: {output_path}")
        return output_path

    except Exception as e:
        print(f"\nOcorreu um erro durante o processo: {e}")
        return None

@timer_decorator
def aggregate_column_to_list(
    df: pd.DataFrame, key_column: str, columns_to_aggregate: List[str]
) -> pd.DataFrame:
    """
    Agrupa um DataFrame por uma coluna chave e agrega os valores de outra
    colunas em listas, tornando a chave única. Após a agregação, listas
    que contêm apenas placeholders (ex: ['-']) são convertidas para NaN.

    Para as demais colunas, o primeiro valor encontrado para cada chave é mantido.

    Args:
        df (pd.DataFrame): DataFrame de entrada.
        key_column (str): Coluna para agrupar (ex: 'Proc. Identificação').
        columns_to_aggregate (List[str]): Colunas cujos valores serão agregados em listas
                                          (ex: ['Proc. Tipo Penal', 'Outra Coluna']).

    Returns:
        pd.DataFrame: DataFrame com a `key_column` única.
    """
    # Validação das colunas
    all_cols_to_check = [key_column] + columns_to_aggregate
    for col in all_cols_to_check:
        if col not in df.columns:
            raise ValueError(f"A coluna '{col}' não existe no DataFrame.")

    # Define as regras de agregação
    agg_rules = {
        col: "first" for col in df.columns if col not in all_cols_to_check
    }

    # Adiciona a regra de agregação para cada coluna na lista
    for col_agg in columns_to_aggregate:
        agg_rules[col_agg] = list

    df_aggregated = df.groupby(key_column).agg(agg_rules).reset_index()
    
    # --- Pós-processamento para limpar listas vazias ou com placeholders ---
    # Define placeholders que devem ser considerados "vazios"
    placeholders = {'-', '', 'None', '<NA>', 'nan', 'nat', 'undefined'}

    for col_agg in columns_to_aggregate:
        # Função para limpar cada lista na série
        def clean_list(lst):
            if not isinstance(lst, list):
                return lst # Retorna o valor original se não for uma lista
            
            # Remove placeholders e valores nulos da lista
            cleaned = [item for item in lst if pd.notna(item) and str(item) not in placeholders]
            
            # Se a lista ficar vazia, retorna np.nan, caso contrário, retorna a lista limpa
            return np.nan if not cleaned else cleaned

        if col_agg in df_aggregated.columns:
            df_aggregated[col_agg] = df_aggregated[col_agg].apply(clean_list)

    print(f"\nDataframe com colunas agregadas:\n Shape anterior: {df.shape}\n Shape após: {df_aggregated.shape}\n")
    return df_aggregated

@timer_decorator
def merge_dataframes(
    df_left: pd.DataFrame,
    dfs_right: Union[pd.DataFrame, List[pd.DataFrame]],
    key_column: str,
    how: str = "inner",
) -> pd.DataFrame:
    """
    Realiza o merge de um DataFrame à esquerda com um ou mais DataFrames à direita,
    tratando de forma inteligente as colunas com nomes sobrepostos.

    Regras de tratamento:
    - A coluna do DataFrame da esquerda sempre prevalece.
    - Se uma coluna da direita já existe na esquerda, seus valores são comparados.
    - Um aviso é emitido se houver valores divergentes (onde o valor da direita não é nulo).
    - A coluna duplicada da direita é descartada após a verificação.

    Args:
        df_left (pd.DataFrame): O DataFrame da esquerda.
        dfs_right (Union[pd.DataFrame, List[pd.DataFrame]]): Um ou mais DataFrames para mesclar.
        key_column (str): A coluna chave para o merge.
        how (str, optional): Tipo de merge a ser realizado. Padrão 'inner'.

    Returns:
        pd.DataFrame: O DataFrame resultante do merge.
    """
    if not isinstance(dfs_right, list):
        dfs_right = [dfs_right]

    merged_df = df_left.copy()
    print(f"Shape inicial df_left: {merged_df.shape}")

    for i, df_right in enumerate(dfs_right):
        if key_column not in merged_df.columns or key_column not in df_right.columns:
            raise ValueError(
                f"A coluna chave '{key_column}' não foi encontrada para o merge com o DataFrame de índice {i}."
            )

        print(f"--- Mesclando com DataFrame direito de índice {i} (Shape: {df_right.shape}) ---")

        # Identifica colunas sobrepostas (exceto a chave)
        overlapping_cols = [col for col in df_right.columns if col in merged_df.columns and col != key_column]

        # Realiza o merge, usando sufixos para identificar as colunas de origem
        temp_merged = pd.merge(merged_df, df_right, on=key_column, how=how, suffixes=('_left', '_right'))

        if overlapping_cols:
            print(f"Colunas sobrepostas encontradas: {overlapping_cols}. Verificando divergências...")
            for col in overlapping_cols:
                col_left = f"{col}_left"
                col_right = f"{col}_right"

                # Máscara para encontrar divergências onde o valor da direita não é nulo
                divergence_mask = (
                    (temp_merged[col_left] != temp_merged[col_right]) &
                    (temp_merged[col_right].notna())
                )

                if divergence_mask.any():
                    divergent_count = divergence_mask.sum()
                    print(f"⚠️  Aviso: {divergent_count} divergência(s) encontrada(s) na coluna '{col}'. O valor original (à esquerda) será mantido.")
                    
                    # Mostra alguns exemplos da divergência
                    divergent_samples = temp_merged.loc[divergence_mask, [key_column, col_left, col_right]].head(3)
                    print("   Exemplos de divergência:")
                    print(divergent_samples.to_string(index=False))

                # Remove a coluna da direita e renomeia a da esquerda para o nome original
                temp_merged.drop(columns=[col_right], inplace=True)
                temp_merged.rename(columns={col_left: col}, inplace=True)

        merged_df = temp_merged
        print(f"Shape após merge: {merged_df.shape}")

    print(f"\nShape final merged: {merged_df.shape}\n")
    return merged_df

@timer_decorator
def filter_columns(df: pd.DataFrame, columns_to_keep: List[str]) -> pd.DataFrame:
    """
    Filtra um DataFrame para manter apenas as colunas especificadas.

    Colunas na lista que não existem no DataFrame são ignoradas com segurança.

    Args:
        df (pd.DataFrame): O DataFrame a ser filtrado.
        columns_to_keep (List[str]): Uma lista de nomes de colunas a serem mantidas.

    Returns:
        pd.DataFrame: Um novo DataFrame contendo apenas as colunas desejadas.
    """
    # Filtra a lista para incluir apenas colunas que realmente existem no DataFrame
    existing_columns = [col for col in columns_to_keep if col in df.columns]

    # Alerta sobre colunas não encontradas
    missing_columns = set(columns_to_keep) - set(existing_columns)
    if missing_columns:
        print(f"\nAviso: As seguintes colunas não foram encontradas e foram ignoradas: {list(missing_columns)}")

    df_filtrado = df[existing_columns] 
    print(f"\nDataframe filtrado:\n {df_filtrado.info()}")
    return df_filtrado

def confirm_cols_exploded(df: pd.DataFrame, key_column: str):
    """
    Verifica quais colunas do DataFrame são explodidas.

    Args:
        df (pd.DataFrame): DataFrame a ser verificado.
        key_column (str): Nome da coluna chave.

    Returns:
        list: Lista de colunas explodidas.
    """
    # 1. Isolar apenas as linhas onde o 'Proc. Identificação' é duplicado
    df_com_duplicatas = df[df.duplicated(subset=[key_column], keep=False)]

    if df_com_duplicatas.empty:
        print("Não foram encontradas duplicatas na coluna chave. Nenhuma verificação é necessária.")
    else:
        # 2. Agrupar pela key_column e contar valores únicos em cada coluna
        verificacao_unicidade = df_com_duplicatas.groupby(key_column).agg({col: 'nunique' for col in df_com_duplicatas.columns if col != key_column})

        # 3. Identificar colunas que têm valores variados
        # Uma coluna é "explodida" se sua contagem de valores únicos (nunique) for > 1
        explodidas = verificacao_unicidade[verificacao_unicidade > 1].sum()
        
        # Filtra para mostrar apenas as colunas que apresentaram variação
        lista_cols_explodidas = explodidas[explodidas > 0].index.tolist()

        return lista_cols_explodidas

# === 

# Referente à Planilha "Casos - Analítico" do ePol bi:
colunas_uteis = [
    
    # Qual procedimento, tipo e situação
    "Proc. Tipo", 
    "Proc. Identificação", 
    "Tipo Instauração",
    "Número do Processo", 
    "Proc. Situação", 
    "Situação Sigla", 
    
    # Onde se encontra
    "Unidade UF", 
    "Lotação Sigla", 
    "Proc. Delegacia", 
    "Proc. Delegado Atual", 
    "Proc. Escrivão",
    
    # Período de tramitação
    "Data Fato", 
    "Data Recebimento", 
    "Data Cadastro", 
    "Data Parecer", 
    "Data Distribuição", 
    "Data Instauração", 
    "Data Relatório", 
    "Data Vencimento",
    "Data Encerrado", 

    # Colunas extrar do Análítico de Alertas_coger
    "Proc. NC Data Recebimento",
    "Proc. NC Data Cadastro",
    "Proc. NC Data Parecer",
    "Proc. NC Data Distribuição",
    "Dias Vencido",

    "Duração Dias", 
    "Última Movimentação", 
    
    # Àrea temática destinada
    "Proc. Tipo Documento", 
    "Proc. Origem Documento", 
    "Proc. Área de Atribuição",   # Coluna extra
    "Matéria Registro Especial",  
    "Proc. Tratamento Especial",  # Coluna extra

    # Tipificação penal           # Colunas extras
    "Proc. Lei", 
    "Proc. Lei Artigo", 
    "Proc. Lei Artigo Isolado", 
    "Lei-Artigo",
    "Proc. Tipo Penal", 
    "Proc. Incidência Penal Principal", 
    
    # Lesados
    "Proc. Órgão Vítima",         # Coluna extra

    # Índices de Alertas          # Colunas extras
    "Proc. Alerta Tipo",
    "Proc. Saneamento Tipo",
    "Proc. Data Cota"

]

type_mapping = {
    'Proc. Tipo':			            'string' ,
    'Proc. Identificação':              'string' ,
    'Tipo Instauração':                 'string' ,
    'Número do Processo':               'string' ,
    'Proc. Situação':                   'string' ,
    'Situação Sigla':                   'string' ,
    'Unidade UF':                       'string' ,
    'Lotação Sigla':                    'string' ,
    'Proc. Delegacia':                  'string' ,
    'Proc. Delegado Atual':             'string' ,
    'Proc. Escrivão':                   'string' ,
    'Data Fato':                        'datetime',
    'Data Recebimento':                 'datetime',
    'Data Cadastro':                    'datetime',
    'Data Parecer':                     'datetime',
    'Data Distribuição':                'datetime',
    'Data Instauração':                 'datetime',
    'Data Relatório':                   'datetime',
    'Data Encerrado':                   'datetime',
    'Duração Dias':                     'numeric' ,
    'Última Movimentação':              'datetime',
    'Proc. Tipo Documento':             'string' ,
    'Proc. Origem Documento':           'string' ,
    'Proc. Área de Atribuição':         'string' ,
    'Matéria Registro Especial':        'string' ,
    'Proc. Tratamento Especial':        'string' ,
    "Proc. Lei":                        'string' ,
    "Proc. Lei Artigo":                 'string' ,
    "Proc. Lei Artigo Isolado":         'string' ,
    "Lei-Artigo":                       'string' ,
    'Proc. Tipo Penal':                 'string' ,
    'Proc. Incidência Penal Principal': 'string' ,    
    
    'Proc. NC Data Recebimento'     : 'datetime', 
    'Proc. NC Data Cadastro'        : 'datetime', 
    'Proc. NC Data Parecer'         : 'datetime', 
    'Proc. NC Data Distribuição'    : 'datetime', 
    'Dias Vencido'                  : 'numeric' ,
    'Proc. Data Cota'               : 'datetime', 
    'Proc. Alerta Tipo'             : 'string', 
    'Proc. Saneamento Tipo'         : 'string', 
}

rename_cols_mapping = {
    "Proc. Tipo"                       : "Tipo",                      
    "Proc. Identificação"              : "Caso Id",             
    "Proc. Situação"                   : "Situação",                  
    "Proc. Delegacia"                  : "Delegacia",                
    "Proc. Delegado Atual"             : "Delegado Atual",            
    "Proc. Escrivão"                   : "Escrivão",                 
    "Proc. Tipo Documento"             : "Documento de Origem",            
    "Proc. Origem Documento"           : "Órgão de Origem",          
    "Proc. Área de Atribuição"         : "Área de Atribuição",        
    "Proc. Tratamento Especial"        : "Matéria Prometheus",      
    "Proc. Lei Artigo"                 : "Proc. Artigo",
    "Proc. Tipo Penal"                 : "Tipo Penal",                
    "Proc. Incidência Penal Principal" : "Incidência Penal Principal",
    "Proc. Órgão Vítima"               : "Órgão Vítima",    
    "Proc. NC Data Recebimento"     : "NC Data Recebimento", 
    "Proc. NC Data Cadastro"        : "NC Data Cadastro", 
    "Proc. NC Data Parecer"         : "NC Data Parecer", 
    "Proc. NC Data Distribuição"    : "NC Data Distribuição", 
    "Proc. Data Cota"               : "Data Cota", 
    "Proc. Alerta Tipo"             : "Tipo Alerta", 
    "Proc. Saneamento Tipo"         : "Tipo Saneamento", 
}


@timer_decorator
def pipeline_tratatamento_dados_1():
    file_name = "Casos_SP_22-09-2025" # filtros: UF ('SP'), Situação ('Em Andamento'), Data de extração: **dd/mm/2025**

    xlsx_principal = rf"C:\\Users\\edson.eab\\Downloads\\{file_name}.xlsx"
    xlsx_complementar = rf"C:\\Users\\edson.eab\\Downloads\\{file_name}_Complementar.xlsx"

    path_parquet_df_principal = convert_spreadsheet_to_parquet(xlsx_principal) # rf"C:\\Users\\edson.eab\\Downloads\\{file_name}.parquet"
    path_parquet_df_complementar = convert_spreadsheet_to_parquet(xlsx_complementar) # rf"C:\\Users\\edson.eab\\Downloads\\{file_name}_Complementar.parquet"
    # O df_principal deve possuir a coluna de valores únicos 'Proc. Identificação'
    df_principal  = pd.read_parquet(path_parquet_df_principal)
    assert 'Proc. Identificação' in df_principal.columns and df_principal['Proc. Identificação'].nunique() == df_principal.shape[0], "O df_principal deve possuir a coluna de valores únicos 'Proc. Identificação'"

    # O df_complementar possui 'Proc. Identificação' duplicados em razão da coluna 'Proc. Tipo Penal' constar explodida
    df_complementar = pd.read_parquet(path_parquet_df_complementar)

    # Filtrar df_complementar para que só permaneçam linhas com 'Proc. Identificação' que também constam em df_principal
    df_complementar = df_complementar[df_complementar['Proc. Identificação'].isin(df_principal['Proc. Identificação'])]

    assert confirm_cols_exploded(df_complementar, 'Proc. Identificação') == ['Proc. Tipo Penal', 'Proc. Lei', 'Proc. Lei Artigo']

    # Concatenar as colunas 'Proc. Lei' e 'Proc. Lei Artigo' numa nova coluna 'Lei-Artigo' separados por ' - '
    df_complementar['Lei-Artigo'] = df_complementar[['Proc. Lei', 'Proc. Lei Artigo']].apply(lambda x: ' - '.join(x.astype(str)), axis=1)

    n_procs_anterior = df_complementar['Proc. Identificação'].unique().shape[0]

    df_complementar_tratado = aggregate_column_to_list(df=df_complementar, 
                                                       key_column='Proc. Identificação', 
                                                       columns_to_aggregate=['Proc. Tipo Penal', 'Proc. Lei', 'Proc. Lei Artigo', 'Proc. Lei Artigo Isolado', 'Lei-Artigo'])
    assert df_complementar_tratado.shape[0] == n_procs_anterior
    
    # df_complementar_tratado.to_parquet(rf"C:\\Users\\edson.eab\\Downloads\\{file_name}_Complementar_Tratado.parquet")

    df_completo = merge_dataframes(df_principal, df_complementar_tratado, key_column='Proc. Identificação', how='left')

    assert df_principal.shape[0] == df_completo.shape[0], "O df_principal deve possuir a mesma quantidade de linhas do df_completo"
    assert df_principal.shape[1] < df_completo.shape[1], "O df_principal deve possuir menos colunas do que o df_completo"

    output_path_0 = rf"C:\\Users\\edson.eab\\Downloads\\{file_name}_Completo.parquet"
    df_completo.to_parquet(output_path_0, index=False)

    # df['Proc. Identificação'].value_counts()
    # df.duplicated().sum()

    df_reduzido = filter_columns(df_completo, colunas_uteis)
    # column_info = detect_column_types(df_reduzido) # print(column_info) 

    df_final, _ = apply_column_types(df_reduzido, type_mapping)
    print(df_final.info())

    df_final = df_final.rename(columns=rename_cols_mapping)
    df_final = obfuscate_name_columns(df_final, ["Delegado Atual", "Escrivão"])

    # info_df = create_info_dataframe(df_final) # print(info_df) # já feito em print_dataframe_info

    print_dataframe_info(df_final)

    output_path = rf"C:\\Users\\edson.eab\\Downloads\\{file_name}_Tratado.parquet"
    df_final.to_parquet(output_path, index=False)

    # filtered_df = df.loc[df['Proc. Situação'] == "Em Andamento"]
    # exloded_df = filtered_df.explode('Proc. Tipo Penal')
    # exloded_df.to_excel(r"C:\\Users\\edson.eab\\Downloads\\{file_name}_TiposPenal.xlsx", index=False)

    return output_path

@timer_decorator
def pipeline_tratatamento_dados_2():
    base_name = "Casos_SP_10-11-2025" # filtros: UF ('SP'), Situação ('Em Andamento'), Data de extração: **dd/mm/2025**
    output_path_0 = rf"C:\\Users\\edson.eab\\Downloads\\{base_name}_Completo.parquet"
    output_path_f = os.path.join('data', f"{base_name}_Tratado.parquet")

    xlsx_principal = rf"C:\\Users\\edson.eab\\Downloads\\{base_name}.xlsx"
    xlsx_complementar1 = rf"C:\\Users\\edson.eab\\Downloads\\{base_name}_TipoAlertas.xlsx"
    xlsx_complementar2 = rf"C:\\Users\\edson.eab\\Downloads\\{base_name}_TipoSaneamentos.xlsx" 
    xlsx_complementar3 = rf"C:\\Users\\edson.eab\\Downloads\\{base_name}_Complementar.xlsx" # Incluída coluna 'Proc. Data Cota'

    path_parquet_df_principal = Path(xlsx_principal).with_suffix('.parquet')
    path_parquet_df_complementar1 = Path(xlsx_complementar1).with_suffix('.parquet')
    path_parquet_df_complementar2 = Path(xlsx_complementar2).with_suffix('.parquet')
    path_parquet_df_complementar3 = Path(xlsx_complementar3).with_suffix('.parquet')

    if not os.path.exists(output_path_f):
        if not os.path.exists(output_path_0):

            if not os.path.exists(path_parquet_df_principal):
                path_parquet_df_principal = convert_spreadsheet_to_parquet(xlsx_principal) # rf"C:\\Users\\edson.eab\\Downloads\\{base_name}.parquet"
            if not os.path.exists(path_parquet_df_complementar1):
                path_parquet_df_complementar1 = convert_spreadsheet_to_parquet(xlsx_complementar1) # rf"C:\\Users\\edson.eab\\Downloads\\{base_name}_TipoAlertas.parquet"
            if not os.path.exists(path_parquet_df_complementar2):
                path_parquet_df_complementar2 = convert_spreadsheet_to_parquet(xlsx_complementar2) # rf"C:\\Users\\edson.eab\\Downloads\\{base_name}_TipoSaneamentos.parquet"
            if not os.path.exists(path_parquet_df_complementar3):        
                path_parquet_df_complementar3 = convert_spreadsheet_to_parquet(xlsx_complementar3) # rf"C:\\Users\\edson.eab\\Downloads\\{base_name}_Complementar.parquet"

            print("\n >>> Conversões de arquivos xlsx para parquet concluídas! \n")

            # O df_principal deve possuir a coluna de valores únicos 'Proc. Identificação'
            df_principal  = pd.read_parquet(path_parquet_df_principal)
            assert 'Proc. Identificação' in df_principal.columns and df_principal['Proc. Identificação'].nunique() == df_principal.shape[0], "O df_principal deve possuir a coluna de valores únicos 'Proc. Identificação'"
            df_complementar1 = pd.read_parquet(path_parquet_df_complementar1)
            df_complementar2 = pd.read_parquet(path_parquet_df_complementar2)
            if path_parquet_df_complementar3:
                df_complementar3 = pd.read_parquet(path_parquet_df_complementar3)
            else:
                df_complementar3 = pd.DataFrame(columns=['Proc. Identificação']).astype(object)

            # O df_complementar possui 'Proc. Identificação' duplicados em razão das colunas 'Proc. Alerta Tipo' constar explodida
            assert confirm_cols_exploded(df_complementar1, 'Proc. Identificação') == ['Proc. Alerta Tipo']
            assert confirm_cols_exploded(df_complementar2, 'Proc. Identificação') == ['Proc. Alerta Tipo', 'Proc. Saneamento Tipo', 'Proc. Prescrição Situação']
            
            print(" >>> Confirmadas colunas explodidas.")

            # Tratando df_complementar1 
            n_procs_anterior1 = df_complementar1['Proc. Identificação'].unique().shape[0]
            df_complementar_tratado1 = aggregate_column_to_list(df=df_complementar1, 
                                                                key_column='Proc. Identificação', 
                                                                columns_to_aggregate=['Proc. Alerta Tipo'])
            assert df_complementar_tratado1.shape[0] == n_procs_anterior1
            print(" >>> Agregada 'Proc. Alerta Tipo' em df_complementar1")
                
            # Tratando df_complementar2
            n_procs_anterior2 = df_complementar2['Proc. Identificação'].unique().shape[0]
            df_complementar2 = df_complementar2[['Proc. Identificação', 'Proc. Saneamento Tipo']]
            df_complementar_tratado2 = aggregate_column_to_list(df=df_complementar2, 
                                                                key_column='Proc. Identificação', 
                                                                columns_to_aggregate=['Proc. Saneamento Tipo'])
            assert df_complementar_tratado2.shape[0] == n_procs_anterior2
            print(" >>> Agregada 'Proc. Saneamento Tipo' em df_complementar2")
            print("\n")

            # df_complementar_tratado.to_parquet(rf"C:\\Users\\edson.eab\\Downloads\\{file_name}_Complementar_Tratado.parquet")

            df_completo = merge_dataframes(df_principal, [df_complementar_tratado1, df_complementar_tratado2, df_complementar3], 
                                            key_column='Proc. Identificação', how='left')

            assert df_principal.shape[0] == df_completo.shape[0], "O df_principal deve possuir a mesma quantidade de linhas do df_completo"
            assert df_principal.shape[1] < df_completo.shape[1], "O df_principal deve possuir menos colunas do que o df_completo"
            
            df_completo.to_parquet(output_path_0, index=False)
        else:
            df_complementar1 = pd.read_parquet(path_parquet_df_complementar1)
            df_completo = pd.read_parquet(output_path_0)

        print("\n >>> Merge completo procedido com sucesso! \n")
            
        # df['Proc. Identificação'].value_counts()
        # df.duplicated().sum()

        # --- ---------------------------------------------------------------------
        # Conferências de confrontamento:
        tipos_alertas = [
            'NCV Pendente Parecer > 15 dias',
            'NC Pendente Parecer > 15 dias',
            'NC Pendente Instauração > 30 dias',
            'CP Vencido > 10 dias',
            'TC Vencido > 10 dias',
            'RE Vencido > 10 dias',
            'MP Vencido > 10 dias',
            'NCV Vencido > 90 dias',
            'NC Vencido > 90 dias',
            'IPL Vencido > 10 dias',
            'IPL Cota Duração > 1 ano', 
            'IPL Duração > 3 anos',
            'IPL Duração > 5 anos',
            'TC Duração > 90 dias'
        ]
        df = df_completo
        # datetime_target = datetime(2025, 10, 20)
        datetime_target = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        dfs_filtros = [
            df.loc[(df['Proc. Tipo']=='NCV') & (df['Situação Sigla']=='Aguardando Parecer')    & (datetime_target-df['Data Parecer'] > timedelta(days=15))],
            df.loc[(df['Proc. Tipo']=='NC') & (df['Situação Sigla']=='Aguardando Parecer')     & (datetime_target-df['Data Cadastro'] > timedelta(days=15))],
            df.loc[(df['Proc. Tipo']=='NC') & (df['Situação Sigla']=='Aguardando Instauração') & (datetime_target-df['Data Parecer'] > timedelta(days=30))],
            df.loc[(df['Proc. Tipo']=='CP') & (datetime_target-df['Data Vencimento'] >= timedelta(days=11))],
            df.loc[(df['Proc. Tipo']=='TC') & (datetime_target-df['Data Vencimento'] >= timedelta(days=11))],
            df.loc[(df['Proc. Tipo']=='RE') & (datetime_target-df['Data Vencimento'] >= timedelta(days=11))],
            df.loc[(df['Proc. Tipo']=='MP') & (datetime_target-df['Data Vencimento'] >= timedelta(days=11))],
            df.loc[(df['Proc. Tipo']=='NCV') & (datetime_target-df['Data Vencimento']>= timedelta(days=91))],
            df.loc[(df['Proc. Tipo']=='NC') & (datetime_target-df['Data Vencimento'] >= timedelta(days=91))],
            df.loc[(df['Proc. Tipo']=='IPL') & (datetime_target-df['Data Vencimento']>= timedelta(days=11)) & (~df['Situação Sigla'].isin(['Apreciação', 'Pedido de Baixa']))],
            df.loc[(df['Proc. Tipo']=='IPL') & (df['Proc. Data Cota'] <  ((datetime_target + timedelta(days=1)) - pd.DateOffset(years=1)) )] if 'Proc. Data Cota' in df.columns else None,
            df.loc[(df['Proc. Tipo']=='IPL') & (df['Data Instauração'] < ((datetime_target + timedelta(days=1)) - pd.DateOffset(years=3)) )],
            df.loc[(df['Proc. Tipo']=='IPL') & (df['Data Instauração'] < ((datetime_target + timedelta(days=1)) - pd.DateOffset(years=5)) )],
            df.loc[(df['Proc. Tipo']=='TC')  & (df['Data Instauração'] < ((datetime_target + timedelta(days=1)) - pd.DateOffset(days=90)) )],
        ]

        registros_extras = {}
        for tipo_alerta, df_check in zip(tipos_alertas, dfs_filtros):
            print('\n')
            df_a = df_check
            df_b = df_complementar1.loc[df_complementar1['Proc. Alerta Tipo']==tipo_alerta]
            #
            if df_a is None:
                print(f" >>> Alerta '{tipo_alerta}' sem registros capturados! ")
                continue 

            set_a = set(df_a['Proc. Identificação'])
            set_b = set(df_b['Proc. Identificação'])
            #
            if set_a == set_b: 
                print(f"Alerta '{tipo_alerta}' OK")
            else:
                if set_b - set_a:
                    print(f"Alerta '{tipo_alerta}' FALTAndo registros: !!! !!! !!!")
                    print(set_b - set_a)
                    # raise ValueError(f"Alerta '{tipo_alerta}' FALTAndo registros!")
                elif set_a - set_b:
                    print(f"Alerta '{tipo_alerta}' EXTRAs:")
                    print(set_a - set_b)
                    registros_extras[tipo_alerta] = set_a - set_b
        # --- -------------------------------------------------------------------

        df_reduzido = filter_columns(df_completo, colunas_uteis)
        # column_info = detect_column_types(df_reduzido) # print(column_info) 

        df_final, _ = apply_column_types(df_reduzido, type_mapping)
        print(df_final.info())

        df_final = df_final.rename(columns=rename_cols_mapping)
        df_final = obfuscate_name_columns(df_final, ["Delegado Atual", "Escrivão"])

        # info_df = create_info_dataframe(df_final) # print(info_df) # já feito em print_dataframe_info

        df_final.to_parquet(output_path_f, index=False)

    else:
        print(" \n >>> Dataframe final tratado e já salvo em 'data'! ")
        df_final = pd.read_parquet(output_path_f)
    
    print_dataframe_info(df_final)

    # filtered_df = df.loc[df['Proc. Situação'] == "Em Andamento"]
    # exloded_df = filtered_df.explode('Proc. Tipo Penal')
    # exloded_df.to_excel(r"C:\\Users\\edson.eab\\Downloads\\{file_name}_TiposPenal.xlsx", index=False)

    print("\n >>> Tratamento concluído =D")
    return output_path_f

# >>> python -i data_processing.py
# >>> pipeline_tratatamento_dados_2()

'''

Colunas DF Analítico - Alertas SP = [
    Proc. Tipo
    Proc. Identificação
    Proc. Alerta Tipo
    Proc. Delegado Atual
    Proc. Escrivão Nome
    Proc. Data Fato
    Proc. NC Data Recebimento
    Proc. NC Data Cadastro
    Proc. NC Data Parecer
    Proc. NC Data Distribuição
    Proc. Data Instauração
    Proc. Data Relatório
    Proc. Data Vencimento
    Proc. Data Encerrado
    Proc. Data Última Movimentação
    N° Processo MPF
    N° Processe Justiça
    Proc. Processo Vara
    Proc. Situação
    Valor a Apurar
    Proc. Duração Dias
    Lotação Sigla
    Proc. Situação Sigla
    Proc. Delegacia
    Proc. Delegacia Instauração
    Proc. Retombado
    Proc. Delegado Matrícula
    Proc. Delegado Instaurador Cargo
    Unidade Siscart
    Unidade ePol
    Delegado Sistema Corporativo
    Procedimento Em Andamento ID
]

Colunas DF Analítico - Alertas e Saneam SP = [
    Proc. Identificação
    Proc. Data Instauração        
    Proc. Alerta Tipo
    Proc. Saneamento Tipo
    Proc. Tipo Encerrado
    Proc. Data Vencimento
    Dias Vencido
    Proc. Delegacia
    Proc. Delegado Nome
    Proc. Escrivão Nome
    Proc. Data Última Movimentação
    Proc. Referência Siscart      
    Processo nº
    Proc. Relatado
    Proc. Data Fato
    Proc. Unidade Exercício       
    Proc. Situação Sigla
    Proc. Delegado Instaurador    
    Proc. Tipo
    Proc. Processo Vara
    Tribunal do Caso
    Proc. Processo MPF
    Proc. Localização
    Proc. Prescrição Situação     
    Proc. Última Página
    Proc. Relatado Não Movimentado
    Proc. Alerta Quantidade
    Proc. Perícia em Andamento?    
]

Colunas DF Analítico - Casos SP = [
    Proc. Tipo
    Proc. Tipo Documento
    Proc. Crime CEP
    Tipo Instauração
    Unidade UF
    Lotação Sigla
    Proc. Identificação
    Proc. Referência Siscart
    Data Fato
    Data Recebimento
    Data Cadastro
    Data Parecer
    Data Distribuição
    Data Instauração
    Data Relatório
    Data Vencimento
    Data Encerrado
    Proc. Situação
    Indiciados
    Presos
    Duração Dias
    Valor a Apurar
    Valor Apurado
    Última Movimentação
    N° Processo MPF
    Número do Processo
    Tribunal do Caso
    Seção/Subseção/Comarca/Zona/Órgão Colegiado
    Vara/Relator
    Situação Original
    Proc. Protocolo
    Proc. Origem Documento
    Proc. Tipo Local
    Município Crime
    UF Crime
    Situação Sigla
    Proc. Delegacia
    Delegacia Instauração
    Proc. Retombado
    Proc. Delegado Atual
    Matr. Delegado Instaurador
    Cargo Instaurador
    Delegado Instaurador
    Proc. Delegado Relator
    Proc. Escrivão
    Delegado Sistema Corporativo
    Proc. Autoria Identificada?
    Proc. Não Crime?
    Matéria Registro Especial
    Proc. Quantidade Foro Privilegiado
]

'''
