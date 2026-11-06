select
    d.inicio_mes as mes,
    e.cd_id,
    e.categoria,
    sum(e.saldo) as unidades,
    sum(e.valor_estoque) as valor_estoque
from {{ ref('fct_estoque_diario') }} e
inner join {{ ref('dim_data') }} d on e.data = d.data
where d.fim_de_mes
group by 1, 2, 3
