from flask import Flask, request, jsonify, g
import pyodbc
import pandas as pd
import os
from sklearn import  linear_model
import joblib
import functools

app = Flask(__name__)
API_KEY = os.environ.get("API_KEY")

# Fonctions

def with_market_id(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # 1. Essaye de récupérer le user_id depuis les query params ou les headers
        town = request.args.get("town") 
        post_code = request.args.get("post_code") 
        if not town:
            return jsonify({"error": "Missing town"}), 400
        if not post_code:
            return jsonify({"error": "Missing post_code"}), 400
        # 2. Connexion à la base de données

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

        # 3. Requête pour obtenir le market_id lié à ce user_id_retool
        cursor.execute("SELECT market_id FROM user_market WHERE market_name = ? AND post_code = ? ", (town,post_code,))
        row = cursor.fetchone()

        cursor.close()
        conn.close()

        # 4. Si aucun résultat : user non trouvé
        if not row:
            return jsonify({"error": "user not found"}), 404

        # 5. Stocke le market_id dans flask.g → disponible dans la route ensuite
        g.market_id = row.market_id  # ou row[0] selon ton curseur

        # 6. Exécute la fonction route
        return f(*args, **kwargs)
    return wrapper
    
# Routes

# Defining route name 
@app.before_request
# The function contain in the API
def check_api_key():
    #If the route not health then request the API 
    if request.path != "/health":
        key = request.headers.get("x-api-key")
        if key != API_KEY:
            return jsonify({"error": "unauthorized"}), 401


#Route to get all sold properties on user market
@app.route('/dvf_market', methods=['GET'])
#Defining the market_id variable which is called at the beginning of the file
@with_market_id
def dvf_market(): # The function
    try: # Credential to access Azure SQL database
        f1 = int(float(g.market_id))
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

        conn = pyodbc.connect(connection_string) # Initiate the connection to SQL Server database
        cursor = conn.cursor()

        query = "SELECT * FROM dvf WHERE market_id = ?" # SQL Query
        cursor.execute(query, (f1,)) # Execute the query on the table in the database

        columns = [column[0] for column in cursor.description]  
        results = [dict(zip(columns, row)) for row in cursor.fetchall()] # Structure the results in a dictionnary

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
@with_market_id
def prediction():
    f1 = int(float(request.args.get('type_bien')))
    f2 = float(request.args.get('nomb_piece'))
    f3 = float(request.args.get('terr_m2'))
    f4 = float(request.args.get('hab_m2'))
    f5 = float(request.args.get('Year'))
    f6 = int(float(g.market_id))
    f7 = int(float(request.args.get('tiers')))
    f8 = request.args.get('situation')
    f9 = float(request.args.get('price_user'))

    model = joblib.load(f"models/model_tier_{f6}_{f7}.pkl")
    data = pd.DataFrame({'type_bien' : [str(f1)],  'nomb_piece' : [f2], 'terr_m2' : [f3], 'hab_m2' : [f4], 'Year' : [f5], 'tiers' : [f6]})
    X_real = data[['type_bien',  'nomb_piece', 'terr_m2', 'hab_m2', 'Year']]
    prediction = model.predict(X_real)
    prediction_basse = prediction-(prediction*0.08)
    prediction_haute = prediction+(prediction*0.08)


    model = joblib.load(f"models/model_tier_{f6}_{f7}.pkl")
    data = pd.DataFrame({'type_bien' : [str(f1)],  'nomb_piece' : [f2], 'terr_m2' : [f3], 'hab_m2' : [f4], 'Year' : [2020], 'tiers' : [f6]})
    X_real = data[['type_bien',  'nomb_piece', 'terr_m2', 'hab_m2', 'Year']]
    prediction_2020 = model.predict(X_real)
    Taux_croissance = ((prediction/prediction_2020)**(1/(f5-2020))-1)

    if Taux_croissance < 0:
        Taux_croissance[0] = 0
    else:
        pass

    price_5 = prediction * (1 + Taux_croissance) ** 5 
    price_10 = prediction * (1 + Taux_croissance) ** 10 
    price_15 = prediction * (1 + Taux_croissance) ** 15 
    price_20 = prediction * (1 + Taux_croissance) ** 20 

    if f9 > prediction and f8 == "achat":
        analysis_text = "Le bien que vous projetez d'acheter se situe au dessus de la prédiction, cela peut être tout a fait possible et du à une situation exceptionnelle (Accès au transports, écoles...), à des atouts du type ascenceur, cave, vue exceptionnelle ou à une certaine rareté. Cependant si ce bien n'a à vos yeux ces atouts supplémentaires, il serait convenable de négocier ou de passer votre chemin."
    elif f9 < prediction and f8 == "achat":
        analysis_text = "Le bien que vous projetez d'acheter se situe en dessous de la prédiction, cela peut être tout a fait plausible si celui-ci s'avère excentré des commodités ou encore avec des défauts. À vous de comprendre pourquoi cette différence et s'il n'y pas de point noir, c'est la bonne affaire!"
    elif f9 > prediction and f8 == "vente":
        analysis_text = "Le bien que vous projetez de vendre a un prix qui se situe au dessus de la prédiction : c'est bien ! Toutefois, prenez votre temps et préparez-vous pour votre négociation quels sont ces atouts et qu'est ce qui justifie ce prix (rénovations, accès aux commodités...) ?"
    elif f9 < prediction and f8 == "vente":
        analysis_text = "Le bien que vous projetez de vendre qui se situe en dessous de la prédiction : c'est bien pour attirer les visites, compenser des défauts et vendre vite. Cependant si ce n'est pas votre cas alors n'hésitez pas à réhausser."
    elif f9 > prediction and f8 == "estimation":
        analysis_text = "Le prix estimé est supérieur à la prédiction qui elle est un prix réel de vente. En cas de forte différence, vérifier les caractéristiques et surtout que l'état du bien choisi est conforme avec les biens dans le même état sur le marché. Le propriétaire pourrait avoir une mauvaise idée du marché. Si écart mineur, il y a peut être des spécificités permettant d'augmenter le prix (exemple : Ascenceur, terrasse, vue...). Bien penser que la prédiction est un prix réel de vente donc le prix estimé devrait tenir compte d'une marge de négociation."
    elif f9 < prediction and f8 == "estimation":
        analysis_text = "Le prix estimé est inférieur à la prédiction qui elle est un prix réel de vente. Vérifier les caractéristique du bien puis que l'état du bien n'est pas sous estimé par rapport au marché. Est ce que le bien a des défauts ? Si oui, il faut en tenir compte, si non ce serait interessant d'augmenter le prix.Bien penser que la prédiction est un prix réel de vente donc le prix estimé devrait tenir compte d'une marge de négociation."
    else:
        analysis_text = ""
        pass
    return jsonify({"prediction": prediction[0], "prediction_2020": prediction_2020[0],"price_5" : price_5[0], "price_10" : price_10[0], "price_15" : price_15[0],"price_20" : price_20[0], "Taux_croissance" : Taux_croissance[0], "analysis_text": analysis_text if analysis_text else "", "prediction_basse" : prediction_basse[0], "prediction_haute": prediction_haute[0]}), 200

@app.route('/sample_sold', methods=['GET'])
@with_market_id
def sample_sold():
    try:
        f1 = int(float(g.market_id))
        f2 = int(float(request.args.get('type_bien')))
        if f2 == 1:
            f2 = "Appartement"
        else:
            f2 = "Maison"
        f3 = float(request.args.get('nomb_piece'))
        f4 = float(request.args.get('terr_m2'))
        f5 = float(request.args.get('hab_m2'))
        f6 = "2024"
        f7 = int(float(request.args.get('tiers')))
        f5_inf = f5-(f5*0.20)
        f5_sup = f5+(f5*0.20)


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
        if f2 == "Appartement":
            f3_inf = f3
            f3_sup = f3
        else:
            f3_inf = f3-1
            f3_sup = f3+1

        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        query = "SELECT *, address + ' ' + post_code + ' ' + Commune as addresse_all FROM dvf WHERE market_id = ? AND type = ? AND (nb_room >= ? AND nb_room <= ?) AND (surface > ? AND surface < ?) AND year = ?"
        cursor.execute(query, (f1,f2,f3_inf,f3_sup,f5_inf,f5_sup,f6,))

        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.close()
        conn.close()
        
        # Catch into a dataframe

        df = pd.DataFrame(results)



        return jsonify(df.to_dict(orient='records'))

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/now_online', methods=['GET'])
@with_market_id
def now_online():
    try:
        f1 = int(float(g.market_id))
        f2 = int(float(request.args.get('type_bien')))
        if f2 == 1:
            f2 = "Appartement"
        else:
            f2 = "Maison"
        f3 = float(request.args.get('nomb_piece'))
        f4 = float(request.args.get('terr_m2'))
        f5 = float(request.args.get('hab_m2'))
        f6 = "2024"
        f5_inf = f5-(f5*0.10)
        f5_sup = f5+(f5*0.10)
        f4_inf = f4-(f4*0.10)
        f4_sup = f4+(f4*0.10)

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

        query = "SELECT * FROM desc_ad as a LEFT JOIN market as b ON b.market_name = a.place WHERE b.Id = ? AND a.type_bien = ? AND a.nomb_piece = ? AND (a.hab_m2 > ? AND a.hab_m2 < ?) "
        cursor.execute(query, (f1,f2, f3,  f5_inf, f5_sup,))

        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.close()
        conn.close()
        
        # Catch into a dataframe

        df = pd.DataFrame(results)

        return jsonify(df.to_dict(orient='records'))

    except Exception as e:
        return jsonify({"error": str(e)})
    

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/health')
def health():
    return 'OK', 200

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8000))  # 8000 par défaut en local
    app.run(host='0.0.0.0', port=port)
