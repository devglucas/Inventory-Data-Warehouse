-- Desempenho por fornecedor e trimestre de emissão. Item ainda sem entrega não entra no prazo médio.
select
    i.fornecedor_id,
    f.nome,
    f.prazo_contratual_dias,
    cast({{ dbt.date_trunc('quarter', 'i.emitido_em') }} as date) as trimestre,
    count(*) as itens,
    sum(case when i.ultima_entrega is not null then 1 else 0 end) as itens_entregues,
    avg(i.lead_time_dias) as lead_time_medio,
    avg(i.atraso_dias) as atraso_medio,
    sum(case when i.no_prazo_e_completo then 1 else 0 end) * 1.0 / count(*) as otif
from {{ ref('fct_itens_pedido') }} i
inner join {{ ref('dim_fornecedor') }} f on i.fornecedor_id = f.fornecedor_id
where i.emitido_em <= cast({{ dbt.dateadd('day', -45, "cast('" ~ var('data_fim') ~ "' as date)") }} as date)
group by 1, 2, 3, 4
