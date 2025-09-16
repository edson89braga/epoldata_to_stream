import os, json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table

def sanitize_for_streamlit(df: pd.DataFrame) -> pd.DataFrame:
    """
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
        if file_extension == ".parquet":
            df = pd.read_parquet(file_path)
        elif file_extension in (".pkl", ".pck") or file_extension == ".pickle":
            df = pd.read_pickle(file_path)
        elif file_extension == ".csv":
            df = pd.read_csv(file_path)
        elif file_extension == ".xlsx":
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
            "original_dtype": str(df[col].dtype),
            "null_count": df[col].isna().sum(),
            "null_percent": (df[col].isna().sum() / len(df)) * 100,
            "unique_count": df[col].nunique(),
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
    rprint(Panel(info_text, title="DataFrame Info", border_style="cyan"))

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

    rprint(table)


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

