select
    {{ normalizar_sku('sku') }} as sku,
    cd as cd_id,
    {{ para_data('data', '%d/%m/%Y') }} as data_saldo,
    cast(quantidade as {{ dbt.type_int() }}) as quantidade
from {{ source('raw', 'saldo_inicial') }}
