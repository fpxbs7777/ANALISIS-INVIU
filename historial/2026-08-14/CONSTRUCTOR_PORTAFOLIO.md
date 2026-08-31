# Constructor de Portafolio — Sectores beneficiados por Murphy
**Fecha:** 2026-08-14

> Pipeline: sectores Murphy → unificado de tickers → métricas de riesgo-retorno → fundamentos → Markowitz max-Sharpe.

## Contexto Murphy
- Sectores líderes (200d): XLE, XLK, XLI
- Sectores del unificado seleccionados: Energía, Tecnología, Acciones Industriales

## Cash disponible
- USD: $10226.39
- ARS: $2056136.68

## Bucket ARS — Métricas cuantitativas de candidatos
| ticker   | nombre                                             | sector_json           | industria                                       |   rend_esperado_annual |   volatilidad_annual |      sharpe |     var_95 |   ultimo_precio |   news_score |   news_count |   news_bullish |   news_bearish |
|:---------|:---------------------------------------------------|:----------------------|:------------------------------------------------|-----------------------:|---------------------:|------------:|-----------:|----------------:|-------------:|-------------:|---------------:|---------------:|
| INTC.BA  | Intel Corporation                                  | Tecnología            | Semiconductores                                 |              2.01599   |             0.807949 |  2.44568    | -0.0591488 |         33140   |            4 |           10 |              4 |              0 |
| UGP.BA   | Ultrapar Participações S.A.                        | Energía               | Refinacion y comercializacion de petróleo y gas |              0.916293  |             0.411073 |  2.13172    | -0.0355322 |          9695   |            3 |           10 |              4 |              1 |
| AMD.BA   | Advanced Micro Devices, Inc.                       | Tecnología            | Semiconductores                                 |              1.43549   |             0.707232 |  1.97317    | -0.0573729 |         76500   |            4 |           10 |              4 |              0 |
| MRVL.BA  | Marvell Technology, Inc.                           | Tecnología            | Semiconductores                                 |              1.56901   |             0.791514 |  1.93175    | -0.0706742 |         25060   |            7 |           10 |              7 |              0 |
| ADI.BA   | Analog Devices, Inc.                               | Tecnología            | Semiconductores                                 |              0.754697  |             0.388083 |  1.84161    | -0.0354588 |         40140   |            7 |           10 |              8 |              1 |
| SLB.BA   | SLB N.V.                                           | Energía               | Equipos y servicios de petróleo y gas           |              0.737952  |             0.414387 |  1.6843     | -0.0349861 |         27500   |            5 |           10 |              6 |              1 |
| DAL.BA   | DELTA AIR LINES INC CEDEAR EACH                    | Acciones Industriales | Aerolíneas                                      |              0.766507  |             0.440196 |  1.65042    | -0.0392108 |         18120   |            2 |           10 |              3 |              1 |
| GARO.BA  | Garovaglio y Zorraquín S.A.                        | Acciones Industriales | Conglomerados                                   |              1.19644   |             0.765615 |  1.51047    | -0.043053  |           465   |            0 |            0 |              0 |              0 |
| FDX.BA   | FedEx Corporation                                  | Acciones Industriales | Transporte y logistica integrados               |              0.671387  |             0.420172 |  1.50269    | -0.0350891 |         53675   |           -2 |           10 |              0 |              2 |
| PBI.BA   | Pitney Bowes Inc.                                  | Acciones Industriales | Transporte y logistica integrados               |              0.707773  |             0.457462 |  1.45973    | -0.0412278 |         26540   |            7 |           10 |              7 |              0 |
| NVDA.BA  | NVIDIA Corporation                                 | Tecnología            | Semiconductores                                 |              0.484975  |             0.393411 |  1.13107    | -0.0393433 |         14850   |            3 |           10 |              3 |              0 |
| UAL.BA   | United Airlines Holdings, Inc.                     | Acciones Industriales | Aerolíneas                                      |              0.588396  |             0.520748 |  1.05309    | -0.0494823 |         40020   |            0 |           10 |              1 |              1 |
| MMM.BA   | 3M Company                                         | Acciones Industriales | Conglomerados                                   |              0.405739  |             0.347387 |  1.05283    | -0.0278618 |         28860   |            7 |           10 |              8 |              1 |
| HON.BA   | Honeywell International Inc.                       | Acciones Industriales | Conglomerados                                   |              0.320004  |             0.330343 |  0.847617   | -0.0307211 |         46299.9 |            8 |           10 |              8 |              0 |
| CADO.BA  | Carlos Casado S.A.                                 | Acciones Industriales | Conglomerados                                   |              0.226653  |             0.25039  |  0.745447   | -0.019647  |           544   |            0 |            0 |              0 |              0 |
| PAMP.BA  | Pampa Energía S.A.                                 | Acciones Industriales | Conglomerados                                   |              0.325454  |             0.390468 |  0.731055   | -0.0334433 |          5000   |            4 |           10 |              5 |              1 |
| CRES.BA  | Cresud S.A.                                        | Acciones Industriales | Conglomerados                                   |              0.321077  |             0.420492 |  0.668447   | -0.0333159 |          1676   |            3 |            3 |              3 |              0 |
| RENT3.BA | Localiza Rent a Car S.A.                           | Acciones Industriales | Servicios de alquiler y arrendamiento           |              0.401949  |             0.542023 |  0.667774   | -0.050418  |          5265   |            5 |           10 |              6 |              1 |
| QCOM.BA  | QUALCOMM Incorporated                              | Tecnología            | Semiconductores                                 |              0.37296   |             0.529732 |  0.628543   | -0.0540413 |         23700   |            3 |           10 |              3 |              0 |
| CAR.BA   | Avis Budget Group, Inc.                            | Acciones Industriales | Servicios de alquiler y arrendamiento           |              0.651092  |             1.02867  |  0.594059   | -0.0676727 |          8425   |            0 |           10 |              2 |              2 |
| TGSU2.BA | Transportadora de Gas del Sur S.A.                 | Energía               | Petróleo y Gas Integrados                       |              0.307047  |             0.489186 |  0.5459     | -0.0372209 |          8880   |            5 |           10 |              5 |              0 |
| AUSO.BA  | Autopistas Del Sol SA                              | Acciones Industriales | Operaciones de infraestructura                  |              0.322557  |             0.55789  |  0.506475   | -0.039887  |          3230   |            0 |            0 |              0 |              0 |
| SWKS.BA  | SKYWORKS SOLUTIONS INC CEDEAR E                    | Tecnología            | Semiconductores                                 |              0.295534  |             0.590846 |  0.432488   | -0.0515215 |          5150   |            4 |           10 |              5 |              1 |
| OEST.BA  | Grupo Concesionario del Oeste S.A.                 | Acciones Industriales | Operaciones de infraestructura                  |              0.2512    |             0.547932 |  0.385449   | -0.036606  |           766   |            0 |            0 |              0 |              0 |
| TGNO4.BA | Transportadora de Gas del Norte S.A.               | Energía               | Midstream de petróleo y gas                     |              0.281002  |             0.65308  |  0.369024   | -0.0449653 |          3495   |            0 |            0 |              0 |              0 |
| ADP.BA   | Automatic Data Processing, Inc.                    | Tecnología            | Software - Aplicacion                           |              0.167674  |             0.354815 |  0.359833   | -0.0344896 |         72900   |            5 |           10 |              5 |              0 |
| CRM.BA   | Salesforce, Inc.                                   | Tecnología            | Software - Aplicacion                           |              0.151619  |             0.475053 |  0.234961   | -0.0459772 |         17670   |            4 |           10 |              5 |              1 |
| PAC.BA   | Grupo Aeroportuario del Pacífico, S.A.B. de C.V.   | Acciones Industriales | Aeropuertos y servicios aéreos                  |              0.112297  |             0.38554  |  0.187521   | -0.0411317 |         20710   |            6 |           10 |              6 |              0 |
| ASR.BA   | Grupo Aeroportuario del Sureste, S. A. B. de C. V. | Acciones Industriales | Aeropuertos y servicios aéreos                  |              0.0860313 |             0.370444 |  0.12426    | -0.0321069 |         21180   |            5 |           10 |              5 |              0 |
| UBER.BA  | Uber Technologies, Inc.                            | Tecnología            | Software - Aplicacion                           |              0.0871981 |             0.419828 |  0.112423   | -0.0376613 |         59975   |            4 |           10 |              4 |              0 |
| ADBE.BA  | Adobe Inc.                                         | Tecnología            | Software - Aplicacion                           |              0.036145  |             0.457105 | -0.00843358 | -0.0520967 |          9725   |            1 |           10 |              2 |              1 |
| SAP.BA   | SAP SE                                             | Tecnología            | Software - Aplicacion                           |              0.0098642 |             0.465696 | -0.0647113  | -0.0437495 |         55125   |            2 |           10 |              4 |              2 |
| LEDE.BA  | Ledesma S.A. Agrícola Industrial                   | Acciones Industriales | Conglomerados                                   |             -0.0929741 |             0.424749 | -0.313065   | -0.0359607 |           763   |            0 |            0 |              0 |              0 |
| CAPX.BA  | Capex S.A.                                         | Energía               | Exploración y producción de petróleo y gas      |             -0.226383  |             0.530707 | -0.501941   | -0.0439967 |          3290   |            0 |            0 |              0 |              0 |
| MIRG.BA  | Mirgor S.A.                                        | Tecnología            | Electrónica de Consumo                          |             -1.13596   |             0.982548 | -1.19685    | -0.0351477 |          1625   |            0 |            0 |              0 |              0 |
| MSTR.BA  | Strategy Inc                                       | Tecnología            | Software - Aplicacion                           |             -0.896815  |             0.768573 | -1.2189     | -0.0805702 |          7700   |           -2 |           10 |              1 |              3 |

## Bucket ARS — Fundamentos
| ticker   | nombre                                             |   fund_trailingPE |   fund_forwardPE |   fund_priceToBook |   fund_returnOnEquity |   fund_revenueGrowth |   fund_earningsGrowth |   fund_debtToEquity |   fund_recommendationMean |   fund_targetMeanPrice |
|:---------|:---------------------------------------------------|------------------:|-----------------:|-------------------:|----------------------:|---------------------:|----------------------:|--------------------:|--------------------------:|-----------------------:|
| INTC.BA  | Intel Corporation                                  |         nan       |         51.7075  |           6.07696  |              -0.10715 |                0.254 |               nan     |              48.997 |                   2.59574 |               114.05   |
| UGP.BA   | Ultrapar Participações S.A.                        |           9.70635 |         10.2516  |           2.01901  |               0.19804 |                0.219 |                 0.443 |              97.688 |                   2       |                 6.723  |
| AMD.BA   | Advanced Micro Devices, Inc.                       |         128.71    |         32.5523  |          12.2176   |               0.10196 |                0.501 |                 1.595 |               6.361 |                   1.4902  |               613.335  |
| MRVL.BA  | Marvell Technology, Inc.                           |          74.0503  |         35.3497  |          10.6071   |               0.16028 |                0.276 |                -0.804 |              28.97  |                   1.4186  |               256.914  |
| ADI.BA   | Analog Devices, Inc.                               |          57.8876  |         25.6341  |           5.57374  |               0.09639 |                0.372 |                 1.105 |              25.81  |                 nan       |               457.733  |
| SLB.BA   | SLB N.V.                                           |          26.1073  |         16.511   |           3.04645  |               0.12909 |                0.05  |                -0.297 |              47.002 |                   1.6     |                61.9655 |
| DAL.BA   | DELTA AIR LINES INC CEDEAR EACH                    |          14.8385  |         10.2697  |           2.72719  |               0.20125 |                0.187 |                -0.254 |              96.649 |                 nan       |               105.521  |
| GARO.BA  | Garovaglio y Zorraquín S.A.                        |          33.6713  |        nan       |           1.77574  |               0.06296 |                0.259 |               nan     |              15.949 |                 nan       |               nan      |
| FDX.BA   | FedEx Corporation                                  |          18.3279  |         16.3221  |           2.57969  |               0.14846 |                0.125 |                -0.043 |             135.697 |                   1.82143 |               352.226  |
| PBI.BA   | Pitney Bowes Inc.                                  |          13.4594  |          9.08782 |          -2.62819  |             nan       |               -0.023 |                 1.158 |             nan     |                   2.8     |                19.56   |
| NVDA.BA  | NVIDIA Corporation                                 |          34.6118  |         17.6347  |          28.0068   |               1.14288 |                0.852 |                 2.145 |               6.555 |                   1.29508 |               302.828  |
| UAL.BA   | United Airlines Holdings, Inc.                     |          11.8464  |          8.18164 |           2.45952  |               0.23252 |                0.16  |                -0.172 |             201.641 |                   1.36    |               162.152  |
| MMM.BA   | 3M Company                                         |          32.5169  |         18.7225  |          31.9829   |               0.81892 |                0.025 |                 0.328 |             437.937 |                   2.22222 |               183.258  |
| HON.BA   | Honeywell International Inc.                       |           8.97867 |         23.3207  |           3.99448  |               0.46577 |                0.043 |                 2.639 |             185.369 |                   1.91667 |               263.105  |
| CADO.BA  | Carlos Casado S.A.                                 |          22.714   |        nan       |           1.05675  |               0.05414 |              nan     |               nan     |              20.015 |                 nan       |               nan      |
| PAMP.BA  | Pampa Energía S.A.                                 |           7.61615 |          6.52392 |           1.10053  |               0.15264 |                0.535 |                 3.333 |              65.025 |                   1.66667 |              8259.83   |
| CRES.BA  | Cresud S.A.                                        |           5.79029 |        936.313   |           0.909463 |               0.16041 |                0.05  |                -0.263 |              69.055 |                 nan       |               nan      |
| RENT3.BA | Localiza Rent a Car S.A.                           |         nan       |        nan       |           0.769727 |               0.13011 |                0.245 |               nan     |             171.495 |                 nan       |               nan      |
| QCOM.BA  | QUALCOMM Incorporated                              |          18.9646  |         16.2356  |           6.34158  |               0.33754 |               -0.04  |                -0.23  |              55.21  |                   2.51351 |               194.767  |
| CAR.BA   | Avis Budget Group, Inc.                            |         nan       |         22.7278  |          -1.4317   |             nan       |               -0.013 |                 8.8   |             nan     |                   3.375   |               129.143  |
| TGSU2.BA | Transportadora de Gas del Sur S.A.                 |          12.8699  |         10.3292  |           1.68515  |               0.15984 |                0.154 |                 1.476 |              43.07  |                   1.5     |             20500      |
| AUSO.BA  | Autopistas Del Sol SA                              |           8.07762 |        nan       |           0.748939 |               0.05907 |                0.256 |                -0.347 |             nan     |                 nan       |               nan      |
| SWKS.BA  | SKYWORKS SOLUTIONS INC CEDEAR E                    |          36.4093  |         14.1296  |           1.843    |               0.05094 |               -0.031 |                -0.686 |              11.869 |                   3       |                68.25   |
| OEST.BA  | Grupo Concesionario del Oeste S.A.                 |           7.42968 |        nan       |           0.719426 |               0.07161 |                0.169 |                -0.357 |             nan     |                 nan       |               nan      |
| TGNO4.BA | Transportadora de Gas del Norte S.A.               |           7.8679  |         97.0833  |           1.18012  |               0.1804  |                0.019 |                 0.635 |               0.681 |                 nan       |               nan      |
| ADP.BA   | Automatic Data Processing, Inc.                    |          24.8647  |         20.3024  |          17.9421   |               0.72239 |                0.068 |                 0.098 |              91.436 |                   2.72222 |               286.667  |
| CRM.BA   | Salesforce, Inc.                                   |          21.8469  |         12.6395  |           4.69331  |               0.16908 |                0.133 |                 0.522 |             124.282 |                   1.67308 |               241.72   |
| PAC.BA   | Grupo Aeroportuario del Pacífico, S.A.B. de C.V.   |          19.7166  |         19.0794  |         579.979    |               0.2803  |                0.037 |                -0.064 |             117.519 |                   2.14286 |               263.343  |
| ASR.BA   | Grupo Aeroportuario del Sureste, S. A. B. de C. V. |          14       |         11.3018  |           3.31668  |               0.22776 |                0.099 |                 0.071 |              71.103 |                   2       |               343.641  |
| UBER.BA  | Uber Technologies, Inc.                            |          16.739   |         17.3463  |           6.28024  |               0.3716  |                0.122 |                 0.855 |              51.872 |                   1.52    |               101.501  |
| ADBE.BA  | Adobe Inc.                                         |          14.3376  |          9.53796 |           9.08425  |               0.62954 |                0.127 |                 0.079 |              61.443 |                   2.725   |               269.608  |
| SAP.BA   | SAP SE                                             |          27.0935  |         21.7317  |          65.6618   |               0.18321 |                0.094 |                 0.306 |              21.966 |                   1.5625  |               242.917  |
| LEDE.BA  | Ledesma S.A. Agrícola Industrial                   |         nan       |        nan       |           0.638495 |              -0.06593 |                0.108 |               nan     |              51.566 |                 nan       |               nan      |
| CAPX.BA  | Capex S.A.                                         |          12.8868  |        nan       |           0.830477 |               0.06536 |                0.345 |               nan     |              98.277 |                 nan       |               nan      |
| MIRG.BA  | Mirgor S.A.                                        |           9.83299 |        nan       |           0.725553 |               0.07321 |               -0.05  |               nan     |             145.364 |                 nan       |               nan      |
| MSTR.BA  | Strategy Inc                                       |         nan       |          1.87492 |           1.11639  |              -0.63562 |                0.069 |               nan     |              14.938 |                   1.26667 |               229.071  |

## Bucket ARS — Portafolio óptimo Max Sharpe
| ticker   | nombre                               |       peso |   monto_sugerido_ars |   cantidad_sugerida |   ultimo_precio |
|:---------|:-------------------------------------|-----------:|---------------------:|--------------------:|----------------:|
| UGP.BA   | Ultrapar Participações S.A.          | 0.160603   |             330221   |                  34 |            9695 |
| FDX.BA   | FedEx Corporation                    | 0.157014   |             322842   |                   6 |           53675 |
| CADO.BA  | Carlos Casado S.A.                   | 0.137222   |             282147   |                 519 |             544 |
| GARO.BA  | Garovaglio y Zorraquín S.A.          | 0.108038   |             222141   |                 478 |             465 |
| NVDA.BA  | NVIDIA Corporation                   | 0.0831639  |             170996   |                  12 |           14850 |
| PBI.BA   | Pitney Bowes Inc.                    | 0.0607414  |             124893   |                   5 |           26540 |
| AUSO.BA  | Autopistas Del Sol SA                | 0.0554307  |             113973   |                  35 |            3230 |
| ADP.BA   | Automatic Data Processing, Inc.      | 0.0511292  |             105129   |                   1 |           72900 |
| INTC.BA  | Intel Corporation                    | 0.0477929  |              98268.7 |                   3 |           33140 |
| TGNO4.BA | Transportadora de Gas del Norte S.A. | 0.036634   |              75324.5 |                  22 |            3495 |
| SLB.BA   | SLB N.V.                             | 0.0319063  |              65603.7 |                   2 |           27500 |
| DAL.BA   | DELTA AIR LINES INC CEDEAR EACH      | 0.0318124  |              65410.6 |                   4 |           18120 |
| PAMP.BA  | Pampa Energía S.A.                   | 0.0182914  |              37609.5 |                   8 |            5000 |
| CAR.BA   | Avis Budget Group, Inc.              | 0.0122046  |              25094.3 |                   3 |            8425 |
| ADI.BA   | Analog Devices, Inc.                 | 0.00539857 |              11100.2 |                   0 |           40140 |

- **Rendimiento esperado:** 95.24%
- **Volatilidad:** 17.55%
- **Sharpe:** 5.200

## Bucket USD — Métricas cuantitativas de candidatos
| ticker   | nombre                                      | sector_json           | industria                                       |   rend_esperado_annual |   volatilidad_annual |     sharpe |     var_95 |   ultimo_precio |   news_score |   news_count |   news_bullish |   news_bearish |
|:---------|:--------------------------------------------|:----------------------|:------------------------------------------------|-----------------------:|---------------------:|-----------:|-----------:|----------------:|-------------:|-------------:|---------------:|---------------:|
| MU       | Micron Technology, Inc.                     | Tecnología            | Semiconductores                                 |             2.39316    |             0.810924 |  2.90183   | -0.0698202 |        975.6    |            3 |           10 |              4 |              1 |
| PSX      | Phillips 66                                 | Energía               | Refinacion y comercializacion de petróleo y gas |             0.734337   |             0.30923  |  2.24537   | -0.0282015 |        234.99   |            3 |           10 |              4 |              1 |
| INTC     | Intel Corporation                           | Tecnología            | Semiconductores                                 |             1.79712    |             0.790747 |  2.22211   | -0.061603  |        105.245  |            4 |           10 |              4 |              0 |
| TEN      | Tsakos Energy Navigation Limited            | Energía               | Equipos y servicios de petróleo y gas           |             0.827941   |             0.358296 |  2.19914   | -0.0319296 |         41.5395 |            2 |           10 |              3 |              1 |
| FDX      | FedEx Corporation                           | Acciones Industriales | Transporte y logistica integrados               |             0.66574    |             0.286263 |  2.18589   | -0.0246479 |        340.065  |           -2 |           10 |              0 |              2 |
| CAT      | Caterpillar, Inc.                           | Acciones Industriales | Maquinaria agricola y de construcción pesada    |             0.817465   |             0.394193 |  1.9723    | -0.0371734 |        864.44   |            5 |           10 |              6 |              1 |
| UGP      | Ultrapar Participacoes S.A. (Ne             | Energía               | Refinacion y comercializacion de petróleo y gas |             0.693343   |             0.359125 |  1.81926   | -0.0310099 |          6.115  |            3 |           10 |              4 |              1 |
| AMD      | Advanced Micro Devices, Inc.                | Tecnología            | Semiconductores                                 |             1.27491    |             0.714892 |  1.72741   | -0.0594384 |        501.77   |            4 |           10 |              4 |              0 |
| XOM      | ExxonMobil Holdings Corporation             | Energía               | Petroleo y Gas Integrados                       |             0.470466   |             0.253945 |  1.69511   | -0.0257986 |        160.965  |            4 |           10 |              4 |              0 |
| MRVL     | Marvell Technology, Inc.                    | Tecnología            | Semiconductores                                 |             1.33607    |             0.789833 |  1.64094   | -0.0724147 |        220.205  |            6 |           10 |              6 |              0 |
| TTE      | TotalEnergies SE                            | Energía               | Petroleo y Gas Integrados                       |             0.433324   |             0.244962 |  1.60565   | -0.0228475 |         88.12   |            4 |           10 |              5 |              1 |
| EQNR     | Equinor ASA                                 | Energía               | Petroleo y Gas Integrados                       |             0.639944   |             0.385055 |  1.55807   | -0.0381473 |         40.77   |            6 |           10 |              6 |              0 |
| ADI      | Analog Devices, Inc.                        | Tecnología            | Semiconductores                                 |             0.570322   |             0.35613  |  1.48912   | -0.0302668 |        386.08   |           10 |           10 |             10 |              0 |
| SLB      | SLB N.V.                                    | Energía               | Equipos y servicios de petróleo y gas           |             0.568784   |             0.356323 |  1.484     | -0.0320114 |         53.505  |            5 |           10 |              6 |              1 |
| HAL      | Halliburton Company                         | Energía               | Equipos y servicios de petróleo y gas           |             0.556779   |             0.361737 |  1.4286    | -0.0323771 |         34.055  |            6 |           10 |              7 |              1 |
| PBR      | Petróleo Brasileiro S.A. - Petrobras        | Energía               | Petroleo y Gas Integrados                       |             0.489717   |             0.318874 |  1.41033   | -0.0321545 |         18.08   |            4 |           10 |              5 |              1 |
| RTX      | RTX Corporation                             | Acciones Industriales | Aeroespacial y Defensa                          |             0.40213    |             0.25783  |  1.40453   | -0.025071  |        220.45   |            6 |           10 |              7 |              1 |
| UNP      | Union Pacific Corporation                   | Acciones Industriales | Ferrocarriles                                   |             0.34993    |             0.220893 |  1.40308   | -0.0210118 |        299.58   |            4 |           10 |              4 |              0 |
| BKR      | Baker Hughes Company                        | Energía               | Equipos y servicios de petróleo y gas           |             0.469805   |             0.326152 |  1.3178    | -0.0352387 |         64.48   |            6 |           10 |              6 |              0 |
| LMT      | Lockheed Martin Corporation                 | Acciones Industriales | Aeroespacial y Defensa                          |             0.387598   |             0.273077 |  1.27289   | -0.024149  |        603.8    |            5 |           10 |              5 |              0 |
| DAL      | Delta Air Lines, Inc.                       | Acciones Industriales | Aerolíneas                                      |             0.52196    |             0.392099 |  1.22918   | -0.0351961 |         90.915  |            2 |           10 |              3 |              1 |
| CVX      | Chevron Corporation                         | Energía               | Petroleo y Gas Integrados                       |             0.327617   |             0.235207 |  1.22282   | -0.0233144 |        200.755  |           -2 |           10 |              1 |              3 |
| ARM      | Arm Holdings plc                            | Tecnología            | Semiconductores                                 |             0.965687   |             0.758607 |  1.22025   | -0.0683051 |        278.23   |            5 |           10 |              5 |              0 |
| VIST     | Vista Energy, S.A.B. de C.V.                | Energía               | Exploracion y produccion de petróleo y gas      |             0.622594   |             0.500779 |  1.16338   | -0.0456511 |         68.105  |            3 |           10 |              3 |              0 |
| AM       | Antero Midstream Corporation                | Energía               | Oil & Gas Midstream                             |             0.272247   |             0.200672 |  1.15735   | -0.0194543 |         22.36   |            5 |           10 |              5 |              0 |
| SHEL     | Shell plc                                   | Energía               | Petroleo y Gas Integrados                       |             0.292779   |             0.223801 |  1.12948   | -0.0227391 |         90.53   |            2 |           10 |              3 |              1 |
| PCAR     | PACCAR Inc                                  | Acciones Industriales | Maquinaria agricola y de construcción pesada    |             0.334147   |             0.277425 |  1.06028   | -0.0226332 |        130.635  |            4 |           10 |              4 |              0 |
| SNOW     | Snowflake Inc.                              | Tecnología            | Software - Aplicacion                           |             0.729969   |             0.658449 |  1.04787   | -0.0486234 |        329.62   |            3 |           10 |              3 |              0 |
| NXE      | NexGen Energy Ltd.                          | Energía               | Uranio                                          |             0.60197    |             0.567389 |  0.990449  | -0.0609681 |         10.53   |            2 |           10 |              2 |              0 |
| GE       | GE Aerospace                                | Acciones Industriales | Aeroespacial y Defensa                          |             0.357703   |             0.320899 |  0.990039  | -0.0341212 |        364.01   |            5 |           10 |              5 |              0 |
| ACDC     | ProFrac Holding Corp.                       | Energía               | Oil & Gas Equipment & Services                  |             0.777361   |             0.832362 |  0.885866  | -0.072351  |          5.4    |           -1 |           10 |              1 |              2 |
| DE       | Deere & Company                             | Acciones Industriales | Maquinaria agricola y de construcción pesada    |             0.305143   |             0.305178 |  0.868814  | -0.0244158 |        612.218  |            0 |           10 |              2 |              2 |
| GPRK     | GeoPark Limited                             | Energía               | Exploracion y produccion de petróleo y gas      |             0.525084   |             0.561957 |  0.863205  | -0.0461774 |          9.57   |            3 |           10 |              3 |              0 |
| AVGO     | Broadcom Inc.                               | Tecnología            | Semiconductores                                 |             0.376427   |             0.478154 |  0.703595  | -0.0423965 |        401.25   |            3 |           10 |              4 |              1 |
| NVDA     | NVIDIA Corporation                          | Tecnología            | Semiconductores                                 |             0.285659   |             0.368203 |  0.667183  | -0.0377358 |        225.89   |            2 |           10 |              3 |              1 |
| UAL      | United Airlines Holdings, Inc.              | Acciones Industriales | Aerolíneas                                      |             0.357018   |             0.476511 |  0.66529   | -0.0446883 |        126.52   |            1 |           10 |              2 |              1 |
| MMM      | 3M Company                                  | Acciones Industriales | Conglomerados                                   |             0.210357   |             0.265474 |  0.641708  | -0.022709  |        183.135  |            7 |           10 |              8 |              1 |
| BKV      | BKV Corporation                             | Energía               | Oil & Gas E&P                                   |             0.291581   |             0.419139 |  0.600232  | -0.0447399 |         26.24   |            4 |           10 |              5 |              1 |
| AAL      | American Airlines Group Inc.                | Acciones Industriales | Aerolíneas                                      |             0.277823   |             0.481465 |  0.493957  | -0.0468075 |         15.0795 |            7 |           10 |              7 |              0 |
| BLBD     | Blue Bird Corporation                       | Acciones Industriales | Farm & Heavy Construction Machinery             |             0.251061   |             0.427528 |  0.493676  | -0.0350327 |         66      |            5 |           10 |              5 |              0 |
| AR       | Antero Resources Corporation                | Energía               | Oil & Gas E&P                                   |             0.21535    |             0.378751 |  0.462969  | -0.0405016 |         37.32   |            7 |           10 |              8 |              1 |
| HON      | Honeywell International Inc.                | Acciones Industriales | Conglomerados                                   |             0.137294   |             0.266784 |  0.364692  | -0.02541   |        233.625  |            8 |           10 |              8 |              0 |
| AESI     | Atlas Energy Solutions Inc.                 | Energía               | Oil & Gas Equipment & Services                  |             0.257197   |             0.614978 |  0.353178  | -0.0605798 |         12.1    |           -2 |           10 |              1 |              3 |
| SHOP     | Shopify Inc.                                | Tecnología            | Software - Aplicacion                           |             0.241467   |             0.574015 |  0.350978  | -0.0591532 |        155.8    |            4 |           10 |              4 |              0 |
| AAON     | AAON, Inc.                                  | Acciones Industriales | Building Products & Equipment                   |             0.245857   |             0.613341 |  0.335633  | -0.0588065 |         88.4    |            4 |           10 |              5 |              1 |
| IBM      | International Business Machines Corporation | Tecnología            | Servicios de tecnologia de la información       |             0.1375     |             0.482074 |  0.202251  | -0.0332392 |        234.662  |            1 |           10 |              2 |              1 |
| APOG     | Apogee Enterprises, Inc.                    | Acciones Industriales | Building Products & Equipment                   |             0.0873356  |             0.418089 |  0.113219  | -0.0368331 |         42.445  |            3 |           10 |              4 |              1 |
| ASTE     | Astec Industries, Inc.                      | Acciones Industriales | Farm & Heavy Construction Machinery             |             0.0426149  |             0.427858 |  0.0061117 | -0.0390329 |         43.055  |            1 |           10 |              3 |              2 |
| DOCU     | DocuSign, Inc.                              | Tecnología            | Software - Aplicacion                           |             0.00324045 |             0.486528 | -0.0755549 | -0.0511069 |         61.5    |            0 |           10 |              3 |              3 |
| AGCO     | AGCO Corporation                            | Acciones Industriales | Farm & Heavy Construction Machinery             |            -0.0338846  |             0.33896  | -0.217975  | -0.0317811 |        100.7    |           -2 |           10 |              0 |              2 |
| CRM      | Salesforce, Inc.                            | Tecnología            | Software - Aplicacion                           |            -0.079517   |             0.414165 | -0.288573  | -0.0414426 |        196.335  |            4 |           10 |              5 |              1 |
| ADP      | Automatic Data Processing, Inc.             | Tecnología            | Software - Aplicacion                           |            -0.0403019  |             0.269137 | -0.298368  | -0.0239673 |        272.06   |            5 |           10 |              5 |              0 |
| UBER     | Uber Technologies, Inc.                     | Tecnología            | Software - Aplicacion                           |            -0.117775   |             0.355153 | -0.444244  | -0.0365023 |         76.365  |            3 |           10 |              3 |              0 |
| ACN      | Accenture plc                               | Tecnología            | Servicios de tecnologia de la información       |            -0.221383   |             0.433576 | -0.602854  | -0.0410157 |        175.81   |            5 |           10 |              5 |              0 |
| SAP      | SAP SE                                      | Tecnología            | Software - Aplicacion                           |            -0.199788   |             0.382715 | -0.626545  | -0.0378813 |        208.71   |            1 |           10 |              3 |              2 |
| ADBE     | Adobe Inc.                                  | Tecnología            | Software - Aplicacion                           |            -0.208999   |             0.388542 | -0.640857  | -0.0408902 |        262.54   |            1 |           10 |              2 |              1 |
| EFX      | Equifax Inc.                                | Acciones Industriales | Servicios de consultoria                        |            -0.228783   |             0.384228 | -0.699542  | -0.0429763 |        181.435  |            0 |           10 |              3 |              3 |
| ALG      | Alamo Group                                 | Acciones Industriales | Farm & Heavy Construction Machinery             |            -0.255374   |             0.320183 | -0.922518  | -0.0273155 |        165.4    |            4 |           10 |              4 |              0 |
| GLOB     | Globant S.A.                                | Tecnología            | Servicios de tecnologia de la información       |            -0.54121    |             0.600158 | -0.968429  | -0.0552338 |         38.23   |            2 |           10 |              3 |              1 |
| MSTR     | Strategy Inc                                | Tecnología            | Software - Aplicacion                           |            -1.11728    |             0.745727 | -1.55188   | -0.0707893 |         92.96   |           -2 |           10 |              1 |              3 |

## Bucket USD — Fundamentos
| ticker   | nombre                                      |   fund_trailingPE |   fund_forwardPE |   fund_priceToBook |   fund_returnOnEquity |   fund_revenueGrowth |   fund_earningsGrowth |   fund_debtToEquity |   fund_recommendationMean |   fund_targetMeanPrice |
|:---------|:--------------------------------------------|------------------:|-----------------:|-------------------:|----------------------:|---------------------:|----------------------:|--------------------:|--------------------------:|-----------------------:|
| MU       | Micron Technology, Inc.                     |          22.1193  |          6.32063 |          10.9735   |               0.66638 |                3.457 |                13.685 |               6.33  |                   1.41304 |              1501.98   |
| PSX      | Phillips 66                                 |          13.4127  |         11.017   |           3.30255  |               0.23453 |                0.531 |                 3.449 |              62.884 |                   2.1     |               217.105  |
| INTC     | Intel Corporation                           |         nan       |         51.7614  |           6.0833   |              -0.10715 |                0.254 |               nan     |              48.997 |                   2.59574 |               114.05   |
| TEN      | Tsakos Energy Navigation Limited            |           6.77643 |         14.1532  |           0.639168 |               0.11649 |                0.284 |                 1.628 |             109.664 |                   1       |                46      |
| FDX      | FedEx Corporation                           |          18.3276  |         16.3219  |           2.57965  |               0.14846 |                0.125 |                -0.043 |             135.697 |                   1.82143 |               352.226  |
| CAT      | Caterpillar, Inc.                           |          37.3258  |         27.1113  |          20.568    |               0.56972 |                0.24  |                 0.682 |             232.783 |                   2.14286 |               970.707  |
| UGP      | Ultrapar Participacoes S.A. (Ne             |           9.70635 |         10.2516  |           2.01901  |               0.19804 |                0.219 |                 0.443 |              97.688 |                   2       |                 6.723  |
| AMD      | Advanced Micro Devices, Inc.                |         128.628   |         32.5316  |          12.2098   |               0.10196 |                0.501 |                 1.595 |               6.361 |                   1.4902  |               613.335  |
| XOM      | ExxonMobil Holdings Corporation             |          20.8703  |         15.001   |           2.55089  |               0.12584 |                0.441 |                 1.128 |              15.921 |                   2.4     |               168.318  |
| MRVL     | Marvell Technology, Inc.                    |          74.0403  |         35.3449  |          10.6057   |               0.16028 |                0.276 |                -0.804 |              28.97  |                   1.4186  |               256.914  |
| TTE      | TotalEnergies SE                            |          11.0238  |          9.1344  |           1.52564  |               0.1448  |                0.278 |                 1.06  |              48.045 |                 nan       |               nan      |
| EQNR     | Equinor ASA                                 |          11.1699  |         11.1298  |           4.60314  |               0.2127  |                0.374 |                 2.98  |              75.162 |                 nan       |                34.7417 |
| ADI      | Analog Devices, Inc.                        |          57.94    |         25.6573  |           5.5788   |               0.09639 |                0.372 |                 1.105 |              25.81  |                 nan       |               457.733  |
| SLB      | SLB N.V.                                    |          26.1049  |         16.5094  |           3.04616  |               0.12909 |                0.05  |                -0.297 |              47.002 |                   1.6     |                61.9655 |
| HAL      | Halliburton Company                         |          17.8351  |         11.7169  |           2.58049  |               0.14917 |                0.037 |                 0.161 |              74.186 |                   1.75    |                43.52   |
| PBR      | Petróleo Brasileiro S.A. - Petrobras        |           4.56061 |          4.5301  |           1.34413  |               0.30274 |                0.423 |                 0.968 |              76.067 |                   1.78571 |                22.1884 |
| RTX      | RTX Corporation                             |          38.7399  |         28.0686  |           4.47574  |               0.12274 |                0.145 |                 0.287 |              57.02  |                   1.86957 |               232.272  |
| UNP      | Union Pacific Corporation                   |          24.2375  |         21.1639  |           9.15907  |               0.39696 |                0.115 |                 0.066 |             150.772 |                   1.8     |               329.25   |
| BKR      | Baker Hughes Company                        |          20.7299  |         20.3733  |           3.21354  |               0.16463 |               -0.024 |                -0.042 |              80.925 |                   1.70833 |                71.3913 |
| LMT      | Lockheed Martin Corporation                 |          22.2652  |         18.4769  |          15.857    |               0.89165 |                0.105 |                 4.438 |             234.238 |                   2.52381 |               630.316  |
| DAL      | Delta Air Lines, Inc.                       |          14.8361  |         10.268   |           2.72674  |               0.20125 |                0.187 |                -0.254 |              96.649 |                 nan       |               105.521  |
| CVX      | Chevron Corporation                         |          19.2294  |         15.309   |           2.07392  |               0.12231 |                0.535 |                 3.219 |              18.959 |                   1.72    |               216.958  |
| ARM      | Arm Holdings plc                            |         284.173   |         91.0625  |          34.4623   |               0.13353 |                0.224 |                 1.083 |               5.62  |                   1.87805 |               287.795  |
| VIST     | Vista Energy, S.A.B. de C.V.                |           8.96118 |          6.4971  |           2.27555  |               0.29795 |                1.023 |                 0.298 |             106.502 |                 nan       |                99.1    |
| AM       | Antero Midstream Corporation                |          26.9398  |         13.872   |           5.45632  |               0.19822 |                0.083 |                -0.08  |             185.545 |                   3.14286 |                24.2857 |
| SHEL     | Shell plc                                   |          10.01    |         10.2602  |           1.39421  |               0.14341 |                0.447 |                 2.2   |              40.2   |                   2.25    |                98.0333 |
| PCAR     | PACCAR Inc                                  |          27.6152  |         18.3113  |           3.38332  |               0.12756 |                0.005 |                 0.042 |              72.91  |                   2.42105 |               141.029  |
| SNOW     | Snowflake Inc.                              |         nan       |        121.92    |          58.8      |              -0.54869 |                0.335 |               nan     |             142.912 |                   1.5098  |               303.954  |
| NXE      | NexGen Energy Ltd.                          |         nan       |        -64.3776  |           5.77024  |              -0.17667 |              nan     |               nan     |              33.569 |                   1.5     |                19.3841 |
| GE       | GE Aerospace                                |          42.9791  |         40.1607  |          21.4377   |               0.48232 |                0.211 |                 0.194 |             113.225 |                   1.45455 |               404.905  |
| ACDC     | ProFrac Holding Corp.                       |         nan       |        -10.1698  |           1.80933  |              -0.44762 |               -0.008 |               nan     |             169.781 |                   3.6     |                 4.89   |
| DE       | Deere & Company                             |          34.7069  |         27.0478  |           6.03022  |               0.18349 |               -0.111 |                -0.085 |             376.022 |                   2.125   |               647.615  |
| GPRK     | GeoPark Limited                             |           6.64583 |          5.3764  |           1.41401  |               0.28567 |                0.196 |               nan     |             181.1   |                   2       |                10.85   |
| AVGO     | Broadcom Inc.                               |          66.6173  |         20.5337  |          21.76     |               0.37281 |                0.479 |                 0.854 |              74.018 |                   1.3125  |               527.884  |
| NVDA     | NVIDIA Corporation                          |          34.6087  |         17.6331  |          28.0043   |               1.14288 |                0.852 |                 2.145 |               6.555 |                   1.29508 |               302.828  |
| UAL      | United Airlines Holdings, Inc.              |          11.8446  |          8.18034 |           2.45913  |               0.23252 |                0.16  |                -0.172 |             201.641 |                   1.36    |               162.152  |
| MMM      | 3M Company                                  |          32.5293  |         18.7296  |          31.9951   |               0.81892 |                0.025 |                 0.328 |             437.937 |                   2.22222 |               183.258  |
| BKV      | BKV Corporation                             |           9.40502 |         13.8879  |           1.29478  |               0.14052 |                0.188 |                -0.472 |              53.294 |                   1.09091 |                34.0909 |
| AAL      | American Airlines Group Inc.                |         nan       |          6.08256 |          -2.51403  |             nan       |                0.163 |                -0.882 |             nan     |                   2.24    |                19.0348 |
| BLBD     | Blue Bird Corporation                       |           7.82012 |         13.7873  |           3.19613  |               0.64286 |                0.299 |                 3.705 |              17.675 |                   1.25    |                89.125  |
| AR       | Antero Resources Corporation                |          10.6877  |          8.53141 |           1.38363  |               0.14216 |                0.126 |                 0.799 |              55.493 |                   1.8     |                49.1    |
| HON      | Honeywell International Inc.                |           8.98693 |         23.3421  |           3.99815  |               0.46577 |                0.043 |                 2.639 |             185.369 |                   1.91667 |               263.105  |
| AESI     | Atlas Energy Solutions Inc.                 |         nan       |         65.0345  |           1.36343  |              -0.09925 |                0.016 |               nan     |              94.273 |                   2.41667 |                18.8333 |
| SHOP     | Shopify Inc.                                |         105.823   |         63.8315  |          16.1873   |               0.15543 |                0.337 |                 0.681 |               1.403 |                   1.69231 |               167.891  |
| AAON     | AAON, Inc.                                  |          45.7641  |         25.2948  |           7.28193  |               0.17284 |                1.012 |                 2.579 |              44.742 |                   1.6     |               143      |
| IBM      | International Business Machines Corporation |          20.7339  |         17.799   |           6.41271  |               0.34461 |                0.011 |                -0.018 |             188.97  |                   2.12    |               244.157  |
| APOG     | Apogee Enterprises, Inc.                    |          13.3056  |         10.8833  |           1.74606  |               0.13756 |               -0.011 |               nan     |              56.254 |                 nan       |                44      |
| ASTE     | Astec Industries, Inc.                      |          51.256   |         11.0468  |           1.4367   |               0.02859 |                0.236 |                -0.375 |              57.089 |                   1       |                67.25   |
| DOCU     | DocuSign, Inc.                              |          39.9383  |         12.0674  |           6.52504  |               0.1644  |                0.087 |                 0.176 |              10.075 |                   2.72727 |                59.3272 |
| AGCO     | AGCO Corporation                            |          13.9281  |         13.3642  |           1.72751  |               0.11827 |               -0.01  |                -0.744 |              66.053 |                   2.5625  |               123.133  |
| CRM      | Salesforce, Inc.                            |          21.8341  |         12.6321  |           4.69056  |               0.16908 |                0.133 |                 0.522 |             124.282 |                   1.67308 |               241.72   |
| ADP      | Automatic Data Processing, Inc.             |          24.8684  |         20.3053  |          17.9447   |               0.72239 |                0.068 |                 0.098 |              91.436 |                   2.72222 |               286.667  |
| UBER     | Uber Technologies, Inc.                     |          16.7357  |         17.3429  |           6.279    |               0.3716  |                0.122 |                 0.855 |              51.872 |                   1.52    |               101.501  |
| ACN      | Accenture plc                               |          14.0512  |         11.9871  |           3.37254  |               0.24406 |                0.056 |                 0.09  |              25.035 |                   2.07407 |               178.891  |
| SAP      | SAP SE                                      |          27.0597  |         21.7046  |          65.58     |               0.18321 |                0.094 |                 0.306 |              21.966 |                   1.5625  |               242.917  |
| ADBE     | Adobe Inc.                                  |          14.3308  |          9.53342 |           9.07992  |               0.62954 |                0.127 |                 0.079 |              61.443 |                   2.725   |               269.608  |
| EFX      | Equifax Inc.                                |          31.8307  |         17.8647  |           4.87113  |               0.14275 |                0.106 |                 0.007 |             120.956 |                   1.83333 |               210.524  |
| ALG      | Alamo Group                                 |          19.8321  |         13.5841  |           1.66558  |               0.08771 |                0.076 |                -0.008 |              23.471 |                   1.75    |               204.8    |
| GLOB     | Globant S.A.                                |          14.7442  |          5.97259 |           0.778123 |               0.0548  |                0     |               nan     |              23.821 |                   2.21739 |                54.5455 |
| MSTR     | Strategy Inc                                |         nan       |          1.87836 |           1.11844  |              -0.63562 |                0.069 |               nan     |              14.938 |                   1.26667 |               229.071  |

## Bucket USD — Portafolio óptimo Max Sharpe
| ticker   | nombre                           |       peso |   monto_sugerido_usd |   cantidad_sugerida |   ultimo_precio |
|:---------|:---------------------------------|-----------:|---------------------:|--------------------:|----------------:|
| TEN      | Tsakos Energy Navigation Limited | 0.151329   |            1547.54   |                  37 |         41.5395 |
| PSX      | Phillips 66                      | 0.145938   |            1492.42   |                   6 |        234.99   |
| UNP      | Union Pacific Corporation        | 0.123507   |            1263.03   |                   4 |        299.58   |
| XOM      | ExxonMobil Holdings Corporation  | 0.122921   |            1257.04   |                   8 |        160.965  |
| RTX      | RTX Corporation                  | 0.114214   |            1167.99   |                   5 |        220.45   |
| FDX      | FedEx Corporation                | 0.0973366  |             995.402  |                   3 |        340.065  |
| MU       | Micron Technology, Inc.          | 0.0957424  |             979.099  |                   1 |        975.6    |
| SNOW     | Snowflake Inc.                   | 0.0519737  |             531.504  |                   2 |        329.62   |
| EQNR     | Equinor ASA                      | 0.0390069  |             398.9    |                  10 |         40.77   |
| INTC     | Intel Corporation                | 0.0287495  |             294.004  |                   3 |        105.245  |
| DAL      | Delta Air Lines, Inc.            | 0.0182559  |             186.692  |                   2 |         90.915  |
| UGP      | Ultrapar Participacoes S.A. (Ne  | 0.00540769 |              55.3012 |                   9 |          6.115  |
| SHOP     | Shopify Inc.                     | 0.00514911 |              52.6568 |                   0 |        155.8    |

- **Rendimiento esperado:** 78.14%
- **Volatilidad:** 15.14%
- **Sharpe:** 4.898

## Noticias recientes (resumen)
| ticker   |   noticias |   score_neto |   bullish |   bearish |
|:---------|-----------:|-------------:|----------:|----------:|
| AAL      |          5 |            5 |         5 |         0 |
| ADI.BA   |          5 |            5 |         5 |         0 |
| ADI      |          5 |            5 |         5 |         0 |
| HON.BA   |          5 |            5 |         5 |         0 |
| HON      |          5 |            5 |         5 |         0 |
| GE       |          5 |            4 |         4 |         0 |
| ADP.BA   |          5 |            4 |         4 |         0 |
| ADP      |          5 |            4 |         4 |         0 |
| PBI.BA   |          5 |            4 |         4 |         0 |
| RENT3.BA |          5 |            4 |         4 |         0 |
| SHOP     |          5 |            3 |         3 |         0 |
| CRES.BA  |          3 |            3 |         3 |         0 |
| CAT      |          5 |            3 |         3 |         0 |
| MRVL     |          5 |            3 |         3 |         0 |
| LMT      |          5 |            3 |         3 |         0 |
| MRVL.BA  |          5 |            3 |         3 |         0 |
| BLBD     |          5 |            3 |         3 |         0 |
| INTC.BA  |          5 |            3 |         3 |         0 |
| INTC     |          5 |            3 |         3 |         0 |
| PAMP.BA  |          5 |            3 |         3 |         0 |
| TGSU2.BA |          5 |            3 |         3 |         0 |
| AM       |          5 |            3 |         3 |         0 |
| SLB      |          5 |            3 |         3 |         0 |
| UNP      |          5 |            3 |         3 |         0 |
| XOM      |          5 |            2 |         2 |         0 |
| RTX      |          5 |            2 |         3 |         1 |
| NVDA     |          5 |            2 |         2 |         0 |
| NVDA.BA  |          5 |            2 |         2 |         0 |
| VIST     |          5 |            2 |         2 |         0 |
| UGP.BA   |          5 |            2 |         2 |         0 |
| UGP      |          5 |            2 |         2 |         0 |
| SWKS.BA  |          5 |            2 |         2 |         0 |
| PAC.BA   |          5 |            2 |         2 |         0 |
| GLOB     |          5 |            2 |         2 |         0 |
| MMM      |          5 |            2 |         3 |         1 |
| HAL      |          5 |            2 |         3 |         1 |
| APOG     |          5 |            2 |         2 |         0 |
| AR       |          5 |            2 |         3 |         1 |
| ARM      |          5 |            2 |         2 |         0 |
| BKR      |          5 |            2 |         2 |         0 |
| ASTE     |          5 |            2 |         2 |         0 |
| ALG      |          5 |            2 |         2 |         0 |
| GPRK     |          5 |            2 |         2 |         0 |
| UAL      |          5 |            2 |         2 |         0 |
| CRM.BA   |          5 |            2 |         2 |         0 |
| CRM      |          5 |            2 |         2 |         0 |
| EQNR     |          5 |            2 |         2 |         0 |
| MMM.BA   |          5 |            2 |         3 |         1 |
| ADBE.BA  |          5 |            1 |         2 |         1 |
| ACN      |          5 |            1 |         1 |         0 |
| ADBE     |          5 |            1 |         2 |         1 |
| AAON     |          5 |            1 |         2 |         1 |
| AMD      |          5 |            1 |         1 |         0 |
| AMD.BA   |          5 |            1 |         1 |         0 |
| ASR.BA   |          5 |            1 |         1 |         0 |
| AVGO     |          5 |            1 |         2 |         1 |
| UBER     |          5 |            1 |         1 |         0 |
| TTE      |          5 |            1 |         1 |         0 |
| SLB.BA   |          5 |            1 |         2 |         1 |
| BKV      |          5 |            1 |         2 |         1 |
| QCOM.BA  |          5 |            1 |         1 |         0 |
| SHEL     |          5 |            1 |         1 |         0 |
| SAP      |          5 |            1 |         2 |         1 |
| PSX      |          5 |            1 |         1 |         0 |
| UBER.BA  |          5 |            1 |         1 |         0 |
| MSTR.BA  |          5 |            1 |         1 |         0 |
| MSTR     |          5 |            1 |         1 |         0 |
| IBM      |          5 |            1 |         1 |         0 |
| DE       |          5 |            1 |         1 |         0 |
| NXE      |          5 |            1 |         1 |         0 |
| PBR      |          5 |            1 |         2 |         1 |
| PCAR     |          5 |            1 |         1 |         0 |
| SNOW     |          5 |            1 |         1 |         0 |
| TEN      |          5 |            0 |         1 |         1 |
| ACDC     |          5 |            0 |         1 |         1 |
| SAP.BA   |          5 |            0 |         1 |         1 |
| CAR.BA   |          5 |            0 |         1 |         1 |
| EFX      |          5 |            0 |         1 |         1 |
| MU       |          5 |            0 |         1 |         1 |
| AGCO     |          5 |           -1 |         0 |         1 |
| DOCU     |          5 |           -1 |         1 |         2 |
| CVX      |          5 |           -1 |         1 |         2 |
| DAL      |          5 |           -1 |         0 |         1 |
| DAL.BA   |          5 |           -1 |         0 |         1 |
| UAL.BA   |          5 |           -1 |         0 |         1 |
| FDX      |          5 |           -2 |         0 |         2 |
| FDX.BA   |          5 |           -2 |         0 |         2 |
| AESI     |          5 |           -3 |         0 |         3 |

**Alertas bajistas por noticias:** FDX, FDX.BA, AESI

Detalle completo en `CONSTRUCTOR_PORTAFOLIO_noticias.csv`.

## Advertencias
- Los retornos esperados se calculan sobre 1 año de historial; en periodos cortos con tendencias fuertes (ej. semiconductores, energía) el Sharpe puede estar inflado.
- La optimización Markowitz asume que correlaciones y volatilidades históricas se mantienen, un supuesto que raramente se cumple en el corto plazo.
- Para cedears ARS se usan los tickers `.BA`; para el bucket USD se usan los ADRs/acciones subyacentes. Los fundamentales provienen del ticker subyacente en USD.
- El sentimiento de noticias es un scoring keyword simple (no NLP avanzado); usarlo como filtro adicional, no como señal única.
- Revisar liquidez, comisiones, impuestos y horizonte antes de ejecutar.