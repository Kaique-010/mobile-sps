# gerencial/services/preditivo.py

import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np
from decimal import Decimal

def gerar_previsao_linear(df, coluna_data, coluna_valor, meses_prever=6):
    if df.empty or len(df) < 3:
        return {"erro": "Dados insuficientes para gerar previsão."}

    try:
        df[coluna_data] = pd.to_datetime(df[coluna_data])
        
        # Convert Decimal values to float to avoid type mismatch
        df[coluna_valor] = df[coluna_valor].apply(lambda x: float(x) if isinstance(x, Decimal) else x)
        
        df['mes_num'] = (df[coluna_data].dt.year - df[coluna_data].dt.year.min()) * 12 + df[coluna_data].dt.month
        df['mes_num'] -= df['mes_num'].min()

        X = df[['mes_num']]
        y = df[coluna_valor]

        modelo = LinearRegression()
        modelo.fit(X, y)

        ult_mes = df[coluna_data].max()
        previsoes = []
        for i in range(1, meses_prever + 1):
            prox_mes = ult_mes + pd.DateOffset(months=i)
            prox_mes_num = df['mes_num'].max() + i
            valor_previsto = modelo.predict(pd.DataFrame([[prox_mes_num]], columns=['mes_num']))[0]
            previsoes.append({
                "mes": prox_mes.strftime("%Y-%m"),
                "valor": round(valor_previsto, 2)
            })

        historico = df[[coluna_data, coluna_valor]].copy()
        historico[coluna_data] = historico[coluna_data].dt.strftime('%Y-%m')

        return {
            "historico": historico.rename(columns={coluna_data: "mes", coluna_valor: "valor"}).to_dict(orient='records'),
            "previsao": previsoes,
            "modelo": "regressao_linear",
            "erro_medio": round(np.mean(np.abs(modelo.predict(X) - y)), 2)
        }

    except Exception as e:
        return {"erro": f"Erro ao gerar previsão: {str(e)}"}
