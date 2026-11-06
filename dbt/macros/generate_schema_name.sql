{# Usa o nome do esquema como está, em vez de prefixar com o esquema do perfil. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name if custom_schema_name else target.schema }}
{%- endmacro %}
