-- Ruptura por mês e fornecedor. SKU descontinuado sem saldo não é ruptura: ninguém está tentando vender.
with ativos as (
    select e.sku, e.cd_id, e.data, e.fornecedor_id, e.sem_estoque
    from {{ ref('fct_estoque_diario') }} e
    inner join {{ ref('dim_produto') }} p on e.sku = p.sku and p.vigente and p.ativo
),

dias as (
    select
        cast({{ dbt.date_trunc('month', 'data') }} as date) as mes,
        fornecedor_id,
        count(*) as sku_dias,
        sum(case when sem_estoque then 1 else 0 end) as sku_dias_sem_estoque
    from ativos
    group by 1, 2
),

perdas as (
    select
        cast({{ dbt.date_trunc('month', 'data_demanda') }} as date) as mes,
        fornecedor_id,
        sum(quantidade) as unidades_perdidas,
        sum(receita_perdida) as receita_perdida,
        sum(margem_perdida) as margem_perdida
    from {{ ref('fct_demanda_perdida') }}
    group by 1, 2
)

select
    d.mes,
    d.fornecedor_id,
    d.sku_dias,
    d.sku_dias_sem_estoque,
    d.sku_dias_sem_estoque * 1.0 / d.sku_dias as taxa_ruptura,
    coalesce(p.unidades_perdidas, 0) as unidades_perdidas,
    coalesce(p.receita_perdida, 0) as receita_perdida,
    coalesce(p.margem_perdida, 0) as margem_perdida
from dias d
left join perdas p on d.mes = p.mes and d.fornecedor_id = p.fornecedor_id
