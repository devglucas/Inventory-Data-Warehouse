-- Snapshot periódico: uma linha por SKU, CD e dia, mesmo nos dias sem movimento.
-- O saldo é o saldo inicial mais a soma acumulada dos impactos.
{{ config(
    partition_by={'field': 'data', 'data_type': 'date', 'granularity': 'month'} if target.type == 'bigquery' else none,
    cluster_by=['sku', 'cd_id'] if target.type == 'bigquery' else none
) }}

with pares as (
    select sku, cd_id, quantidade as saldo_inicial, data_saldo from {{ ref('stg_wms__saldo_inicial') }}
),

por_dia as (
    select
        sku,
        cd_id,
        data_movimento as data,
        sum(impacto) as impacto,
        sum(case when grupo = 'venda' then -impacto else 0 end) as saidas_venda,
        sum(case when grupo = 'compra' then impacto else 0 end) as entradas_compra
    from {{ ref('fct_movimentos') }}
    group by 1, 2, 3
),

grade as (
    select p.sku, p.cd_id, p.saldo_inicial, d.data
    from pares p
    cross join {{ ref('dim_data') }} d
    where d.data > p.data_saldo
),

saldos as (
    select
        g.sku,
        g.cd_id,
        g.data,
        coalesce(m.saidas_venda, 0) as saidas_venda,
        coalesce(m.entradas_compra, 0) as entradas_compra,
        g.saldo_inicial + sum(coalesce(m.impacto, 0)) over (
            partition by g.sku, g.cd_id order by g.data rows between unbounded preceding and current row
        ) as saldo
    from grade g
    left join por_dia m on g.sku = m.sku and g.cd_id = m.cd_id and g.data = m.data
)

select
    s.sku,
    s.cd_id,
    s.data,
    s.saldo,
    s.saidas_venda,
    s.entradas_compra,
    s.saldo <= 0 as sem_estoque,
    p.custo as custo_vigente,
    p.preco as preco_vigente,
    p.categoria,
    p.fornecedor_id,
    s.saldo * p.custo as valor_estoque
from saldos s
inner join {{ ref('dim_produto') }} p
    on s.sku = p.sku
    and {{ para_instante(dbt.dateadd('day', 1, 's.data')) }} > p.valido_de
    and ({{ para_instante(dbt.dateadd('day', 1, 's.data')) }} <= p.valido_ate or p.valido_ate is null)
