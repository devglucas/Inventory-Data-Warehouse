select
    {{ normalizar_sku('sku') }} as sku,
    cd as cd_id,
    {{ para_data('data', '%Y-%m-%d') }} as data_demanda,
    cast(quantidade as {{ dbt.type_int() }}) as quantidade
from {{ source('raw', 'demanda_perdida') }}
