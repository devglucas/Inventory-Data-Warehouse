-- Em cada SKU, uma versão termina exatamente onde a seguinte começa.
with versoes as (
    select sku, valido_ate, lead(valido_de) over (partition by sku order by valido_de) as proxima
    from {{ ref('dim_produto') }}
)

select * from versoes where proxima is not null and proxima <> valido_ate
