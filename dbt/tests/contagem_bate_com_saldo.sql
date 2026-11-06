{{ config(severity='warn') }}
-- Conciliação independente: depois do ajuste, o saldo calculado precisa ser o que foi contado.
select c.sku, c.cd_id, c.data_contagem, c.quantidade_contada, f.saldo
from {{ ref('fct_contagens') }} c
inner join {{ ref('fct_estoque_diario') }} f
    on c.sku = f.sku and c.cd_id = f.cd_id and c.data_contagem = f.data
where c.quantidade_contada <> f.saldo
