-- Transforma cada linha do razão em impacto no saldo, em unidades.
--   1. o fator de caixa é o que valia na data do movimento, vindo do snapshot
--   2. o sinal vem do tipo, porque o WMS mudou a convenção em julho
--   3. ajuste já tem sinal; estorno é o inverso do movimento original
with movimentos as (
    select * from {{ ref('stg_wms__movimentos') }}
),

produto_vigente as (
    select
        m.movimento_id,
        p.unidades_por_caixa,
        p.custo
    from movimentos m
    inner join {{ ref('snap_produtos') }} p
        on m.sku = p.sku
        and m.ocorrido_em >= p.dbt_valid_from
        and (m.ocorrido_em < p.dbt_valid_to or p.dbt_valid_to is null)
),

em_unidades as (
    select
        m.*,
        t.tipo,
        t.sinal,
        t.grupo,
        v.custo as custo_vigente,
        case when m.unidade = 'CX' then abs(m.quantidade) * v.unidades_por_caixa else abs(m.quantidade) end as unidades
    from movimentos m
    inner join {{ ref('tipos_movimento') }} t on m.tipo_origem = t.tipo_origem
    inner join produto_vigente v on m.movimento_id = v.movimento_id
    where m.cd_id is not null and m.quantidade is not null and m.ocorrido_em is not null
),

com_impacto as (
    select
        *,
        case when tipo = 'AJUSTE_INVENTARIO' then quantidade else unidades * sinal end as impacto_direto
    from em_unidades
)

select
    c.movimento_id,
    c.sku,
    c.cd_id,
    c.tipo,
    c.grupo,
    c.unidades,
    case when c.tipo = 'ESTORNO' then -coalesce(o.impacto_direto, 0) else c.impacto_direto end as impacto,
    c.custo_vigente,
    c.ocorrido_em,
    cast(c.ocorrido_em as date) as data_movimento,
    c.referencia,
    c._arquivo,
    c._carregado_em
from com_impacto c
left join com_impacto o
    on c.tipo = 'ESTORNO' and cast(o.movimento_id as {{ dbt.type_string() }}) = c.referencia
