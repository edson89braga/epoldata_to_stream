# Dashboard de Análise de Casos

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red.svg)](https://streamlit.io)
[![Pandas](https://img.shields.io/badge/Library-Pandas-blue.svg)](https://pandas.pydata.org/)
[![Plotly](https://img.shields.io/badge/Library-Plotly-purple.svg)](https://plotly.com/)

Dashboard interativo para análise e visualização de dados de casos. A aplicação foi projetada para consumir um conjunto de dados pré-processado, permitindo que usuários explorem informações complexas através de filtros dinâmicos, tabelas interativas e visualizações gráficas.

## Principais Funcionalidades

- **Dashboard Multi-abas:** Navegação intuitiva separada por tipo de análise (Tabela Geral, Agregações, Análise Cruzada, Série Temporal).
- **Filtros Dinâmicos:** Barra lateral com filtros principais e secundários para segmentar os dados em tempo real.
- **Tabela Interativa:** Visualização dos dados brutos filtrados com opções de seleção de colunas, ordenação e download para Excel.
- **Visualizações Agregadas:** Gráficos de barras e pizza para analisar a distribuição de dados por categoria, com suporte a colunas que contêm listas (ex: Tipos Penais).
- **Análise Cruzada:** Geração de mapas de calor (*heatmaps*) para investigar a relação entre duas variáveis categóricas.
- **Análise Temporal:** Gráficos de linha para visualizar a evolução do número de casos ao longo do tempo, com granularidade ajustável (Ano, Mês, Dia, etc.).
- **Interface Aditiva:** Permite ao usuário adicionar e remover múltiplas análises (cruzadas e temporais) dinamicamente na mesma sessão.
- **Otimização de Performance:** Carregamento de dados otimizado usando o formato Parquet e o cache do Streamlit (`@st.cache_data`) para garantir alta responsividade.

## Arquitetura do Projeto

O projeto é dividido em duas partes principais:

1.  **Pipeline de Preparação de Dados (`data_processing.py`):**
    Um script offline responsável por realizar o ETL (Extração, Transformação e Carga). Ele serve como um modelo para ler dados brutos (de planilhas Excel, CSV, etc.), realizar a limpeza, fusão (`merge`), agregação de informações e, por fim, salvar o resultado em um arquivo Parquet otimizado para consumo.

2.  **Aplicação Web (Streamlit):**
    Composta pelo `app.py` e o módulo `src`, esta é a interface com o usuário. Ela carrega o arquivo Parquet pré-processado e fornece todos os componentes interativos para a análise dos dados. A estrutura modular no diretório `src` separa as responsabilidades de configuração, carregamento de dados, gerenciamento de estado e componentes da interface.

## Como Executar o Projeto

Siga os passos abaixo para configurar e executar a aplicação localmente.

### Pré-requisitos

- Python 3.13 ou superior
- Git (opcional, para clonar o repositório)

### Passos

1.  **Clone o repositório:**
    ```bash
    git clone <URL_DO_REPOSITORIO>
    cd <NOME_DO_DIRETORIO>
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    (Nota: Crie um arquivo `requirements.txt` com as bibliotecas abaixo)
    ```
    streamlit
    pandas
    plotly
    openpyxl
    pyarrow
    rich
    ```
    Execute o comando de instalação:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Prepare os Dados (ETL):**
    A aplicação consome um arquivo de dados otimizado no formato Parquet. O script `data_processing.py` serve como um pipeline de exemplo para converter e tratar dados brutos.
    
    a. **Adapte o Pipeline:** Modifique o script `data_processing.py` para ler seus arquivos de dados de origem. Será necessário ajustar os caminhos dos arquivos de entrada e, possivelmente, a lógica de tratamento (nomes de colunas, transformações) para adequá-la ao seu dataset.
    
    b. **Execute o Pipeline:**
    ```bash
    python data_processing.py
    ```
    c. **Configure o Caminho de Dados:** Após a execução, o script gerará um arquivo `.parquet`. Certifique-se de que este arquivo seja salvo no caminho especificado pela variável `PATH_DF_TRATADO_PARQUET` dentro do arquivo `src/config.py`. Por padrão, a aplicação procurará o arquivo no diretório `data/`.

5.  **Execute a Aplicação Streamlit:**
    ```bash
    streamlit run app.py
    ```
    A aplicação será aberta automaticamente no seu navegador padrão.

## Estrutura do Repositório

```
.
├── data/
│   └── (coloque_seu_arquivo_tratado.parquet_aqui)
├── src/
│   ├── __init__.py
│   ├── config.py             # Configurações globais, constantes e textos da UI
│   ├── data_loader.py        # Módulo para carregar os dados com cache
│   ├── gui_components.py     # Lógica para renderizar todos os componentes da UI
│   └── state_manager.py      # Gerenciamento do estado da sessão (st.session_state)
├── app.py                    # Ponto de entrada da aplicação Streamlit
├── data_processing.py        # Script modelo do pipeline de preparação dos dados
└── README.md                 # Este arquivo
```