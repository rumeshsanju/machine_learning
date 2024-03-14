import numpy as np
import pandas as pd
from flask import Flask, request, render_template, jsonify,redirect, send_from_directory,url_for
import pickle
from sklearn.preprocessing import LabelEncoder
from flask_sqlalchemy import SQLAlchemy
from flask import send_from_directory

# Initialize the Flask
app = Flask(__name__)

model = pickle.load(open("my_modle.pkl", "rb"))



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)

class Player1(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    prediction_prob = db.Column(db.Float, nullable=False)
    predicted_label = db.Column(db.String(100), nullable=False)
    top = db.Column(db.Float, nullable=False)
    middle = db.Column(db.Float, nullable=False)
    low = db.Column(db.Float, nullable=False)
    tail = db.Column(db.Float, nullable=False)

#app.config['STATIC_FOLDER'] = 'static'
app.config['INSTANCE_FOLDER'] = 'static'

@app.route('/static/<filename>')
def serve_image(filename):
    return send_from_directory(app.config['INSTANCE_FOLDER'], filename)


# Define html file to get user input
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/data')
def data():
    return render_template('data.html')

@app.route('/ranking')
def ranking():
    return render_template('ranking.html')

@app.route('/details')
def details():
    return render_template('details.html')


@app.route('/database')
def database():
    players = Player1.query.all()
    return render_template('database.html', players=players)

@app.route('/predict', methods=["POST"])
def predict():
    feature_names = ["Matches", "Innings", "Not_outs", "Runs", "Higest_Score", "Average", "Ball_Faced",
                     "Strike_Rate", "Centures", "Half-Centures", "Ducks", "Fours", "Sixs", "Bowling_Ability", "Allround_Ablity"]

    try:
        # Try to convert form values to float
        float_features = [float(request.form.get(feature, 0.0)) for feature in feature_names]
    except ValueError as e:
        # Handle the case where a value couldn't be converted to float
        return jsonify({"success": False, "error": "Invalid input. Please enter numeric values."})

    features = [np.array(float_features)]
    prediction = model.predict(features)
    prediction_probabilities = model.predict_proba(features)
    maxi = np.max(prediction_probabilities)
    top =prediction_probabilities[0,0]
    middle =prediction_probabilities[0,1]
    low = prediction_probabilities[0,2]
    tail = prediction_probabilities[0,3]

    if prediction[0] == 0:
        classfication = "Top Order Batsman"
    elif prediction[0] == 1:
        classfication = "Middle order Batsmen"
    elif prediction[0] == 2:
        classfication = "Lower order Batsmen"
    else:
        classfication = "Tailender Batsmen"

    return jsonify({"success": True, "prediction_text": classfication, "prediction_p": maxi,"top":top,"middle":middle,"low":low,"tail":tail})


@app.route('/save', methods=["POST"])
def save():
    # Access player name, prediction probability, and predicted label from the hidden form
    player_name = request.form.get("player_name")
    prediction_prob = request.form.get("prediction_prob")
    predicted_label = request.form.get("predicted_label")
    top=request.form.get("top")
    middle=request.form.get("middle")
    low=request.form.get("low")
    tail=request.form.get("tail")

     # Check if the player with the same name already exists
    existing_player = Player1.query.filter_by(name=player_name).first()
    if existing_player:
        return jsonify({"success": False, "message": "Player with the same name already exists."})


    # Save the data to your database or perform any other desired actions
    new_player = Player1(name=player_name, prediction_prob=prediction_prob, predicted_label=predicted_label,top=top,middle=middle,low=low,tail=tail)
    db.session.add(new_player)
    db.session.commit()

    return jsonify({"success": True, "message": "suceesfuly store."})
     
@app.route('/delete_players', methods=["POST"])
def delete_players():
    player_ids = request.form.getlist('player_ids')

    if player_ids:
        # Delete selected players from the database
        Player1.query.filter(Player1.id.in_(player_ids)).delete(synchronize_session='fetch')
        db.session.commit()

    return redirect(url_for('database'))


@app.route('/generate_rankings', methods=["POST"])
def generate_rankings():
    # Fetch all players from the database
    all_players = Player1.query.all()

    # Separate players into categories
    top_order = []
    middle_order = []
    lower_order = []
    tailender = []

    for player in all_players:
        if player.predicted_label == "Top Order Batsman":
            top_order.append(player)
        elif player.predicted_label == "Middle order Batsmen":
            middle_order.append(player)
        elif player.predicted_label == "Lower order Batsmen":
            lower_order.append(player)
        elif player.predicted_label == "Tailender Batsmen":
            tailender.append(player)

    # Rank players within each category based on prediction probability
    top_order_ranked = sorted(top_order, key=lambda x: x.prediction_prob, reverse=True)
    middle_order_ranked = sorted(middle_order, key=lambda x: x.prediction_prob, reverse=True)
    lower_order_ranked = sorted(lower_order, key=lambda x: x.prediction_prob, reverse=True)
    tailender_ranked = sorted(tailender, key=lambda x: x.prediction_prob, reverse=True)

    return render_template('ranking.html',
                           top_order_ranked=top_order_ranked,
                           middle_order_ranked=middle_order_ranked,
                           lower_order_ranked=lower_order_ranked,
                           tailender_ranked=tailender_ranked,
                           show_details_button=True)

@app.route('/display_details', methods=["POST"])
def display_details():
    category = request.form.get("category")

    # Mapping between category and corresponding column names
    category_column_mapping = {
        "top": "top",
        "middle": "middle",
        "low": "low",
        "tail": "tail"
    }

    # Ensure the category is valid
    if category not in category_column_mapping:
        return render_template('error.html', message='Invalid category selected.')

    # Fetch details for the selected category and order by the corresponding column
    column_name = category_column_mapping[category]
    players = Player1.query.order_by(getattr(Player1, column_name).desc()).limit(6).all()

    return render_template('details.html', category=category, players=players)




if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create database tables before running the app
    app.run(debug=True)

