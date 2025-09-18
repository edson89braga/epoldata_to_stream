
Descrição da GUI Streamlit desejada:

- Sugere-se um appbar de barra superior contendo ao menos:
    - Título + Botão toggle dark/light mode
    - botão home
    - Botão Expand/collapse All sections_expanders
    - Quais outros widgets sugere aqui?

- home_page informativa sobre o que trata os dados da aplicação


- Tab "Agregações"
    - Essa aba apresenta as visualizações de acordo com nosso list_agregation_views, e de acordo com os filtros do side_bar;
    - Nas tabelas de agregações vamos unificar os valores nulos (nulls_placeholders_to_drop);
    
    - inicialmente com todos os expanders (sections) expandidos;

- list_agregation_views:
    - Cada section contem:
        - Pequeno botão indicativo do modo de visualização: tabela, gráfico, ou tabela + gráfico (default = gráfico);        
        - Pequeno botão para modo de cores do gráfico: monocromático ou multi-colors (default = monocromático);

        - A tabela é composta por 3 colunas: Valores da respectiva coluna_df, Contagem de valores, e Percentuais;
        - o gráfico deve possuir toggle de pelo menos dois modos: Colunas e Pizza;
        - A contagem de valores é sempre referente à key_column principal;

# TODO:
- explode columns específicas