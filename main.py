import os
import firebase_admin
from flask import Flask, request, jsonify
from flask_cors import CORS
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

cred = credentials.Certificate({
    "type":                        os.getenv("FIREBASE_TYPE", "service_account"),
    "project_id":                  os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id":              os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key":                 os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
    "client_email":                os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id":                   os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri":                    os.getenv("FIREBASE_AUTH_URI"),
    "token_uri":                   os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url":        os.getenv("FIREBASE_CLIENT_CERT_URL"),
})
firebase_admin.initialize_app(cred)
db = firestore.client()

# ── helpers ──────────────────────────────────────────────
PLAYERS = lambda: db.collection('DND').document('players').collection('player_list')
ALIENS  = lambda: db.collection('DND').document('aliens').collection('alien_list')
P_ALIENS = lambda pid: PLAYERS().document(pid).collection('aliens')


# ═══════════════════════════════════════════════
#  MASTER ALIENS  (template กลาง)
# ═══════════════════════════════════════════════

@app.route('/aliens', methods=['GET'])
def get_all_master_aliens():
    docs = ALIENS().stream()
    return jsonify({doc.id: doc.to_dict() for doc in docs}), 200

@app.route('/aliens', methods=['POST'])
def add_master_alien_bulk():
    data = request.get_json()
    alien_id = data.get('alien_id')
    if not alien_id:
        return jsonify({'message': 'alien_id is required'}), 400
    ALIENS().document(alien_id).set({
        'name':       data.get('name'),
        'rank':       data.get('rank'),
        'species':    data.get('species'),
        'hp':         data.get('hp'),
        'hp_max':     data.get('hp_max'),
        'ac':         data.get('ac'),
        'speed':      data.get('speed'),
        'STR':        data.get('STR'),
        'DEX':        data.get('DEX'),
        'CON':        data.get('CON'),
        'INT':        data.get('INT'),
        'WIS':        data.get('WIS'),
        'CHA':        data.get('CHA'),
        'abilities':  data.get('abilities', []),
        'weaknesses': data.get('weaknesses', []),
        'items':      data.get('items', []),
    })
    return jsonify({'message': f'Master alien {alien_id} created.'}), 201

@app.route('/alien/<alien_id>', methods=['GET'])
def get_master_alien(alien_id):
    doc = ALIENS().document(alien_id).get()
    if not doc.exists:
        return jsonify({'message': 'Alien not found'}), 404
    return jsonify(doc.to_dict()), 200

@app.route('/alien', methods=['POST'])
def add_master_alien():
    data = request.get_json()
    alien_id = data.get('alien_id')
    if not alien_id:
        return jsonify({'message': 'alien_id is required'}), 400
    ALIENS().document(alien_id).set({
        'name':       data.get('name'),
        'rank':       data.get('rank'),
        'hp':         data.get('hp'),
        'hp_max':     data.get('hp_max'),
        'ac':         data.get('ac'),
        'speed':      data.get('speed'),
        'STR':        data.get('STR'),
        'DEX':        data.get('DEX'),
        'CON':        data.get('CON'),
        'INT':        data.get('INT'),
        'WIS':        data.get('WIS'),
        'CHA':        data.get('CHA'),
        'abilities':  data.get('abilities', []),
        'weaknesses': data.get('weaknesses', []),
        'items':      data.get('items', []),
    })
    return jsonify({'message': f'Master alien {alien_id} created.'}), 201

@app.route('/alien/<alien_id>', methods=['PATCH'])
def patch_master_alien(alien_id):
    data = request.get_json()
    ALIENS().document(alien_id).update(data)
    return jsonify({'message': f'Master alien {alien_id} updated.'}), 200

@app.route('/alien/<alien_id>', methods=['DELETE'])
def delete_master_alien(alien_id):
    ALIENS().document(alien_id).delete()
    return jsonify({'message': f'Master alien {alien_id} deleted.'}), 200


# ═══════════════════════════════════════════════
#  PLAYERS
# ═══════════════════════════════════════════════

@app.route('/players', methods=['GET'])
def get_all_players():
    docs = PLAYERS().stream()
    return jsonify({doc.id: doc.to_dict() for doc in docs}), 200

@app.route('/player/<player_id>', methods=['GET'])
def get_player(player_id):
    doc = PLAYERS().document(player_id).get()
    if not doc.exists:
        return jsonify({'message': 'Player not found'}), 404
    return jsonify(doc.to_dict()), 200

@app.route('/player', methods=['POST'])
def add_player():
    data = request.get_json()
    player_id = data.get('player_id')
    if not player_id:
        return jsonify({'message': 'player_id is required'}), 400
    PLAYERS().document(player_id).set({
        'name':              data.get('name'),
        'CHA':               data.get('CHA'),
        'level':             data.get('level'),
        'xp':                data.get('xp'),
        'hp':                data.get('hp'),
        'hp_max':            data.get('hp_max'),
        'active_alien':      None,
        'omnitrix_cooldown': False,
        'status_effects':    [],
        'inventory':         [],
    })
    return jsonify({'message': f'Player {player_id} created.'}), 201

@app.route('/player/<player_id>', methods=['PATCH'])
def patch_player(player_id):
    data = request.get_json()
    PLAYERS().document(player_id).update(data)
    return jsonify({'message': f'Player {player_id} updated.'}), 200

@app.route('/player/<player_id>', methods=['DELETE'])
def delete_player(player_id):
    PLAYERS().document(player_id).delete()
    return jsonify({'message': f'Player {player_id} deleted.'}), 200


# ═══════════════════════════════════════════════
#  PLAYER'S ALIENS  (ก็อปจาก master + upgrade ได้)
# ═══════════════════════════════════════════════

@app.route('/player/<player_id>/aliens', methods=['GET'])
def get_player_aliens(player_id):
    docs = P_ALIENS(player_id).stream()
    return jsonify({doc.id: doc.to_dict() for doc in docs}), 200

@app.route('/player/<player_id>/alien/<alien_id>', methods=['GET'])
def get_player_alien(player_id, alien_id):
    doc = P_ALIENS(player_id).document(alien_id).get()
    if not doc.exists:
        return jsonify({'message': 'Alien not found'}), 404
    return jsonify(doc.to_dict()), 200

@app.route('/player/<player_id>/alien', methods=['POST'])
def add_player_alien(player_id):
    """
    ก็อป base stats จาก master alien ก่อน
    แล้ว merge กับ data ที่ส่งมา (player สามารถ override ได้)
    """
    data = request.get_json()
    alien_id = data.get('alien_id')
    if not alien_id:
        return jsonify({'message': 'alien_id is required'}), 400

    # โหลด master template (ถ้ามี)
    master_doc = ALIENS().document(alien_id).get()
    base = master_doc.to_dict() if master_doc.exists else {}

    # merge: master เป็น base, data ที่ส่งมา override ทับ
    def pick(key):
        return data.get(key) if data.get(key) is not None else base.get(key)

    # rank เป็น field ของ master alien เท่านั้น ไม่ copy ไป player
    merged = {
        'name':       data.get('name') or base.get('name'),
        'hp':         pick('hp'),
        'hp_max':     pick('hp_max'),
        'ac':         pick('ac'),
        'speed':      pick('speed'),
        'STR':        pick('STR'),
        'DEX':        pick('DEX'),
        'CON':        pick('CON'),
        'INT':        pick('INT'),
        'WIS':        pick('WIS'),
        'CHA':        pick('CHA'),
        'abilities':  data.get('abilities')  or base.get('abilities',  []),
        'weaknesses': data.get('weaknesses') or base.get('weaknesses', []),
        'items':      data.get('items')      or base.get('items',      []),
    }

    P_ALIENS(player_id).document(alien_id).set(merged)
    source = 'master template' if master_doc.exists else 'custom'
    return jsonify({'message': f'Alien {alien_id} added to {player_id} (from {source}).'}), 201

@app.route('/player/<player_id>/alien/<alien_id>', methods=['PATCH'])
def patch_player_alien(player_id, alien_id):
    data = request.get_json()
    P_ALIENS(player_id).document(alien_id).update(data)
    return jsonify({'message': f'Alien {alien_id} updated.'}), 200

@app.route('/player/<player_id>/alien/<alien_id>', methods=['DELETE'])
def delete_player_alien(player_id, alien_id):
    P_ALIENS(player_id).document(alien_id).delete()
    return jsonify({'message': f'Alien {alien_id} deleted from {player_id}.'}), 200


# ═══════════════════════════════════════════════
#  TRANSFORM
# ═══════════════════════════════════════════════

@app.route('/player/<player_id>/transform', methods=['PATCH'])
def patch_transform(player_id):
    data = request.get_json()
    alien_id = data.get('alien_id')
    if alien_id:
        PLAYERS().document(player_id).update({
            'active_alien': alien_id,
            'omnitrix_cooldown': True,
        })
    else:
        PLAYERS().document(player_id).update({
            'active_alien': None,
            'omnitrix_cooldown': False,
        })
    return jsonify({'message': 'Transform updated.'}), 200


if __name__ == '__main__':
    app.run(debug=True)
