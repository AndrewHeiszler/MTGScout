from flask import Flask, render_template, request, jsonify
import json
import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv

load_dotenv() 

app = Flask(__name__)

# Load environment variables
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_S3_BUCKET_NAME = os.getenv('AWS_S3_BUCKET_NAME')
AWS_S3_REGION = os.getenv('AWS_S3_REGION')
DATA_FILE = 'data/tournament_data.json'


s3_client = boto3.client(
    's3',
    region_name=AWS_S3_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# Load or initialize tournament data
def load_data():
    try:
        s3_response = s3_client.get_object(Bucket=AWS_S3_BUCKET_NAME, Key=DATA_FILE)
        data = s3_response['Body'].read().decode('utf-8')
        return json.loads(data)
    except s3_client.exceptions.NoSuchKey:
        return {'players': {}, 'tables': [], 'deductions': {}}
    except (NoCredentialsError, ClientError) as e:
        print(f"Error loading data: {e}")
        return {'players': {}, 'tables': [], 'deductions': {}}
    
tournament_data = load_data()

def save_data(data_to_save):
    try:
        s3_client.put_object(Bucket=AWS_S3_BUCKET_NAME, Key=DATA_FILE, Body=json.dumps(data_to_save))
    except (NoCredentialsError, ClientError) as e:
        print(f"Error saving data: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_player', methods=['POST'])
def add_player():
    load_data()
    player_name = request.form['playerName'].strip().lower()
    deck = request.form['deck'].strip().lower()
    tournament_data['players'][player_name] = deck
    save_data(tournament_data)
    return jsonify({'status': 'success'})

@app.route('/add_table', methods=['POST'])
def add_table():
    load_data()
    table_data = json.loads(request.form['tableData'])
    for table in table_data:
        table['player1'] = table['player1'].strip().lower()
        table['player2'] = table['player2'].strip().lower()
        table['deck1'] = table['deck1'].strip().lower()
        table['deck2'] = table['deck2'].strip().lower()
    tournament_data['tables'].extend(table_data)  # Append new tables to the list
    save_data(tournament_data)
    return jsonify({'status': 'success'})

@app.route('/deduce_decks', methods=['POST'])
def deduce_decks():
    tournament_data = load_data()
    known_decks = tournament_data['players']
    tables = tournament_data['tables']

    possible_decks = {}

    for table_data in tables:
        player1, player2 = table_data['player1'], table_data['player2']
        deck1, deck2 = table_data['deck1'], table_data['deck2']

        if player1 not in possible_decks:
            possible_decks[player1] = {}
        if player2 not in possible_decks:
            possible_decks[player2] = {}

        if deck1 not in possible_decks[player1]:
            possible_decks[player1][deck1] = 0
        if deck2 not in possible_decks[player1]:
            possible_decks[player1][deck2] = 0
        if deck1 not in possible_decks[player2]:
            possible_decks[player2][deck1] = 0
        if deck2 not in possible_decks[player2]:
            possible_decks[player2][deck2] = 0

        possible_decks[player1][deck1] += 1
        possible_decks[player1][deck2] += 1
        possible_decks[player2][deck1] += 1
        possible_decks[player2][deck2] += 1

        # Update known players based on tables
        if player1 in known_decks and player2 not in known_decks:
            known_decks[player2] = deck2 if known_decks[player1] == deck1 else deck1
        elif player2 in known_decks and player1 not in known_decks:
            known_decks[player1] = deck1 if known_decks[player2] == deck2 else deck2

    # Deduce possible decks
    deduced_decks = {}
    for player, decks in possible_decks.items():
        max_count = max(decks.values())
        max_seen_decks = [deck for deck, count in decks.items() if count == max_count]
        if player not in known_decks and len(max_seen_decks) == 1:
            known_decks[player] = max_seen_decks[0]
            if player in deduced_decks:
                del deduced_decks[player]
        else:
            deduced_decks[player] = max_seen_decks

    to_delete = []
    for player in deduced_decks:
        if player in known_decks:
            to_delete.append(player)
    while(len(to_delete) > 0):
        temp = to_delete.pop()
        del deduced_decks[temp]

    
    tournament_data['deductions'] = dict(sorted(deduced_decks.items()))
    tournament_data['players'] = dict(sorted(known_decks.items()))
    output_data = {'Known Decks': known_decks, 'Deduced Decks': deduced_decks}
    save_data(tournament_data)
    return jsonify(output_data)

@app.route('/reset_data', methods=['POST'])
def reset_data():
    global tournament_data
    tournament_data = {'players': {}, 'tables': [], 'deductions': {}}
    save_data(tournament_data)
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/edit_tables', methods=['GET'])
def edit_tables():
    return jsonify({'tables': tournament_data['tables']})

@app.route('/update_tables', methods=['POST'])
def update_tables():
    table_data = json.loads(request.form['tableData'])
    tournament_data['tables'] = table_data
    save_data()
    return jsonify({'status': 'success'})
