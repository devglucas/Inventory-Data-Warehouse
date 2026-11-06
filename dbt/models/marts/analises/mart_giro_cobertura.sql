-- Situação de cada SKU em cada CD na última data, com o consumo médio da janela configurada.
with ultima as (
    select max(data) as data from {{ ref('fct_estoque_diario') }}
),

consumo as (
    select
        e.sku,
        e.cd_id,
        sum(e.saidas_venda) * 1.0 / {{ var('janela_consumo_dias') }} as consumo_diario
    from {{ ref('fct_estoque_diario') }} e
    cross join ultima u
    where e.data > cast({{ dbt.dateadd('day', -var('janela_consumo_dias'), 'u.data') }} as date)
    group by 1, 2
),

anual as (
    select
        sku,
        cd_id,
        sum(saidas_venda * custo_vigente) as custo_vendido,
        avg(valor_estoque) as valor_medio
    from {{ ref('fct_estoque_diario') }}
    group by 1, 2
),

base as (
    select
        e.sku,
        e.cd_id,
        e.categoria,
        p.ativo,
        abc.classe_abc,
        e.saldo,
        e.valor_estoque,
        c.consumo_diario,
        case when c.consumo_diario > 0 then e.saldo / c.consumo_diario end as dias_cobertura,
        a.custo_vendido / nullif(a.valor_medio, 0) as giro_anual
    from {{ ref('fct_estoque_diario') }} e
    inner join ultima u on e.data = u.data
    inner join consumo c on e.sku = c.sku and e.cd_id = c.cd_id
    inner join anual a on e.sku = a.sku and e.cd_id = a.cd_id
    inner join {{ ref('mart_curva_abc') }} abc on e.sku = abc.sku
    inner join {{ ref('dim_produto') }} p on e.sku = p.sku and p.vigente
)

select
    cast(sku as string) as sku,
    cast(cd_id as string) as cd_id,
    cast(categoria as string) as categoria,
    cast(ativo as boolean) as ativo,
    cast(classe_abc as string) as classe_abc,
    cast(saldo as int64) as saldo,
    cast(valor_estoque as numeric) as valor_estoque,
    cast(consumo_diario as numeric) as consumo_diario,
    cast(dias_cobertura as numeric) as dias_cobertura,
    cast(giro_anual as numeric) as giro_anual,
    cast(case
        when saldo <= 0 then 'ruptura'
        when consumo_diario = 0 then 'sem_giro'
        when dias_cobertura < {{ var('dias_risco_cobertura') }} then 'risco'
        when dias_cobertura > {{ var('dias_excesso_cobertura') }} then 'excesso'
        else 'saudavel'
    end as string) as situacao
from base
