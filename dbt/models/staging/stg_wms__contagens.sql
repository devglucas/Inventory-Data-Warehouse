select
    {{ normalizar_sku('sku') }} as sku,
    cd as cd_id,
    {{ para_data('data', '%d/%m/%Y') }} as data_contagem,
    cast(quantidade_sistema as {{ dbt.type_int() }}) as quantidade_sistema,
    cast(quantidade_contada as {{ dbt.type_int() }}) as quantidade_contada
from {{ source('raw', 'contagens') }}
