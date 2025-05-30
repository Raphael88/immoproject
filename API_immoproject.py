from flask import Flask, request, jsonify
import pyodbc
import pandas as pd
import os
from sklearn import  linear_model
import joblib

app = Flask(__name__)
API_KEY = os.environ.get("API_KEY")

# Check api accessibility and verify with key

@app.before_request
def check_api_key():
    if request.path != "/health":
        key = request.headers.get("x-api-key")
        if key != API_KEY:
            return jsonify({"error": "unauthorized"}), 401


#Route to get all sold properties on user market

@app.route('/dvf_market', methods=['GET'])

def dvf_market():
    try:
        f1 = int(float(request.args.get('market_id')))
        server = os.environ.get("SERVER")
        database = os.environ.get("DATABASE")
        username = os.environ.get("DB_USERNAME")
        password = os.environ.get("DB_PASSWORD")
        
        connection_string = (
            f'DRIVER={{ODBC Driver 18 for SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'UID={username};'
            f'PWD={password};'
            'Encrypt=yes;'
            'TrustServerCertificate=no;'
            'Connection Timeout=30;'
        )

        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        query = "SELECT * FROM dvf WHERE market_id = ?"
        cursor.execute(query, (f1,))

        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.close()
        conn.close()
        
        # Catch into a dataframe

        df = pd.DataFrame(results)



        return jsonify(df.to_dict(orient='records'))

    except Exception as e:
        return jsonify({"error": str(e)})


# Route to get the market associated to the user

@app.route('/user_market', methods=['GET'])
def user_market():
    try:
        f1 = int(float(request.args.get('user_id_retool')))

        server = os.environ.get("SERVER")
        database = os.environ.get("DATABASE")
        username = os.environ.get("DB_USERNAME")
        password = os.environ.get("DB_PASSWORD")

        connection_string = (
            f'DRIVER={{ODBC Driver 18 for SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'UID={username};'
            f'PWD={password};'
            'Encrypt=yes;'
            'TrustServerCertificate=no;'
            'Connection Timeout=30;'
        )

        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        query = "SELECT * FROM user_market WHERE user_id_retool = ?"
        cursor.execute(query, (f1,))

        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        # Catch into a dataframe

        df = pd.DataFrame(results)
        market_list = df['market_name'].to_list()
        df_1 = pd.DataFrame({"label": [], "value":[]})
        value = 1
        # Return a list to retool format
        for market in market_list:
            df_1_temp = pd.DataFrame({"label": [market], "value":[value]})
            df_1 = pd.concat([df_1, df_1_temp], ignore_index = True)                         
            value = value + 1


        return jsonify(df_1.to_dict(orient="records"))

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/predict', methods=['GET'])
def prediction():
    f1 = int(float(request.args.get('type_bien')))
    f2 = float(request.args.get('nomb_piece'))
    f3 = float(request.args.get('terr_m2'))
    f4 = float(request.args.get('hab_m2'))
    f5 = float(request.args.get('Year'))
    f6 = int(float(request.args.get('market_id')))
    f7 = int(float(request.args.get('tiers')))

    model = joblib.load(f"immoproject/models/{f6}_model_tier_{f7}.pkl")
    data = pd.DataFrame({'type_bien' : [str(f1)],  'nomb_piece' : [f2], 'terr_m2' : [f3], 'hab_m2' : [f4], 'Year' : [f5], 'tiers' : [f6]})
    X_real = data[['type_bien',  'nomb_piece', 'terr_m2', 'hab_m2', 'Year']]
    prediction = model.predict(X_real)
    
    return jsonify({"prediction": prediction[0]}), 200

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/health')
def health():
    return 'OK', 200

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8000))  # 8000 par défaut en local
    app.run(host='0.0.0.0', port=port)
