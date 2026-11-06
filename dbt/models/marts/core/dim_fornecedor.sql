select fornecedor_id, nome, categoria_principal, prazo_contratual_dias from {{ ref('stg_erp__fornecedores') }}
