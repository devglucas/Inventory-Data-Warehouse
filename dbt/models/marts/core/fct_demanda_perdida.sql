select
    d.sku,
    d.cd_id,
    d.data_demanda,
    d.quantidade,
    p.categoria,
    p.fornecedor_id,
    p.preco,
    d.quantidade * p.preco as receita_perdida,
    d.quantidade * (p.preco - p.custo) as margem_perdida
from {{ ref('stg_vendas__demanda_perdida') }} d
inner join {{ ref('dim_produto') }} p
    on d.sku = p.sku
    and {{ para_instante('d.data_demanda') }} >= p.valido_de
    and ({{ para_instante('d.data_demanda') }} < p.valido_ate or p.valido_ate is null)
