-- Classifica cada SKU pela participação acumulada na receita de venda.
with receita as (
    select sku, sum(saidas_venda * preco_vigente) as receita
    from {{ ref('fct_estoque_diario') }}
    group by 1
),

acumulado as (
    select
        sku,
        receita,
        sum(receita) over (order by receita desc, sku rows between unbounded preceding and current row)
            / nullif(sum(receita) over (), 0) as participacao_acumulada
    from receita
)

select
    sku,
    receita,
    participacao_acumulada,
    case
        when participacao_acumulada <= 0.8 then 'A'
        when participacao_acumulada <= 0.95 then 'B'
        else 'C'
    end as classe_abc
from acumulado
