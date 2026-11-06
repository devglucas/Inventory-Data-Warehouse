-- Dimensão com histórico. Para o atributo atual, filtre vigente = true.
select
    {{ dbt_utils.generate_surrogate_key(['sku', 'dbt_valid_from']) }} as produto_chave,
    sku,
    nome,
    categoria,
    fornecedor_id,
    custo,
    preco,
    unidades_por_caixa,
    ativo,
    dbt_valid_from as valido_de,
    dbt_valid_to as valido_ate,
    dbt_valid_to is null as vigente
from {{ ref('snap_produtos') }}
