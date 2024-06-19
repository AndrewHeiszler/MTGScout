from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

DATA_FILE = 'data/tournament_data.json'

# Load or initialize tournament data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    else:
        return {'players': {}, 'tables': [], 'deductions': {}}

tournament_data = load_data()

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(tournament_data, f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_player', methods=['POST'])
def add_player():
    player_name = request.form['playerName'].strip().lower()
    deck = request.form['deck'].strip().lower()
    tournament_data['players'][player_name] = deck
    save_data()
    return jsonify({'status': 'success'})

@app.route('/add_table', methods=['POST'])
def add_table():
    table_data = json.loads(request.form['tableData'])
    for table in table_data:
        table['player1'] = table['player1'].strip().lower()
        table['player2'] = table['player2'].strip().lower()
        table['deck1'] = table['deck1'].strip().lower()
        table['deck2'] = table['deck2'].strip().lower()
    tournament_data['tables'].extend(table_data)  # Append new tables to the list
    save_data()
    return jsonify({'status': 'success'})

@app.route('/deduce_decks', methods=['POST'])
def deduce_decks():
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
    save_data()
    return jsonify(output_data)

@app.route('/reset_data', methods=['POST'])
def reset_data():
    global tournament_data
    tournament_data = {'players': {}, 'tables': [], 'deductions': {}}
    save_data()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)
