import os
import firebase_admin
from flask import Flask, request, jsonify
from flask_cors import CORS
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, origins="*")

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
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ── helpers ──────────────────────────────────────────────
PLAYERS    = lambda: db.collection('DND').document('players').collection('player_list')
ALIENS     = lambda: db.collection('DND').document('aliens').collection('alien_list')
P_ALIENS   = lambda pid: PLAYERS().document(pid).collection('aliens')
META       = lambda: db.collection('DND').document('meta')
CHARACTERS = lambda: db.collection('DND').document('characters').collection('character_list')
SESSIONS   = lambda: db.collection('DND').document('sessions').collection('session_list')

EMPTY_ALIEN = {
    'rank': None, 'species': None,
    'hp': None, 'hp_max': None, 'ac': None, 'speed': None,
    'STR': None, 'DEX': None, 'CON': None,
    'INT': None, 'WIS': None, 'CHA': None,
    'abilities': [], 'weaknesses': [], 'items': [],
}


def _build_empty_slots(filled: int, total: int) -> list:
    """สร้าง empty slot list ให้ครบ total โดยไม่บันทึก DB"""
    count = max(0, total - filled)
    slots = []
    for i in range(count):
        alien_id = 'empty_slot' if count == 1 else f'empty_slot_{i + 1}'
        name     = 'Empty Slot'  if count == 1 else f'Empty Slot {i + 1}'
        slots.append({'alien_id': alien_id, 'name': name, **EMPTY_ALIEN})
    return slots


# ═══════════════════════════════════════════════
#  CAMPAIGN META
# ═══════════════════════════════════════════════

@app.route('/meta', methods=['GET'])
def get_meta():
    doc = META().get()
    data = doc.to_dict() if doc.exists else {}
    return jsonify({
        'campaign':              data.get('campaign',              'Ben 10 D&D'),
        'session':               data.get('session',               1),
        'total_xp_to_level_3':  data.get('total_xp_to_level_3',  2700),
    }), 200

@app.route('/meta', methods=['PATCH'])
def patch_meta():
    data = request.get_json()
    META().set(data, merge=True)
    return jsonify({'message': 'Meta updated.'}), 200


# ═══════════════════════════════════════════════
#  STORY CHARACTERS
# ═══════════════════════════════════════════════

@app.route('/characters', methods=['GET'])
def get_characters():
    docs = CHARACTERS().stream()
    return jsonify({doc.id: doc.to_dict() for doc in docs}), 200

@app.route('/character', methods=['POST'])
def add_character():
    data = request.get_json()
    char_id = data.get('character_id')
    if not char_id:
        return jsonify({'message': 'character_id is required'}), 400
    CHARACTERS().document(char_id).set({
        'name':       data.get('name'),
        'faction':    data.get('faction', 'unknown'),  # ally | enemy | unknown
        'species':    data.get('species'),
        'status':     data.get('status'),
        'extra_info': data.get('extra_info'),
        'image_url':  data.get('image_url'),
        'hp':         data.get('hp'),
        'ac':         data.get('ac'),
    })
    return jsonify({'message': f'Character {char_id} created.'}), 201

@app.route('/character/<char_id>', methods=['PATCH'])
def patch_character(char_id):
    data = request.get_json()
    CHARACTERS().document(char_id).update(data)
    return jsonify({'message': f'Character {char_id} updated.'}), 200

@app.route('/character/<char_id>', methods=['DELETE'])
def delete_character(char_id):
    CHARACTERS().document(char_id).delete()
    return jsonify({'message': f'Character {char_id} deleted.'}), 200


# ═══════════════════════════════════════════════
#  SESSIONS
# ═══════════════════════════════════════════════

@app.route('/sessions', methods=['GET'])
def get_sessions():
    docs = SESSIONS().order_by('session').stream()
    return jsonify({doc.id: doc.to_dict() for doc in docs}), 200

@app.route('/session', methods=['POST'])
def add_session():
    data = request.get_json()
    session_num = data.get('session')
    if session_num is None:
        return jsonify({'message': 'session is required'}), 400
    session_id = f'session_{session_num}'
    SESSIONS().document(session_id).set({
        'session':           session_num,
        'title':             data.get('title'),
        'summary':           data.get('summary'),
        'player_upgrades':   data.get('player_upgrades',   {}),
        'character_notes':   data.get('character_notes',   {}),
    })
    return jsonify({'message': f'Session {session_num} created.'}), 201

@app.route('/session/<session_id>', methods=['PATCH'])
def patch_session(session_id):
    data = request.get_json()
    SESSIONS().document(session_id).update(data)
    return jsonify({'message': f'Session {session_id} updated.'}), 200

@app.route('/session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    SESSIONS().document(session_id).delete()
    return jsonify({'message': f'Session {session_id} deleted.'}), 200


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

@app.route('/players/full', methods=['GET'])
def get_players_full():
    """ดึงข้อมูลทุกอย่างในรูปแบบ players.json พร้อม aliens embed + empty slots"""
    meta_doc = META().get()
    meta = meta_doc.to_dict() if meta_doc.exists else {}

    result = {
        'campaign':             meta.get('campaign',             'Ben 10 D&D'),
        'session':              meta.get('session',              1),
        'total_xp_to_level_3': meta.get('total_xp_to_level_3', 2700),
        'players': [],
    }

    for pdoc in PLAYERS().stream():
        p   = pdoc.to_dict()
        pid = pdoc.id

        # รวม aliens จาก subcollection เป็น list
        aliens = []
        for adoc in P_ALIENS(pid).stream():
            a = adoc.to_dict()
            a['alien_id'] = adoc.id
            aliens.append(a)

        # เติม empty slots ให้ครบ omnitrix_slots
        slots = p.get('omnitrix_slots', 0)
        aliens += _build_empty_slots(len(aliens), slots)

        result['players'].append({
            'player_id':         pid,
            'player_name':       p.get('name'),
            'level':             p.get('level'),
            'xp':                p.get('xp'),
            'hp':                p.get('hp'),
            'hp_max':            p.get('hp_max'),
            'status_effects':    p.get('status_effects',    []),
            'omnitrix_cooldown': p.get('omnitrix_cooldown', False),
            'upgrade':           p.get('upgrade'),
            'inventory':         p.get('inventory',         []),
            'omnitrix_slots':    slots,
            'aliens':            aliens,
        })

    return jsonify(result), 200

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
        'omnitrix_slots':    data.get('omnitrix_slots', 10),
        'upgrade':           data.get('upgrade'),
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

    merged = {
        'name':       data.get('name') or base.get('name'),
        'rank':       pick('rank'),
        'species':    pick('species'),
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
