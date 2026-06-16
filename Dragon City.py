print("="*55)
print(" INICIANDO SERVIDOR LOCAL: DRAGON CITY v1.0 ")
print("="*55)
print("[+] Inicializando módulos de Flask y dependencias...")
from flask import Flask, request, jsonify, send_from_directory
import json
import os
import time
import hmac
import hashlib
import random
import atexit
import ctypes
import math
import queue

app = Flask(__name__)

jugadores_sse = {}

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"

HOSTS_ENTRIES = [
    "127.0.0.1 static.socialpointgames.com",
    "127.0.0.1 ajax.googleapis.com",
    "127.0.0.1 api.omniata.com",
    "127.0.0.1 sp-translations.socialpointgames.com",
]

MARKER = "# --- Dragon City Flash ---"

def add_hosts():
    with open(HOSTS_PATH, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    if MARKER in contenido:
        print("[+] Las entradas del hosts ya están activas.")
        return

    with open(HOSTS_PATH, 'a', encoding='utf-8') as f:
        f.write(f"\n{MARKER}\n")
        for entry in HOSTS_ENTRIES:
            f.write(f"{entry}\n")
        f.write(f"{MARKER}\n")
    
    print("[+] Entradas añadidas al hosts correctamente.")

def remove_hosts():
    with open(HOSTS_PATH, 'r', encoding='utf-8') as f:
        lineas = f.readlines()

    nuevas_lineas = []
    dentro_del_bloque = False

    for linea in lineas:
        if MARKER in linea:
            dentro_del_bloque = not dentro_del_bloque
            continue
        if not dentro_del_bloque:
            nuevas_lineas.append(linea)

    with open(HOSTS_PATH, 'w', encoding='utf-8') as f:
        f.writelines(nuevas_lineas)

    print("[+] Entradas del hosts eliminadas correctamente.")

atexit.register(remove_hosts)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
FLASH_DIR     = os.path.join(BASE_DIR, 'flash')
WEB_DIR       = os.path.join(BASE_DIR, 'web')
SRV_DIR       = os.path.join(WEB_DIR, 'srv')
DOMAIN_MAP_DIR = os.path.join(BASE_DIR, 'domains')
ASSETS_DIR    = os.path.join(BASE_DIR, 'assets')

SECRET_KEY = "RGhXbiy4xEeDnSNX1oBG"

print("[+] Cargando motor de cría y genéticas...")
print("    -> Configurando pesos y multiplicadores de rareza...")
print("    -> Registrando combinaciones Legendarias y Puras...")
WEIGHT_DIFFICULTY = {1: 55, 2: 25, 3: 5}
WEIGHT_DIFFICULTY_BOOSTED = {1: 40, 2: 35, 3: 25}

CATEGORY_MULTIPLIER = {
    1: 1.0,
    2: 0.95,
    3: 0.55,
    4: 0.22,
    5: 0.15,
}

LEGENDARY_COMBOS_BY_ATTRS = {
    frozenset({'w','p','i','f'}): [1041, 1054],
    frozenset({'e','m','f','i'}): [1041, 1052, 1053, 1054],
    frozenset({'w','p','f','i'}): [1052, 1053],
    frozenset({'w','d'}):          [1052],
}

LEGENDARY_FROM_COMBO_CHANCE = 15.0

PURE_DRAGON_BASE_ID = 1081
PURE_CHANCE_BASE    = 3.0
PURE_CHANCE_BOOSTED = 5.0

PURE_ELEMENT_IDS = [1082, 1083, 1084, 1085, 1086, 1087, 1088, 1089]
PURE_ELEMENT_CHANCE_BASE    = 5.0
PURE_ELEMENT_CHANCE_BOOSTED = 7.5

def build_dragon_db(config):
    db = {}
    for item in config.get('items', []):
        if item.get('group_type') != 'DRAGON':
            continue
        db[item['id']] = {
            'name':          item.get('name', 'Unknown'),
            'attributes':    set(item.get('attributes', [])),
            'difficulty':    item.get('difficulty', 3),
            'category':      item.get('category', 1),
            'breeding_time': item.get('breeding_time', 86400),
            'breedable':     item.get('breedable', 0),
        }
    return db

def get_breed_result(dragon1_type, dragon2_type, level1, level2, dragon_db, boosted=False):
    if dragon1_type not in dragon_db or dragon2_type not in dragon_db:
        print(f"[!] Tipos desconocidos ({dragon1_type}, {dragon2_type}). Fallback Terra.")
        return 1011

    parent1 = dragon_db[dragon1_type]
    parent2 = dragon_db[dragon2_type]
    pool    = parent1['attributes'] | parent2['attributes']

    is_leg1 = 'l' in parent1['attributes']
    is_leg2 = 'l' in parent2['attributes']

    if is_leg1 != is_leg2:
        print("[★] Cruce Legendario + Común. Resultado aleatorio de la base de datos.")
        valid_any = [
            dtype for dtype, ddata in dragon_db.items()
            if ddata['breedable'] > 0 and level1 >= ddata['breedable'] and level2 >= ddata['breedable']
        ]
        if valid_any:
            chosen = random.choice(valid_any)
            print(f"[★] Resultado aleatorio: Dragon {chosen} ({dragon_db[chosen]['name']})")
            return chosen

    both_legendary = (is_leg1 and is_leg2)
    if both_legendary:
        pure_chance  = PURE_CHANCE_BOOSTED    if boosted else PURE_CHANCE_BASE
        pe_chance    = PURE_ELEMENT_CHANCE_BOOSTED if boosted else PURE_ELEMENT_CHANCE_BASE

        roll = random.uniform(0, 100)

        if roll < pure_chance:
            if PURE_DRAGON_BASE_ID in dragon_db:
                print(f"[★] ¡PURO BASE! Dragon {PURE_DRAGON_BASE_ID}")
                return PURE_DRAGON_BASE_ID

        elif roll < pure_chance + pe_chance:
            pure_with_el = [
                did for did, dd in dragon_db.items()
                if 'pu' in dd['attributes'] and len(dd['attributes']) > 1
                and dd['attributes'] != {'pu'}
            ]
            if not pure_with_el:
                pure_with_el = [i for i in PURE_ELEMENT_IDS if i in dragon_db]
            if pure_with_el:
                chosen = random.choice(pure_with_el)
                print(f"[★] ¡PURO CON ELEMENTO! Dragon {chosen} ({dragon_db[chosen]['name']})")
                return chosen

    if boosted:
        key = frozenset(pool)
        if key in LEGENDARY_COMBOS_BY_ATTRS:
            if random.uniform(0, 100) < LEGENDARY_FROM_COMBO_CHANCE:
                possible = [lid for lid in LEGENDARY_COMBOS_BY_ATTRS[key] if lid in dragon_db]
                if possible:
                    chosen = random.choice(possible)
                    print(f"[★] ¡LEGENDARIO por combo! Dragon {chosen} ({dragon_db[chosen]['name']})")
                    return chosen

    candidates = []
    weights_diff = WEIGHT_DIFFICULTY_BOOSTED if boosted else WEIGHT_DIFFICULTY

    for dtype, ddata in dragon_db.items():
        if ddata['breedable'] == 0:
            continue
        if level1 < ddata['breedable'] or level2 < ddata['breedable']:
            continue
            
        attrs = ddata['attributes']
        if not attrs:
            continue
        if not attrs.issubset(pool):
            continue
        if 'l' in attrs or 'pu' in attrs:
            continue

        diff = ddata['difficulty']
        cat  = ddata['category']
        base_w = weights_diff.get(diff, 5)
        mult   = CATEGORY_MULTIPLIER.get(cat, 0.01)
        final_w = base_w * mult

        if final_w > 0:
            candidates.append((dtype, final_w))

    if not candidates:
        print("[!] Sin candidatos válidos por nivel/atributos. Fallback Terra.")
        return dragon1_type

    total = sum(w for _, w in candidates)
    r     = random.uniform(0, total)
    cumulative = 0
    for dtype, w in candidates:
        cumulative += w
        if r <= cumulative:
            return dtype

    return candidates[-1][0]

print("    -> Motor de cría inicializado correctamente.")

def sign_packet(payload_dict):
    json_payload = json.dumps(payload_dict, separators=(',', ':'))
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        json_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"{signature};{json_payload}"

def get_item_config(config, model_id):
    model_id_str = str(model_id)
    for item in config.get('items', []):
        if str(item.get('id')) == model_id_str:
            return item
    return None

print("[+] Cargando configuración del juego (get_game_config.json)...")
def load_game_config():
    path = os.path.join(SRV_DIR, 'get_game_config.json')
    with open(path, 'r', encoding='utf-8') as f:
        contenido = f.read()
        if ';' in contenido:
            contenido = contenido.split(';', 1)[1]
        return json.loads(contenido)

print("    -> Configuración cargada...")
print("[+] Preparando sistema de guardado y perfiles de jugador...")
def load_player(user_id):
    """Carga el JSON del usuario y sincroniza el timestamp al tiempo real."""
    user_file = os.path.join(SRV_DIR, f"{user_id}.json")
    template_file = os.path.join(SRV_DIR, 'get_player_info.json')
    
    target_path = user_file if os.path.exists(user_file) else template_file
    
    if not os.path.exists(target_path):
        print(f"[!] ERROR CRÍTICO: No existe ni el archivo de usuario ni la plantilla en {SRV_DIR}")
        return {}

    with open(target_path, 'r', encoding='utf-8') as f:
        player_data = json.load(f)

    current_time = int(time.time())
    player_data['timestamp'] = current_time
    
    return player_data

def save_player(state, user_id):
    path = os.path.join(SRV_DIR, f"{user_id}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

@app.route('/')
def serve_login():
    return send_from_directory(TEMPLATES_DIR, 'login.html')

@app.route('/index.html')
def serve_game():
    return send_from_directory(TEMPLATES_DIR, 'index.html')

@app.route('/flash/<path:path>')
def serve_flash(path):
    return send_from_directory(FLASH_DIR, path)

@app.route('/assets/<path:path>')
def serve_assets(path):
    return send_from_directory(ASSETS_DIR, path)

@app.route('/ajax/libs/swfobject/2.2/swfobject.js')
def serve_swfobject():
    file_path = os.path.join(DOMAIN_MAP_DIR, 'ajax.googleapis.com', 'ajax', 'libs', 'swfobject', '2.2', 'swfobject.js')
    if os.path.exists(file_path):
        return send_from_directory(os.path.dirname(file_path), 'swfobject.js')
    return "No encontrado", 404

@app.route('/sp-translations.socialpointgames.com/crossdomain.xml')
@app.route('/crossdomain.xml')
def serve_crossdomain():
    path = os.path.join(DOMAIN_MAP_DIR, 'api.omniata.com', 'crossdomain.xml')
    if os.path.exists(path):
        return send_from_directory(os.path.dirname(path), 'crossdomain.xml')
    return '''<?xml version="1.0"?><cross-domain-policy><allow-access-from domain="*"/></cross-domain-policy>''', 200, {'Content-Type': 'application/xml'}

@app.route('/deploy/dc/canvas/prod/<filename>')
def serve_translations(filename):
    translations_dir = os.path.join(DOMAIN_MAP_DIR, 'sp-translations.socialpointgames.com', 'deploy', 'dc', 'canvas', 'prod')
    if os.path.exists(os.path.join(translations_dir, filename)):
        return send_from_directory(translations_dir, filename)
    return jsonify({"error": "Translation file not found"}), 404

@app.route('/static/dragoncity/srv/<filename>', methods=['GET', 'POST'])
def srv_handler(filename):
    user_id = request.args.get('USERID') or request.form.get('USERID')
    player_name_from_url = request.args.get('player_name')

    target_id = request.form.get('user') or request.args.get('user')
    is_visiting = bool(target_id and target_id not in ('0', '', user_id))
    if is_visiting:
        user_id = target_id

    print(f"\n>>> [PETICIÓN SRV] {filename} | USERID: {user_id}")

    if filename in ('get_game_config.json', 'get_game_config.php'):
        config_data = load_game_config()
        signed = sign_packet(config_data)
        response = app.response_class(
            response=signed,
            status=200,
            mimetype='text/plain'
        )
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        return response

    if filename in ('get_player_info.json', 'get_player_info.php'):
        player_data = load_player(user_id)

        if 'playerInfo' in player_data:
            if not player_data['playerInfo'].get('pid'):
                player_data['playerInfo']['pid'] = user_id
            if player_name_from_url:
                player_data['playerInfo']['name'] = player_name_from_url
                
            if not is_visiting:
                save_player(player_data, user_id)
        signed = sign_packet(player_data)
        return signed, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    return jsonify({"result": "200"})

@app.route('/init_player', methods=['GET'])
def init_player():
    user_id = request.args.get('user_id')
    player_name = request.args.get('player_name')
    
    if user_id and player_name:
        player_data = load_player(user_id)
        if 'playerInfo' in player_data:
            player_data['playerInfo']['name'] = player_name
            player_data['playerInfo']['pid'] = user_id
            save_player(player_data, user_id)
            print(f"✅ Jugador inicializado → Nombre: {player_name} | PID: {user_id}")
            return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

@app.route('/static/dragoncity/srv/sync_error_track.php', methods=['POST', 'GET'])
def sync_error_handler():
    return ("", 200)

@app.route('/static/dragoncity/srv/track_game_status.php', methods=['GET', 'POST'])
def track_status_handler():
    return ("", 200)

@app.route('/stream')
def stream():
    user_id = request.args.get('USERID')
    
    if not user_id:
        return "USERID requerido", 400

    if user_id not in jugadores_sse:
        jugadores_sse[user_id] = queue.Queue()

    def event_stream():
        while True:
            try:
                mensaje = jugadores_sse[user_id].get(timeout=20)
                yield f"data: {mensaje}\n\n"
            except queue.Empty:
                yield "data: PING\n\n"
            except Exception as e:
                print(f"[!] Error en el canal de transmisión SSE: {e}")
                break

    return app.response_class(event_stream(), mimetype='text/event-stream')

print("[+] Analizando protocolo de comandos (packet.php)...")
print("    -> Se han identificado 104 comandos...")
print("    -> [ESTADO] Comandos implementados: 46/104 | Progreso:  44,2%")
print("    -> El resto de comandos devolverán un 'fallback' automático para evitar cierres.")
@app.route('/static/dragoncity/srv/packet.php', methods=['POST', 'GET'])
def packet_handler():
    user_id = request.args.get('USERID') or request.form.get('id')
    print("\n" + "=" * 70)
    print(f">>> [PACKET] Procesando para USERID: {user_id}")

    response_results = []

    if request.method == 'POST':
        data_raw = request.form.get('data', '')
        if ';' in data_raw:
            json_str = data_raw.split(';', 1)[1]
        else:
            json_str = data_raw

        try:
            payload = json.loads(json_str)
            player_data = load_player(user_id)
            game_config = load_game_config()
            commands = payload.get('commands', [])

            response_results = []

            comandos_añadidos = ['buy','buy_egg','place_stored_egg','hatch_egg','feed_dragon','set_goals','complete_goal','breed_dragon','move','sell','sell_egg','sell_dragon','store_item','orient','complete_tutorial','collect','expand_gold', 'expand_cash','activate','finish_building','upgrade','rename_dragon','speed_collect','speed_hatch','sync','ping','finish_breeding2','expand_island','move_dragon','buy_treasure_new','set_attack_team','deus_cards_generate','deus_cards_claim','begin_tournament','end_tournament','admin_speed_tournament','start_training','speed_training','finish_training','weekly_reward','place_stored_item','buy_treasure_popup','complete_collection','dragonarium_push','dragonarium_pull','dragonarium_add']
            
            comando_valido_procesado = False
            comandos_ignorados = []

            for cmd_data in commands:
                cmd = cmd_data.get('cmd')
                cmd_number = cmd_data.get('number')
                args = cmd_data.get('args', [])

                cmd_result = "ok"

                print(f"-> Comando: {cmd} | Args: {args} | N: {cmd_number}")

                if cmd in comandos_añadidos:
                    comando_valido_procesado = True
                
                if cmd == 'buy':
                    iso_id = str(args[0])
                    item_id = args[1]
                    tx = args[2]
                    ty = args[3]
                    p_id = args[4]
                    frame = args[5]
                    flag = args[6]
                    
                    item_cfg = None
                    for item in game_config.get('items', []):
                        if str(item.get('id')) == str(item_id):
                            item_cfg = item
                            break
                    
                    if item_cfg:
                        group_type = item_cfg.get('group_type', '')
                        costs = item_cfg.get('costs', {})
                        gold_cost = costs.get('g', 0)
                        cash_cost = costs.get('c', 0)
                        
                        if gold_cost > 0:
                            player_data['playerInfo']['gold'] = max(0, player_data['playerInfo']['gold'] - gold_cost)
                        if cash_cost > 0:
                            player_data['playerInfo']['cash'] = max(0, player_data['playerInfo']['cash'] - cash_cost)

                        build_time = item_cfg.get('build_time', 0)
                        attributes = {}
                        current_ts = player_data.get('timestamp', int(time.time()))
                        
                        if group_type == 'HABITAT':
                            attributes['ar'] = 0
                            attributes['lat'] = current_ts
                        
                        if build_time > 0:
                            attributes['tb'] = current_ts + build_time
                        else:
                            xp_gain = item_cfg.get('xp', 0)
                            player_data['playerInfo']['xp'] += xp_gain
                            
                        player_data['map']['items'][iso_id] = [item_id, tx, ty, p_id, frame, flag, attributes]
                        
                        print(f"   [BUY OK] {item_cfg.get('name')} construido en ({tx}, {ty}). Atributos: {attributes}")
                        print(f"   [-] Oro restante: {player_data['playerInfo']['gold']} | Gemas: {player_data['playerInfo']['cash']} | XP: {player_data['playerInfo']['xp']}")
                    else:
                        print(f"   [!] Error: El objeto con ID {item_id} no existe en get_game_config.json")

                elif cmd == 'buy_egg':
                    egg_uid = args[0]
                    dragon_id = args[1]
                    
                    item_cfg = None
                    for item in game_config.get('items', []):
                        if str(item.get('id')) == str(dragon_id):
                            item_cfg = item
                            break
                    
                    if item_cfg:
                        costs = item_cfg.get('costs', {})
                        gold_cost = costs.get('g', 0)
                        cash_cost = costs.get('c', 0)
                        
                        if gold_cost > 0:
                            player_data['playerInfo']['gold'] = max(0, player_data['playerInfo']['gold'] - gold_cost)
                        if cash_cost > 0:
                            player_data['playerInfo']['cash'] = max(0, player_data['playerInfo']['cash'] - cash_cost)
                            
                        xp_gain = item_cfg.get('xp', 0)
                        player_data['playerInfo']['xp'] += xp_gain

                        if 'eggs' not in player_data['map']:
                            player_data['map']['eggs'] = []

                        nombres_dragon = ["Roxy", "Horacio", "Sergi", "Kasia", "Xavi", "Draco", "Ignis", "Gabriel"]

                        new_egg = {
                            "id": egg_uid,
                            "type": dragon_id,
                            "name": random.choice(nombres_dragon),
                            "xp": 0,
                            "hatched": False,
                            "ts": int(time.time())
                        }
                        
                        player_data['map']['eggs'].append(new_egg)
                        
                        print(f"   [BUY_EGG OK] Huevo de {item_cfg.get('name')} comprado (UID: {egg_uid}).")
                        print(f"   [-] Oro: {player_data['playerInfo']['gold']} | Gemas: {player_data['playerInfo']['cash']} | XP: {player_data['playerInfo']['xp']}")
                    else:
                        print(f"   [!] Error: El dragón con ID {dragon_id} no existe en get_game_config.json")
                
                elif cmd == 'place_stored_egg':
                    egg_uid = args[0]
                    dragon_id = args[1]

                    item_cfg = None
                    for item in game_config.get('items', []):
                        if str(item.get('id')) == str(dragon_id):
                            item_cfg = item
                            break
                    
                        if 'eggs' not in player_data['map']:
                            player_data['map']['eggs'] = []
                            
                        nombres_dragon = ["Roxy", "Horacio", "Sergi", "Kasia", "Xavi", "Draco", "Ignis", "Gabriel", "Abdona", "Adolfina", "Agripina", "Aleja", "Altagracia", "Amadora", "Amelia", "Anatolia", "Aniceta", "Antolina", "Apolonia", "Arcadia", "Argimira", "Atanasia", "Áurea", "Balbina", "Baltasara", "Basilisa", "Bercia", "Bernabea", "Bernarda", "Blacina", "Blasina", "Brígida", "Bonifacia", "Calista", "Casilda", "Castora", "Cayetana", "Celedonia", "Celestina", "Celina", "Cesárea", "Clementa", "Crisanta", "Crisóstoma", "Críspula", "Cristeta", "Dámasa", "Demetria", "Diega", "Dionisia", "Dominga", "Dominica", "Dorotea", "Dosinda", "Edelmira", "Edicta", "Eduvigis", "Efigenia", "Eleuteria", "Elicia", "Emerenciana", "Emeteria", "Ermisinda", "Escolástica", "Esmaragda", "Esmerencia", "Estanislá", "Etelvina", "Eudosia", "Eulogia", "Eustaquia", "Ezequiela", "Evarista", "Facunda", "Fausta", "Felicia", "Felisa", "Feliciana", "Froilana", "Fulgencia", "Gaspara", "Gelsumina", "Genoveva", "Getrudis", "Gertrudis", "Gervasia", "Gliceria", "Gracia", "Graciana", "Gregoria", "Guillerma", "Gumersinda", "Felicia", "Fidela", "Froilana", "Hermelinda", "Herminia", "Hilaria", "Humildad", "Indalecia", "Ilora", "Isidora", "Isidra", "Jacoba", "Jerónima", "Jesusa", "Jorja", "Juliana", "Laureana", "Leocadia", "Leoncia", "Liberata", "Librada", "Lopa", "Lorenza", "Luciana", "Lucrecia", "Mamesa", "Marciala", "Marciana", "Matea", "Matiasa", "Máxima", "Melchora", "Melitona", "Micaela", "Miguela", "Montserrate", "Nazaria", "Nemesia", "Nestora", "Nicanora", "Nicasia", "Jacinta", "Jesusa", "Olalla", "Olaya", "Orosia", "Parda", "Paspasia", "Patrocinia", "Peregrina", "Perpétua", "Petra", "Petrola", "Petrona", "Petronila", "Pia", "Polonia", "Pomposa", "Potencia", "Práxedes", "Preciosa", "Prisca", "Priscila", "Quintina", "Quiteria", "Ramira", "Reparada", "Ricarda", "Romualda", "Rudesinda", "Rufa", "Rufina", "Salvadora", "Sancia", "Sandalia", "Santas", "Santiaga", "Saturia", "Saturnina", "Sebastiana", "Segunda", "Semproniana", "Serapia", "Sergia", "Silvestra", "Simeona", "Simona", "Socorro", "Sotera", "Teodomira", "Teodora", "Teodosia", "Tiburcia", "Tomasa", "Toribia", "Úrsula", "Abundio", "Acacio", "Agapito", "Amalio", "Ambrosio", "Aniceto", "Anselmo", "Apolonio", "Aquilino", "Argimiro", "Arquimimo", "Arsenio", "Ascensio", "Asterio", "Atanasio", "Atilano", "Áureo", "Avelino", "Bartolo", "Basilio", "Baudilio", "Belarmino", "Benigno", "Bonifacio", "Buenaventura", "Calisto", "Calixto", "Casiano", "Casildo", "Castiano", "Casimiro", "Cecilio", "Celdonio", "Celedonio", "Cesáreo", "Cipriaco", "Cipriano", "Cipriniano", "Ciriaco", "Cirilo", "Clemente", "Cleto", "Columbano", "Conrado", "Crescencio", "Crisóstomo", "Crispín", "Críspulo", "Cruz", "Deogracias", "Dionisio", "Domiciano", "Doroteo", "Eleuterio", "Eliodoro", "Eliseo", "Emerico", "Emeterio", "Emmanuel", "Epafrodito", "Epifanio", "Escolástico", "Estanislao", "Eufrasio", "Eulogio", "Evelio", "Fabriciano", "Faustina", "Feliciano", "Florencio", "Floro", "Froilán", "Fructuoso", "Frutos", "Fulgencio", "Gregorio", "Guadalupe", "Gumersindo", "Helimenas", "Hermenegildo", "Herminio", "Hermógenes", "Higinio", "Hilario", "Hilarión", "Hipólito", "Indalecio", "Inocente", "Isabelo", "Isidoro", "Juvernón", "Laureano", "Leandro", "Leocadio", "León", "Leovigildo", "Lesmes", "Lisardo", "Lope", "Lupicinio", "Macabeo", "Macario", "Macedonio", "Margarito", "Magin", "Mauro", "Maximino", "Medardo", "Melitón", "Minervino", "Minervo", "Natalio", "Nemesio", "Nicanor", "Niceto", "Nicomedes", "Norberto", "Odón", "Orencio", "Pantaleón", "Paulilo", "Paulino", "Patricio", "Perfecto", "Petrolino", "Petronilo", "Pío", "Policarpo", "Polonio", "Pomposo", "Ponciano", "Primitivo", "Protasio", "Prudencio", "Regino", "Remigio", "Restituto", "Rinaldo", "Robustiano", "Romualdo", "Rómulo", "Rosalino", "Ruperto", "Rufino", "Rufo", "Sabas", "Sabiniano", "Salvio", "Sandalio", "Saturio", "Saturnino", "Serapio", "Servando", "Serbando", "Severo", "Silverio", "Silvestre", "Silvio", "Simeón", "Sinforosio", "Sinforoso", "Sofío", "Sofronio", "Sotero", "Teódulo", "Telesforo", "Teopisto", "Tereso", "Tiburcio", "Timoteo", "Toribio", "Trifón", "Trinitario", "Ulpiano", "Valeriano", "Venancio", "Victoriano", "Zoilo"]

                        new_egg = {
                            "id": egg_uid,
                            "type": dragon_id,
                            "name": random.choice(nombres_dragon),
                            "xp": 0,
                            "hatched": False,
                            "ts": int(time.time())
                        }
                        
                        player_data['map']['eggs'].append(new_egg)
                        
                        print(f"   [PLACE_STORE_EGG OK] Huevo de {item_cfg.get('name')} colocado (UID: {egg_uid}).")
                    else:
                        print(f"   [!] Error: El dragón con ID {dragon_id} no existe en el almacen")
                        
                elif cmd == 'hatch_egg':
                    egg_uid = args[0]
                    habitat_uid = args[2]
                    dragon_name = args[3]
                    habitat_id = str(args[2])

                    current_ts = player_data.get('timestamp', int(time.time()))

                    if habitat_id in player_data['map']['items']:
                        item_data = player_data['map']['items'][habitat_id]
                        if len(item_data) > 6 and isinstance(item_data[6], dict):
                            if 'ar' in item_data[6]:
                                item_data[6]['lat'] = current_ts
                                del item_data[6]['ar']
                                print(f"   [FINISH] Propiedad 'ar' eliminada del iso_id {habitat_uid}")
                                print(f"   [FINISH] Propiedad 'lat' actualizada a la hora {current_ts}")

                    egg_data = None
                    if 'eggs' in player_data['map']:
                        for i, egg in enumerate(player_data['map']['eggs']):
                            if str(egg.get('id')) == str(egg_uid):
                                egg_data = player_data['map']['eggs'].pop(i)
                                break
                    
                    if egg_data:
                        dragon_type_id = egg_data.get('type')

                        item_cfg = get_item_config(game_config, dragon_type_id)
                        
                        if item_cfg:
                            hatch_xp = item_cfg.get('xp', 0)
                            attacks = item_cfg.get('attacks', 0)
                            player_data['playerInfo']['xp'] += hatch_xp

                            if 'dragons' not in player_data['map']:
                                player_data['map']['dragons'] = []

                            new_dragon = {
                                "id": egg_uid,
                                "type": dragon_type_id,
                                "xp": 0,
                                "habitatId": habitat_uid,
                                "name": dragon_name,
                                "ts": int(time.time()),
                                "work_id": [],
                                "nbKill": 0,
                                "attack": attacks
                            }
                            
                            player_data['map']['dragons'].append(new_dragon)

                            if 'ownedDragons' not in player_data['map']:
                                player_data['map']['ownedDragons'] = {}

                            id_str = str(dragon_type_id)

                            if id_str not in player_data['map']['ownedDragons']:
                                player_data['map']['ownedDragons'][id_str] = [1, 0, 0]
                            
                            print(f"   [HATCH_EGG OK] Dragón {dragon_name} (Tipo: {dragon_type_id}) eclosionado en el hábitat {habitat_uid}.")
                            print(f"   [-] XP ganado: {hatch_xp} | XP total: {player_data['playerInfo']['xp']}")
                            print(f"   [-] Dragón {dragon_name} (Tipo: {dragon_type_id}) añadido al Libro de Dragones")
                        else:
                            print(f"   [!] Error: Configuración para el dragón {dragon_type_id} no encontrada en game_config.")
                    else:
                        print(f"   [!] Error: No se encontró un huevo con UID {egg_uid} en la incubadora.")

                elif cmd == 'feed_dragon':
                    FOOD_COSTS = [
                        0,
                        5,
                        10,
                        20,
                        40,
                        80,
                        160,
                        320,
                        640,
                        1280,
                        1664,
                        2163,
                        2812,
                        3656,
                        4753,
                        6178,
                        8032,
                        10441,
                        13574,
                        17646,
                        22940,
                        29822,
                        38768,
                        50398,
                        65518,
                        88173,
                        110725,
                        143943,
                        187126,
                        243264,
                        316243,
                        411115,
                        534450,
                        694785,
                        903220,
                        1174187,
                        1526443,
                        1984375,
                        2579688,
                        3353594,
                        4359673
                    ]
                    
                    dragon_uid = args[0]
                    
                    dragon_found = False
                    if 'dragons' in player_data['map']:
                        for dragon in player_data['map']['dragons']:
                            if str(dragon.get('id')) == str(dragon_uid):
                                dragon_found = True
                                current_xp = dragon.get('xp', 0)
                                current_level = (current_xp // 4) + 1

                                if current_level >= len(FOOD_COSTS):
                                    print(f"   [!] Aviso: El dragón {dragon_uid} ya alcanzó el nivel máximo registrado.")
                                    break
                                
                                food_cost = FOOD_COSTS[current_level]
                                
                                if player_data['playerInfo']['food'] >= food_cost:
                                    player_data['playerInfo']['food'] -= food_cost

                                    dragon['xp'] = current_xp + 1
                                    new_level = (dragon['xp'] // 4) + 1

                                    dragon_type_str = str(dragon.get('type'))

                                    if 'ownedDragons' not in player_data['map']:
                                        player_data['map']['ownedDragons'] = {}

                                    if dragon_type_str not in player_data['map']['ownedDragons']:
                                        player_data['map']['ownedDragons'][dragon_type_str] = [1, 0, 0]

                                    if new_level >= 4:
                                        player_data['map']['ownedDragons'][dragon_type_str][1] = 2
                                    if new_level >= 7:
                                        player_data['map']['ownedDragons'][dragon_type_str][2] = 3
                                    
                                    print(f"   [FEED_DRAGON OK] Dragón '{dragon.get('name', 'Desconocido')}' (UID: {dragon_uid}) alimentado.")
                                    print(f"   [-] XP Dragón subió a: {dragon['xp']} | Costo: {food_cost} | Comida restante: {player_data['playerInfo']['food']}")
                                else:
                                    print(f"   [!] Error: No hay suficiente comida ({food_cost} requerida) para alimentar al dragón {dragon_uid}.")
                                
                                break
                                
                    if not dragon_found:
                        print(f"   [!] Error: Dragón con UID {dragon_uid} no encontrado en el mapa.")

                elif cmd == 'set_goals':
                    goal_id = int(args[0])
                    goal_state = json.loads(args[1])

                    if 'goals' not in player_data['privateState']:
                        player_data['privateState']['goals'] = [None] * 200

                    while len(player_data['privateState']['goals']) <= goal_id:
                        player_data['privateState']['goals'].append(None)
                        
                    player_data['privateState']['goals'][goal_id] = goal_state
                    
                    print(f"   [SET_GOALS OK] Goal ID {goal_id} establecido a estado {goal_state}")
                
                elif cmd == 'complete_goal':
                    goal_id = int(args[0])
                    goal_config = game_config.get('goals', {}).get(str(goal_id))
                    
                    if goal_config:
                        reward = goal_config.get('reward', {})

                        gold_reward = reward.get('g', 0)
                        food_reward = reward.get('f', 0)
                        cash_reward = reward.get('c', 0)
                        xp_reward = reward.get('x', 0)

                        if gold_reward > 0:
                            player_data['playerInfo']['gold'] += gold_reward
                        if food_reward > 0:
                            player_data['playerInfo']['food'] += food_reward
                        if cash_reward > 0:
                            player_data['playerInfo']['cash'] += cash_reward
                        if xp_reward > 0:
                            player_data['playerInfo']['xp'] += xp_reward
                                                
                        print(f"   [COMPLETE_GOAL OK] Goal ID {goal_id} completado!")
                        print(f"   [+] Recompensas: Gold +{gold_reward} | Food +{food_reward} | XP +{xp_reward}")
                        print(f"   [-] Totales: Oro: {player_data['playerInfo']['gold']} | Comida: {player_data['playerInfo']['food']} | XP: {player_data['playerInfo']['xp']}")
                    else:
                        print(f"   [!] Error: El goal con ID {goal_id} no existe en get_game_config.json")
                        
                elif cmd == 'breed_dragon':
                    iso_id = str(args[0])
                    parent1_id = int(args[1])
                    parent2_id = int(args[2])
                    use_gems = int(args[3])

                    current_ts = player_data.get('timestamp', int(time.time()))

                    boosted = False
                    if use_gems == 1:
                        boost_cost = game_config.get('globals', {}).get('RARITY_BOOST_COST', {}).get('value', 5)
                        if player_data['playerInfo']['cash'] >= int(boost_cost):
                            player_data['playerInfo']['cash'] -= int(boost_cost)
                            boosted = True
                        else:
                            print("[!] Gemas insuficientes para Boost. Cruce normal.")

                    dragon1_type = None
                    dragon2_type = None
                    dragon1_level = 1
                    dragon2_level = 1
                    
                    for d in player_data.get('map', {}).get('dragons', []):
                        if d.get('id') == parent1_id:
                            dragon1_type = d.get('type')
                            xp1 = d.get('xp', 0)
                            dragon1_level = (xp1 // 4) + 1
                        elif d.get('id') == parent2_id:
                            dragon2_type = d.get('type')
                            xp2 = d.get('xp', 0)
                            dragon2_level = (xp2 // 4) + 1

                    dragon_db = build_dragon_db(game_config)

                    if dragon1_type and dragon2_type:
                        outcome_id = get_breed_result(dragon1_type, dragon2_type, dragon1_level, dragon2_level, dragon_db, boosted)
                    else:
                        print(f"[!] Padres {parent1_id} o {parent2_id} no encontrados en el mapa. Fallback a Terra.")
                        outcome_id = 1011

                    duration = 3600
                    if outcome_id in dragon_db:
                        duration = dragon_db[outcome_id]['breeding_time']

                    if 'work' not in player_data['map']:
                        player_data['map']['work'] = {}
                        
                    player_data['map']['work'][iso_id] = [
                        parent1_id,
                        parent2_id,
                        current_ts,
                        duration,
                        outcome_id
                    ]

                    if iso_id in player_data['map'].get('items', {}):
                        player_data['map']['items'][iso_id][3] = current_ts

                    print(f"   [BREED_DRAGON OK] Breed: cueva={iso_id} | padres tipos=({dragon1_type},{dragon2_type}) "
                          f"| resultado={outcome_id} ({dragon_db.get(outcome_id,{}).get('name','?')}) "
                          f"| boost={boosted}")

                    cmd_result = outcome_id
                    
                elif cmd == 'move':
                    iso_id = str(args[0])
                    tx = args[1]
                    ty = args[2]
                    frame = args[3]

                    if iso_id in player_data['map']['items']:
                        player_data['map']['items'][iso_id][1] = tx
                        player_data['map']['items'][iso_id][2] = ty
                        player_data['map']['items'][iso_id][4] = frame
                        
                        print(f"   [MOVE OK] Objeto {iso_id} movido a ({tx}, {ty}) con rotación {frame}.")
                    else:
                        print(f"   [!] Error: El objeto con iso_id {iso_id} no se encontró en el mapa.")

                elif cmd == 'sell':
                    iso_id = str(args[0])
                    reason = args[1] if len(args) > 1 else "UNKNOWN"
                    
                    if iso_id in player_data['map']['items']:
                        item_data = player_data['map']['items'][iso_id]
                        item_type_id = str(item_data[0])
                        
                        item_cfg = get_item_config(game_config, item_type_id)
                        if item_cfg:
                            sell_price = item_cfg.get('sell_price', {}).get('g', 0)
                            player_data['playerInfo']['gold'] += sell_price
                            print(f"   [SELL OK] {item_cfg.get('name')} vendido por {sell_price} oro. (Razón: {reason})")
                        else:
                            print(f"   [!] Error: El objeto con ID {item_type_id} no existe en config.")

                        del player_data['map']['items'][iso_id]

                        
                elif cmd == 'sell_egg':
                    egg_uid = args[0]
                    egg_index = next((i for i, e in enumerate(player_data['map']['eggs']) if e.get('id') == egg_uid), None)
                    
                    if egg_index is not None:
                        egg_data = player_data['map']['eggs'][egg_index]
                        dragon_type = str(egg_data.get('type'))
                        
                        item_cfg = get_item_config(game_config, dragon_type)
                        if item_cfg:
                            sell_price = item_cfg.get('sell_price', {}).get('g', 0)
                            player_data['playerInfo']['gold'] += sell_price
                            print(f"   [SELL_EGG OK] Huevo de {item_cfg.get('name')} vendido por {sell_price} oro.")
                        
                        player_data['map']['eggs'].pop(egg_index)
                    else:
                        print(f"   [!] Error: Huevo con UID {egg_uid} no encontrado.")

                elif cmd == 'sell_dragon':
                    dragon_uid = args[0]
                    dragon_index = next((i for i, d in enumerate(player_data['map']['dragons']) if d.get('id') == dragon_uid), None)
                    
                    if dragon_index is not None:
                        dragon_data = player_data['map']['dragons'][dragon_index]
                        dragon_type = str(dragon_data.get('type'))
                        
                        item_cfg = get_item_config(game_config, dragon_type)
                        if item_cfg:
                            sell_price = item_cfg.get('sell_price', {}).get('g', 0)
                            player_data['playerInfo']['gold'] += sell_price
                            print(f"   [SELL_DRAGON OK] Dragón {item_cfg.get('name')} vendido por {sell_price} oro.")
                        
                        player_data['map']['dragons'].pop(dragon_index)
                    else:
                        print(f"   [!] Error: Dragón con UID {dragon_uid} no encontrado.")

                elif cmd == 'store_item':
                    iso_id = str(args[0])
                    
                    if iso_id in player_data['map']['items']:
                        item_id = str(player_data['map']['items'][iso_id][0])

                        del player_data['map']['items'][iso_id]

                        if 'store' not in player_data['map']:
                            player_data['map']['store'] = {}
                        if 'items' not in player_data['map']['store']:
                            player_data['map']['store']['items'] = {}

                        if item_id in player_data['map']['store']['items']:
                            player_data['map']['store']['items'][item_id] += 1
                        else:
                            player_data['map']['store']['items'][item_id] = 1
                            
                        print(f"   [STORE_ITEM OK] Objeto {item_id} (ISO: {iso_id}) guardado en el almacén.")
                    else:
                        print(f"   [!] Error: El objeto con ISO ID {iso_id} no existe en el mapa.")

                elif cmd == 'orient':
                    iso_id = str(args[0])
                    frame = args[1]

                    if iso_id in player_data['map']['items']:
                        player_data['map']['items'][iso_id][4] = frame
                        
                        print(f"   [ORIENT OK] Objeto {iso_id} rotado a la posición {frame}.")
                    else:
                        print(f"   [!] Error: El objeto con iso_id {iso_id} no se encontró en el mapa.")

                elif cmd == 'level_up':
                    new_level = int(args[0])

                    player_data['playerInfo']['level'] = new_level

                    levels_config = game_config.get('levels', [])

                    if 0 <= new_level - 1 < len(levels_config):
                        level_info = levels_config[new_level - 1]
                        reward = level_info.get('reward', {})

                        for reward_type, reward_amount in reward.items():
                            if reward_type == 'c':
                                player_data['playerInfo']['cash'] += reward_amount
                            elif reward_type == 'g':
                                player_data['playerInfo']['gold'] += reward_amount
                            elif reward_type == 'f':
                                player_data['playerInfo']['food'] += reward_amount
                            elif reward_type == 'x':
                                player_data['playerInfo']['xp'] += reward_amount
                                
                    print(f"   [LEVEL UP OK] Jugador alcanzó el nivel {new_level}.")
                    print(f"   [-] Recompensa aplicada: {reward}")

                elif cmd == 'complete_tutorial':
                    tutorial_value = args[0]

                    player_data['playerInfo']['completed_tutorial'] = str(tutorial_value)
                    
                    print(f"   [COMPLETE_TUTORIAL OK] Tutorial marcado como completado (Valor: {tutorial_value}).")
                    

                elif cmd in ['expand_gold', 'expand_cash']:
                    expansion_id = int(args[0])

                    prices_list = game_config.get('expansion_prices', [])

                    current_idx = len(player_data['map'].get('expansions', []))
                    
                    if current_idx < len(prices_list):
                        price_data = prices_list[current_idx]

                        if cmd == 'expand_gold':
                            costo = int(price_data.get('coins', 0))
                            recurso_key = 'gold'
                        else:
                            costo = int(price_data.get('cash', 0))
                            recurso_key = 'cash'

                        if player_data['playerInfo'][recurso_key] >= costo:
                            player_data['playerInfo'][recurso_key] -= costo
                            
                            if expansion_id not in player_data['map']['expansions']:
                                player_data['map']['expansions'].append(expansion_id)
                                print(f"   [EXPANSION OK] ID {expansion_id} desbloqueada. Indice precio: {current_idx}. Costo: {costo} {recurso_key}.")
                            else:
                                print(f"   [!] La expansión {expansion_id} ya figuraba como comprada.")
                        else:
                            print(f"   [!] Oro/Gemas insuficientes: Necesita {costo}, tiene {player_data['playerInfo'][recurso_key]}")
                    else:
                        print(f"   [!] Error: No hay más precios definidos en expansion_prices para la expansión nro {current_idx + 1}")

                elif cmd == 'collect':
                    iso_id = str(args[0])
                    
                    if iso_id in player_data['map']['items']:
                        item_data = player_data['map']['items'][iso_id]

                        while len(item_data) <= 6:
                            item_data.append({})
                        if not isinstance(item_data[6], dict):
                            item_data[6] = {}
                            
                        attrs = item_data[6]
                        current_ts = int(time.time())

                        if len(args) > 1 and isinstance(args[1], (int, float)):
                            gold_collected = int(args[1])
                            player_data['playerInfo']['gold'] += gold_collected

                            item_data[3] = current_ts
                            attrs['lat'] = current_ts
                            
                            print(f"   [COLLECT_HÁBITAT OK] Oro recolectado: {gold_collected}")

                        elif len(args) > 1 and args[1] == "fc":
                            if 'cp' in attrs:
                                cp_value = int(attrs['cp'])
                                cp_index = cp_value - 1 

                                collect_values = game_config.get('globals', {}).get('COLLECT_VALUES', {}).get('value', [])
                                collect_xp = game_config.get('globals', {}).get('COLLECT_XP', {}).get('value', [])

                                if 0 <= cp_index < len(collect_values):
                                    food_collected = int(collect_values[cp_index])
                                    xp_collected = int(collect_xp[cp_index])

                                    player_data['playerInfo']['food'] += food_collected
                                    player_data['playerInfo']['xp'] += xp_collected

                                    print(f"   [COLLECT_GRANJA OK] Comida: {food_collected} | XP: {xp_collected}")

                                del attrs['cp']

                            item_data[3] = 0

                        else:
                            item_data[3] = 0 
                            if 'lat' in attrs:
                                attrs['lat'] = current_ts
                            print(f"   [COLLECT OK] Recolección en el ID: {iso_id}")

                        print(f"   [-] Estado actual -> Oro: {player_data['playerInfo']['gold']} | Comida: {player_data['playerInfo']['food']} | XP: {player_data['playerInfo']['xp']}")
                    
                    else:
                        print(f"   [!] Error: No se puede recolectar. El item {iso_id} no existe en el mapa.")

                elif cmd == 'activate':
                    iso_id = str(args[0])
                    cp_val = args[1]

                    if iso_id in player_data['map']['items']:
                        item_data = player_data['map']['items'][iso_id]
                        item_id = item_data[0]

                        while len(item_data) < 7:
                            item_data.append({})
                        
                        attrs = item_data[6]

                        item_cfg = None
                        for item in game_config.get('items', []):
                            if str(item.get('id')) == str(item_id):
                                item_cfg = item
                                break
                                
                        if item_cfg:
                            group_type = item_cfg.get('group_type', '')
                            properties = item_cfg.get('properties', {})

                            if group_type == 'FARM' or 'multiCollectable' in properties:
                                if isinstance(cp_val, int) and cp_val > 0:
                                    collect_prices = game_config.get('globals', {}).get('COLLECT_PRICE', {}).get('value', [])

                                    if (cp_val - 1) < len(collect_prices):
                                        cost = collect_prices[cp_val - 1]
                                        if 'g' in cost:
                                            player_data['playerInfo']['gold'] = max(0, player_data['playerInfo']['gold'] - cost['g'])
                                        if 'c' in cost:
                                            player_data['playerInfo']['cash'] = max(0, player_data['playerInfo']['cash'] - cost['c'])

                                    attrs['cp'] = cp_val
                                    item_data[3] = int(time.time())
                                    
                                elif cp_val == 0:
                                    attrs['cp'] = 0
                                    item_data[3] = 0

                            elif group_type == 'OBSTACLE':
                                costs = item_cfg.get('costs', {})
                                if 'g' in costs:
                                    player_data['playerInfo']['gold'] = max(0, player_data['playerInfo']['gold'] - costs['g'])
                                if 'c' in costs:
                                    player_data['playerInfo']['cash'] = max(0, player_data['playerInfo']['cash'] - costs['c'])

                                item_data[3] = int(time.time())
                        
                        print(f"   [ACTIVATE OK] Objeto {iso_id} activado con Timestamp de inicio {item_data[3]}")

                elif cmd == 'finish_building':
                    iso_id = str(args[0])
                    is_speed_up = args[1]

                    if iso_id in player_data['map']['items']:
                        item_data = player_data['map']['items'][iso_id]
                        item_type_id = item_data[0]

                        xp_to_add = 0
                        item_cfg = get_item_config(game_config, item_type_id)
                        if item_cfg:
                            xp_to_add = item_cfg.get('xp', 0)

                        player_data['playerInfo']['xp'] += xp_to_add

                        item_data[3] = 0

                        if len(item_data) > 6 and isinstance(item_data[6], dict):
                            if 'tb' in item_data[6]:
                                del item_data[6]['tb']
                                print(f"   [FINISH] Propiedad 'tb' eliminada del iso_id {iso_id}")

                        print(f"   [FINISH_BUILDING OK] Objeto {iso_id} terminado. XP Ganada: {xp_to_add}")
                    else:
                        print(f"   [!] Error: El iso_id {iso_id} no existe en el mapa.")

                elif cmd == 'upgrade':
                    unique_id = str(args[0])
                    
                    if unique_id in player_data['map']['items']:
                        item_data = player_data['map']['items'][unique_id]
                        current_type_id = str(item_data[0])

                        all_items = game_config.get('items', {})
                        
                        current_item_conf = None
                        if isinstance(all_items, dict):
                            current_item_conf = all_items.get(current_type_id)
                        else:
                            current_item_conf = next((i for i in all_items if str(i.get('id')) == current_type_id), None)

                        if current_item_conf and 'upgrades_to' in current_item_conf:
                            new_type_id = str(current_item_conf['upgrades_to'])

                            new_item_conf = None
                            if isinstance(all_items, dict):
                                new_item_conf = all_items.get(new_type_id)
                            else:
                                new_item_conf = next((i for i in all_items if str(i.get('id')) == new_type_id), None)

                            if new_item_conf:
                                item_data[0] = int(new_type_id)
                                build_time = new_item_conf.get('build_time', 0)
                                current_ts = int(time.time())
                                
                                while len(item_data) < 7:
                                    item_data.append(0)

                                if not isinstance(item_data[6], dict):
                                    item_data[6] = {}

                                if build_time > 0:
                                    item_data[6]['tb'] = current_ts + build_time
                                    
                                else:
                                    item_data[6].pop('tb', None)
                                    item_data[3] = 0 

                                print(f"   [UPGRADE OK] Item {unique_id} mejorado a tipo {new_type_id}. TB: {item_data[6].get('tb')}")

                elif cmd == 'rename_dragon':
                    dragon_id = args[0]
                    nuevo_nombre = str(args[1])

                    dragon_encontrado = False
                    if 'dragons' in player_data.get('map', {}):
                        for dragon in player_data['map']['dragons']:
                            if dragon.get('id') == dragon_id:
                                dragon['name'] = nuevo_nombre
                                dragon_encontrado = True
                                print(f"   [RENAME_DRAGON OK]Dragón {dragon_id} renombrado exitosamente a: {nuevo_nombre}")
                                break
                    
                    if not dragon_encontrado:
                        print(f"[!] Advertencia: No se encontró el dragón con ID {dragon_id} en el archivo del jugador.")

                elif cmd == 'speed_collect':
                    unique_id = str(args[0])
                    type_speed = args[1]
                    
                    if unique_id in player_data['map']['items']:
                        item_data = player_data['map']['items'][unique_id]

                        props = item_data[6] if len(item_data) > 6 and isinstance(item_data[6], dict) else {}
                        
                        if 'cp' in props:
                            crop_id = int(props['cp'])
                            
                            globals_conf = game_config.get('globals', {})
                            collect_minutes = globals_conf.get('COLLECT_MINUTES', {}).get('value', [0.5, 5, 30, 120, 360, 720, 1440, 2160, 2880])
                            
                            if 1 <= crop_id <= len(collect_minutes):
                                duration_seconds = int(collect_minutes[crop_id - 1] * 60)
                                
                                start_time = int(item_data[3])
                                current_ts = int(time.time())
                                
                                elapsed_time = current_ts - start_time
                                time_remaining = max(0, duration_seconds - elapsed_time)

                                gems_cost = max(1, (time_remaining + 3599) // 3600)
                                
                                if player_data['playerInfo']['cash'] >= gems_cost:
                                    player_data['playerInfo']['cash'] -= gems_cost

                                    item_data[3] = current_ts - duration_seconds
                                    
                                    print(f"   [SPEED_COLLECT OK] En {unique_id}. Costo: {gems_cost} gemas. Adelantados {time_remaining}s.")
                                    print(f"    Gemas restantes: {player_data['playerInfo']['cash']}")
                                else:
                                    print(f"[!] Sin gemas suficientes para speed_collect en granja {unique_id}")
                        else:
                            print(f"[!] El objeto {unique_id} no tiene un cultivo activo ('cp')")

                elif cmd == 'speed_hatch':
                    egg_id = args[0]
                    
                    if 'eggs' in player_data.get('map', {}):
                        egg_data = next((egg for egg in player_data['map']['eggs'] if egg.get('id') == egg_id), None)
                        
                        if egg_data:
                            dragon_type = str(egg_data.get('type'))

                            all_items = game_config.get('items', [])
                            dragon_conf = None
                            if isinstance(all_items, dict):
                                dragon_conf = all_items.get(dragon_type)
                            else:
                                dragon_conf = next((i for i in all_items if str(i.get('id')) == dragon_type), None)
                                
                            if dragon_conf:
                                hatching_time = dragon_conf.get('hatching_time', 0)
                                start_time = int(egg_data.get('ts', 0))
                                current_ts = int(time.time())
                                
                                elapsed_time = current_ts - start_time
                                time_remaining = max(0, hatching_time - elapsed_time)

                                gems_cost = max(1, (time_remaining + 3599) // 3600)
                                
                                if player_data['playerInfo']['cash'] >= gems_cost:
                                    player_data['playerInfo']['cash'] -= gems_cost
                                    egg_data['ts'] = current_ts - hatching_time
                                    
                                    print(f"   [SPEED_HATCH OK] En huevo {egg_id} (Tipo {dragon_type}). Costo: {gems_cost} gemas.")
                                    print(f"    Gemas restantes: {player_data['playerInfo']['cash']}")
                                else:
                                    print(f"[!] Sin gemas suficientes para speed_hatch en huevo {egg_id}")
                            else:
                                print(f"[!] No se encontró la configuración para el dragón tipo {dragon_type}")
                        else:
                            print(f"[!] Huevo con ID {egg_id} no encontrado en el mapa.")

                elif cmd == 'sync':
                    random_ping = args[0] if len(args) > 0 else "Desconocido"
                    
                    print(f"   [SYNC] Ping de sincronización recibido (Hash: {random_ping}).")
                    print(f"   [-] Todo en orden. Devolviendo estado actual al cliente.")

                elif cmd == 'ping':
                    print(f"   [PING OK] Señal de actividad (keep-alive) recibida del cliente.")

                elif cmd == 'finish_breeding2':
                    breeding_iso_id = str(args[0])
                    new_egg_uid = args[1]
                    hatchery_iso_id = str(args[2])
                    
                    work_data = player_data.get('map', {}).get('work', {}).get(breeding_iso_id)
                    
                    if work_data:
                        dragon_id = work_data[4]
                        
                        if 'eggs' not in player_data['map']:
                            player_data['map']['eggs'] = []
                        
                        nombres_dragon = ["Roxy", "Horacio", "Sergi", "Kasia", "Xavi", "Draco", "Ignis", "Gabriel"]
                        
                        new_egg = {
                            "id": new_egg_uid,
                            "type": dragon_id,
                            "name": random.choice(nombres_dragon),
                            "xp": 0,
                            "ts": int(time.time())
                        }
                        
                        player_data['map']['eggs'].append(new_egg)
                        
                        del player_data['map']['work'][breeding_iso_id]

                        if breeding_iso_id in player_data['map'].get('items', {}):
                            player_data['map']['items'][breeding_iso_id][3] = 0

                        print(f"   [FINISH_BREEDING2 OK] En {breeding_iso_id}")
                        print(f"    -> Huevo creado: {dragon_id} (UID: {new_egg_uid}) movido a Hatchery {hatchery_iso_id}")
                    else:
                        print(f"[!] Error: No se encontró información de cría para el edificio {breeding_iso_id}")

                    cmd_result = dragon_id

                elif cmd == 'expand_island':
                    expansion_id = int(args[0])
                    cost_index = int(args[1])
                    
                    if 'expansions' not in player_data['map']:
                        player_data['map']['expansions'] = []
                        
                    if expansion_id not in player_data['map']['expansions']:
                        player_data['map']['expansions'].append(expansion_id)
                        
                    try:
                        globals_data = game_config.get('globals', {})
                        islands_costs = globals_data.get('ISLANDS_COSTS', {}).get('value', [])
                        
                        if cost_index < len(islands_costs):
                            cost_item = islands_costs[cost_index]

                            cost_obj = cost_item.get('value', cost_item) if isinstance(cost_item, dict) else {}
                            
                            for res_type, amount in cost_obj.items():
                                amt = int(amount)
                                if res_type == 'g':
                                    player_data['playerInfo']['gold'] = max(0, player_data['playerInfo']['gold'] - amt)
                                elif res_type == 'c':
                                    player_data['playerInfo']['cash'] = max(0, player_data['playerInfo']['cash'] - amt)
                                
                            print(f"   [EXPAND_ISLAND OK] Isla expandida hacia parcela {expansion_id}.")
                            print(f"    -> Costo cobrado (Índice {cost_index}): {cost_obj}")
                        else:
                            print(f"[!] Aviso: El índice de costo {cost_index} supera el límite de ISLANDS_COSTS.")
                            
                    except Exception as e:
                        print(f"[!] Error procesando el cobro de expand_island: {e}")

                elif cmd == 'move_dragon':
                    dragon_uid = int(args[0])
                    new_habitat_id = int(args[1])
                    
                    dragon_found = False
                    
                    if 'dragons' in player_data['map']:
                        for dragon in player_data['map']['dragons']:
                            if int(dragon.get('id', 0)) == dragon_uid:
                                old_habitat = dragon.get('habitatId')
                                dragon['habitatId'] = new_habitat_id
                                dragon_found = True
                                
                                nombre_dragon = dragon.get('name', 'Unknown')
                                print(f"   [MOVE_DRAGON OK] Dragón {dragon_uid} ('{nombre_dragon}')")
                                print(f"    -> Movido del habitat {old_habitat} al habitat {new_habitat_id}")
                                break
                                
                    if not dragon_found:
                        print(f"[!] Error: No se encontró el dragón con ID {dragon_uid} para mover.")

                elif cmd == 'buy_treasure_new':
                    treasure_id = str(args[0])
                    
                    if 'treasure_items' in game_config and treasure_id in game_config['treasure_items']:
                        treasure_data = game_config['treasure_items'][treasure_id]

                        price = int(treasure_data.get('price', 0))
                        amount = int(treasure_data.get('amount', 0))
                        res_type = treasure_data.get('type', '') 

                        if res_type == 'g':
                            res_type = 'gold'
                        elif res_type == 'f':
                            res_type = 'food'

                        current_cash = int(player_data.get('playerInfo', {}).get('cash', 0))
                        
                        if current_cash >= price:
                            player_data['playerInfo']['cash'] -= price
                            
                            if res_type in player_data['playerInfo']:
                                player_data['playerInfo'][res_type] += amount
                            else:
                                player_data['playerInfo'][res_type] = amount
                                
                            print(f"   [BUY_TREASURE_NEW OK] Tesoro ID {treasure_id} comprado.")
                            print(f"    -> Costo: {price} gemas | Recompensa: +{amount} {res_type}.")
                            print(f"    -> Gemas restantes: {player_data['playerInfo']['cash']}")
                        else:
                            print(f"[!] Error: Fondos insuficientes. Tienes {current_cash} gemas pero el tesoro {treasure_id} cuesta {price}.")
                    else:
                        print(f"[!] Error: No se encontró el tesoro con ID {treasure_id} en la configuración (treasure_items).")

                elif cmd == 'set_attack_team':
                    team_type = cmd_data.get('args')[0]
                    team_ids_str = cmd_data.get('args')[1]

                    team_ids = json.loads(team_ids_str) 

                    formatted_team = [{"id": int(dragon_id)} for dragon_id in team_ids]

                    if "teams" not in player_data["privateState"]:
                        player_data["privateState"]["teams"] = {}

                    player_data["privateState"]["teams"][team_type] = formatted_team
                    print(f"   [SET_ATTACK_TEAM OK] Dragones elegidos: {formatted_team}")
                    
                elif cmd == 'deus_cards_generate':
                    is_paid = int(args[0]) if len(args) > 0 else 0
                    is_super = int(args[1]) if len(args) > 1 else 0

                    if is_super == 1:
                        cost = game_config.get('globals', {}).get('DRAGON_CARDS_SUPER_TRY', {}).get('value', 10)
                        player_data['playerInfo']['cash'] = max(0, player_data['playerInfo']['cash'] - cost)
                    elif is_paid == 1:
                        cost = game_config.get('globals', {}).get('DRAGON_CARDS_TRY', {}).get('value', 3)
                        player_data['playerInfo']['cash'] = max(0, player_data['playerInfo']['cash'] - cost)

                    prize_id = random.randint(0, 8) 

                    if 'deus_cards' not in player_data['privateState']:
                        player_data['privateState']['deus_cards'] = {}
                    player_data['privateState']['deus_cards']['pending_prize'] = prize_id

                    cmd_result = prize_id
                    print(f"   [DEUS_CARDS_GENERATE OK] Tirada generada. Premio ID: {prize_id}")
                    
                elif cmd == 'deus_cards_claim':
                    current_time = int(time.time())
                    prize_id = player_data['privateState'].get('deus_cards', {}).get('pending_prize', 0)

                    prize_cfg = None
                    for p in game_config.get('dragon_card_prizes', []):
                        if p.get('id') == prize_id:
                            prize_cfg = p
                            break
                            
                    if prize_cfg:
                        reward = prize_cfg.get('reward', {})
                        
                        if isinstance(reward, dict):
                            gold_reward = reward.get('g', 0)
                            food_reward = reward.get('f', 0)
                            cash_reward = reward.get('c', 0)
                            
                            player_data['playerInfo']['gold'] += gold_reward
                            player_data['playerInfo']['food'] += food_reward
                            player_data['playerInfo']['cash'] += cash_reward
                                
                            print(f"   [DEUS_CARDS_CLAIM OK] Premio reclamado: Oro +{gold_reward} | Comida +{food_reward} | Gemas +{cash_reward}")

                        elif isinstance(reward, int):
                            dragon_id = reward
                            print(f"   [DEUS_CARDS_CLAIM OK] Premio reclamado: Dragón ID {dragon_id}")

                        elif reward == "retry":
                            print("   [DEUS_CARDS_CLAIM OK] Premio: Retry (Tirada extra gratis)")
                    
                    if 'deus_cards' in player_data['privateState']:
                        player_data['privateState']['deus_cards']['pending_prize'] = None
                        
                    player_data['privateState']['deusCardsLastTimestamp'] = current_time
                    
                elif cmd == 'begin_tournament':
                    if 'privateState' not in player_data:
                        player_data['privateState'] = {}

                    current_ts = int(time.time())
                    player_data['privateState']['beginTournamentTs'] = current_ts
                    
                    print(f"   [BEGIN_TOURNAMENT OK] Torneo iniciado. Timestamp guardado: {current_ts}")

                elif cmd == 'end_tournament':
                    player_won = str(args[0]) == "1"
                    kills_log = json.loads(args[1]) if len(args) > 1 else {}
                    
                    if 'privateState' not in player_data:
                        player_data['privateState'] = {}

                    current_ts = int(time.time())
                    player_data['privateState']['endTournamentTs'] = current_ts
                    
                    print(f"   [END_TOURNAMENT] Resultado: {'Ganador' if player_won else 'Perdedor'}. Kills: {kills_log}")

                    if kills_log and 'dragons' in player_data.get('map', {}):
                        for dragon in player_data['map']['dragons']:
                            dragon_id_str = str(dragon.get('id'))
                            
                            if dragon_id_str in kills_log:
                                kills_to_add = int(kills_log[dragon_id_str])
     
                                current_kills = dragon.get('nbKill', 0)
                                dragon['nbKill'] = current_kills + kills_to_add
                                
                                print(f"   [+] Dragón {dragon.get('name', 'Unknown')} (ID: {dragon_id_str}) suma {kills_to_add} kills. Total: {dragon['nbKill']}")

                    if player_won:
                        current_tourney = str(player_data['privateState'].get('currentTournament', 1))
                        tournaments_db = game_config.get('tournaments', {})
                        
                        if current_tourney in tournaments_db:
                            tourney_data = tournaments_db[current_tourney]
                            rewards = tourney_data.get('reward', {}).get('resources', {})

                            gold_reward = rewards.get('g', 0)
                            food_reward = rewards.get('f', 0)
                            cash_reward = rewards.get('c', 0)

                            if gold_reward > 0:
                                player_data['playerInfo']['gold'] += gold_reward
                            if food_reward > 0:
                                player_data['playerInfo']['food'] += food_reward
                            if cash_reward > 0:
                                player_data['playerInfo']['cash'] += cash_reward

                            player_data['privateState']['currentTournament'] = int(current_tourney) + 1
                            
                            print(f"   [END_TOURNAMENT OK] ¡Torneo {current_tourney} completado!")
                            print(f"   [-] Recompensas añadidas -> Oro: {gold_reward} | Comida: {food_reward} | Gemas: {cash_reward}")
                            print(f"   [-] Siguiente torneo configurado: {player_data['privateState']['currentTournament']}")
                        else:
                            print(f"   [!] Error: El torneo {current_tourney} no existe en get_game_config.json")

                elif cmd == 'admin_speed_tournament':
                    if 'privateState' not in player_data:
                        player_data['privateState'] = {}

                    globals_db = game_config.get('globals', {})

                    speed_up_price = globals_db.get('TOURNAMENT_SPEED_UP_PRICE', {}).get('value', 2)

                    cooldown_hours = globals_db.get('TOURNAMENT_COOLDOWN', {}).get('value', 12)
                    cooldown_seconds = cooldown_hours * 3600

                    if player_data['playerInfo']['cash'] >= speed_up_price:
                        player_data['playerInfo']['cash'] -= speed_up_price

                        current_end_ts = player_data['privateState'].get('beginTournamentTs', 0)
                        new_ts = max(0, current_end_ts - cooldown_seconds)
                        player_data['privateState']['beginTournamentTs'] = new_ts
                        
                        print(f"   [ADMIN_SPEED_TOURNAMENT OK] Torneo acelerado. Costo: {speed_up_price} gemas.")
                        print(f"   [-] Nuevo endTournamentTs: {new_ts} | Gemas restantes: {player_data['playerInfo']['cash']}")
                    else:
                        print("   [!] Error: No hay suficientes gemas para acelerar el torneo.")
                    
                elif cmd == 'start_training':
                    building_uid = str(args[0])
                    dragon_uid = args[1]
                    attack_id = args[2]
                    attack_pos = args[3]
                    
                    current_ts = int(time.time())

                    if 'work' not in player_data['map']:
                        player_data['map']['work'] = {}

                    player_data['map']['work'][building_uid] = [
                        dragon_uid,
                        attack_id,
                        current_ts,
                        attack_pos
                    ]

                    if 'dragons' in player_data.get('map', {}):
                        for dragon in player_data['map']['dragons']:
                            if str(dragon.get('id')) == str(dragon_uid):
                                dragon['work_id'] = int(building_uid)
                                print(f"   [-] El dragón {dragon.get('name', 'Unknown')} (ID: {dragon_uid}) ha entrado al centro de entrenamiento.")
                                break
                                
                    print(f"   [START_TRAINING OK] Edificio {building_uid} entrenando el ataque {attack_id} en el slot {attack_pos}.")

                elif cmd == 'speed_training':
                    building_uid = str(args[0])
                    
                    if 'work' in player_data.get('map', {}) and building_uid in player_data['map']['work']:
                        work_data = player_data['map']['work'][building_uid]

                        attack_id = str(work_data[1])
                        start_ts = int(work_data[2])
                        current_ts = int(time.time())

                        dragon_uid = str(work_data[0])
                        attack_id = int(work_data[1])
                        attack_pos = int(work_data[3])

                        attacks_db = game_config.get('attacks', {})
                        training_time = 0
                        
                        if attack_id in attacks_db:
                            training_time = attacks_db[attack_id].get('training_time', 0)

                        time_elapsed = current_ts - start_ts
                        time_left = max(0, training_time - time_elapsed)
                        
                        
                        speed_up_cost = max(1, math.ceil(time_left / 3600.0))

                        if player_data['playerInfo']['cash'] >= speed_up_cost:
                            player_data['playerInfo']['cash'] -= speed_up_cost

                            player_data['map']['work'][building_uid][2] = current_ts - training_time - 10
                            
                            print(f"   [SPEED_TRAINING OK] Entrenamiento acelerado. Costo: {speed_up_cost} gemas.")
                            print(f"   [-] Gemas restantes: {player_data['playerInfo']['cash']}")
                        else:
                            print("   [!] Error: No hay suficientes gemas para acelerar el entrenamiento.")

                        dragon_found = False
                        if 'dragons' in player_data.get('map', {}):
                            for dragon in player_data['map']['dragons']:
                                if str(dragon.get('id')) == dragon_uid:
                                    dragon_found = True

                                    if 'attack' not in dragon or not isinstance(dragon['attack'], list):
                                        dragon['attack'] = [-1, -1, -1, -1]

                                    while len(dragon['attack']) <= attack_pos:
                                        dragon['attack'].append(-1)

                                    old_attack = dragon['attack'][attack_pos]
                                    dragon['attack'][attack_pos] = attack_id

                                    dragon['work_id'] = [] 
                                    
                                    print(f"   [+] Dragón {dragon.get('name', 'Unknown')} (ID: {dragon_uid}) aprendió el ataque {attack_id} (reemplazando {old_attack} en slot {attack_pos}).")
                                    break
                        
                        if dragon_found:
                            del player_data['map']['work'][building_uid]
                            print(f"   [FINISH_TRAINING OK] Entrenamiento finalizado y cola de trabajo limpiada en edificio {building_uid}.")
                        else:
                            print(f"   [!] Error: No se encontró al dragón {dragon_uid} en el mapa para enseñarle el ataque.")
                            
                    else:
                        print(f"   [!] Error: El edificio {building_uid} no está en proceso de entrenamiento (no se encontró en 'work').")

                elif cmd == 'finish_training':
                    building_uid = str(args[0])

                    if 'work' in player_data.get('map', {}) and building_uid in player_data['map']['work']:
                        work_data = player_data['map']['work'][building_uid]
                        
                        dragon_uid = str(work_data[0])
                        attack_id = int(work_data[1])
                        attack_pos = int(work_data[3])

                        dragon_found = False
                        if 'dragons' in player_data.get('map', {}):
                            for dragon in player_data['map']['dragons']:
                                if str(dragon.get('id')) == dragon_uid:
                                    dragon_found = True

                                    if 'attack' not in dragon or not isinstance(dragon['attack'], list):
                                        dragon['attack'] = [-1, -1, -1, -1]

                                    while len(dragon['attack']) <= attack_pos:
                                        dragon['attack'].append(-1)

                                    old_attack = dragon['attack'][attack_pos]
                                    dragon['attack'][attack_pos] = attack_id

                                    dragon['work_id'] = [] 
                                    
                                    print(f"   [+] Dragón {dragon.get('name', 'Unknown')} (ID: {dragon_uid}) aprendió el ataque {attack_id} (reemplazando {old_attack} en slot {attack_pos}).")
                                    break
                        
                        if dragon_found:
                            del player_data['map']['work'][building_uid]
                            print(f"   [FINISH_TRAINING OK] Entrenamiento finalizado y cola de trabajo limpiada en edificio {building_uid}.")
                        else:
                            print(f"   [!] Error: No se encontró al dragón {dragon_uid} en el mapa para enseñarle el ataque.")
                            
                    else:
                        print(f"   [!] Error: El edificio {building_uid} no estaba registrado en 'work' (posiblemente ya finalizó o es un error de sincronización).")

                elif cmd == 'weekly_reward':
                    reward_args = json.loads(args[0])
                    reward_index = int(reward_args[0])
                    dragon_index = int(reward_args[1]) if len(reward_args) > 1 else 0

                    globals_db = game_config.get('globals', {})
                    monday_rewards = globals_db.get('MONDAY_BONUS_REWARDS', {}).get('value', [])
                    monday_dragons = globals_db.get('MONDAY_BONUS_REWARDS_DRAGONS', {}).get('value', [])
                    
                    if reward_index < len(monday_rewards):
                        reward = monday_rewards[reward_index]
                        r_type = reward.get('type')
                        r_value = reward.get('value', 0)

                        if r_type == 'g':
                            player_data['playerInfo']['gold'] += r_value
                            print(f"   [WEEKLY_REWARD OK] Recompensa entregada: {r_value} Oro.")
                        elif r_type == 'c':
                            player_data['playerInfo']['cash'] += r_value
                            print(f"   [WEEKLY_REWARD OK] Recompensa entregada: {r_value} Gemas.")
                        elif r_type == 'f':
                            player_data['playerInfo']['food'] += r_value
                            print(f"   [WEEKLY_REWARD OK] Recompensa entregada: {r_value} Comida.")
                        elif r_type == 'u':
                            dragon_id = monday_dragons[dragon_index] if dragon_index < len(monday_dragons) else 1011

                            new_egg_uid = int(time.time()) + random.randint(1000, 9999)
                            new_egg = {
                                "id": new_egg_uid,
                                "type": dragon_id,
                                "name": "Bonus",
                                "xp": 0,
                                "hatched": False,
                                "ts": int(time.time())
                            }
                            if 'eggs' not in player_data['map']:
                                player_data['map']['eggs'] = []
                            player_data['map']['eggs'].append(new_egg)
                            print(f"   [WEEKLY_REWARD OK] Recompensa entregada: Huevo de dragón ID {dragon_id}.")

                        if 'privateState' not in player_data:
                            player_data['privateState'] = {}
                            
                        current_ts = int(time.time())
                        player_data['privateState']['timeStampMondayBonus'] = current_ts
                        
                        print(f"   [WEEKLY_REWARD OK] timeStampMondayBonus actualizado a: {current_ts}.")
                    else:
                        print(f"   [!] Error: El índice de recompensa {reward_index} no existe en la configuración global.")

                elif cmd == 'place_stored_item':
                    iso_id = str(args[0])
                    item_id = str(args[1])
                    tx = args[2]
                    ty = args[3]

                    item_found = False
                    if 'store' in player_data['map'] and 'items' in player_data['map']['store']:
                        if item_id in player_data['map']['store']['items']:
                            item_found = True

                            if player_data['map']['store']['items'][item_id] > 1:
                                player_data['map']['store']['items'][item_id] -= 1
                            else:
                                del player_data['map']['store']['items'][item_id]

                            if not player_data['map']['store']['items']:
                                del player_data['map']['store']['items']
                    
                    if item_found:
                        player_data['map']['items'][iso_id] = [int(item_id), int(tx), int(ty), 0, 0, 1, {}]
                        
                        print(f"   [PLACE_STORED OK] Objeto {item_id} sacado del almacén y colocado en mapa.")
                    else:
                        print(f"   [!] Error: Se intentó colocar el objeto {item_id} pero no existe en el almacén.")

                elif cmd == 'buy_treasure_popup':
                    treasure_id = int(args[0])
                    
                    treasures_db = {
                        1: {"type": "gold", "amount": 75000, "price": 15},
                        2: {"type": "gold", "amount": 200000, "price": 30},
                        3: {"type": "gold", "amount": 500000, "price": 80},
                        5: {"type": "food", "amount": 10000, "price": 15},
                        6: {"type": "food", "amount": 22500, "price": 30},
                        7: {"type": "food", "amount": 70000, "price": 80},
                    }
                    
                    if treasure_id in treasures_db:
                        treasure = treasures_db[treasure_id]
                        res_type = treasure["type"]
                        amount = treasure["amount"]
                        price = treasure["price"]
                        
                        if player_data['playerInfo']['cash'] >= price:
                            player_data['playerInfo']['cash'] -= price

                            if res_type == "food":
                                player_data['playerInfo']['food'] += amount
                            elif res_type == "gold":
                                player_data['playerInfo']['gold'] += amount
                                
                            print(f"   [BUY_TREASURE_POPUP OK] Tesoro {treasure_id} comprado: +{amount} {res_type} por -{price} gemas.")
                        else:
                            print(f"   [!] Error: Cash insuficiente para el tesoro {treasure_id}. Cash actual: {player_data['playerInfo']['cash']}")
                    else:
                        print(f"   [!] Error: El ID de tesoro {treasure_id} no está registrado en el diccionario del servidor.")

                elif cmd == 'complete_collection':
                    collection_id = int(args[0])

                    if 'privateState' not in player_data:
                        player_data['privateState'] = {}
                    if 'completedCollection' not in player_data['privateState']:
                        player_data['privateState']['completedCollection'] = []

                    if collection_id not in player_data['privateState']['completedCollection']:
                        player_data['privateState']['completedCollection'].append(collection_id)

                        collections_list = game_config.get('collections', [])
                        collection_found = None
                        
                        for col in collections_list:
                            if col.get('id') == collection_id:
                                collection_found = col
                                break

                        if collection_found:
                            rewards = collection_found.get('reward', {})
                            col_name = collection_found.get('name', f"Colección {collection_id}")

                            gold_reward = rewards.get("g", 0)
                            food_reward = rewards.get("f", 0)
                            cash_reward = rewards.get("c", 0)
                            xp_reward   = rewards.get("x", 0)

                            player_data['playerInfo']['gold'] += gold_reward
                            player_data['playerInfo']['food'] += food_reward
                            player_data['playerInfo']['cash'] += cash_reward
                            player_data['playerInfo']['xp']   += xp_reward
                            
                            print(f"   [COMPLETE_COLLECTION OK] '{col_name}' (ID: {collection_id}) completada.")
                            print(f"   [+] Recompensas aplicadas -> Oro: +{gold_reward}, Comida: +{food_reward}, Gemas: +{cash_reward}, XP: +{xp_reward}")
                        else:
                            print(f"   [!] Aviso: Colección {collection_id} registrada, pero no existe ese ID en get_game_config.json.")
                    else:
                        print(f"   [!] Aviso: El jugador ya había completado la colección {collection_id}.")

                elif cmd == 'dragonarium_push':
                    dragon_id = int(args[0])

                    if 'dragonariumSlot' not in player_data['privateState'] or len(player_data['privateState'].get('dragonariumSlot', [])) < 5:
                        player_data['privateState']['dragonariumSlot'] = [2, 2, 2, 1, 1]

                    if 'dragonarium' not in player_data['privateState'] or len(player_data['privateState'].get('dragonarium', [])) < 5:
                        player_data['privateState']['dragonarium'] = [[], [], [], [], []]

                    active_dragons = player_data.get('map', {}).get('dragons', [])
                    dragon_to_move = None
                    
                    for d in active_dragons:
                        if d.get('id') == dragon_id:
                            dragon_to_move = d
                            break
                            
                    if dragon_to_move:
                        dragon_type = dragon_to_move.get('type')
                        category_index = 0
                        
                        items_source = game_config.get('items', [])
                        item_data = None
                        
                        for item in items_source:
                            if item.get('id') == dragon_type:
                                item_data = item
                                break

                        if item_data:
                            attributes = item_data.get('attributes', [])

                            if 'pu' in attributes:
                                category_index = 4
                            elif 'l' in attributes:
                                category_index = 3
                            elif 'd' in attributes:
                                category_index = 2
                            elif 'm' in attributes:
                                category_index = 1
                            else:
                                category_index = 0

                        old_habitat = dragon_to_move.get('habitatId')
                        dragon_to_move['habitatId'] = 0

                        player_data['privateState']['dragonarium'][category_index].append(dragon_to_move)
                        player_data['map']['dragons'].remove(dragon_to_move)
                        
                        dragon_name = dragon_to_move.get('name', 'Desconocido')
                        print(f"   [DRAGONARIUM_PUSH OK] Dragón '{dragon_name}' (ID Único: {dragon_id}, Type: {dragon_type}).")
                        print(f"                         Movido del Hábitat {old_habitat} a Pestaña: {category_index}.")
                    else:
                        print(f"   [!] Error: No se encontró el dragón con ID único {dragon_id} en el mapa del jugador.")

                elif cmd == 'dragonarium_pull':
                    category_index = int(args[1])
                    dragon_index = int(args[2])
                    target_habitat_id = int(args[3])

                    dragonarium = player_data.get('privateState', {}).get('dragonarium', [])
                    
                    if 0 <= category_index < len(dragonarium):
                        tab_dragons = dragonarium[category_index]

                        if 0 <= dragon_index < len(tab_dragons):
                            dragon_to_move = tab_dragons.pop(dragon_index)

                            dragon_to_move['habitatId'] = target_habitat_id

                            if 'map' not in player_data:
                                player_data['map'] = {}
                            if 'dragons' not in player_data['map']:
                                player_data['map']['dragons'] = []

                            player_data['map']['dragons'].append(dragon_to_move)
                            
                            dragon_name = dragon_to_move.get('name', 'Desconocido')
                            dragon_uniq_id = dragon_to_move.get('id', 'S/D')
                            
                            print(f"   [DRAGONARIUM_PULL OK] Dragón '{dragon_name}' (ID Único: {dragon_uniq_id}) extraído con éxito.")
                            print(f"                         Origen: Pestaña {category_index}, Posición {dragon_index} -> Destino: Hábitat {target_habitat_id}")
                        else:
                            print(f"   [!] Error: El índice de dragón {dragon_index} está fuera de rango para la pestaña {category_index}.")
                    else:
                        print(f"   [!] Error: El índice de pestaña {category_index} no existe en el Dragonario.")

                elif cmd == 'dragonarium_add':
                    DRAGONARIUM_COSTS = [
                        2,
                        2,
                        3,
                        4,
                        5
                    ]
                    
                    slot_index = int(args[0])
                    
                    nombres_slots = {
                        0: "Elemental",
                        1: "Metal",
                        2: "Dark",
                        3: "Legendary",
                        4: "Pure"
                    }

                    dragonarium_cost = DRAGONARIUM_COSTS[slot_index]

                    player_data['playerInfo']['cash'] -= dragonarium_cost

                    nombre_slot = nombres_slots.get(slot_index, f"Desconocido ({slot_index})")
                    
                    if 'dragonariumSlot' not in player_data['privateState'] or len(player_data['privateState'].get('dragonariumSlot', [])) < 5:
                        player_data['privateState']['dragonariumSlot'] = [2, 2, 2, 1, 1]
                        
                    slots = player_data['privateState']['dragonariumSlot']

                    if 0 <= slot_index < len(slots):
                        slots[slot_index] += 1
                        
                        print(f"   [DRAGONARIUM ADD OK] Pestaña {nombre_slot} se añadió un espacio con éxito.")
                        print(f"                        Estado actual del slot {nombre_slot}: {slots[slot_index]} espacios")
                        print(f"                        Gemas restantes: {player_data['playerInfo']['cash']}")
                    else:
                        print(f"   [!] Error: El índice de slot {slot_index} está fuera de rango para el Dragonario.")
                else:
                    comandos_ignorados.append(cmd)
                    
                response_results.append({
                    "result": cmd_result,
                    "number": cmd_number,
                    "cmd": cmd,
                    "resources": {
                        "pu": {
                            "gold": player_data['playerInfo']['gold'],
                            "cash": player_data['playerInfo']['cash'],
                            "food": player_data['playerInfo']['food'],
                            "xp": player_data['playerInfo']['xp']
                        }
                    },
                    "error": None
                })

            save_player(player_data, user_id)
            current_time = int(time.time())
            player_data['timestamp'] = current_time
            print("")
            if comando_valido_procesado:
                print(f"[+] Juego guardado para usuario {user_id}...")
            else:
                print(f"[~] No se aplicaron cambios porque los comandos recibidos no están añadidos: {comandos_ignorados}")

            if user_id in jugadores_sse:
                jugadores_sse[user_id].put("JUEGO_GUARDADO")
            
        except Exception as e:
            print(f"[!] Error procesando packet.php: {e}")

    response_data = {
        "result": True,
        "response": response_results,
        "ts": int(time.time()),
        "publishActions": 0
    }

    signed_response = sign_packet(response_data)
    return sign_packet(response_data)

print("[+] [MINIJUEGOS] Cargando librería de minijuegos...")
print("    -> Disponible: 'REFLEJO DEL DRAGÓN'")
print("    -> No disponible: 'MEMORIA' (Próximamente)")
print("    -> No disponible: 'TESORO' (Próximamente)")
print("️ "*10 + "\n")
@app.route('/minigames.html')
def serve_minigames():
    return send_from_directory(TEMPLATES_DIR, 'minigames.html')

@app.route('/minigame/reward', methods=['POST'])
def minigame_reward():
    """
    Recibe la recompensa del minijuego Reflejo del Dragón y la suma al
    campo 'cash' del jugador en su archivo JSON.
 
    Body JSON esperado:
        { "user_id": "645751329", "gems": 3 }
 
    Respuesta JSON:
        { "status": "ok", "gems_earned": 3, "new_cash": 58 }
    """
    try:
        data = request.get_json(force=True)
 
        user_id = data.get('user_id')
        gems    = int(data.get('gems', 0))

        if not user_id:
            return jsonify({"status": "error", "msg": "user_id requerido"}), 400
        if gems < 0 or gems > 3:
            return jsonify({"status": "error", "msg": "Cantidad de gemas fuera de rango"}), 400

        if gems == 0:
            return jsonify({"status": "ok", "gems_earned": 0, "new_cash": None})
 
        player_data = load_player(user_id)
        if 'playerInfo' not in player_data:
            return jsonify({"status": "error", "msg": "Jugador no encontrado"}), 404
 
        current_cash = player_data['playerInfo'].get('cash', 0)
        new_cash     = current_cash + gems
        player_data['playerInfo']['cash'] = new_cash
 
        save_player(player_data, user_id)
 
        print(f"\n💎 [MINIJUEGO] Jugador {user_id} ganó {gems} gema(s) | "
              f"{current_cash} → {new_cash}")
 
        return jsonify({
            "status":     "ok",
            "gems_earned": gems,
            "new_cash":   new_cash
        })
 
    except Exception as e:
        print(f"[!] Error en /minigame/reward: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500


if __name__ == '__main__':
    add_hosts()
    print("\n" + "★"*55)
    print("  EL SERVIDOR ESTÁ EN LÍNEA Y LISTO PARA JUGAR  ")
    print("   ¡Tenga un excelente juego, Maestro Dragón! ")
    print("★"*55 + "\n")
    app.run(host='127.0.0.1', port=80, debug=False)
