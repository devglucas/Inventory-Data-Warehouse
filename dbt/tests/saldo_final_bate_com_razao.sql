-- O saldo de 31/12 precisa ser o saldo inicial mais todos os movimentos.
with razao as (
    select sku, cd_id, sum(impacto) as impacto from {{ ref('fct_movimentos') }} group by 1, 2
),

esperado as (
    select s.sku, s.cd_id, s.quantidade + coalesce(r.impacto, 0) as saldo
    from {{ ref('stg_wms__saldo_inicial') }} s
    left join razao r on s.sku = r.sku and s.cd_id = r.cd_id
)

select e.sku, e.cd_id, e.saldo as esperado, f.saldo as calculado
from esperado e
inner join {{ ref('fct_estoque_diario') }} f
    on e.sku = f.sku and e.cd_id = f.cd_id and f.data = cast('{{ var("data_fim") }}' as date)
where e.saldo <> f.saldo
