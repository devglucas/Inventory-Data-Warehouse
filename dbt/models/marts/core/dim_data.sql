with dias as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('" ~ var('data_inicio') ~ "' as date)",
        end_date=dbt.dateadd('day', 1, "cast('" ~ var('data_fim') ~ "' as date)")
    ) }}
)

select
    cast(date_day as date) as data,
    extract(year from date_day) as ano,
    extract(month from date_day) as mes,
    extract(quarter from date_day) as trimestre,
    cast({{ dbt.date_trunc('month', 'date_day') }} as date) as inicio_mes,
    cast(date_day as date) = cast({{ dbt.last_day('date_day', 'month') }} as date) as fim_de_mes
from dias
