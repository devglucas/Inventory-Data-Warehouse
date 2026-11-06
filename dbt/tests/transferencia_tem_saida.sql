-- Unidade não pode chegar sem ter saído de algum lugar.
with entradas as (select referencia, sku from {{ ref('fct_movimentos') }} where tipo = 'TRANSF_ENTRADA'),
saidas as (select referencia, sku from {{ ref('fct_movimentos') }} where tipo = 'TRANSF_SAIDA')

select e.* from entradas e left join saidas s on e.referencia = s.referencia and e.sku = s.sku
where s.referencia is null
