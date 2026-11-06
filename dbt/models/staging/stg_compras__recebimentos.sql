-- O ERP de compras grava datas em dois formatos. Tenta um e depois o outro.
select
    pedido_id,
    fornecedor_id,
    cd as cd_id,
    {{ normalizar_sku('sku') }} as sku,
    coalesce({{ para_data('emitido_em', '%Y-%m-%d') }}, {{ para_data('emitido_em', '%d/%m/%Y') }}) as emitido_em,
    coalesce({{ para_data('previsto_para', '%Y-%m-%d') }}, {{ para_data('previsto_para', '%d/%m/%Y') }}) as previsto_para,
    coalesce({{ para_data('recebido_em', '%Y-%m-%d') }}, {{ para_data('recebido_em', '%d/%m/%Y') }}) as recebido_em,
    cast(unidades_pedidas as {{ dbt.type_int() }}) as unidades_pedidas,
    {{ dbt.safe_cast("nullif(unidades_recebidas, '')", dbt.type_int()) }} as unidades_recebidas,
    {{ para_numero('custo_unitario') }} as custo_unitario,
    cast(recebimento_ordem as {{ dbt.type_int() }}) as recebimento_ordem
from {{ source('raw', 'pedidos_compra') }}
