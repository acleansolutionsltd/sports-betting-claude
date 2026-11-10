# Model error analysis (Stage 6)

Generated 2026-11-10 22:19 UTC from the out-of-sample (test season) legs of the Stage 5 backtests. Only legs at or above the 65% floor.

Rule: nothing here changes the model. A proposed fix must improve out-of-sample results on the walk-forward harness first.

## Football

Legs: 19779. Mean residual (hit rate minus stated probability): +0.0045 (95% CI -0.0007 to +0.0098, resampling whole games). Calibration intercept -0.016, slope 1.037 (ideal 0 and 1).

Stated probability vs hit rate:

| bucket   |    n |   mean_model_prob |   hit_rate |     se |    gap |
|:---------|-----:|------------------:|-----------:|-------:|-------:|
| 65%-70%  | 3361 |            0.6758 |     0.679  | 0.0081 | 0.0032 |
| 70%-75%  | 4781 |            0.7264 |     0.7287 | 0.0064 | 0.0023 |
| 75%-80%  | 4557 |            0.7739 |     0.7806 | 0.0061 | 0.0067 |
| 80%-85%  | 3394 |            0.8242 |     0.8268 | 0.0065 | 0.0025 |
| 85%-90%  | 2394 |            0.8732 |     0.8826 | 0.0066 | 0.0094 |
| 90%-95%  | 1161 |            0.9196 |     0.9225 | 0.0078 | 0.0029 |
| 95%-100% |  131 |            0.9616 |     0.9771 | 0.0131 | 0.0155 |

### By market

| market    |    n |   mean_model_prob |   hit_rate |   residual |   corrected_ci_low |   corrected_ci_high | verdict      |
|:----------|-----:|------------------:|-----------:|-----------:|-------------------:|--------------------:|:-------------|
| under_2.5 |  135 |            0.6792 |     0.6444 |    -0.0347 |            -0.1506 |              0.0785 | within noise |
| btts_yes  |  204 |            0.6745 |     0.6471 |    -0.0274 |            -0.1198 |              0.0637 | within noise |
| over_2.5  |  528 |            0.7068 |     0.6856 |    -0.0212 |            -0.0761 |              0.0316 | within noise |
| dc_12     | 4004 |            0.7593 |     0.751  |    -0.0083 |            -0.0279 |              0.0104 | within noise |
| over_1.5  | 3753 |            0.7807 |     0.7831 |     0.0024 |            -0.0165 |              0.0214 | within noise |
| under_3.5 | 2649 |            0.7388 |     0.7433 |     0.0045 |            -0.0199 |              0.0273 | within noise |
| under_4.5 | 3926 |            0.8402 |     0.8492 |     0.009  |            -0.0067 |              0.0249 | within noise |
| dc_1x     | 2524 |            0.7865 |     0.7956 |     0.0091 |            -0.0124 |              0.0309 | within noise |
| dc_x2     | 1289 |            0.7578 |     0.7843 |     0.0266 |            -0.0044 |              0.0569 | within noise |
| home      |  600 |            0.7382 |     0.78   |     0.0418 |            -0.0072 |              0.0899 | within noise |
| away      |  144 |            0.7232 |     0.7847 |     0.0615 |            -0.0335 |              0.154  | within noise |

No segment differs from zero beyond noise.

### By market_group

| market_group   |     n |   mean_model_prob |   hit_rate |   residual |   corrected_ci_low |   corrected_ci_high | verdict         |
|:---------------|------:|------------------:|-----------:|-----------:|-------------------:|--------------------:|:----------------|
| BTTS           |   227 |            0.6738 |     0.63   |    -0.0438 |            -0.1269 |              0.036  | within noise    |
| double chance  |  7817 |            0.7678 |     0.7709 |     0.0031 |            -0.0063 |              0.013  | within noise    |
| totals         | 10991 |            0.787  |     0.7907 |     0.0037 |            -0.0061 |              0.0127 | within noise    |
| 1X2            |   744 |            0.7353 |     0.7809 |     0.0456 |             0.008  |              0.0818 | under-estimated |

Segments whose interval excludes zero after correction (candidates for a Stage 5 test): 1X2.

### By league

| league   |    n |   mean_model_prob |   hit_rate |   residual |   corrected_ci_low |   corrected_ci_high | verdict      |
|:---------|-----:|------------------:|-----------:|-----------:|-------------------:|--------------------:|:-------------|
| E0       | 4168 |            0.774  |     0.7728 |    -0.0013 |            -0.0169 |              0.0141 | within noise |
| D1       | 3408 |            0.7745 |     0.7738 |    -0.0008 |            -0.0188 |              0.0173 | within noise |
| F1       | 3434 |            0.7743 |     0.7761 |     0.0018 |            -0.0148 |              0.0184 | within noise |
| I1       | 4401 |            0.777  |     0.7846 |     0.0076 |            -0.0074 |              0.0219 | within noise |
| SP1      | 4368 |            0.7802 |     0.7933 |     0.013  |            -0.0023 |              0.0273 | within noise |

No segment differs from zero beyond noise.

### By season

|   season |    n |   mean_model_prob |   hit_rate |   residual |   corrected_ci_low |   corrected_ci_high | verdict      |
|---------:|-----:|------------------:|-----------:|-----------:|-------------------:|--------------------:|:-------------|
|     2425 | 8688 |            0.7776 |     0.7804 |     0.0028 |            -0.0071 |              0.0125 | within noise |
|     2526 | 8633 |            0.7753 |     0.78   |     0.0047 |            -0.0053 |              0.0144 | within noise |
|     2627 | 2458 |            0.7743 |     0.784  |     0.0097 |            -0.0094 |              0.0284 | within noise |

No segment differs from zero beyond noise.

### By team (each leg counted for both teams in the match)

| team          |   n |   mean_model_prob |   hit_rate |   residual |   corrected_ci_low |   corrected_ci_high | verdict      |
|:--------------|----:|------------------:|-----------:|-----------:|-------------------:|--------------------:|:-------------|
| Hull          |  50 |            0.7867 |     0.7    |    -0.0867 |            -0.1823 |              0.0507 | within noise |
| Coventry      |  49 |            0.787  |     0.7143 |    -0.0727 |            -0.1949 |              0.0819 | within noise |
| Schalke 04    |  39 |            0.7863 |     0.7179 |    -0.0683 |            -0.4477 |              0.2053 | within noise |
| La Coruna     |  58 |            0.7748 |     0.7069 |    -0.0679 |            -0.2542 |              0.078  | within noise |
| Werder Bremen | 372 |            0.7665 |     0.7177 |    -0.0487 |            -0.1147 |              0.0136 | within noise |
| St Pauli      | 340 |            0.7722 |     0.8206 |     0.0484 |            -0.0216 |              0.1153 | within noise |
| Valladolid    | 202 |            0.792  |     0.8416 |     0.0496 |            -0.0435 |              0.1209 | within noise |
| Leicester     | 190 |            0.7862 |     0.8421 |     0.0559 |            -0.0423 |              0.1551 | within noise |
| Malaga        |  59 |            0.7853 |     0.8475 |     0.0622 |            -0.0692 |              0.1771 | within noise |
| Le Mans       |  46 |            0.782  |     0.8478 |     0.0658 |            -0.0706 |              0.2077 | within noise |

No team out of 121 differs from zero beyond noise.

### By side backed

| side              |     n |   mean_model_prob |   hit_rate |   residual |   corrected_ci_low |   corrected_ci_high | verdict         |
|:------------------|------:|------------------:|-----------:|-----------:|-------------------:|--------------------:|:----------------|
| neutral market    | 15222 |            0.778  |     0.7779 |    -0.0002 |            -0.0083 |              0.0073 | within noise    |
| backing home side |  3124 |            0.7772 |     0.7926 |     0.0154 |            -0.0032 |              0.033  | within noise    |
| backing away side |  1433 |            0.7543 |     0.7844 |     0.0301 |             0.0048 |              0.055  | under-estimated |

## NFL derived markets

Legs: 22571. Mean residual (hit rate minus stated probability): +0.0107 (95% CI +0.0026 to +0.0189, resampling whole games). Calibration intercept -0.025, slope 1.081 (ideal 0 and 1).

Stated probability vs hit rate:

| bucket   |    n |   mean_model_prob |   hit_rate |     se |    gap |
|:---------|-----:|------------------:|-----------:|-------:|-------:|
| 65%-70%  | 6004 |            0.678  |     0.6904 | 0.006  | 0.0124 |
| 70%-75%  | 6576 |            0.7228 |     0.7321 | 0.0055 | 0.0093 |
| 75%-80%  | 5199 |            0.7733 |     0.7763 | 0.0058 | 0.003  |
| 80%-85%  | 3028 |            0.8192 |     0.8402 | 0.0067 | 0.021  |
| 85%-90%  | 1102 |            0.8732 |     0.8811 | 0.0097 | 0.008  |
| 90%-95%  |  595 |            0.9203 |     0.9496 | 0.009  | 0.0292 |
| 95%-100% |   67 |            0.9578 |     0.9851 | 0.0148 | 0.0273 |

### By family

| family     |    n |   mean_model_prob |   hit_rate |   residual |   corrected_ci_low |   corrected_ci_high | verdict      |
|:-----------|-----:|------------------:|-----------:|-----------:|-------------------:|--------------------:|:-------------|
| alt spread | 7826 |            0.7424 |     0.7493 |     0.0069 |            -0.0088 |              0.0228 | within noise |
| team total | 7565 |            0.78   |     0.7927 |     0.0127 |            -0.0001 |              0.0256 | within noise |
| alt total  | 7180 |            0.7226 |     0.7354 |     0.0128 |            -0.003  |              0.0286 | within noise |

No segment differs from zero beyond noise.

### By season

|   season |    n |   mean_model_prob |   hit_rate |   residual |   corrected_ci_low |   corrected_ci_high | verdict         |
|---------:|-----:|------------------:|-----------:|-----------:|-------------------:|--------------------:|:----------------|
|     2025 | 5071 |            0.7507 |     0.7515 |     0.0008 |            -0.0213 |              0.0228 | within noise    |
|     2026 | 2522 |            0.7488 |     0.7514 |     0.0026 |            -0.0289 |              0.0328 | within noise    |
|     2023 | 5020 |            0.7484 |     0.752  |     0.0036 |            -0.0177 |              0.0257 | within noise    |
|     2022 | 4966 |            0.7471 |     0.7644 |     0.0173 |            -0.0073 |              0.04   | within noise    |
|     2024 | 4992 |            0.7484 |     0.774  |     0.0256 |             0.0024 |              0.0491 | under-estimated |

Segments whose interval excludes zero after correction (candidates for a Stage 5 test): 2024.
