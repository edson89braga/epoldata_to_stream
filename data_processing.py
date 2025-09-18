import os, json
from time import perf_counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

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
    df: pd.DataFrame, key_column: str, column_to_aggregate: str
) -> pd.DataFrame:
    """
    Agrupa um DataFrame por uma coluna chave e agrega os valores de outra
    coluna em uma lista, tornando a chave única.

    Para as demais colunas, o primeiro valor encontrado para cada chave é mantido.

    Args:
        df (pd.DataFrame): DataFrame de entrada.
        key_column (str): Coluna para agrupar (ex: 'Proc. Identificação').
        column_to_aggregate (str): Coluna cujos valores serão agregados em uma lista
                                   (ex: 'Proc. Tipo Penal').

    Returns:
        pd.DataFrame: DataFrame com a `key_column` única.
    """
    if key_column not in df.columns or column_to_aggregate not in df.columns:
        raise ValueError("A coluna chave ou a coluna de agregação não existem no DataFrame.")

    # Define as regras de agregação
    agg_rules = {
        col: "first" for col in df.columns if col not in [key_column, column_to_aggregate]
    }
    agg_rules[column_to_aggregate] = list

    df_aggregated = df.groupby(key_column).agg(agg_rules).reset_index()

    print(f"\nDataframe com colunas agregadas:\n Shape anteior: {df.shape}\n Shape após: {df_aggregated.shape}\n")
    return df_aggregated

@timer_decorator
def merge_dataframes(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    key_column: str,
    how: str = "inner",
) -> pd.DataFrame:
    """
    Realiza o merge de dois DataFrames com base em uma coluna chave comum.

    Args:
        df_left (pd.DataFrame): O DataFrame da esquerda.
        df_right (pd.DataFrame): O DataFrame da direita.
        key_column (str): O nome da coluna a ser usada como chave para o merge.
        how (str, optional): Tipo de merge a ser realizado.
            Padrão é 'inner'. Opções: 'left', 'right', 'outer', 'inner'.

    Returns:
        pd.DataFrame: O DataFrame resultante do merge.
        
    Raises:
        ValueError: Se a coluna chave não existir em um dos DataFrames.
    """
    if key_column not in df_left.columns or key_column not in df_right.columns:
        raise ValueError(
            f"A coluna chave '{key_column}' não foi encontrada em ambos os DataFrames."
        )
    
    print(f"Shape df1: {df_left.shape}")
    print(f"Shape df2: {df_right.shape}")
    merged_df = pd.merge(df_left, df_right, on=key_column, how=how)
    print(f"\nShape merged: {merged_df.shape}\n")
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

colunas_uteis = [
    
    # Qual procedimento, tipo e situação
    "Proc. Tipo", 
    "Proc. Identificação", 
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
    "Data Encerrado", 
    "Duração Dias", 
    "Última Movimentação", 
    
    # Àrea temática destinada
    "Proc. Tipo Documento", 
    "Proc. Origem Documento", 
    "Proc. Área de Atribuição", 
    "Matéria Registro Especial",
    "Proc. Tratamento Especial",

    # Tipificação penal
    "Proc. Lei", 
    "Proc. Lei Artigo", 
    "Proc. Lei Artigo Isolado", 
    "Proc. Tipo Penal", 
    "Proc. Incidência Penal Principal", 
    
    # Lesados
    "Proc. Órgão Vítima", 

]

type_mapping = {
    'Proc. Tipo':			            'string' ,
    'Proc. Identificação':              'string' ,
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
    'Proc. Tipo Penal':                 'string' ,
    'Proc. Incidência Penal Principal': 'string' ,    
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
    "Proc. Tipo Penal"                 : "Tipo Penal",                
    "Proc. Incidência Penal Principal" : "Incidência Penal Principal",
    "Proc. Órgão Vítima"               : "Órgão Vítima",              
}

file_name = "Casos_SP_XX-09-2025"

@timer_decorator
def pipeline_tratatamento_dados():

    xlsx_principal = rf"C:\\Users\\edson.eab\\Downloads\\{file_name}.xlsx"
    xlsx_complementar = rf"C:\\Users\\edson.eab\\Downloads\\{file_name}_Complementar.xlsx"

    path_parquet_df_principal = convert_spreadsheet_to_parquet(xlsx_principal)
    path_parquet_df_complementar = convert_spreadsheet_to_parquet(xlsx_complementar)

    # O df_principal deve possuir a coluna de valores únicos 'Proc. Identificação'
    df_principal  = pd.read_parquet(path_parquet_df_principal)
    assert 'Proc. Identificação' in df_principal.columns and df_principal['Proc. Identificação'].nunique() == df_principal.shape[0], "O df_principal deve possuir a coluna de valores únicos 'Proc. Identificação'"

    # O df_complementar possui 'Proc. Identificação' duplicados em razão da coluna 'Proc. Tipo Penal' constar explodida
    df_complementar = pd.read_parquet(path_parquet_df_complementar)
    assert confirm_cols_exploded(df_complementar, 'Proc. Identificação') == ['Proc. Tipo Penal']

    df_complementar_tratado = aggregate_column_to_list(df=df_complementar, key_column='Proc. Identificação', column_to_aggregate='Proc. Tipo Penal')

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

    # info_df = create_info_dataframe(df_final) # print(info_df) # já feito em print_dataframe_info

    print_dataframe_info(df_final)

    output_path = rf"C:\\Users\\edson.eab\\Downloads\\{file_name}_Tratado.parquet"
    df_final.to_parquet(output_path, index=False)

    # filtered_df = df.loc[df['Proc. Situação'] == "Em Andamento"]
    # exloded_df = filtered_df.explode('Proc. Tipo Penal')
    # exloded_df.to_excel(r"C:\\Users\\edson.eab\\Downloads\\{file_name}_TiposPenal.xlsx", index=False)

    return output_path


