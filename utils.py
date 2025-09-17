import os
from time import perf_counter
from pathlib import Path
from typing import List, Optional
import pandas as pd

def timer_decorator(func):
    def wrapper_timer(*args, **kwargs):
        start_time = perf_counter()
        value = func(*args, **kwargs)
        end_time = perf_counter()
        print(f"\nTempo de execução da função {func.__name__}: {round(end_time - start_time, 2)} segundos")
        return value
    return wrapper_timer

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


'''

input_path = r"C:\\Users\\edson.eab\\Downloads\\Casos_SRSP_16-09-2025.xlsx"
convert_spreadsheet_to_parquet(input_path)

---

df_left  = pd.read_parquet(r"C:\\Users\\edson.eab\\Downloads\\Casos_SRSP_16-09-2025.parquet")
df_right = pd.read_parquet(r"C:\\Users\\edson.eab\\Downloads\\epol_bi_colunas_extras.parquet")

df_right_unico = aggregate_column_to_list(df=df_right, key_column='Proc. Identificação', column_to_aggregate='Proc. Tipo Penal')

df_completo = merge_dataframes(df_left, df_right_unico, key_column='Proc. Identificação', how='left')

output_path = r"C:\\Users\\edson.eab\\Downloads\\Casos_SRSP_16-09-2025-Completo.parquet"
df_completo.to_parquet(output_path, index=False)

...
df_right['Proc. Identificação'].value_counts()
df_right.duplicated().sum()

---

colunas_uteis = [
    "Proc. Tipo", 
    "Proc. Identificação", 
    "Número do Processo", 
    "Proc. Situação", 
    "Situação Sigla", 
    "Unidade UF", 
    "Lotação Sigla", 
    "Proc. Delegacia", 
    "Proc. Delegado Atual", 
    "Proc. Escrivão",
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
    "Tipo Instauração",
    "Matéria Registro Especial",
    "Proc. Tipo Documento", 
    "Proc. Origem Documento", 
    "Proc. Área de Atribuição", 
    "Proc. Tipo Penal", 
    "Proc. Incidência Penal Principal", 
    "Proc. Tratamento Especial",
]

df_completo  = pd.read_parquet(_path)

df_reduzido = filter_columns(df_completo, colunas_uteis)

output_path = r"C:\\Users\\edson.eab\\Downloads\\Casos_SRSP_16-09-2025-Filtrado.parquet"
df_reduzido.to_parquet(output_path, index=False)

'''

'''
# Suponha que este é o seu DataFrame com os dados explodidos
# df_right = seu_dataframe_aqui

key_column = 'Proc. Identificação'
suspect_column = 'Proc. Tipo Penal'

# 1. Isolar apenas as linhas onde o 'Proc. Identificação' é duplicado
df_com_duplicatas = df_right[df_right.duplicated(subset=[key_column], keep=False)]

if df_com_duplicatas.empty:
    print("✅ Não foram encontradas duplicatas na coluna chave. Nenhuma verificação é necessária.")
else:
    # 2. Agrupar por 'Proc. Identificação' e contar valores únicos em cada coluna
    verificacao_unicidade = df_com_duplicatas.groupby(key_column).nunique()

    # 3. Identificar colunas (além da suspeita) que também têm valores variados
    # Uma coluna é "culpada" se sua contagem de valores únicos (nunique) for > 1
    colunas_problematicas = verificacao_unicidade.drop(columns=[suspect_column], errors='ignore')
    culpados = colunas_problematicas[colunas_problematicas > 1].sum()
    
    # Filtra para mostrar apenas as colunas que apresentaram variação
    outros_culpados = culpados[culpados > 0].astype(int)

    # 4. Apresentar o resultado
    if outros_culpados.empty:
        print(f"✅ Hipótese confirmada!")
        print(f"Apenas a coluna '{suspect_column}' apresenta valores diferentes para os processos duplicados.")
    else:
        print("❌ Atenção! Além de 'Proc. Tipo Penal', outras colunas também variam:")
        print("\nContagem de processos afetados por coluna:")
        print(outros_culpados.sort_values(ascending=False))

'''

