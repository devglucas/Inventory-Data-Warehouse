select
    c.sku,
    c.cd_id,
    c.data_contagem,
    c.quantidade_sistema,
    c.quantidade_contada,
    c.quantidade_contada - c.quantidade_sistema as diferenca,
    p.categoria,
    p.custo,
    (c.quantidade_contada - c.quantidade_sistema) * p.custo as diferenca_valor,
    abs(c.quantidade_contada - c.quantidade_sistema) <= greatest(c.quantidade_sistema, 1) * {{ var('tolerancia_contagem') }} as dentro_da_tolerancia
from {{ ref('stg_wms__contagens') }} c
inner join {{ ref('dim_produto') }} p
    on c.sku = p.sku
    and {{ para_instante('c.data_contagem') }} >= p.valido_de
    and ({{ para_instante('c.data_contagem') }} < p.valido_ate or p.valido_ate is null)
