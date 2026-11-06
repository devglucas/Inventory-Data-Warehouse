-- O que não virou movimento, com o motivo. A singular test de conciliação garante que nada some.
with movimentos as (
    select * from {{ ref('stg_wms__movimentos') }}
),

classificados as (
    select movimento_id from {{ ref('int_movimentos_classificados') }}
),

produtos as (
    select distinct sku from {{ ref('snap_produtos') }}
)

select
    m.movimento_id,
    m.sku,
    m.cd_origem,
    m.tipo_origem,
    m.quantidade_origem,
    m._arquivo,
    case
        when p.sku is null then 'sku_desconhecido'
        when m.cd_id is null then 'cd_desconhecido'
        when m.quantidade is null then 'quantidade_invalida'
        when m.ocorrido_em is null then 'data_invalida'
        else 'tipo_ou_vigencia_desconhecidos'
    end as motivo
from movimentos m
left join classificados c on m.movimento_id = c.movimento_id
left join produtos p on m.sku = p.sku
where c.movimento_id is null
