-- Nada some: todo id que chegou virou movimento ou foi rejeitado com motivo.
with recebidos as (select count(distinct movimento_id) as n from {{ source('raw', 'movimentos') }}),
aceitos as (select count(*) as n from {{ ref('fct_movimentos') }}),
rejeitados as (select count(*) as n from {{ ref('int_movimentos_rejeitados') }})

select r.n as recebidos, a.n as aceitos, j.n as rejeitados
from recebidos r cross join aceitos a cross join rejeitados j
where r.n <> a.n + j.n
