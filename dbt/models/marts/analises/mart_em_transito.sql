-- Saída de transferência sem a entrada correspondente: unidades que não estão em nenhum CD.
with saidas as (
    select referencia, sku, cd_id as cd_origem, data_movimento, -impacto as unidades, custo_vigente
    from {{ ref('fct_movimentos') }}
    where tipo = 'TRANSF_SAIDA'
),

entradas as (
    select referencia, sku from {{ ref('fct_movimentos') }} where tipo = 'TRANSF_ENTRADA'
)

select s.*, s.unidades * s.custo_vigente as valor
from saidas s
left join entradas e on s.referencia = e.referencia and s.sku = e.sku
where e.referencia is null
