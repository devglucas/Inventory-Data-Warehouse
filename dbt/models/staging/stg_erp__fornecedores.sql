select
    fornecedor_id,
    trim(nome) as nome,
    categoria_principal,
    cast(prazo_contratual_dias as {{ dbt.type_int() }}) as prazo_contratual_dias
from {{ source('raw', 'fornecedores') }}
