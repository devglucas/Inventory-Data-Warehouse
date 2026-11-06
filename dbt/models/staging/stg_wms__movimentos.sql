-- Limpa o razão, sem aplicar regra de negócio. Reenvio e correção têm o mesmo id:
-- vale a última versão que chegou.
with origem as (
    select * from {{ source('raw', 'movimentos') }}
),

ultima_versao as (
    select *
    from origem
    where true
    qualify row_number() over (partition by movimento_id order by _carregado_em desc) = 1
)

select
    cast(movimento_id as {{ dbt.type_bigint() }}) as movimento_id,
    {{ normalizar_sku('sku') }} as sku,
    apelido.cd_id,
    upper(trim(cd)) as cd_origem,
    upper(trim(tipo)) as tipo_origem,
    {{ para_numero('quantidade') }} as quantidade,
    quantidade as quantidade_origem,
    upper(trim(unidade)) as unidade,
    {{ para_momento('momento') }} as ocorrido_em,
    nullif(referencia, '') as referencia,
    _arquivo,
    _carregado_em
from ultima_versao
left join {{ ref('cd_apelidos') }} as apelido
    on upper(trim(ultima_versao.cd)) = apelido.apelido
