select cd_id, nome, uf from {{ ref('centros_distribuicao') }}
