-- Antes de comprar, olhar a rede: SKU em risco em um CD e sobrando em outro.
with situacao as (
    select * from {{ ref('mart_giro_cobertura') }} where ativo
),

falta as (
    select sku, cd_id, saldo, consumo_diario, dias_cobertura
    from situacao
    where situacao in ('risco', 'ruptura') and consumo_diario > 0
),

sobra as (
    select sku, cd_id, saldo, consumo_diario,
           saldo - consumo_diario * {{ var('dias_excesso_cobertura') }} as excedente
    from situacao
    where situacao in ('excesso', 'sem_giro')
)

select
    f.sku,
    s.cd_id as cd_origem,
    f.cd_id as cd_destino,
    floor(least(s.excedente, f.consumo_diario * 30)) as unidades_sugeridas,
    f.dias_cobertura as cobertura_destino,
    p.custo * floor(least(s.excedente, f.consumo_diario * 30)) as compra_evitada
from falta f
inner join sobra s on f.sku = s.sku and f.cd_id <> s.cd_id
inner join {{ ref('dim_produto') }} p on f.sku = p.sku and p.vigente
where s.excedente >= 1 and f.consumo_diario * 30 >= 1
