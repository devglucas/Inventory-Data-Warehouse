# Relatório de estoque: Ponte Alta Distribuidora

## Resumo

- Valor do estoque em 31/12/2025: R$ 977.891,74
- Receita perdida por falta de estoque: R$ 233.926,54
- Estoque parado: R$ 17.704,94
- dbt: {'success': 31, 'pass': 67, 'warn': 2, 'no-op': 1}

## Giro e cobertura por CD

| cd_id | valor_estoque | giro_mediano | cobertura_mediana_dias |
|---|---|---|---|
| CWB | 230.735,95 | 10,15 | 31,28 |
| GRU | 494.857,20 | 11,93 | 28,88 |
| REC | 234.823,60 | 5,69 | 42,63 |

## Situação por CD

| cd_id | situacao | sku_cds | valor_estoque |
|---|---|---|---|
| CWB | excesso | 1 | 163,59 |
| CWB | risco | 5 | 7.470,70 |
| CWB | ruptura | 2 | 0,00 |
| CWB | saudavel | 300 | 223.101,66 |
| CWB | sem_giro | 12 | 5.562,38 |
| GRU | risco | 4 | 299,14 |
| GRU | ruptura | 2 | 0,00 |
| GRU | saudavel | 302 | 494.558,06 |
| GRU | sem_giro | 12 | 7.537,25 |
| REC | excesso | 49 | 50.610,16 |
| REC | risco | 2 | 228,26 |
| REC | ruptura | 1 | 0,00 |
| REC | saudavel | 255 | 183.755,23 |
| REC | sem_giro | 13 | 4.605,31 |

## Ruptura por mês

| mes | taxa_ruptura | unidades_perdidas | receita_perdida | margem_perdida |
|---|---|---|---|---|
| 2025-01 | 0,002 | 18,000 | 533,090 | 188,750 |
| 2025-02 | 0,002 | 12,000 | 1.040,600 | 358,160 |
| 2025-03 | 0,003 | 14,000 | 823,030 | 309,480 |
| 2025-04 | 0,003 | 25,000 | 1.059,420 | 344,510 |
| 2025-05 | 0,004 | 36,000 | 2.782,250 | 954,850 |
| 2025-06 | 0,003 | 30,000 | 1.867,530 | 657,000 |
| 2025-07 | 0,003 | 33,000 | 673,090 | 231,970 |
| 2025-08 | 0,004 | 95,000 | 3.070,770 | 1.147,460 |
| 2025-09 | 0,012 | 408,000 | 17.150,200 | 6.490,800 |
| 2025-10 | 0,013 | 732,000 | 27.448,050 | 9.418,890 |
| 2025-11 | 0,040 | 3.868,000 | 158.616,510 | 47.635,330 |
| 2025-12 | 0,011 | 437,000 | 18.862,000 | 7.155,620 |

## Ruptura por fornecedor

| fornecedor_id | nome | taxa_ruptura | unidades_perdidas | receita_perdida | margem_perdida |
|---|---|---|---|---|---|
| F01 | Metalúrgica Forte | 0,029 | 2.626,000 | 101.604,610 | 39.045,110 |
| F04 | Luminar Componentes | 0,009 | 2.291,000 | 91.854,090 | 21.718,090 |
| F05 | Tubonorte | 0,005 | 350,000 | 14.568,310 | 5.072,320 |
| F06 | Proteja EPIs | 0,005 | 86,000 | 7.570,060 | 2.788,890 |
| F02 | Aço Sul Ferramentas | 0,006 | 177,000 | 7.425,380 | 2.640,880 |
| F03 | Eletrofio Condutores | 0,003 | 94,000 | 7.195,400 | 2.290,540 |
| F07 | Cor Viva Tintas | 0,003 | 46,000 | 2.227,000 | 785,750 |
| F08 | Rosca Fina Fixadores | 0,003 | 38,000 | 1.481,690 | 551,240 |

## Curva ABC

| classe_abc | skus | receita |
|---|---|---|
| A | 77 | 14.059.928,01 |
| B | 113 | 2.650.573,01 |
| C | 130 | 887.194,63 |

## Acuracidade das contagens

| cd_id | categoria | contagens | acuracidade | diferenca_unidades | diferenca_valor |
|---|---|---|---|---|---|
| CWB | EPI | 29 | 0,931 | -2,000 | -107,060 |
| CWB | Elétrica | 275 | 0,971 | -23,000 | -1.049,070 |
| CWB | Ferramentas | 208 | 0,952 | -20,000 | -319,470 |
| CWB | Fixadores | 62 | 1,000 | 0,000 | 0,000 |
| CWB | Hidráulica | 139 | 0,986 | -12,000 | -162,990 |
| CWB | Pintura | 88 | 0,966 | -4,000 | -125,240 |
| CWB | Segurança | 60 | 0,983 | -5,000 | -97,400 |
| GRU | EPI | 38 | 1,000 | -4,000 | -27,410 |
| GRU | Elétrica | 251 | 0,952 | -47,000 | -1.191,240 |
| GRU | Ferramentas | 209 | 0,928 | -43,000 | -1.201,530 |
| GRU | Fixadores | 57 | 0,930 | -6,000 | -263,320 |
| GRU | Hidráulica | 149 | 0,966 | -22,000 | -399,840 |
| GRU | Pintura | 77 | 0,974 | -4,000 | -159,510 |
| GRU | Segurança | 39 | 0,949 | -9,000 | -315,420 |
| REC | EPI | 30 | 0,933 | -3,000 | -66,360 |
| REC | Elétrica | 229 | 0,961 | -21,000 | -569,240 |
| REC | Ferramentas | 195 | 0,410 | -287,000 | -7.840,470 |
| REC | Fixadores | 60 | 0,950 | -3,000 | -90,080 |
| REC | Hidráulica | 173 | 0,988 | -8,000 | -75,300 |
| REC | Pintura | 92 | 0,957 | -4,000 | -103,420 |
| REC | Segurança | 63 | 0,921 | -8,000 | -381,170 |

## Movimentos rejeitados

| motivo | linhas |
|---|---|
| sku_desconhecido | 68 |
| quantidade_invalida | 27 |

## Conferência com o gabarito

| verificacao | resultado | detalhe |
|---|---|---|
| gabarito: movimentos válidos | ok | 137492 x 137492 |
| gabarito: unidades vendidas | ok | 399767.0 x 399767 |
| gabarito: demanda perdida | ok | 5708.0 x 5708 |
| gabarito: pedidos de compra | ok | 3691 x 3691 |
| gabarito: contagens | ok | 2523 x 2523 |
| gabarito: unidades em trânsito | ok | 8.0 x 8 |
| gabarito: SKU inexistente | ok | 68 x 68 |
| gabarito: quantidade inválida | ok | 27 x 27 |
| gabarito: saldo total nos 12 fins de mês | ok | 0 meses diferentes |
| gabarito: saldo final por CD | ok | {'REC': 7808, 'CWB': 7756, 'GRU': 16548} |
| gabarito: valor do estoque final | ok | 977891.74 x 977891.74 |
