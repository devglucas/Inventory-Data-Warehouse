{#
  O SQL dos modelos é o mesmo em DuckDB e BigQuery. O que muda entre os dois fica aqui,
  com dispatch: o dbt escolhe a versão do adaptador em uso.
#}

{% macro para_data(coluna, formato) %}{{ return(adapter.dispatch('para_data')(coluna, formato)) }}{% endmacro %}

{% macro default__para_data(coluna, formato) -%}
    cast(try_strptime(nullif({{ coluna }}, ''), '{{ formato }}') as date)
{%- endmacro %}

{% macro bigquery__para_data(coluna, formato) -%}
    safe.parse_date('{{ formato }}', nullif({{ coluna }}, ''))
{%- endmacro %}


{% macro para_momento(coluna) %}{{ return(adapter.dispatch('para_momento')(coluna)) }}{% endmacro %}

{% macro default__para_momento(coluna) -%}
    try_cast({{ coluna }} as timestamp)
{%- endmacro %}

{% macro bigquery__para_momento(coluna) -%}
    safe_cast({{ coluna }} as datetime)
{%- endmacro %}


{% macro para_numero(coluna) %}{{ return(adapter.dispatch('para_numero')(coluna)) }}{% endmacro %}

{% macro default__para_numero(coluna) -%}
    try_cast(nullif(replace({{ coluna }}, ',', '.'), '') as decimal(18, 4))
{%- endmacro %}

{% macro bigquery__para_numero(coluna) -%}
    safe_cast(nullif(replace({{ coluna }}, ',', '.'), '') as numeric)
{%- endmacro %}


{# Data como instante, para comparar com a validade das versões do snapshot. #}
{% macro para_instante(coluna) %}{{ return(adapter.dispatch('para_instante')(coluna)) }}{% endmacro %}

{% macro default__para_instante(coluna) -%}
    cast({{ coluna }} as timestamp)
{%- endmacro %}

{% macro bigquery__para_instante(coluna) -%}
    cast({{ coluna }} as datetime)
{%- endmacro %}
