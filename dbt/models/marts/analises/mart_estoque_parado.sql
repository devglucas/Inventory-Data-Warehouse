-- Capital parado: saldo positivo e nenhuma venda há mais tempo que o limite.
with ultima as (
    select max(data) as data from {{ ref('fct_estoque_diario') }}
),

ultima_venda as (
    select sku, cd_id, max(data) as data_ultima_venda
    from {{ ref('fct_estoque_diario') }}
    where saidas_venda > 0
    group by 1, 2
)

select
    e.sku,
    e.cd_id,
    e.categoria,
    p.ativo,
    e.saldo,
    e.valor_estoque,
    v.data_ultima_venda,
    {{ dbt.datediff('v.data_ultima_venda', 'u.data', 'day') }} as dias_sem_venda
from {{ ref('fct_estoque_diario') }} e
inner join ultima u on e.data = u.data
inner join {{ ref('dim_produto') }} p on e.sku = p.sku and p.vigente
left join ultima_venda v on e.sku = v.sku and e.cd_id = v.cd_id
where e.saldo > 0
    and (v.data_ultima_venda is null
        or {{ dbt.datediff('v.data_ultima_venda', 'u.data', 'day') }} >= {{ var('dias_sem_venda_parado') }})
