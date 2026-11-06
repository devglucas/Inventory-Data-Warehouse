{{ config(severity='warn') }}
-- Lançamento errado que só é estornado dias depois pode deixar o saldo negativo por um tempo.
select sku, cd_id, data, saldo from {{ ref('fct_estoque_diario') }} where saldo < 0
