select
    cd_id,
    categoria,
    count(*) as contagens,
    sum(case when dentro_da_tolerancia then 1 else 0 end) * 1.0 / count(*) as acuracidade,
    sum(diferenca) as diferenca_unidades,
    sum(diferenca_valor) as diferenca_valor
from {{ ref('fct_contagens') }}
group by 1, 2
