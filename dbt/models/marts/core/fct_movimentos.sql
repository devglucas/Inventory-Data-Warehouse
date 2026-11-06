-- Fato no grão da linha do razão. Incremental: cada carga traz só o que chegou depois da última,
-- e o unique_key faz a versão corrigida substituir a anterior, mesmo meses depois.
{{ config(
    materialized='incremental',
    unique_key='movimento_id',
    incremental_strategy='merge',
    on_schema_change='fail',
    partition_by={'field': 'data_movimento', 'data_type': 'date', 'granularity': 'month'} if target.type == 'bigquery' else none,
    cluster_by=['sku', 'cd_id'] if target.type == 'bigquery' else none
) }}

with classificados as (
    select * from {{ ref('int_movimentos_classificados') }}
)

{% if is_incremental() %}
, novos as (
    select movimento_id, _carregado_em
    from classificados
    where _carregado_em > (select max(carregado_em) from {{ this }})
)
{% endif %}

select
    movimento_id,
    {{ dbt_utils.generate_surrogate_key(['sku', 'cd_id']) }} as sku_cd_chave,
    sku,
    cd_id,
    tipo,
    grupo,
    unidades,
    impacto,
    custo_vigente,
    impacto * custo_vigente as impacto_valor,
    ocorrido_em,
    data_movimento,
    referencia,
    _carregado_em as carregado_em
from classificados
{% if is_incremental() %}
where movimento_id in (select movimento_id from novos)
    -- estorno herda a quantidade do original: se o original foi corrigido, o estorno antigo precisa ser refeito
    or (tipo = 'ESTORNO' and referencia in (select cast(movimento_id as {{ dbt.type_string() }}) from novos))
{% endif %}
