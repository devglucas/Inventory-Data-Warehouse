{# Grafias aceitas: ' sku00123 ', 'SKU123', 'sku-00123'. Resultado: SKU-00123. #}
{% macro normalizar_sku(coluna) %}{{ return(adapter.dispatch('normalizar_sku')(coluna)) }}{% endmacro %}

{% macro default__normalizar_sku(coluna) -%}
    concat('SKU-', lpad(regexp_replace({{ coluna }}, '[^0-9]', '', 'g'), 5, '0'))
{%- endmacro %}

{% macro bigquery__normalizar_sku(coluna) -%}
    concat('SKU-', lpad(regexp_replace({{ coluna }}, r'[^0-9]', ''), 5, '0'))
{%- endmacro %}
