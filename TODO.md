# TODO:

- Sugere-se um appbar de barra superior contendo ao menos:
    - Título + Botão toggle dark/light mode
    - Melhorar visualização dos rótulos de Tab e fixá-los
    - Quais outros widgets sugere aqui?

- Tab "Agregações"
    - Essa aba apresenta as visualizações de acordo com nosso list_agregation_views, e de acordo com os filtros do side_bar;
    - Nas tabelas de agregações vamos unificar os valores nulos (nulls_placeholders_to_drop);

- Cada section contem:
    - Pequeno botão indicativo do modo de visualização: tabela, gráfico, ou tabela + gráfico (default = gráfico);        
    - Pequeno botão para modo de cores do gráfico: monocromático ou multi-colors (default = monocromático);

    - A tabela é composta por 3 colunas: Valores da respectiva coluna_df, Contagem de valores, e Percentuais;
    - o gráfico deve possuir toggle de pelo menos dois modos: Colunas e Pizza;
    - A contagem de valores é sempre referente à key_column principal;


- explode columns específicas
- eliminação de null values 