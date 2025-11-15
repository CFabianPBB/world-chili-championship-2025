from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chili-secret-key-change-in-production')

# In-memory storage (you can upgrade to Redis/database later if needed)
contestants = {}
votes = []
results_public = False  # Toggle this to make results visible to everyone

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'chili2025')

@app.route('/')
def index():
    return render_template('vote.html', contestants=contestants)

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return render_template('admin_login.html')
    return render_template('admin.html', contestants=contestants)

@app.route('/admin/login', methods=['POST'])
def admin_login():
    password = request.form.get('password')
    if password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return redirect(url_for('admin'))
    return render_template('admin_login.html', error='Invalid password')

@app.route('/results/login', methods=['POST'])
def results_login():
    password = request.form.get('password')
    if password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return redirect(url_for('results'))
    return render_template('results_login.html', error='Invalid password')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin/add_contestant', methods=['POST'])
def add_contestant():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    contestant_number = data.get('number')
    contestant_name = data.get('name', f'Chili #{contestant_number}')
    
    if not contestant_number:
        return jsonify({'error': 'Number is required'}), 400
    
    contestants[contestant_number] = {
        'number': contestant_number,
        'name': contestant_name,
        'added_at': datetime.now().isoformat()
    }
    
    return jsonify({'success': True, 'contestants': contestants})

@app.route('/admin/remove_contestant', methods=['POST'])
def remove_contestant():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    contestant_number = data.get('number')
    
    if contestant_number in contestants:
        del contestants[contestant_number]
        return jsonify({'success': True, 'contestants': contestants})
    
    return jsonify({'error': 'Contestant not found'}), 404

@app.route('/admin/toggle_results_public', methods=['POST'])
def toggle_results_public():
    global results_public
    
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    results_public = not results_public
    
    return jsonify({
        'success': True, 
        'results_public': results_public,
        'message': 'Results are now ' + ('PUBLIC - everyone can see!' if results_public else 'PRIVATE - admin only')
    })

@app.route('/vote', methods=['POST'])
def submit_vote():
    data = request.json
    first = data.get('first')
    second = data.get('second')
    third = data.get('third')
    voter_name = data.get('voter_name', 'Anonymous')
    
    # Validate votes
    if not all([first, second, third]):
        return jsonify({'error': 'Please select all three places'}), 400
    
    if len(set([first, second, third])) != 3:
        return jsonify({'error': 'Please select three different chilies'}), 400
    
    if not all([c in contestants for c in [first, second, third]]):
        return jsonify({'error': 'Invalid contestant number'}), 400
    
    vote = {
        'first': first,
        'second': second,
        'third': third,
        'voter_name': voter_name,
        'timestamp': datetime.now().isoformat()
    }
    
    votes.append(vote)
    
    return jsonify({'success': True, 'message': 'Vote submitted successfully!'})

@app.route('/results')
def results():
    # Allow public access if results_public is True, otherwise require admin login
    if not results_public and not session.get('admin_logged_in'):
        return render_template('results_login.html')
    
    if not votes:
        return render_template('results.html', results=None, contestants=contestants)
    
    # Calculate scores (3 points for 1st, 2 for 2nd, 1 for 3rd)
    scores = {}
    vote_counts = {}
    
    for contestant_num in contestants:
        scores[contestant_num] = 0
        vote_counts[contestant_num] = {'first': 0, 'second': 0, 'third': 0, 'total': 0}
    
    for vote in votes:
        scores[vote['first']] = scores.get(vote['first'], 0) + 3
        scores[vote['second']] = scores.get(vote['second'], 0) + 2
        scores[vote['third']] = scores.get(vote['third'], 0) + 1
        
        vote_counts[vote['first']]['first'] += 1
        vote_counts[vote['second']]['second'] += 1
        vote_counts[vote['third']]['third'] += 1
        
        vote_counts[vote['first']]['total'] += 1
        vote_counts[vote['second']]['total'] += 1
        vote_counts[vote['third']]['total'] += 1
    
    # Sort by score
    sorted_contestants = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    results_data = []
    for contestant_num, score in sorted_contestants[:3]:
        if score > 0:  # Only show contestants with votes
            results_data.append({
                'number': contestant_num,
                'name': contestants[contestant_num]['name'],
                'score': score,
                'first_place_votes': vote_counts[contestant_num]['first'],
                'second_place_votes': vote_counts[contestant_num]['second'],
                'third_place_votes': vote_counts[contestant_num]['third'],
                'total_votes': vote_counts[contestant_num]['total']
            })
    
    return render_template('results.html', results=results_data, contestants=contestants, total_votes=len(votes))

@app.route('/api/contestants')
def get_contestants():
    return jsonify(contestants)

@app.route('/api/results_status')
def get_results_status():
    return jsonify({
        'results_public': results_public,
        'is_admin': session.get('admin_logged_in', False)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)