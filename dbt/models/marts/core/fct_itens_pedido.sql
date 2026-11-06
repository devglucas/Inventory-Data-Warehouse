-- Um item de pedido por linha, com a primeira e a última entrega. Recebimento parcial é o caso comum de OTIF ruim.
with itens as (
    select
        pedido_id,
        fornecedor_id,
        cd_id,
        sku,
        min(emitido_em) as emitido_em,
        min(previsto_para) as previsto_para,
        min(unidades_pedidas) as unidades_pedidas,
        min(custo_unitario) as custo_unitario,
        min(recebido_em) as primeira_entrega,
        max(recebido_em) as ultima_entrega,
        coalesce(sum(unidades_recebidas), 0) as unidades_recebidas
    from {{ ref('stg_compras__recebimentos') }}
    group by 1, 2, 3, 4
)

select
    {{ dbt_utils.generate_surrogate_key(['pedido_id', 'sku']) }} as item_chave,
    *,
    {{ dbt.datediff('emitido_em', 'ultima_entrega', 'day') }} as lead_time_dias,
    {{ dbt.datediff('previsto_para', 'ultima_entrega', 'day') }} as atraso_dias,
    unidades_recebidas >= unidades_pedidas as completo,
    ultima_entrega is not null and ultima_entrega <= previsto_para and unidades_recebidas >= unidades_pedidas as no_prazo_e_completo
from itens
