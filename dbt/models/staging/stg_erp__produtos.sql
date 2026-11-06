-- Última foto do catálogo. É ela que alimenta o snapshot: quem guarda o histórico é o dbt.
with ultima_foto as (
    select *
    from {{ source('raw', 'produtos') }}
    where _arquivo = (select max(_arquivo) from {{ source('raw', 'produtos') }})
),

normalizado as (
    select
        {{ normalizar_sku('sku') }} as sku,
        trim(nome) as nome,
        -- o ERP às vezes exporta em maiúsculas: a primeira letra alta, o resto como veio cadastrado
        case upper(trim(categoria))
            when 'ELÉTRICA' then 'Elétrica'
            when 'HIDRÁULICA' then 'Hidráulica'
            when 'SEGURANÇA' then 'Segurança'
            when 'EPI' then 'EPI'
            when 'FERRAMENTAS' then 'Ferramentas'
            when 'PINTURA' then 'Pintura'
            when 'FIXADORES' then 'Fixadores'
            else trim(categoria)
        end as categoria,
        fornecedor_id,
        {{ para_numero('custo') }} as custo,
        {{ para_numero('preco') }} as preco,
        cast(unidades_por_caixa as {{ dbt.type_int() }}) as unidades_por_caixa,
        lower(ativo) = 'true' as ativo,
        {{ para_momento('atualizado_em') }} as atualizado_em
    from ultima_foto
)

select *
from normalizado
where true
qualify row_number() over (partition by sku order by atualizado_em desc) = 1
