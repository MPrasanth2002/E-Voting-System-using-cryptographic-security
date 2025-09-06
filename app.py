from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import json
import os
import gnupg

gpg = gnupg.GPG()
GPG_PASSPHRASE ="Patra@321"

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # for session management it is required



VOTERS_DB = 'voters.json'
VOTES_DB = 'votes.json'

with open("public_key.asc") as f:
    gpg.import_keys(f.read())
with open("private_key.asc") as f:
    gpg.import_keys(f.read())

# make sure json file is present in the folder
for db in [VOTERS_DB, VOTES_DB]:
    if not os.path.exists(db):
        with open(db, 'w') as f:
            json.dump([], f)

def encrypted_data(data):
    """Encrypt data using GPG and return as a string."""
    encrypted = gpg.encrypt(data, recipients=['animationff6@gmail.com'], symmetric='AES256', passphrase=GPG_PASSPHRASE)
    return str(encrypted)

def decrypt_data(encrypted_data):
    """Decrypt data using GPG and return as a string."""
    decrypted = gpg.decrypt(encrypted_data, passphrase=GPG_PASSPHRASE)
    return str(decrypted)


def load_voters():
    """here it Load voter data from JSON file."""
    if os.path.exists(VOTERS_DB):
        with open(VOTERS_DB, 'r') as f:
            return json.load(f)
    return []

def save_voter(voter):
    """Saves new voters to JSON file."""
    voters = load_voters()
    voters.append(voter)
    with open(VOTERS_DB, 'w') as f:
        json.dump(voters, f)

def load_votes():
    """itt Loads votes from JSON file."""
    if os.path.exists(VOTES_DB):
        with open(VOTES_DB, 'r') as f:
            return json.load(f)
    return []

def save_vote(vote):
    """always Saves a new vote."""
    votes = load_votes()
    votes.append(vote)
    with open(VOTES_DB, 'w') as f:
        json.dump(votes, f)

@app.route('/')
def home():
    return render_template('vote.html')  


@app.route('/register')
def register():
    return render_template('register.html')  

@app.route('/register', methods=['POST'])
def register_user():
    """used tto Registers a new voter."""
    data = request.get_json()
    full_name = data.get('full_name')
    ssn = data.get('ssn')
    phone = data.get('phone')
    security_answer = data.get('security_answer')

    # Encrypt personal info before saving that helps a lot
    encrypted_full_name =encrypted_data(full_name)
    encrypted_phone = encrypted_data(phone) 
    encrypted_ssn = encrypted_data(ssn)
    encrypted_security_answer = encrypted_data(security_answer)

    # Checks whether the user is already in thje data base or not
    voters = load_voters()
    if any(decrypt_data(v['ssn']) == ssn for v in voters):  # Decrypt SSN for checking
        return jsonify({"success": False, "message": "SSN already registered."})

    new_voter = {
        "full_name": full_name,
        "ssn": encrypted_ssn,  # ssn encrypted will be stored
        "phone": phone,
        "security_answer": encrypted_security_answer  # Store answer encryptedly
    }
    save_voter(new_voter)

    return jsonify({"success": True, "message": "Registration successful!"})


@app.route('/login', methods=['POST'])
def login():
    """this is used to Login and store session data."""
    data = request.get_json()
    ssn = data.get('ssn')
    security_answer = data.get('security_answer')

    voters = load_voters()
    user = next((v for v in voters if decrypt_data(v['ssn']) == ssn), None)  # this step is used for decrypting

    if not user:
        return jsonify({"success": False, "message": "SSN not found."})

    if decrypt_data(user['security_answer']) != security_answer:  # here the security answer is decrypted
        return jsonify({"success": False, "message": "Incorrect security answer."})

    # here the user is stored in the session (except SSN for privacy)
    session['voter'] = {
        "full_name": user["full_name"],
        "phone": user["phone"]
    }

    return jsonify({"success": True, "message": "Login successful!", "redirect": url_for('dashboard')})

@app.route('/dashboard')
def dashboard():
    """here the User dashboard after login."""
    if 'voter' not in session:
        return redirect(url_for('home'))  # directly goes to home if not logged in

    return render_template('dashboard.html', voter=session['voter'])


@app.route('/vote', methods=['POST'])
def vote():
    """we will Submit a vote."""
    if 'voter' not in session:
        return jsonify({"success": False, "message": "Not logged in!"})

    data = request.get_json()
    party = data.get('party')

    votes = load_votes()
    # to prevent duplicate votes
    if any(v['full_name'] == session['voter']['full_name'] for v in votes):
        return jsonify({"success": False, "message": "You have already voted!"})
    encrypted_full_name =encrypted_data(session['voter']['full_name'])
    vote_data = {
        "full_name": encrypted_full_name,
        "vote": party
    }
    save_vote(vote_data)

    return jsonify({"success": True, "message": "Vote casted successfully!"})

@app.route('/vote-results')
def vote_results():
    """it Calculates total votes and percentage for each party and give output."""
    votes = load_votes()
    
    # vote counting for party
    party_counts = {}
    for vote in votes:
        party = vote['vote']
        party_counts[party] = party_counts.get(party, 0) + 1

    # total votes will be calculated here
    total_votes = sum(party_counts.values())

    # Calculate percentages for the entire poll
    party_percentages = {party: round((count / total_votes) * 100, 2) for party, count in party_counts.items()} if total_votes > 0 else {}

    return jsonify({
        "total_votes": total_votes,
        "party_counts": party_counts,
        "party_percentages": party_percentages
    })


@app.route('/vote')
def vote_page():
    return render_template('vote.html')

@app.route('/main')
def main_page():
    return render_template('mainpage.html')


@app.route('/logout')
def logout():
    """used to Logout user."""
    session.pop('voter', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
