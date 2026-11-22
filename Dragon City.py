import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
except Exception:
    pass
print("="*55)
print(" INICIANDO SERVIDOR LOCAL: DRAGON CITY v2.0 ")
print("="*55)
print("[+] Inicializando módulos de Flask y dependencias...")
from flask import Flask, request, jsonify, send_from_directory
import json
import os
import time
import hmac
import hashlib
import random
import traceback
import atexit
import ctypes
import math
import re
import queue
import base64
import shutil
import socket
import threading
import copy
from pypresence import Presence
import asyncio
from collections import deque

try:
    from pypresence import Presence
    PYPRESENCE_OK = True
except ImportError:
    PYPRESENCE_OK = False
    
app = Flask(__name__)

jugadores_sse = {}
def notificar_cliente(user_id, mensaje):
    q = jugadores_sse.get(str(user_id))
    if q:
        q.put(mensaje)

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"

HOSTS_ENTRIES = [
    "127.0.0.1 static.socialpointgames.com",
    "127.0.0.1 ajax.googleapis.com",
    "127.0.0.1 api.omniata.com",
    "127.0.0.1 sp-translations.socialpointgames.com",
    "127.0.0.1 graph.facebook.com",
    "127.0.0.1 www.google-analytics.com",
    "127.0.0.1 ssl.google-analytics.com",
    "127.0.0.1 google-analytics.com",
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
    1: 0.65,
    2: 0.90,
    3: 0.55,
    4: 0.22,
    5: 0.15,
}

LEGENDARY_COMBOS_BY_ATTRS = {
    frozenset({'el','p','i','f'}): [1041, 1054],
    frozenset({'e','m','f','i'}): [1041, 1052, 1053, 1054],
    frozenset({'el','p','f','i'}): [1052, 1053],
    frozenset({'w','d'}):          [1052],
}

LEGENDARY_FROM_COMBO_CHANCE = 80.0

PURE_DRAGON_BASE_ID = 1081
PURE_CHANCE_BASE    = 3.0
PURE_CHANCE_BOOSTED = 5.0

PURE_ELEMENT_IDS = [1082, 1083, 1084, 1085, 1086, 1087, 1088, 1089, 1450]
PURE_ELEMENT_CHANCE_BASE    = 5.0
PURE_ELEMENT_CHANCE_BOOSTED = 7.5

SANCTUARY_WEIGHT_MULTIPLIER = 10

def socket_policy_server(port=5840):
    policy_xml = (
        '<?xml version="1.0"?>'
        '<!DOCTYPE cross-domain-policy SYSTEM '
        '"http://www.adobe.com/xml/dtds/cross-domain-policy.dtd">'
        '<cross-domain-policy>'
        '<allow-access-from domain="*" to-ports="*" />'
        '</cross-domain-policy>\0'
    ).encode('utf-8')

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('127.0.0.1', port))
    srv.listen(20)

    while True:
        conn, addr = srv.accept()
        try:
            conn.recv(1024)
            conn.sendall(policy_xml)
        except Exception as e:
            print(f"[!] Error en policy server: {e}")
        finally:
            conn.close()

threading.Thread(target=socket_policy_server, daemon=True).start()

def build_items_index(config):
    return {str(item.get('id')): item for item in config.get('items', [])}

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

def get_breed_result(dragon1_type, dragon2_type, level1, level2, dragon_db, boosted=False, sanctuary_dragons=None):
    if sanctuary_dragons is None:
        sanctuary_dragons = set()
        
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
        is_sanctuary_dragon = ddata['breedable'] == 0 and dtype in sanctuary_dragons

        if ddata['breedable'] == 0 and not is_sanctuary_dragon:
            continue
        if not is_sanctuary_dragon and (level1 < ddata['breedable'] or level2 < ddata['breedable']):
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

        if is_sanctuary_dragon:
            final_w *= SANCTUARY_WEIGHT_MULTIPLIER

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
print("[+] Cargando funciones del Santuario de cría...")
print("    -> 6 niveles cargados correctamente.")
print("[+] Cargando motor de cría del Mundo Ancestral...")

ANCIENT_WORLD_DRAGON_IDS = {
    1405,  # Amber Dragon
    1417,  # Secret Fire Dragon
    1428,  # The Amazing Dragon
    1429,  # Prophet Dragon
    1430,  # Flawless Dragon
    1433,  # Balloon Dragon
    1441,  # Dreamcatcher Dragon
    1442,  # Bride Dragon
    1443,  # Gurgle Dragon
    1444,  # Naughty Dragon
    1445,  # Underworld Dragon
    1446,  # Red Rose Dragon
    1447,  # Mermaid Dragon
    1448,  # Illusion Dragon
    1449,  # Chakra Dragon
}

ANCIENT_CATEGORY_MULTIPLIER = {
    1: 0.65,
    2: 0.90,
    3: 0.55,
    4: 0.22,
    5: 0.15,
    6: 0.10,
    7: 0.10,
}

ANCIENT_FALLBACK_DRAGON_ID = 1405
ANCIENT_TO_NORMAL_CROSSOVER_MULT = 0.05


def build_deity_dragon_db(deity_config):
    db = {}
    for item in deity_config.get('dragons', []):
        db[item['id']] = {
            'name':       item.get('name', 'Unknown'),
            'attributes': set(item.get('attributes', [])),
            'level':      item.get('level', 1),
        }
    return db

def get_ancient_breed_result(dragon1_iid, dragon2_iid, deity_dragon_db, dragon_db):
    parent1 = deity_dragon_db.get(dragon1_iid)
    parent2 = deity_dragon_db.get(dragon2_iid)

    if parent1 is None or parent2 is None:
        print(f"[!] [ANCESTRAL] Dragón padre desconocido (iid {dragon1_iid}, {dragon2_iid}). Fallback Amber.")
        return ANCIENT_FALLBACK_DRAGON_ID

    pool = parent1['attributes'] | parent2['attributes']

    candidates       = []
    loose_candidates = []

    for dtype in ANCIENT_WORLD_DRAGON_IDS:
        ddata = dragon_db.get(dtype)
        if not ddata:
            continue

        attrs = ddata['attributes']
        if not attrs:
            continue

        diff = ddata['difficulty']
        cat  = ddata['category']
        base_w  = WEIGHT_DIFFICULTY.get(diff, 5)
        mult    = ANCIENT_CATEGORY_MULTIPLIER.get(cat, 0.05)
        final_w = base_w * mult
        if final_w <= 0:
            continue

        if attrs.issubset(pool):
            candidates.append((dtype, final_w))
        elif attrs & pool:
            loose_candidates.append((dtype, final_w))

    for dtype, ddata in dragon_db.items():
        if dtype in ANCIENT_WORLD_DRAGON_IDS:
            continue
        if ddata['breedable'] <= 0:
            continue

        attrs = ddata['attributes']
        if not attrs or not attrs.issubset(pool):
            continue
        if 'l' in attrs or 'pu' in attrs:
            continue

        diff = ddata['difficulty']
        cat  = ddata['category']
        base_w  = WEIGHT_DIFFICULTY.get(diff, 5)
        mult    = CATEGORY_MULTIPLIER.get(cat, 0.01)
        final_w = base_w * mult * ANCIENT_TO_NORMAL_CROSSOVER_MULT
        if final_w > 0:
            candidates.append((dtype, final_w))

    if not candidates:
        candidates = loose_candidates

    if not candidates:
        print("[!] [ANCESTRAL] Sin candidatos válidos por atributos. Fallback Amber.")
        return ANCIENT_FALLBACK_DRAGON_ID

    total = sum(w for _, w in candidates)
    r = random.uniform(0, total)
    cumulative = 0
    result = candidates[-1][0]
    for dtype, w in candidates:
        cumulative += w
        if r <= cumulative:
            result = dtype
            break

    if result in ANCIENT_WORLD_DRAGON_IDS:
        print(f"[*] [ANCESTRAL] Resultado: {result} ({dragon_db[result]['name']})")
    else:
        print(f"[!] [ANCESTRAL->NORMAL] ¡Fuga al mundo normal! Resultado: {result} ({dragon_db[result]['name']})")

    return result

print("    -> Motor de cría del Mundo Ancestral inicializado correctamente.")

MARKET_REFRESH_SECONDS = 6 * 60 * 60

RESOURCE_RULES = {
    "gold":  {"min": 500000,  "max": 40000000, "per_unit": 4000, "min_cost": 125, "max_cost": 10000},
    "food":  {"min": 350000,  "max": 10000000, "per_unit": 1000, "min_cost": 350, "max_cost": 10000},
    "gems":  {"min": 100,     "max": 2500,     "per_unit": 0.4,  "min_cost": 250, "max_cost": 6250},
}

DRAGON_BASE_COST_BY_CATEGORY = {
    3: 4000,
    4: 7500,
    5: 15000,
}
DRAGON_BASE_COST_DEFAULT_STEP = 5000

ATTRIBUTE_SURCHARGE = {
    "e": 0, "f": 0, "w": 0, "p": 0, "el": 0, "m": 0,
    "d": 500, "li": 500, "i": 500,
    "wr": 1000,
    "pu": 2000,
    "l": 4000,
}

HALLOWEEN_START_TS = 1790812800
DEFAULT_EVENT_DURATION = 2592000

ISLAND_DATA = {
    "Halloween": {"collect_game_id": 20, "game_island": 168, "assets_path": "halloweenIsland/",
                  "progressStepValues": [10, 20, 25, 30, 35, 42, 52],
                  "dragons": [[1086],[1042],[1006],[1013],[1152],[1101],[1007],[1080],[1225],[1156],[1286],[1287]],
                  "islandType": 1, "lost_item_id": 0},
    "Castle":    {"collect_game_id": 21, "game_island": 161, "assets_path": "castleIsland/",
                  "progressStepValues": [10, 20, 30, 40, 50, 60, 70],
                  "dragons": [[1024],[1039],[1063],[1040],[1070],[1194],[1195]],
                  "islandType": 1, "lost_item_id": 0},
    "Egypt":     {"collect_game_id": 26, "game_island": 165, "assets_path": "egyptIsland/",
                  "progressStepValues": [], "dragons": [], "islandType": 0, "lost_item_id": 137},
    "Olympus":   {"collect_game_id": 28, "game_island": 145, "assets_path": "olympusIsland/",
                  "progressStepValues": [], "dragons": [], "islandType": 0, "lost_item_id": 0, "lost_item_id": 0},
    "Aztec":     {"collect_game_id": 29, "game_island": 163, "assets_path": "aztecIsland/",
                  "progressStepValues": [], "dragons": [], "islandType": 0, "lost_item_id": 0},
    "Pirate":    {"collect_game_id": 15, "game_island": 127, "assets_path": "pirateIsland/",
                  "progressStepValues": [10, 20, 25, 30, 35, 42, 52],
                  "dragons": [[1065],[1055],[1084],[1167],[1155],[1167],[1115]],
                  "islandType": 1, "lost_item_id": 0},
    "Viking":    {"collect_game_id": 27, "game_island": 158, "assets_path": "vikingIsland/",
                  "progressStepValues": [], "dragons": [], "islandType": 0, "lost_item_id": 0},
}

print("[+] Cargando motor de oponentes...")
print("    -> Motor de oponentes cargado correctamente...")
PVP_PAGE_SIZE = 8
PVP_GEN_ID_BASE = 8_000_000_000_000
PVP_NOMBRES_PILA = ["Deus", "Aria", "Magnus", "Drake", "Sera", "Korvan", "Lyra", "Tiberius", "Valera", "Kael", "Mateo", "Elena", "Lucas", "Sofia", "Alejandro", "Valeria", "Diego", "Camila", "Benjamin", "Isabella", "Gideon", "Freya", "Zephyr", "Thalia", "Dorian", "Nova", "Caspian", "Iris", "Phoenix", "Ember","Carlos", "Martina", "Sebastian", "Lucia", "Javier", "Gabriela", "Nicolas", "Daniela", "Samuel", "Aurora"]
PVP_APELLIDOS = ["", "Gonzalez", "Rodriguez", "Gomez", "Fernandez", "Lopez", "Diaz", "Martinez", "Perez", "Garcia", "Sanchez", "Romero", "Alvarez", "Torres", "Ruiz", "Ramirez", "Flores", "Acosta", "Benitez", "Medina", "Herrera", "Suarez", "Aguirre", "Gimenez", "Gutierrez", "Pereira", "Ramos", "Mendoza", "Silva", "Castillo", "Ortiz", "Castro", "Rios", "Alonso", "Caceres", "Morales", "Sosa", "Maldonado", "Burgos", "Vargas", "Rojas", "Cardozo", "Luna", "Miranda", "Villar", "Mendez", "Guzman", "Paz", "Peralta", "Aquino", "Vega"]
PVP_NOMBRES_DRAGON = ["Roxy", "Horacio", "Sergi", "Kasia", "Xavi", "Draco", "Ignis", "Gabriel", "Abdona", "Adolfina", "Agripina", "Aleja", "Altagracia", "Amadora", "Amelia", "Anatolia", "Aniceta", "Antolina", "Apolonia", "Arcadia", "Argimira", "Atanasia", "Áurea", "Balbina", "Baltasara", "Basilisa", "Bercia", "Bernabea", "Bernarda", "Blacina", "Blasina", "Brígida", "Bonifacia", "Calista", "Casilda", "Castora", "Cayetana", "Celedonia", "Celestina", "Celina", "Cesárea", "Clementa", "Crisanta", "Crisóstoma", "Críspula", "Cristeta", "Dámasa", "Demetria", "Diega", "Dionisia", "Dominga", "Dominica", "Dorotea", "Dosinda", "Edelmira", "Edicta", "Eduvigis", "Efigenia", "Eleuteria", "Elicia", "Emerenciana", "Emeteria", "Ermisinda", "Escolástica", "Esmaragda", "Esmerencia", "Estanislá", "Etelvina", "Eudosia", "Eulogia", "Eustaquia", "Ezequiela", "Evarista", "Facunda", "Fausta", "Felicia", "Felisa", "Feliciana", "Froilana", "Fulgencia", "Gaspara", "Gelsumina", "Genoveva", "Getrudis", "Gertrudis", "Gervasia", "Gliceria", "Gracia", "Graciana", "Gregoria", "Guillerma", "Gumersinda", "Felicia", "Fidela", "Froilana", "Hermelinda", "Herminia", "Hilaria", "Humildad", "Indalecia", "Ilora", "Isidora", "Isidra", "Jacoba", "Jerónima", "Jesusa", "Jorja", "Juliana", "Laureana", "Leocadia", "Leoncia", "Liberata", "Librada", "Lopa", "Lorenza", "Luciana", "Lucrecia", "Mamesa", "Marciala", "Marciana", "Matea", "Matiasa", "Máxima", "Melchora", "Melitona", "Micaela", "Miguela", "Montserrate", "Nazaria", "Nemesia", "Nestora", "Nicanora", "Nicasia", "Jacinta", "Jesusa", "Olalla", "Olaya", "Orosia", "Parda", "Paspasia", "Patrocinia", "Peregrina", "Perpétua", "Petra", "Petrola", "Petrona", "Petronila", "Pia", "Polonia", "Pomposa", "Potencia", "Práxedes", "Preciosa", "Prisca", "Priscila", "Quintina", "Quiteria", "Ramira", "Reparada", "Ricarda", "Romualda", "Rudesinda", "Rufa", "Rufina", "Salvadora", "Sancia", "Sandalia", "Santas", "Santiaga", "Saturia", "Saturnina", "Sebastiana", "Segunda", "Semproniana", "Serapia", "Sergia", "Silvestra", "Simeona", "Simona", "Socorro", "Sotera", "Teodomira", "Teodora", "Teodosia", "Tiburcia", "Tomasa", "Toribia", "Úrsula", "Abundio", "Acacio", "Agapito", "Amalio", "Ambrosio", "Aniceto", "Anselmo", "Apolonio", "Aquilino", "Argimiro", "Arquimimo", "Arsenio", "Ascensio", "Asterio", "Atanasio", "Atilano", "Áureo", "Avelino", "Bartolo", "Basilio", "Baudilio", "Belarmino", "Benigno", "Bonifacio", "Buenaventura", "Calisto", "Calixto", "Casiano", "Casildo", "Castiano", "Casimiro", "Cecilio", "Celdonio", "Celedonio", "Cesáreo", "Cipriaco", "Cipriano", "Cipriniano", "Ciriaco", "Cirilo", "Clemente", "Cleto", "Columbano", "Conrado", "Crescencio", "Crisóstomo", "Crispín", "Críspulo", "Cruz", "Deogracias", "Dionisio", "Domiciano", "Doroteo", "Eleuterio", "Eliodoro", "Eliseo", "Emerico", "Emeterio", "Emmanuel", "Epafrodito", "Epifanio", "Escolástico", "Estanislao", "Eufrasio", "Eulogio", "Evelio", "Fabriciano", "Faustina", "Feliciano", "Florencio", "Floro", "Froilán", "Fructuoso", "Frutos", "Fulgencio", "Gregorio", "Guadalupe", "Gumersindo", "Helimenas", "Hermenegildo", "Herminio", "Hermógenes", "Higinio", "Hilario", "Hilarión", "Hipólito", "Indalecio", "Inocente", "Isabelo", "Isidoro", "Juvernón", "Laureano", "Leandro", "Leocadio", "León", "Leovigildo", "Lesmes", "Lisardo", "Lope", "Lupicinio", "Macabeo", "Macario", "Macedonio", "Margarito", "Magin", "Mauro", "Maximino", "Medardo", "Melitón", "Minervino", "Minervo", "Natalio", "Nemesio", "Nicanor", "Niceto", "Nicomedes", "Norberto", "Odón", "Orencio", "Pantaleón", "Paulilo", "Paulino", "Patricio", "Perfecto", "Petrolino", "Petronilo", "Pío", "Policarpo", "Polonio", "Pomposo", "Ponciano", "Primitivo", "Protasio", "Prudencio", "Regino", "Remigio", "Restituto", "Rinaldo", "Robustiano", "Romualdo", "Rómulo", "Rosalino", "Ruperto", "Rufino", "Rufo", "Sabas", "Sabiniano", "Salvio", "Sandalio", "Saturio", "Saturnino", "Serapio", "Servando", "Serbando", "Severo", "Silverio", "Silvestre", "Silvio", "Simeón", "Sinforosio", "Sinforoso", "Sofío", "Sofronio", "Sotero", "Teódulo", "Telesforo", "Teopisto", "Tereso", "Tiburcio", "Timoteo", "Toribio", "Trifón", "Trinitario", "Ulpiano", "Valeriano", "Venancio", "Victoriano", "Zoilo"]

def _build_dragon_pool(config_data):
    pool = {1: [], 2: [], 3: [], 4: [], 5: []}
    for item in config_data.get('items', []):
        if item.get('group_type') == 'DRAGON':
            cat  = item.get('category', 1)
            d_id = item.get('id')
            if cat in pool:
                pool[cat].append(d_id)
    return pool

def _get_dragon_type_for_level(level, pool, rng=random):
    if level <= 15:
        allowed = [1, 2]
    elif level <= 30:
        allowed = [2, 3, 4]
    else:
        allowed = [3, 4, 5]
    valid_cats = [c for c in allowed if pool[c]] or [1]
    chosen_cat = rng.choice(valid_cats)
    return rng.choice(pool[chosen_cat])

def _roll_team_size(rng=random):
    roll = rng.random()
    if roll <= 0.85:   return 3
    elif roll <= 0.95: return 2
    else:              return 1

def build_pvp_team(opp_id, opp_level, config_data):
    rng = random.Random(str(opp_id))
    dragon_pool = _build_dragon_pool(config_data)
    units = []
    for d_idx in range(1, _roll_team_size(rng) + 1):
        d_type = _get_dragon_type_for_level(opp_level, dragon_pool, rng)
        xp = rng.randint(16, 156)
        units.append({
            "name": rng.choice(PVP_NOMBRES_DRAGON),
            "type": d_type,
            "lvl": level_from_xp(xp, d_type),
            "id": d_idx
        })
    return units

def _generate_pvp_opponents(player_data, amount, island_numbers):
    ps = player_data['privateState']
    opponents = []
    for _ in range(amount):
        ps['pvpGenCounter'] = ps.get('pvpGenCounter', 0) + 1
        lvl = random.randint(12, 60)
        if   lvl < 20: pvp_isle_val = 0
        elif lvl < 35: pvp_isle_val = 1
        elif lvl < 50: pvp_isle_val = 2
        else:          pvp_isle_val = 3

        avatar = random.randint(1, 307)
        
        opponents.append({
            "id": str(PVP_GEN_ID_BASE + ps['pvpGenCounter']),
            "name": f"{random.choice(PVP_NOMBRES_PILA)} {random.choice(PVP_APELLIDOS)}".strip(),
            "level": lvl,
            "pvplevel": random.randint(1, max(1, lvl // 4)),
            "pvpIsle": pvp_isle_val,
            "islandNumber": random.choice(island_numbers),
            "pic": f"http://127.0.0.1/assets/images/en/avatares_oponentes/{avatar}.jpg?type=square"
        })
    opponents.sort(key=lambda o: o["level"])
    return opponents

def get_pvp_league_page(player_data, level, reset=False):
    ps = player_data.setdefault('privateState', {})
    leagues = ps.setdefault('pvpLeagues', {})
    key = str(level)
    start = (level - 1) * PVP_PAGE_SIZE

    all_opponents = load_pvp_isle() or []
    island_numbers = sorted({p.get('islandNumber', 1) for p in all_opponents}) or [1]

    if reset:
        page = _generate_pvp_opponents(player_data, PVP_PAGE_SIZE, island_numbers)
        leagues[key] = page
        player_data.setdefault('map', {})['universAttackWin'] = []
        return page, True

    if key in leagues:
        return leagues[key], False

    page = all_opponents[start:start + PVP_PAGE_SIZE]
    if len(page) < PVP_PAGE_SIZE:
        page = page + _generate_pvp_opponents(player_data, PVP_PAGE_SIZE - len(page), island_numbers)
        leagues[key] = page
        return page, True
    return page, False

#PvP 2.3.0
COMBAT_LEAGUE_OPPONENTS = 7

def get_combat_league_config(game_config, league_id):
    cfg = game_config.get('combat_leagues', {})
    params = {p.get('name'): p.get('value')
              for p in cfg.get('parameters', []) if isinstance(p, dict)}
    leagues = cfg.get('leagues', [])
    league_cfg = next((l for l in leagues if int(l.get('id', 0)) == league_id), None)
    if league_cfg is None and leagues:
        league_cfg = leagues[-1]
    return params, league_cfg

def build_combat_league(player_data, game_config, user_id):
    info = player_data['playerInfo']
    wanted_id = max(1, int(info.get('pvpLevel', 1)))
    params, league_cfg = get_combat_league_config(game_config, wanted_id)

    league_id = int(league_cfg['id']) if league_cfg else wanted_id
    opponents_count = int(league_cfg.get('opponents_count', 7)) if league_cfg else 7
    fights = int(params.get('FIGHTS_BEFORE_COOLDOWN', 3))

    all_opponents = load_pvp_isle() or []
    island_numbers = sorted({p.get('islandNumber', 1) for p in all_opponents}) or [1]
    rivals = _generate_pvp_opponents(player_data, opponents_count, island_numbers)

    combats = [{
        "playerId": str(r['id']),
        "playerLevel": int(r['level']),
        "playerPicture": r['pic'],
        "dragons": [
            {"name": d['name'], "type": d['type'], "level": d['lvl']}
            for d in build_pvp_team(r['id'], int(r['level']), game_config)
        ]
    } for r in rivals]

    return {
        "id": league_id,
        "state": 0,
        "wonOpponents": [],
        "currentOpponent": 0,
        "cooldownsEndAt": [0] * fights,
        "resetCooldownEndsAt": 0,
        "combats": combats
    }

def normalize_combat_league(league):
    changed = False
    for combat in league.get('combats', []):
        for d in combat.get('dragons', []):
            if 'lvl' in d:
                d['level'] = d.pop('lvl')
                changed = True
            d.pop('id', None)
    return changed

def check_kompu_rewards(player_data, game_config, game_type):
    private_state = player_data.setdefault('privateState', {})
    kompu_spells = private_state.get('kompuSpells', 0)
    kompu_steps = private_state.setdefault('kompuSteps', [])

    kompu_offers = game_config.get('kompu_offers', [])
    offer = next((o for o in kompu_offers if o.get('game_type') == game_type), None)
    if offer is None:
        return

    for reward in offer.get('rewards', []):
        cost = reward['cost']
        if kompu_spells >= cost and cost not in kompu_steps:
            dragon_options = reward.get('dragon', [])
            if not dragon_options:
                continue
            chosen = dragon_options[0]

            store = player_data.setdefault('map', {}).setdefault('store', {})
            dragons_list = store.setdefault('dragons', [])
            dragons_list.append({
                "iid": chosen['type'],
                "lvl": 0
            })

            kompu_steps.append(cost)
            print(f"   [KOMPU] Umbral {cost} alcanzado -> se entregó huevo del dragón type={chosen['type']}")
            
print("[+] Cargando motor del mercado de brujas...")
def generate_black_market_boxes(user_game_config):
    cat_1, cat_2_3, cat_4_5, cat_3_4_5 = [], [], [], []
    cat_4, cat_5 = [], []

    for item in user_game_config.get('items', []):
        if item.get('group_type') == 'DRAGON' and 'category' in item:
            cat = item['category']
            d_id = item['id']
            if cat == 1: cat_1.append(d_id)
            elif cat in [2, 3]: cat_2_3.append(d_id)
            if cat == 4: cat_4.append(d_id)
            if cat == 5: cat_5.append(d_id)
            if cat in [4, 5]: cat_4_5.append(d_id)
            if cat in [3, 4, 5]: cat_3_4_5.append(d_id)

    unique_dragon = random.choice(cat_3_4_5) if cat_3_4_5 else 1041

    kompu_boxes = []

    if len(cat_2_3) >= 3:
        kompu_boxes.extend(random.sample(cat_2_3, 3))
    else:
        kompu_boxes.extend(cat_2_3)
        while len(kompu_boxes) < 3: kompu_boxes.append(1011)

    if len(cat_4) >= 2:
        kompu_boxes.extend(random.sample(cat_4, 2))
    else:
        kompu_boxes.extend(cat_4)
        while len(kompu_boxes) < 5: kompu_boxes.append(1011)

    probabilidad_unique = random.randint(1, 100)
    if probabilidad_unique <= 10:
        kompu_boxes.append(unique_dragon)
    else:
        kompu_boxes.append(random.choice(cat_5) if cat_5 else 1041)

    kompu_shuffled = list(kompu_boxes)
    random.shuffle(kompu_shuffled)

    return unique_dragon, kompu_boxes, kompu_shuffled


def build_kompu_offers_payload(user_game_config, start_timestamp, unique_dragon):
    cat_1, cat_2_3, cat_4_5, cat_3_4_5 = [], [], [], []
    for item in user_game_config.get('items', []):
        if item.get('group_type') == 'DRAGON' and 'category' in item:
            cat = item['category']
            d_id = item['id']
            if cat == 1: cat_1.append(d_id)
            elif cat in [2, 3]: cat_2_3.append(d_id)
            if cat in [4, 5]: cat_4_5.append(d_id)
            if cat in [3, 4, 5]: cat_3_4_5.append(d_id)

    pool_x2 = random.sample(cat_1, min(10, len(cat_1))) if cat_1 else [1011]
    pool_x3 = random.sample(cat_2_3, min(10, len(cat_2_3))) if cat_2_3 else [1011]
    pool_x4 = random.sample(cat_4_5, min(7, len(cat_4_5))) if cat_4_5 else [1041]
    pool_x5 = random.sample(cat_3_4_5, min(5, len(cat_3_4_5))) if cat_3_4_5 else [1041]

    return [{
        "id": 1,
        "starts_at": start_timestamp,
        "duration": 259200,
        "game_type": 4,
        "resetable": 0,
        "pick_prize": 0,
        "hurry_up_cost": 10,
        "timer_between": 21600,
        "viral_icon": [],
        "rewards": {
            "uniqueDragonId": unique_dragon,
            "prizes": [pool_x2, pool_x3, pool_x4, pool_x5]
        }
    }]
print("    -> Motor del Mercado de Brujas inicializado correctamente")
print("[+] Avisando a la bruja para que este atenta al jugador....")
def decide_next_kompu_event(player_data, game_config, current_ts):
    private_state = player_data.setdefault('privateState', {})
    event = private_state.setdefault('KompuEventType', {})
    patch = event.setdefault('halloweenPatchApplied', {
        "HalloweenCompleted": [],
        "halloweenNextWheel": 1790827200
    })

    next_halloween = patch['halloweenNextWheel']
    completed = patch['HalloweenCompleted']
    cooldown = random.randint(5 * 86400, 7 * 86400)

    if current_ts >= (next_halloween - cooldown) and next_halloween not in completed:
        new_type = 3
        new_start = max(current_ts, next_halloween)
        new_end = new_start + 1296000
    else:
        new_type = 4 if random.random() < 0.70 else 2
        descanso = random.randint(3 * 86400, 7 * 86400)
        new_start = current_ts + descanso
        new_end = new_start + 259200

    game_config['kompu_offers'] = []
    event['type'] = new_type
    event['KompuEventStart'] = new_start
    event['KompuEventEnd'] = new_end

    if new_type == 4:
        unique_dragon, cajas, cajas_mezcladas = generate_black_market_boxes(game_config)
        private_state['BlackMarketUniqueDragon'] = int(unique_dragon)
        private_state['kompuBoxesDragons'] = cajas
        private_state['kompuBoxesShuffledDragons'] = cajas_mezcladas

    print(f"   [KOMPU] Próximo evento decidido: type={new_type} | "
          f"arranca={new_start} | termina={new_end}")

    return player_data, game_config

def check_and_update_kompu_event(player_data, user_id, game_config):
    current_ts = player_data.get('timestamp', int(time.time()))
    private_state = player_data.setdefault('privateState', {})
    event = private_state.get('KompuEventType')

    if event is None:
        return player_data, game_config

    event_start = int(event.get('KompuEventStart', 0))
    event_end = int(event.get('KompuEventEnd', 0))
    event_type = event.get('type', 4)

    config_modificado = False

    if current_ts >= event_end:
        game_config['kompu_offers'] = []

        if event_type == 3:
            patch = event.setdefault('halloweenPatchApplied', {})
            completed = patch.setdefault('HalloweenCompleted', [])
            completed.append(event_start)
            patch['halloweenNextWheel'] = patch.get('halloweenNextWheel', event_start) + 31536000
            private_state['kompuSpells'] = 0
            private_state['kompuSteps'] = []
            private_state['kompuHWUniqueGiven'] = False
            print(f"   [KOMPU] Rueda de Halloween terminó para {user_id}. Próxima: {patch['halloweenNextWheel']}")

        elif event_type == 2:
            private_state['kompuSpells'] = 0
            private_state['kompuSteps'] = []
            print(f"   [KOMPU] Rueda normal terminó para {user_id}.")

        elif event_type == 4:
            print(f"   [KOMPU] Mercado de Brujas terminó para {user_id}.")

        player_data, game_config = decide_next_kompu_event(player_data, game_config, current_ts)
        config_modificado = True

    elif current_ts >= event_start and current_ts < event_end:
        if not game_config.get('kompu_offers'):
            if event_type == 4:
                unique_dragon = int(private_state.get('BlackMarketUniqueDragon', 1041))
                game_config['kompu_offers'] = build_kompu_offers_payload(game_config, event_start, unique_dragon)
            elif event_type == 2:
                game_config['kompu_offers'] = build_wheel_offer_payload(game_config, event_start)
            elif event_type == 3:
                game_config['kompu_offers'] = build_halloween_wheel_offer_payload(game_config, event_start)

            config_modificado = True
            print(f"   [KOMPU] Evento type={event_type} VISIBLE en HUD para {user_id}!")

        if config_modificado:
            user_dir = os.path.join(SRV_DIR, str(user_id))
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)
            filename = resolve_user_config_filename(user_id)
            user_config_path = os.path.join(user_dir, filename)
            
            with open(user_config_path, 'w', encoding='utf-8') as f:
                json.dump(game_config, f, indent=2, ensure_ascii=False)

            sync_config_progress_across_languages(user_id, game_config, exclude_filename=filename)
            
    return player_data, game_config
print("    -> La bruja del mercado estara atenta para ofrecerte mercancia")

#Sistema de cristales
def distribute_mine_crystals(total_crystals, max_purity_id, crystals_config):
    if not crystals_config or not max_purity_id or total_crystals <= 0:
        return {str(max_purity_id): total_crystals} if max_purity_id else {}

    max_crystal = None
    for c in crystals_config:
        if int(c.get('id')) == int(max_purity_id):
            max_crystal = c
            break

    if not max_crystal:
        return {str(max_purity_id): total_crystals}

    max_purity_level = int(max_crystal.get('purity', 1))
    min_purity_id = int(max_purity_id) - max_purity_level + 1
    num_types = max_purity_level
    weights = [num_types - i for i in range(num_types)]
    total_weight = sum(weights)

    result = {}
    remaining = int(total_crystals)

    for i in range(num_types):
        purity_id = min_purity_id + i

        if i == num_types - 1:
            amount = remaining
        else:
            amount = max(1, int(round(total_crystals * weights[i] / total_weight)))
            min_needed_for_rest = num_types - i - 1
            amount = min(amount, remaining - min_needed_for_rest)
            amount = max(1, amount)

        result[str(purity_id)] = amount
        remaining -= amount

    return result

def pick_wheel_normal_rewards(game_config):
    dragons_by_cat = {}
    for item in game_config.get('items', []):
        if item.get('group_type') == 'DRAGON' and 'category' in item:
            dragons_by_cat.setdefault(item['category'], []).append(item['id'])

    def pick(cat, exclude):
        pool = [d for d in dragons_by_cat.get(cat, []) if d not in exclude]
        if not pool:
            pool = dragons_by_cat.get(cat, [])
        return random.choice(pool) if pool else 1011

    chosen = []
    cat_100 = 4 if random.random() > 0.20 else 5
    chosen.append(pick(cat_100, chosen))

    cat_70 = 3 if random.random() > 0.20 else 4
    chosen.append(pick(cat_70, chosen))

    chosen.append(pick(3, chosen))
    chosen.append(pick(2, chosen))

    dragon_100, dragon_70, dragon_50, dragon_30 = chosen
    return [
        {"cost": 30, "dragon": [{"type": dragon_30, "lvl": 0}]},
        {"cost": 50, "dragon": [{"type": dragon_50, "lvl": 0}]},
        {"cost": 70, "dragon": [{"type": dragon_70, "lvl": 0}]},
        {"cost": 100, "dragon": [{"type": dragon_100, "lvl": 0}]}
    ]


def build_wheel_offer_payload(game_config, start_timestamp):
    return [{
        "id": 1,
        "starts_at": start_timestamp,
        "duration": 259200,
        "game_type": 2,
        "resetable": 0,
        "pick_prize": 0,
        "hurry_up_cost": 5,
        "timer_between": 21600,
        "viral_icon": [],
        "rewards": pick_wheel_normal_rewards(game_config)
    }]

def pick_halloween_wheel_prizes(cost_multiplier=1.0):
    dragon_pool = [1007, 1080, 1094, 1051, 1028, 1006, 1054]

    resto = [d for d in dragon_pool if d != 1094]
    visibles_extra = random.sample(resto, 2)
    dragones_visibles = [1094] + visibles_extra

    pool_sorpresa = [d for d in resto if d not in visibles_extra]
    dragon_sorpresa = random.choice(pool_sorpresa)

    prizes = [None] * 16
    posiciones = list(range(16))
    random.shuffle(posiciones)

    pos_visibles = posiciones[:3]
    pos_sorpresa = posiciones[3]

    for pos, dragon_id in zip(pos_visibles, dragones_visibles):
        prizes[pos] = [dragon_id]

    prizes[pos_sorpresa] = [dragon_sorpresa, dragon_sorpresa]

    recursos_base = [
        {"g": 500}, {"f": 300}, {"g": 1000}, {"c": 20},
        {"f": 600}, {"g": 1500}, {"x": 5000}, {"f": 900},
        {"g": 800}, {"f": 450}, {"g": 300}, {"g": 700}
    ]
    random.shuffle(recursos_base)

    idx_recurso = 0
    for i in range(16):
        if prizes[i] is None:
            recurso = dict(recursos_base[idx_recurso])
            key = list(recurso.keys())[0]
            recurso[key] = int(recurso[key] * cost_multiplier)
            prizes[i] = recurso
            idx_recurso += 1

    return prizes

def build_halloween_wheel_offer_payload(game_config, start_timestamp):
    orden = list(range(16))

    return [{
        "id": 1,
        "starts_at": start_timestamp,
        "duration": 1296000,
        "game_type": 3,
        "resetable": 0,
        "pick_prize": 0,
        "hurry_up_cost": 10,
        "timer_between": 21600,
        "viral_icon": [],
        "rewards": [
            {
                "0": {
                    "cost": {"c": 0},
                    "o": orden,
                    "prizes": pick_halloween_wheel_prizes(1.0)
                },
                "1": {
                    "cost": {"c": 10},
                    "o": orden,
                    "prizes": pick_halloween_wheel_prizes(1.5)
                }
            }
        ]
    }]

print("[+] Cargando generación de Isla de Eventos...")
def check_reward_thresholds(game_config, player_data, cg_id, island_save):
    quest_cfg = next((q for q in game_config.get('collect_game_quests', [])
                       if q.get('collect_game') == cg_id), None)
    if quest_cfg is None:
        return

    reward_map = quest_cfg.get('reward')
    if not isinstance(reward_map, dict):
        return

    total_progress = sum(it.get('amount', 0) for it in island_save.get('items', {}).values())
    island_save.setdefault('rewardsGiven', [])

    for threshold_str, dragon_ids in reward_map.items():
        threshold = int(threshold_str)
        reward_id = dragon_ids[0] if isinstance(dragon_ids, list) else dragon_ids

        if total_progress >= threshold and reward_id not in island_save['rewardsGiven']:
            grant_quest_reward(game_config, player_data, reward_id)
            island_save['rewardsGiven'].append(reward_id)
            print(f"   [🎁] ¡RECOMPENSA ENTREGADA! Progreso {total_progress}/{threshold} -> item {reward_id}")
            
def grant_quest_reward(game_config, player_data, reward_item_id):
    item_cfg = next((it for it in game_config.get('items', [])
                      if it.get('id') == reward_item_id), None)

    if item_cfg is None:
        print(f"   [!] Error: reward id {reward_item_id} no existe en game_config['items']")
        return

    group_type = item_cfg.get('group_type')

    player_data.setdefault('map', {})
    player_data['map'].setdefault('store', {})

    if group_type == 'DRAGON':
        player_data['map']['store'].setdefault('dragons', [])
        player_data['map']['store']['dragons'].append({"iid": reward_item_id, "lvl": 0})
        print(f"   [🎁] Dragón {reward_item_id} ({item_cfg.get('name')}) -> store.dragons")
    else:
        player_data['map']['store'].setdefault('items', {})
        key = str(reward_item_id)
        current = player_data['map']['store']['items'].get(key, 0)
        player_data['map']['store']['items'][key] = current + 1
        print(f"   [🎁] {item_cfg.get('name')} ({group_type}) -> store.items['{key}'] = {current + 1}")

def check_and_complete_quest(game_config, player_data, island_save, quest_id):
    quest_id_str = str(quest_id)

    quest_cfg = next((q for q in game_config.get('collect_game_quests', [])
                       if str(q.get('id')) == quest_id_str), None)

    if quest_cfg is not None:
        reward = quest_cfg.get('reward')
        if isinstance(reward, int):
            reward_item_cfg = next((it for it in game_config.get('items', [])
                                     if it.get('id') == reward), None)
            if reward_item_cfg and reward_item_cfg.get('group_type') == 'DRAGON':
                return False

    containers_de_la_quest = [
        c for c in game_config.get('collect_game_item_containers', [])
        if str(c.get('quest')) == quest_id_str
    ]

    if not containers_de_la_quest:
        return False

    ya_completados = island_save.get('itemsContainers', [])
    todos_completos = all(c['id'] in ya_completados for c in containers_de_la_quest)

    if not todos_completos:
        return False

    island_save.setdefault('quests', {}).setdefault('status', {})
    ya_estaba_completada = island_save['quests']['status'].get(quest_id_str) == 'completed'

    if not ya_estaba_completada:
        island_save['quests']['status'][quest_id_str] = 'completed'
        print(f"   [🏆] Quest {quest_id_str} COMPLETED "
              f"({len(containers_de_la_quest)}/{len(containers_de_la_quest)} containers)")

        if quest_cfg is not None:
            reward = quest_cfg.get('reward')
            if isinstance(reward, int):
                grant_quest_reward(game_config, player_data, reward)

    return True

PASSIVE_RESOURCE_ITEM_IDS = [147, 148, 149, 132, 133, 134, 135, 136, 140, 141, 142, 153, 154, 155, 192, 196]

def add_collect_game_item_progress(game_config, player_data, item_type, amount=1):
    active_games = game_config.get('collect_game', [])
    if not active_games:
        return False

    cg_cfg = active_games[0]
    now = int(time.time())
    ends_at = cg_cfg.get('starts_at', 0) + cg_cfg.get('duration', 0)
    if now > ends_at:
        return False

    cg_key = str(cg_cfg.get('id'))
    item_type_str = str(item_type)

    player_data.setdefault('privateState', {})
    player_data['privateState'].setdefault('collectGame', {})
    collect_game_save = player_data['privateState']['collectGame']
    collect_game_save.setdefault(cg_key, {
        "quests": {"status": {}, "rewardTryTime": 0},
        "formulaVars": {"playerLevelAtCollectGameStart": player_data['playerInfo'].get('level', 1)},
        "itemsContainers": [], "items": {}, "rewardsGiven": []
    })
    island_save = collect_game_save[cg_key]
    island_save.setdefault('items', {})
    island_save['items'].setdefault(item_type_str, {"amount": 0, "timestamp": 0})

    island_save['items'][item_type_str]['amount'] += amount
    island_save['items'][item_type_str]['timestamp'] = now
    print(f"   [+{amount}] Tipo {item_type_str} -> {island_save['items'][item_type_str]['amount']} (isla {cg_key})")
    check_reward_thresholds(game_config, player_data, cg_cfg.get('id'), island_save)
    return True

def build_collect_game(island_name, starts_at, duration=DEFAULT_EVENT_DURATION):
    d = ISLAND_DATA[island_name]
    return {
        "platform": "canvas",
        "id": d["collect_game_id"],
        "starts_at": starts_at,
        "duration": duration,
        "minimum_pack_value": 20,
        "game_island": d["game_island"],
        "discount_price": 0,
        "min_level": 5,
        "game_type": 2,
        "game_data": {
            "retry_price": 10,
            "speedup_price": 2,
            "islandType": d["islandType"],
            "buyallDivisor": 2,
            "buyallMultiplier": 2,
            "buyallSubtract": 2,
            "progressStepValues": d["progressStepValues"],
            "daily_item_cooldown_time": 43200,
            "attack_cooldown": 43200,
            "assets_path": d["assets_path"],
            "lost_item_id": d["lost_item_id"],
            "dragons": d["dragons"]
        }
    }

def _island_name_from_id(cg_id):
    for name, d in ISLAND_DATA.items():
        if d["collect_game_id"] == cg_id:
            return name
    return None

def ensure_island_events_structure(player_data):
    private_state = player_data.setdefault('privateState', {})
    if 'islandEvents' not in private_state:
        private_state['islandEvents'] = {
            "gatillado": 0,
            "halloweenPatchApplied": 0,
            "Islands": {name: (0 if name == "Halloween" else 1) for name in ISLAND_DATA}
        }
        print(f"   [🏝️] Estructura 'islandEvents' creada (jugador nuevo o parcheado)")
    return player_data

def _reset_pool_after_halloween(ie):
    for name in ie['Islands']:
        if name != 'Halloween':
            ie['Islands'][name] = 0

def choose_next_island(islands_state):
    candidates = [name for name, v in islands_state.items() if v == 0]
    if not candidates:
        candidates = [name for name, v in islands_state.items() if v == 2]
    if not candidates:
        return None
    return random.choice(candidates)

def _activate_next_island(game_config, ie, now):
    """Elige y arma la próxima isla, aplicando primero las reglas especiales de Halloween."""
    if ie['halloweenPatchApplied'] == 0:
        if now >= HALLOWEEN_START_TS + DEFAULT_EVENT_DURATION:
            ie['Islands']['Halloween'] = 1
            ie['halloweenPatchApplied'] = 1
            _reset_pool_after_halloween(ie)
            print(f"   [🎃] Ventana de Halloween ya pasó -> marcada 1 sin jugar, pool liberado")
        elif ie['Islands'].get('Halloween') == 0:
            starts_at = max(now, HALLOWEEN_START_TS)
            new_cg = build_collect_game('Halloween', starts_at)
            game_config['collect_game'] = [new_cg]
            ie['halloweenPatchApplied'] = 1
            print(f"   [🎃] Halloween programada para timestamp {starts_at}")
            return game_config, True

    next_name = choose_next_island(ie['Islands'])
    if next_name is None:
        print(f"   [!] No hay islas disponibles para rotar (esto no debería pasar)")
        return game_config, False

    cooldown = random.randint(7 * 86400, 30 * 86400)
    starts_at = now + cooldown
    new_cg = build_collect_game(next_name, starts_at)
    game_config['collect_game'] = [new_cg]
    print(f"   [🏝️] Próxima isla elegida: {next_name} (arranca en {cooldown // 86400} días, ts={starts_at})")
    return game_config, True

def process_island_events(player_data, game_config, user_id):
    now = player_data.get('timestamp', int(time.time()))
    player_data = ensure_island_events_structure(player_data)
    ie = player_data['privateState']['islandEvents']
    player_level = player_data['playerInfo'].get('level', 1)
    config_changed = False

    if ie['gatillado'] == 0:
        if player_level >= 5:
            ie['gatillado'] = 1
            game_config, config_changed = _activate_next_island(game_config, ie, now)
            print(f"   [🏝️] Gatillo de islas de evento ACTIVADO (nivel {player_level})")
        if config_changed:
            save_game_config(game_config, user_id)
        return player_data, game_config

    active_cg = game_config.get('collect_game', [])
    if not active_cg:
        return player_data, game_config

    cg = active_cg[0]
    starts_at = cg.get('starts_at', 0)
    duration = cg.get('duration', 0)
    ends_at = starts_at + duration
    cg_key = str(cg.get('id'))

    if now >= starts_at:
        player_data['privateState'].setdefault('collectGame', {})
        if cg_key not in player_data['privateState']['collectGame']:
            player_data['privateState']['collectGame'][cg_key] = {
                "quests": {"status": {}, "rewardTryTime": 0},
                "formulaVars": {"playerLevelAtCollectGameStart": player_level},
                "itemsContainers": [], "items": {}, "rewardsGiven": []
            }
            print(f"   [🏝️] Isla arrancada para el jugador (collect_game {cg_key})")

    if now >= ends_at:
        island_name = _island_name_from_id(cg.get('id'))
        island_save = player_data['privateState'].get('collectGame', {}).get(cg_key, {})
        status_dict = island_save.get('quests', {}).get('status', {})

        quest_ids_de_la_isla = [str(q.get('id')) for q in game_config.get('collect_game_quests', [])
                                 if q.get('collect_game') == cg.get('id')]

        completada = bool(status_dict) and all(status_dict.get(qid) == 'completed' for qid in quest_ids_de_la_isla)

        if island_name:
            ie['Islands'][island_name] = 1 if completada else 2
            print(f"   [🏝️] Isla {island_name} finalizada -> Islands[{island_name}] = {1 if completada else 2}")
            if island_name == 'Halloween':
                _reset_pool_after_halloween(ie)

        if cg_key in player_data['privateState'].get('collectGame', {}):
            del player_data['privateState']['collectGame'][cg_key]

        game_config, _ = _activate_next_island(game_config, ie, now)
        config_changed = True

    if config_changed:
        save_game_config(game_config, user_id)

    return player_data, game_config
print("    -> Motor de Islas de Eventos cargada correctamente")

_avatar_queue = deque()
_avatar_lock = threading.Lock()
PVP_AVATAR_DIR = os.path.join(ASSETS_DIR, 'images', 'en', 'avatares_oponentes')

def _avatar_number_from_pic(pic):
    m = re.search(r'avatares_oponentes/(\d+)\.jpg', str(pic or ''))
    if m and os.path.exists(os.path.join(PVP_AVATAR_DIR, f"{m.group(1)}.jpg")):
        return int(m.group(1))
    return random.randint(1, 307)

def _queue_avatars_for_page(page):
    with _avatar_lock:
        _avatar_queue.clear()
        for opp in page:
            _avatar_queue.append(_avatar_number_from_pic(opp.get('pic')))
            
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

def get_element_limit(game_config, group_type, level):
    limits_table = game_config.get('globals', {}).get('LIMITS', {}).get('value', {}).get(group_type, {})
    if not limits_table:
        return 1

    thresholds = sorted(int(k) for k in limits_table.keys())
    applicable = 1
    for t in thresholds:
        if t <= level:
            applicable = limits_table[str(t)]
        else:
            break
    return applicable

def calculate_food_container_cost(game_config, quest_cfg, user_starting_level):
    fp = quest_cfg.get('formula_parameters', {})
    days = fp.get('foodDaysUsedQuest', 0)
    hours = fp.get('foodHoursUsed', 0)
    factor = fp.get('foodFactor', 0)
    exponent = fp.get('foodExponent', 0)

    farm_limit = get_element_limit(game_config, 'FARM', user_starting_level)

    inner = days * 24 * 3600 * (hours / 24) * factor * \
            ((1 + user_starting_level / 100) ** exponent) * farm_limit / 400

    return round(inner) * 100

def get_user_language(user_id):
    marker_path = os.path.join(SRV_DIR, str(user_id), '_lenguajeUsado')
    if os.path.exists(marker_path):
        with open(marker_path, 'r', encoding='utf-8') as f:
            lang = f.read().strip()
            if lang:
                return lang
    return None

def set_user_language(user_id, language):
    user_dir = os.path.join(SRV_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    with open(os.path.join(user_dir, '_lenguajeUsado'), 'w', encoding='utf-8') as f:
        f.write(language)

def get_config_filename_for_language(language):
    if language:
        candidate = f'get_game_config_{language}.json'
        if os.path.exists(os.path.join(SRV_DIR, candidate)):
            return candidate
    return 'get_game_config.json'

CONFIG_VERSION = 2

_CONFIG_MIGRATION_LOCK = threading.Lock()
_CONFIG_VERIFIED_USERS = set()

def _user_config_migrated_marker_path(user_id):
    return os.path.join(SRV_DIR, str(user_id), '_configEstructuraMigrada')

def read_user_config_version(user_id):
    path = _user_config_migrated_marker_path(user_id)
    if not os.path.exists(path):
        return 0
    try:
        with open(path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        m = re.search(r'version\s*=\s*(\d+)', contenido)
        return int(m.group(1)) if m else 0
    except Exception:
        return 0

def is_user_config_migrated(user_id):
    uid = str(user_id)
    if uid in _CONFIG_VERIFIED_USERS:
        return True
    if read_user_config_version(uid) >= CONFIG_VERSION:
        _CONFIG_VERIFIED_USERS.add(uid)
        return True
    return False

def mark_user_config_migrated(user_id):
    user_dir = os.path.join(SRV_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    with open(_user_config_migrated_marker_path(user_id), 'w', encoding='utf-8') as f:
        f.write(f"version={CONFIG_VERSION}\nts={int(time.time())}")
    _CONFIG_VERIFIED_USERS.add(str(user_id))
        
def migrate_legacy_user_config(user_id, target_filename):
    if is_user_config_migrated(user_id):
        return

    with _CONFIG_MIGRATION_LOCK:
        if is_user_config_migrated(user_id):
            return

        user_dir = os.path.join(SRV_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)

        variantes_previas = [
            n for n in os.listdir(user_dir)
            if n.startswith('get_game_config') and n.endswith('.json')
        ]
        if target_filename in variantes_previas:
            variantes_previas.remove(target_filename)
            variantes_previas.insert(0, target_filename)

        progreso_rescatado = {}
        for nombre in variantes_previas:
            try:
                with open(os.path.join(user_dir, nombre), 'r', encoding='utf-8') as f:
                    old_data = json.load(f)
                for campo in CONFIG_SYNCED_KEYS:
                    if campo in old_data and campo not in progreso_rescatado:
                        progreso_rescatado[campo] = old_data[campo]
            except Exception as e:
                print(f"   [!] No se pudo leer progreso previo de {nombre} para {user_id}: {e}")

        for nombre in os.listdir(SRV_DIR):
            if not (nombre.startswith('get_game_config') and nombre.endswith('.json')):
                continue
            src = os.path.join(SRV_DIR, nombre)
            dst = os.path.join(user_dir, nombre)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                _GAME_CONFIG_CACHE.pop(dst, None)

        if progreso_rescatado:
            for nombre in os.listdir(user_dir):
                if not (nombre.startswith('get_game_config') and nombre.endswith('.json')):
                    continue
                variant_path = os.path.join(user_dir, nombre)
                try:
                    with open(variant_path, 'r', encoding='utf-8') as f:
                        variant_data = json.load(f)
                    for campo, valor in progreso_rescatado.items():
                        variant_data[campo] = valor
                    with open(variant_path, 'w', encoding='utf-8') as f:
                        json.dump(variant_data, f, indent=2, ensure_ascii=False)
                    _GAME_CONFIG_CACHE.pop(variant_path, None)
                except Exception as e:
                    print(f"   [!] No se pudo reinyectar progreso en {nombre} para {user_id}: {e}")

            print(f"   [🌐] Progreso migrado (kompu_offers/collect_game) para {user_id} -> todas las variantes")

        mark_user_config_migrated(user_id)
        print(f"   [🌐] Config de {user_id} actualizado a la versión {CONFIG_VERSION}")

CONFIG_SYNCED_KEYS = ('kompu_offers', 'collect_game')

def resolve_user_config_filename(user_id, language=None):
    if not user_id:
        return get_config_filename_for_language(language)

    lang_a_usar = language or get_user_language(user_id) or 'en'
    filename = get_config_filename_for_language(lang_a_usar)

    if not is_user_config_migrated(user_id):
        migrate_legacy_user_config(user_id, filename)

    if language:
        set_user_language(user_id, lang_a_usar)

    return filename

def sync_config_progress_across_languages(user_id, data, exclude_filename=None):
    user_dir = os.path.join(SRV_DIR, str(user_id))
    if not os.path.isdir(user_dir):
        return

    for nombre in os.listdir(user_dir):
        if not (nombre.startswith('get_game_config') and nombre.endswith('.json')):
            continue
        if nombre == exclude_filename:
            continue

        variant_path = os.path.join(user_dir, nombre)
        try:
            with open(variant_path, 'r', encoding='utf-8') as f:
                variant_data = json.load(f)

            changed = False
            for campo in CONFIG_SYNCED_KEYS:
                if campo in data and variant_data.get(campo) != data[campo]:
                    variant_data[campo] = data[campo]
                    changed = True

            if changed:
                with open(variant_path, 'w', encoding='utf-8') as f:
                    json.dump(variant_data, f, indent=2, ensure_ascii=False)
                _GAME_CONFIG_CACHE.pop(variant_path, None)
        except Exception as e:
            print(f"   [!] No se pudo sincronizar progreso en {variant_path}: {e}")

VERSION_PLAYER_INFO_THRESHOLD = (1, 2, 0)

def extract_version_from_swf(swf_version):
    if not swf_version:
        return None
    match = re.search(r'(\d+)\.(\d+)\.(\d+)', swf_version)
    if not match:
        return None
    return tuple(int(x) for x in match.groups())

def get_player_info_template_filename(swf_version):
    parsed = extract_version_from_swf(swf_version)
    if parsed and parsed > VERSION_PLAYER_INFO_THRESHOLD:
        candidate_path = os.path.join(SRV_DIR, 'get_player_info_1.2.0.json')
        if os.path.exists(candidate_path):
            return 'get_player_info_1.2.0.json'
    return 'get_player_info.json'

print("[+] Cargando configuración del juego (get_game_config.json)...")
_GAME_CONFIG_CACHE = {}

def load_game_config(user_id=None, language=None):
    if user_id:
        filename = resolve_user_config_filename(user_id, language)
        user_path = os.path.join(SRV_DIR, str(user_id), filename)
        path = user_path if os.path.exists(user_path) else os.path.join(SRV_DIR, filename)
    else:
        filename = get_config_filename_for_language(language)
        path = os.path.join(SRV_DIR, filename)

    cached = _GAME_CONFIG_CACHE.get(path)
    mtime = os.path.getmtime(path)

    if cached and cached['mtime'] == mtime:
        return cached['data']

    with open(path, 'r', encoding='utf-8') as f:
        data = json.loads(f.read())

    _GAME_CONFIG_CACHE[path] = {'data': data, 'mtime': mtime}
    return data

print("    -> Configuración cargada...")

def save_game_config(data, user_id, language=None):
    filename = resolve_user_config_filename(user_id, language)
    user_dir = os.path.join(SRV_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    path = os.path.join(user_dir, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    _GAME_CONFIG_CACHE.pop(path, None)
    sync_config_progress_across_languages(user_id, data, exclude_filename=filename)
    
print("[+] Preparando sistema de guardado y perfiles de jugador...")
def load_player(user_id, swf_version=None):
    user_dir  = os.path.join(SRV_DIR, str(user_id))
    user_file = os.path.join(user_dir, f"{user_id}.json")

    if not os.path.exists(user_file):
        os.makedirs(user_dir, exist_ok=True)

        for nombre in os.listdir(SRV_DIR):
            if nombre.startswith('get_game_config') and nombre.endswith('.json'):
                src = os.path.join(SRV_DIR, nombre)
                dst = os.path.join(user_dir, nombre)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)

        mark_user_config_migrated(user_id)
        
        for nombre in ['get_pvp_isle.json', 'pvp_players_info.json']:
            src = os.path.join(SRV_DIR, nombre)
            dst = os.path.join(user_dir, nombre)
            if os.path.exists(src):
                shutil.copy2(src, dst)

        template_filename = get_player_info_template_filename(swf_version)
        template_file = os.path.join(SRV_DIR, template_filename)

        if not os.path.exists(template_file):
            print(f"[!] ERROR CRÍTICO: No existe la plantilla en {template_file}")
            return {}
        with open(template_file, 'r', encoding='utf-8') as f:
            player_data = json.load(f)

        print(f"   [👤] Nuevo usuario {user_id} creado con plantilla: {template_filename} (swf_version={swf_version})")
    else:
        with open(user_file, 'r', encoding='utf-8') as f:
            player_data = json.load(f)

    player_data['timestamp'] = int(time.time())
    return player_data

def save_player(state, user_id):
    user_dir = os.path.join(SRV_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    path = os.path.join(user_dir, f"{user_id}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def level_from_xp(xp, dragon_type=None):
    if not xp or xp <= 0:
        return 1
    
    calculated_level = (xp // 4) + 1

    if calculated_level > 40:
        calculated_level = 40
        
    return int(calculated_level)

print("[+] Cargando pvp...")
def load_pvp_isle(user_id=None):
    if user_id:
        user_path = os.path.join(SRV_DIR, str(user_id), 'get_pvp_isle.json')
        path = user_path if os.path.exists(user_path) else os.path.join(SRV_DIR, 'get_pvp_isle.json')
    else:
        path = os.path.join(SRV_DIR, 'get_pvp_isle.json')

    if not os.path.exists(path):
        print(f"[!] ADVERTENCIA: No se encontró el archivo {path}.")
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.loads(f.read())

@app.route('/')
def serve_login():
    return send_from_directory(TEMPLATES_DIR, 'login.html')

@app.route('/index.html')
def serve_game():
    user_id = request.args.get('fb_sig_user')
    player_name = request.args.get('player_name')
    language = request.args.get('language')
    swf_version = request.args.get('swf_version')

    if user_id and player_name:
        player_data = load_player(user_id, swf_version)
        
        if 'playerInfo' in player_data:
            nombre_actual = player_data['playerInfo'].get('name', '')
            
            if not nombre_actual:
                player_data['playerInfo']['name'] = player_name
                player_data['playerInfo']['pid'] = user_id

                save_player(player_data, user_id)
                print(f"[+] Nuevo perfil creado desde URL -> PID: {user_id} | Nombre: {player_name}")

            resolve_user_config_filename(user_id, language)
    
    return send_from_directory(TEMPLATES_DIR, 'index.html')

@app.route('/<uid>/picture')
def fake_graph_picture(uid):
    with _avatar_lock:
        num = _avatar_queue.popleft() if _avatar_queue else random.randint(1, 307)

    filename = f"{num}.jpg"
    if not os.path.exists(os.path.join(PVP_AVATAR_DIR, filename)):
        filename = "1.jpg"

    response = send_from_directory(PVP_AVATAR_DIR, filename, mimetype='image/jpeg')
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response

@app.route('/i18n.js')
def serve_i18n():
    return send_from_directory(TEMPLATES_DIR, 'i18n.js')

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

    target_id = request.form.get('user') or request.args.get('user')
    is_visiting = bool(target_id and target_id not in ('0', '', user_id))
    if is_visiting:
        user_id = target_id

    print(f"\n>>> [PETICIÓN SRV] {filename} | USERID: {user_id}")

    if filename in ('get_game_config.json', 'get_game_config.php'):
        config_data = load_game_config(user_id)
        signed = sign_packet(config_data)
        response = app.response_class(
            response=signed,
            status=200,
            mimetype='text/plain'
        )
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        return response

    if filename in ('get_pvp_isle.json', 'get_pvp_isle.php', 'get_pvp_isle_info.php'):
        player_data = load_player(user_id)

        if 'level' in request.args:
            level = int(request.args.get('level'))
        else:
            level = player_data['playerInfo'].get('pvpLevel', 1)

        reset = request.args.get('reset') == '1' and filename != 'get_pvp_isle_info.php'

        page, changed = get_pvp_league_page(player_data, level, reset)
        if changed:
            save_player(player_data, user_id)

        if request.args.get('mapping') == '1':
            # Cliente nuevo: {"data": [...], "mapping": [...]}
            mapping = [
                {"user_id": str(o.get('id')), "linked_accounts": {}}
                for o in page
            ]
            body = {"data": page, "mapping": mapping}
            _queue_avatars_for_page(page)
            formato = "nuevo"
        else:
            # Cliente antiguo: lista plana
            body = page
            formato = "antiguo"

        print(f"   [PVP] Liga {level} | reset={reset} | {len(page)} rivales | formato {formato} | args={dict(request.args)}")

        signed = sign_packet(body)
        response = app.response_class(response=signed, status=200, mimetype='text/plain')
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        return response

    if filename in ('get_player_info.json', 'get_player_info.php'):
        player_data = load_player(user_id)

        if 'playerInfo' in player_data:
            if not player_data['playerInfo'].get('pid'):
                player_data['playerInfo']['pid'] = user_id
                
            if not is_visiting:
                game_config = load_game_config(user_id)
                current_ts = player_data.get('timestamp', int(time.time()))
                private_state = player_data.setdefault('privateState', {})

                if 'KompuEventType' not in private_state and player_data['playerInfo'].get('level', 0) >= 5:
                    bm_ts = private_state.get('BlackMarketTs', 0)
                    event_data = {
                        "gatillado": 0,
                        "type": 4,
                        "KompuEventStart": 0,
                        "KompuEventEnd": 0,
                        "halloweenPatchApplied": {
                            "HalloweenCompleted": [],
                            "halloweenNextWheel": 1790827200
                        }
                    }

                    if bm_ts == 0:
                        private_state['KompuEventType'] = event_data
                        player_data, game_config = decide_next_kompu_event(player_data, game_config, current_ts)
                        print(f"   [KOMPU] Usuario viejo migrado (nunca se disparó nada): {user_id}")
                    elif game_config.get('kompu_offers'):
                        event_data['KompuEventStart'] = int(private_state.get('BlackMarketStart', current_ts))
                        event_data['KompuEventEnd'] = event_data['KompuEventStart'] + 259200
                        private_state['KompuEventType'] = event_data
                        print(f"   [KOMPU] Usuario viejo migrado (mercado activo ahora): {user_id}")
                    else:
                        event_data['KompuEventStart'] = int(private_state.get('BlackMarketStart', 0))
                        event_data['KompuEventEnd'] = int(private_state.get('BlackMarketEnd', 0))
                        private_state['KompuEventType'] = event_data
                        print(f"   [KOMPU] Usuario viejo migrado (entre ciclos): {user_id}")

                player_data, game_config = check_and_update_kompu_event(player_data, user_id, game_config)
                player_data, game_config = process_island_events(player_data, game_config, user_id)
                save_player(player_data, user_id)
        signed = sign_packet(player_data)
        return signed, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    return jsonify({"result": "200"})

@app.route('/__utm.gif')
@app.route('/ga.js')
def serve_ga_stub():
    return PIXEL_GIF, 200, {'Content-Type': 'image/gif'}

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

@app.route('/static/dragoncity/deity_world/track/open', methods=['POST'])
@app.route('/static/dragoncity/deity_world/track/watch-tutorial', methods=['POST'])
def deity_world_track():
    return jsonify({"result": True}), 200

@app.route('/__shutdown', methods=['POST'])
def shutdown_server():
    if request.remote_addr != '127.0.0.1':
        return "", 403
    def _bye():
        time.sleep(0.3)
        try:
            remove_hosts()
        except Exception:
            pass
        os._exit(0)
    threading.Thread(target=_bye, daemon=True).start()
    return "", 200

print("[+] Analizando protocolo de comandos (packet.php)...")
print("    -> Se han identificado 104 comandos...")
print("    -> [ESTADO] Comandos implementados: 92/104 | Progreso:  88,4%")
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
            game_config = load_game_config(user_id)
            items_index = build_items_index(game_config)
            commands = payload.get('commands', [])

            response_results = []

            comandos_añadidos = ['buy','buy_egg','hatch_egg','feed_dragon','set_goals','complete_goal','breed_dragon','move','store_item','place_stored_egg','place_stored_dragon','dragonarium_place_stored','sell','sell_egg','sell_dragon','sell_stored_item','sell_stored_dragon','set_quality','orient','level_up','complete_tutorial','collect','expand_gold', 'expand_cash','activate','finish_building','upgrade','rename_dragon','speed_collect','speed_hatch','sync','ping','finish_breeding2','expand_island','move_dragon','buy_treasure_new','set_attack_team','deus_cards_generate','deus_cards_claim','begin_tournament','end_tournament','admin_speed_tournament','start_training','speed_training','finish_training','weekly_reward','place_stored_item','buy_treasure_popup','complete_collection','dragonarium_push','dragonarium_pull','dragonarium_add','dragonarium_hatch','set_help_map','attack_player','end_attack_f','assist_neighbor','clean_received_assists','assist_receive','kompu_boxes_new_list','kompu_boxes_open_box','kompu_boxes_claim_prize','collect_game_add_item','collect_game_add_items_container','lost_item_found','collect_game_begin_attack','collect_game_end_attack','spinning_try','spin_hallo_wheel','kompu_hurry_up','breeding_sanctuary_activate','breeding_sanctuary_buy_step','breeding_sanctuary_upgrade','change_world','deity_world_mine_start_production','deity_world_mine_collect_speed_up','deity_world_mine_collect','deity_world_building_upgrade','deity_world_building_upgrade_finish','deity_world_building_upgrade_speed_up','deity_world_summoning_start','deity_world_summoning_place_dragon','deity_world_habitat_collect','deity_world_craft','deity_world_craft_filling_with_gems','deity_world_fusion','deity_world_breeding_start','deity_world_breeding_speed_up','deity_world_breeding_finish','IslandTournamentStartBattle','IslandTournamentEndBattle','combat_leagues_initialize','combat_leagues_start_combat']
            nombres_dragon = ["Roxy", "Horacio", "Sergi", "Kasia", "Xavi", "Draco", "Ignis", "Gabriel", "Abdona", "Adolfina", "Agripina", "Aleja", "Altagracia", "Amadora", "Amelia", "Anatolia", "Aniceta", "Antolina", "Apolonia", "Arcadia", "Argimira", "Atanasia", "Áurea", "Balbina", "Baltasara", "Basilisa", "Bercia", "Bernabea", "Bernarda", "Blacina", "Blasina", "Brígida", "Bonifacia", "Calista", "Casilda", "Castora", "Cayetana", "Celedonia", "Celestina", "Celina", "Cesárea", "Clementa", "Crisanta", "Crisóstoma", "Críspula", "Cristeta", "Dámasa", "Demetria", "Diega", "Dionisia", "Dominga", "Dominica", "Dorotea", "Dosinda", "Edelmira", "Edicta", "Eduvigis", "Efigenia", "Eleuteria", "Elicia", "Emerenciana", "Emeteria", "Ermisinda", "Escolástica", "Esmaragda", "Esmerencia", "Estanislá", "Etelvina", "Eudosia", "Eulogia", "Eustaquia", "Ezequiela", "Evarista", "Facunda", "Fausta", "Felicia", "Felisa", "Feliciana", "Froilana", "Fulgencia", "Gaspara", "Gelsumina", "Genoveva", "Getrudis", "Gertrudis", "Gervasia", "Gliceria", "Gracia", "Graciana", "Gregoria", "Guillerma", "Gumersinda", "Felicia", "Fidela", "Froilana", "Hermelinda", "Herminia", "Hilaria", "Humildad", "Indalecia", "Ilora", "Isidora", "Isidra", "Jacoba", "Jerónima", "Jesusa", "Jorja", "Juliana", "Laureana", "Leocadia", "Leoncia", "Liberata", "Librada", "Lopa", "Lorenza", "Luciana", "Lucrecia", "Mamesa", "Marciala", "Marciana", "Matea", "Matiasa", "Máxima", "Melchora", "Melitona", "Micaela", "Miguela", "Montserrate", "Nazaria", "Nemesia", "Nestora", "Nicanora", "Nicasia", "Jacinta", "Jesusa", "Olalla", "Olaya", "Orosia", "Parda", "Paspasia", "Patrocinia", "Peregrina", "Perpétua", "Petra", "Petrola", "Petrona", "Petronila", "Pia", "Polonia", "Pomposa", "Potencia", "Práxedes", "Preciosa", "Prisca", "Priscila", "Quintina", "Quiteria", "Ramira", "Reparada", "Ricarda", "Romualda", "Rudesinda", "Rufa", "Rufina", "Salvadora", "Sancia", "Sandalia", "Santas", "Santiaga", "Saturia", "Saturnina", "Sebastiana", "Segunda", "Semproniana", "Serapia", "Sergia", "Silvestra", "Simeona", "Simona", "Socorro", "Sotera", "Teodomira", "Teodora", "Teodosia", "Tiburcia", "Tomasa", "Toribia", "Úrsula", "Abundio", "Acacio", "Agapito", "Amalio", "Ambrosio", "Aniceto", "Anselmo", "Apolonio", "Aquilino", "Argimiro", "Arquimimo", "Arsenio", "Ascensio", "Asterio", "Atanasio", "Atilano", "Áureo", "Avelino", "Bartolo", "Basilio", "Baudilio", "Belarmino", "Benigno", "Bonifacio", "Buenaventura", "Calisto", "Calixto", "Casiano", "Casildo", "Castiano", "Casimiro", "Cecilio", "Celdonio", "Celedonio", "Cesáreo", "Cipriaco", "Cipriano", "Cipriniano", "Ciriaco", "Cirilo", "Clemente", "Cleto", "Columbano", "Conrado", "Crescencio", "Crisóstomo", "Crispín", "Críspulo", "Cruz", "Deogracias", "Dionisio", "Domiciano", "Doroteo", "Eleuterio", "Eliodoro", "Eliseo", "Emerico", "Emeterio", "Emmanuel", "Epafrodito", "Epifanio", "Escolástico", "Estanislao", "Eufrasio", "Eulogio", "Evelio", "Fabriciano", "Faustina", "Feliciano", "Florencio", "Floro", "Froilán", "Fructuoso", "Frutos", "Fulgencio", "Gregorio", "Guadalupe", "Gumersindo", "Helimenas", "Hermenegildo", "Herminio", "Hermógenes", "Higinio", "Hilario", "Hilarión", "Hipólito", "Indalecio", "Inocente", "Isabelo", "Isidoro", "Juvernón", "Laureano", "Leandro", "Leocadio", "León", "Leovigildo", "Lesmes", "Lisardo", "Lope", "Lupicinio", "Macabeo", "Macario", "Macedonio", "Margarito", "Magin", "Mauro", "Maximino", "Medardo", "Melitón", "Minervino", "Minervo", "Natalio", "Nemesio", "Nicanor", "Niceto", "Nicomedes", "Norberto", "Odón", "Orencio", "Pantaleón", "Paulilo", "Paulino", "Patricio", "Perfecto", "Petrolino", "Petronilo", "Pío", "Policarpo", "Polonio", "Pomposo", "Ponciano", "Primitivo", "Protasio", "Prudencio", "Regino", "Remigio", "Restituto", "Rinaldo", "Robustiano", "Romualdo", "Rómulo", "Rosalino", "Ruperto", "Rufino", "Rufo", "Sabas", "Sabiniano", "Salvio", "Sandalio", "Saturio", "Saturnino", "Serapio", "Servando", "Serbando", "Severo", "Silverio", "Silvestre", "Silvio", "Simeón", "Sinforosio", "Sinforoso", "Sofío", "Sofronio", "Sotero", "Teódulo", "Telesforo", "Teopisto", "Tereso", "Tiburcio", "Timoteo", "Toribio", "Trifón", "Trinitario", "Ulpiano", "Valeriano", "Venancio", "Victoriano", "Zoilo"]

            comando_valido_procesado = False
            comandos_ignorados = []

            for cmd_data in commands:
                cmd = cmd_data.get('cmd')
                cmd_number = cmd_data.get('number')
                args = cmd_data.get('args', [])

                cmd_result = "ok"

                print(f"-> Comando: {cmd} | Args: {args} | N: {cmd_number}")

                try:
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
                        
                        item_cfg = items_index.get(str(item_id))
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
                            print(f"            Oro restante: {player_data['playerInfo']['gold']} | Gemas: {player_data['playerInfo']['cash']} | XP: {player_data['playerInfo']['xp']}")
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
                            print(f"                Oro: {player_data['playerInfo']['gold']} | Gemas: {player_data['playerInfo']['cash']} | XP: {player_data['playerInfo']['xp']}")
                        else:
                            print(f"   [!] Error: El dragón con ID {dragon_id} no existe en get_game_config.json")
                            
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
                                print(f"                  XP ganado: {hatch_xp} | XP total: {player_data['playerInfo']['xp']}")
                                print(f"                  Dragón {dragon_name} (Tipo: {dragon_type_id}) añadido al Libro de Dragones")
                            else:
                                print(f"   [!] Error: Configuración para el dragón {dragon_type_id} no encontrada en game_config.")
                        else:
                            print(f"   [!] Error: No se encontró un huevo con UID {egg_uid} en la incubadora.")

                    elif cmd == 'feed_dragon':
                        dragon_uid = args[0]

                        dragon_found = False
                        if 'dragons' in player_data['map']:
                            for dragon in player_data['map']['dragons']:
                                if str(dragon.get('id')) == str(dragon_uid):
                                    dragon_found = True
                                    current_xp = dragon.get('xp', 0)
                                    current_level = (current_xp // 4) + 1

                                    feed_costs_cfg = game_config.get('dragon_feed_costs', [])
                                    cost_entry = next((c for c in feed_costs_cfg if c.get('level') == current_level), None)

                                    if not cost_entry:
                                        print(f"   [!] Aviso: El dragón {dragon_uid} ya alcanzó el nivel máximo registrado en 'dragon_feed_costs' (nivel {current_level}).")
                                        break

                                    food_cost = cost_entry.get('food', 0)

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
                                        print(f"                    XP Dragón subió a: {dragon['xp']} | Costo: {food_cost} | Comida restante: {player_data['playerInfo']['food']}")
                                    else:
                                        print(f"   [!] Error: No hay suficiente comida ({food_cost} requerida) para alimentar al dragón {dragon_uid}.")

                                    break

                        if not dragon_found:
                            print(f"   [!] Error: Dragón con UID {dragon_uid} no encontrado en el mapa.")

                    elif cmd == 'set_goals':
                        goal_id = int(args[0])
                        goal_state = json.loads(args[1])

                        if 'goals' not in player_data['privateState']:
                            player_data['privateState']['goals'] = [None] * 170

                        while len(player_data['privateState']['goals']) <= goal_id:
                            player_data['privateState']['goals'].append(None)
                            
                        player_data['privateState']['goals'][goal_id] = goal_state
                        
                        print(f"   [SET_GOALS OK] Goal ID {goal_id} establecido a estado {goal_state}")
                    
                    elif cmd == 'complete_goal':
                        goal_id = int(args[0])
                        goal_config = game_config.get('goals', {}).get(str(goal_id))
                        puntos = 35
                        
                        if goal_config:
                            reward = goal_config.get('reward', {})

                            gold_reward = reward.get('g', 0)
                            food_reward = reward.get('f', 0)
                            cash_reward = reward.get('c', 0)
                            xp_reward = reward.get('x', 0)
                            gold_reward = reward.get('g', 0)

                            if gold_reward > 0:
                                player_data['playerInfo']['gold'] += gold_reward
                            if food_reward > 0:
                                player_data['playerInfo']['food'] += food_reward
                            if cash_reward > 0:
                                player_data['playerInfo']['cash'] += cash_reward
                            if xp_reward > 0:
                                player_data['playerInfo']['xp'] += xp_reward
                                
                            player_data['privateState']['achievement_points'] += puntos
                            
                                                    
                            print(f"   [COMPLETE_GOAL OK] Goal ID {goal_id} completado!")
                            print(f"                      Recompensas: Gold +{gold_reward} | Food +{food_reward} | XP +{xp_reward} | Puntos +{puntos}")
                            print(f"                      Totales: Oro: {player_data['playerInfo']['gold']} | Comida: {player_data['playerInfo']['food']} | XP: {player_data['playerInfo']['xp']} | Puntos: {player_data['privateState']['achievement_points']}")
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
                                print("[!] Gemas insuficientes para Boost.")

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

                        sanctuary_dragons = set()
                        if iso_id == "152":
                            sanctuary = player_data.get('privateState', {}).get('breedingSanctuary')
                            if sanctuary and sanctuary.get('activated', 0) == 1:
                                sanctuary_level = sanctuary.get('level', 1)
                                upgrades_cfg = game_config.get('sanctuary_breeding', {}).get('upgrades_config', [])
                                for lvl_cfg in upgrades_cfg:
                                    if lvl_cfg.get('id', 999) <= sanctuary_level:
                                        sanctuary_dragons.update(lvl_cfg.get('dragons_unlocked', []))
                                print(f"   [SANTUARIO] Cría en Santuario (nivel {sanctuary_level}) | Dragones exclusivos disponibles: {sanctuary_dragons}")

                        if dragon1_type and dragon2_type:
                            outcome_id = get_breed_result(dragon1_type, dragon2_type, dragon1_level, dragon2_level, dragon_db, boosted, sanctuary_dragons)
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

                    elif cmd == 'place_stored_egg':
                        egg_uid = args[0]
                        dragon_id = args[1]
                        is_gift = int(args[2])

                        item_cfg = get_item_config(game_config, dragon_id)
                        
                        if item_cfg:
                            removed = False
                            list_name = ""

                            if is_gift == 1:
                                if 'privateState' in player_data and 'giftsi' in player_data['privateState']:
                                    gifts_list = player_data['privateState']['gifts']
                                    list_name = "regalos (gifts)"
                                    
                                    for i, gift in enumerate(gifts_list):
                                        if gift.get('iid') == dragon_id or gift.get('type') == dragon_id:
                                            gifts_list.pop(i)
                                            removed = True
                                            break
                            else:
                                if 'store' in player_data.get('map', {}):
                                    if 'dragons' in player_data['map']['store']:
                                        store_dragons = player_data['map']['store']['dragons']
                                        for i, d in enumerate(store_dragons):
                                            if d.get('iid') == dragon_id:
                                                store_dragons.pop(i)
                                                removed = True
                                                list_name = "almacén (store -> dragons)"
                                                break

                                    if not removed and 'items' in player_data['map']['store']:
                                        store_items = player_data['map']['store']['items']
                                        str_dragon_id = str(dragon_id)
                                        
                                        if str_dragon_id in store_items:
                                            if store_items[str_dragon_id] > 1:
                                                store_items[str_dragon_id] -= 1
                                            else:
                                                del store_items[str_dragon_id]
                                            removed = True
                                            list_name = "almacén (store -> items)"

                            if removed:
                                print(f"   [PLACE_STORED_EGG OK] Huevo de {item_cfg.get('name', dragon_id)} retirado exitosamente de {list_name}.")
                                
                                new_egg = {
                                    "id": egg_uid,
                                    "type": dragon_id,
                                    "name": random.choice(nombres_dragon),
                                    "xp": 0,
                                    "hatched": False,
                                    "ts": int(time.time())
                                }
                                
                                player_data['map']['eggs'].append(new_egg)
                                print(f"   [PLACE_STORED_EGG] Huevo {egg_uid} ({item_cfg.get('name', dragon_id)}) colocado en la torre de incubación.")
                            else:
                                print(f"   [!] Error: El huevo {dragon_id} no se encontró en el almacén. Se aborta la incubación para evitar duplicidad.")
                        else:
                            print(f"   [!] Error: El dragón con ID {dragon_id} no existe en el catálogo get_game_config.json")

                    elif cmd == 'place_stored_dragon':
                        dragon_uid = args[0]
                        habitat_uid = str(args[1])
                        dragon_name = args[2]
                        dragon_type_id = int(args[3])
                        dragon_lvl = int(args[4])
                        is_gift = int(args[5])

                        dragon_xp = 4 * dragon_lvl - 4

                        item_cfg = get_item_config(game_config, dragon_type_id)
                        
                        if item_cfg:
                            removed = False
                            list_name = ""
                            
                            if is_gift == 1:
                                gifts_node = None
                                if 'gifts' in player_data:
                                    gifts_node = player_data['gifts']
                                elif 'privateState' in player_data and 'gifts' in player_data['privateState']:
                                    gifts_node = player_data['privateState']['gifts']
                                elif 'map' in player_data and 'gifts' in player_data['map']:
                                    gifts_node = player_data['map']['gifts']

                                if gifts_node and 'dragons' in gifts_node:
                                    target_list = gifts_node['dragons']
                                    list_name = "regalos (gifts -> dragons)"
                                    
                                    for i, gift in enumerate(target_list):
                                        if isinstance(gift, dict):
                                            if gift.get('iid') == dragon_type_id or gift.get('type') == dragon_type_id:
                                                target_list.pop(i)
                                                removed = True
                                                break
                                            
                                        elif isinstance(gift, (str, int)):
                                            if str(gift) == str(dragon_type_id):
                                                target_list.pop(i)
                                                removed = True
                                                break
                            else:
                                if 'store' in player_data.get('map', {}) and 'dragons' in player_data['map']['store']:
                                    target_list = player_data['map']['store']['dragons']
                                    list_name = "almacén (store -> dragons)"
                                    
                                    for i, stored_dragon in enumerate(target_list):
                                        if isinstance(stored_dragon, dict):
                                            if stored_dragon.get('iid') == dragon_type_id:
                                                target_list.pop(i)
                                                removed = True
                                                break
                                        elif isinstance(stored_dragon, (str, int)):
                                            if str(stored_dragon) == str(dragon_type_id):
                                                target_list.pop(i)
                                                removed = True
                                                break
                                            
                            if removed:
                                print(f"   [PLACE_STORED_DRAGON] Dragón tipo {dragon_type_id} retirado exitosamente de {list_name}.")
                            else:
                                print(f"   [~] Aviso: El dragón tipo {dragon_type_id} no se encontró en {list_name}, pero se intentará colocar.")

                            current_ts = player_data.get('timestamp', int(time.time()))
                            
                            if habitat_uid in player_data['map']['items']:
                                item_data = player_data['map']['items'][habitat_uid]
                                if len(item_data) > 6 and isinstance(item_data[6], dict):
                                    if 'ar' in item_data[6]:
                                        item_data[6]['lat'] = current_ts
                                        del item_data[6]['ar']
                                        print(f"   [FINISH] Propiedad 'ar' eliminada del iso_id {habitat_uid}")
                                        print(f"   [FINISH] Propiedad 'lat' actualizada a la hora {current_ts}")

                            attacks = item_cfg.get('attacks', [])
                            
                            new_dragon = {
                                "id": dragon_uid,
                                "type": dragon_type_id,
                                "xp": dragon_xp,
                                "habitatId": habitat_uid,
                                "name": dragon_name,
                                "ts": current_ts,
                                "work_id": [],
                                "nbKill": 0,
                                "attack": attacks
                            }
                            
                            player_data['map']['dragons'].append(new_dragon)

                            id_str = str(dragon_type_id)
                            if id_str not in player_data['map']['ownedDragons']:
                                if dragon_xp >= 24:
                                    player_data['map']['ownedDragons'][id_str] = [1, 2, 3]
                                elif dragon_xp >= 12:
                                    player_data['map']['ownedDragons'][id_str] = [1, 2, 0]
                                else:
                                    player_data['map']['ownedDragons'][id_str] = [1, 0, 0]
                            
                            print(f"   [PLACE_STORED_DRAGON OK] Dragón {dragon_name} (Tipo: {dragon_type_id}) colocado en el hábitat {habitat_uid} con XP/Lvl: {dragon_xp}.")
                        else:
                            print(f"   [!] Error: El dragón con ID {dragon_type_id} no existe en el catálogo get_game_config.json")

                    elif cmd == 'dragonarium_place_stored':
                        dragon_name = args[0]
                        dragon_type_id = int(args[1])
                        dragon_lvl = int(args[2])
                        is_gift = int(args[3])

                        dragon_uid = int(time.time() * 1000)
                        dragon_xp = 4 * dragon_lvl - 4
                        
                        item_cfg = get_item_config(game_config, dragon_type_id)
                        
                        if item_cfg:
                            removed = False
                            list_name = ""
                            
                            if is_gift == 1:
                                gifts_node = None
                                if 'gifts' in player_data:
                                    gifts_node = player_data['gifts']
                                elif 'privateState' in player_data and 'gifts' in player_data['privateState']:
                                    gifts_node = player_data['privateState']['gifts']
                                elif 'map' in player_data and 'gifts' in player_data['map']:
                                    gifts_node = player_data['map']['gifts']

                                if gifts_node and 'dragons' in gifts_node:
                                    target_list = gifts_node['dragons']
                                    list_name = "regalos (gifts -> dragons)"
                                    
                                    for i, gift in enumerate(target_list):
                                        if isinstance(gift, dict):
                                            if gift.get('iid') == dragon_type_id or gift.get('type') == dragon_type_id:
                                                target_list.pop(i)
                                                removed = True
                                                break
                                            
                                        elif isinstance(gift, (str, int)):
                                            if str(gift) == str(dragon_type_id):
                                                target_list.pop(i)
                                                removed = True
                                                break
                            else:
                                if 'store' in player_data.get('map', {}) and 'dragons' in player_data['map']['store']:
                                    target_list = player_data['map']['store']['dragons']
                                    list_name = "almacén (store -> dragons)"
                                    
                                    for i, stored_dragon in enumerate(target_list):
                                        if isinstance(stored_dragon, dict):
                                            if stored_dragon.get('iid') == dragon_type_id:
                                                target_list.pop(i)
                                                removed = True
                                                break
                                        elif isinstance(stored_dragon, (str, int)):
                                            if str(stored_dragon) == str(dragon_type_id):
                                                target_list.pop(i)
                                                removed = True
                                                break
                                            
                            if removed:
                                print(f"   [DRAGONARIUM_PLACE_STORED] Dragón tipo {dragon_type_id} ({dragon_name}) consumido exitosamente de {list_name}.")
                            else:
                                print(f"   [~] Aviso: El dragón tipo {dragon_type_id} no se encontró en {list_name}, procediendo a forzar la creación.")

                            category_index = 0
                            attributes = item_cfg.get('attributes', [])

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

                            current_ts = player_data.get('timestamp', int(time.time()))
                            attacks = item_cfg.get('attacks', [])
                            
                            new_dragon = {
                                "id": dragon_uid,
                                "type": dragon_type_id,
                                "xp": dragon_xp,
                                "habitatId": 0,
                                "name": dragon_name,
                                "ts": current_ts,
                                "work_id": [],
                                "nbKill": 0,
                                "attack": attacks
                            }

                            player_data['privateState']['dragonarium'][category_index].append(new_dragon)

                            id_str = str(dragon_type_id)
                            if id_str not in player_data['map']['ownedDragons']:
                                if dragon_xp >= 24:
                                    player_data['map']['ownedDragons'][id_str] = [1, 2, 3]
                                elif dragon_xp >= 12:
                                    player_data['map']['ownedDragons'][id_str] = [1, 2, 0]
                                else:
                                    player_data['map']['ownedDragons'][id_str] = [1, 0, 0]
                            
                            print(f"   [DRAGONARIUM_PLACE_STORED OK] '{dragon_name}' (Tipo: {dragon_type_id}) almacenado en Dragonarium (Pestaña: {category_index}). UID Asignado: {dragon_uid}")
                        else:
                            print(f"   [!] Error Crítico: El dragón con ID {dragon_type_id} no existe en el catálogo get_game_config.json y la petición fue descartada.")
                            
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
                            
                    elif cmd == 'sell_stored_item':
                        item_id_to_sell = str(args[0])
                        item_cfg = get_item_config(game_config, item_id_to_sell)
                        
                        if item_cfg:
                            sell_price = item_cfg.get('sell_price', {}).get('g', 0)

                            if 'store' in player_data['map'] and 'items' in player_data['map']['store']:
                                store_items = player_data['map']['store']['items']

                                if item_id_to_sell in store_items:
                                    cantidad_actual = store_items[item_id_to_sell]

                                    if cantidad_actual > 1:
                                        store_items[item_id_to_sell] -= 1
                                        print(f"   [SELL_STORE_ITEM OK] Item {item_cfg.get('name', item_id_to_sell)} vendido. Restan: {store_items[item_id_to_sell]}")
                                    else:
                                        del store_items[item_id_to_sell]
                                        print(f"   [SELL_STORE_ITEM OK] Item {item_cfg.get('name', item_id_to_sell)} vendido. Última unidad eliminada del inventario.")

                                    player_data['playerInfo']['gold'] += sell_price
                                    print(f"   [-] Oro añadido: +{sell_price} | Nuevo saldo: {player_data['playerInfo']['gold']}")
                                    
                                else:
                                    print(f"   [!] Comando sell_stored_item fallido: El jugador no tiene el item {item_id_to_sell} en su inventario.")
                            else:
                                print(f"   [!] Comando sell_stored_item fallido: El perfil del jugador no tiene la clave ['map']['store']['items'].")
                        else:
                            print(f"   [!] Error: El objeto con ID {item_id_to_sell} no existe en el catálogo get_game_config.json")

                    elif cmd == 'sell_stored_dragon':
                        dragon_id = int(args[0])
                        dragon_lvl = int(args[1])
                        is_gift = int(args[2])

                        item_cfg = get_item_config(game_config, dragon_id)
                        
                        if item_cfg:
                            sell_price = item_cfg.get('sell_price', {}).get('g', 0)
                            
                            target_list = None
                            list_name = ""

                            if is_gift == 1:
                                if 'privateState' in player_data and 'gifts' in player_data['privateState']:
                                    target_list = player_data['privateState']['gifts']
                                    list_name = "regalos (gifts)"
                            else:
                                if 'store' in player_data.get('map', {}) and 'dragons' in player_data['map']['store']:
                                    target_list = player_data['map']['store']['dragons']
                                    list_name = "almacén (store)"
                                    
                            if target_list is not None:
                                index_to_remove = -1

                                for i, d in enumerate(target_list):
                                    if d.get('iid') == dragon_id and d.get('lvl') == dragon_lvl:
                                        index_to_remove = i
                                        break
                                    
                                if index_to_remove != -1:
                                    target_list.pop(index_to_remove)
                                    player_data['playerInfo']['gold'] += sell_price
                                    
                                    print(f"   [SELL_STORE_DRAGON OK] Dragón {item_cfg.get('name', dragon_id)} (Lvl {dragon_lvl}) vendido desde {list_name}.")
                                    print(f"                          Oro añadido: +{sell_price} | Nuevo saldo: {player_data['playerInfo']['gold']}")
                                else:
                                    print(f"   [!] Comando sell_stored_dragon fallido: Dragón {dragon_id} nivel {dragon_lvl} no encontrado en {list_name}.")
                            else:
                                print(f"   [!] Comando sell_stored_dragon fallido: La lista destino (is_gift={is_gift}) no existe en el perfil del jugador.")
                        else:
                            print(f"   [!] Error: El dragón con ID {dragon_id} no existe en el catálogo get_game_config.json")
                    
                    elif cmd == 'set_quality':
                        quality = args[0]
                        
                        player_data['privateState']['quality'] = quality
                        print(f"   [SET_QUALITY OK] se establecieron los graficos a {quality}")

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

                        if new_level >= 5 and 'KompuEventType' not in player_data['privateState']:
                            current_ts = player_data.get('timestamp', int(time.time()))
                            player_data['privateState']['KompuEventType'] = {
                                "gatillado": 1,
                                "type": 0,
                                "KompuEventStart": 0,
                                "KompuEventEnd": 0,
                                "halloweenPatchApplied": {
                                    "HalloweenCompleted": [],
                                    "halloweenNextWheel": 1790827200
                                }
                            }
                            player_data, game_config = decide_next_kompu_event(player_data, game_config, current_ts)
                            print(f"   [KOMPU] Gatillo Nivel 5 Activado (nuevo usuario).")

                    elif cmd == 'complete_tutorial':
                        tutorial_value = args[0]

                        player_data['playerInfo']['completed_tutorial'] = str(tutorial_value)
                        
                        print(f"   [COMPLETE_TUTORIAL OK] Tutorial marcado como completado.")
                        

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

                            print(f"                Estado actual -> Oro: {player_data['playerInfo']['gold']} | Comida: {player_data['playerInfo']['food']} | XP: {player_data['playerInfo']['xp']}")
                        
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
                                    print(f"   [RENAME_DRAGON OK] Dragón {dragon_id} renombrado exitosamente a: {nuevo_nombre}")
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
                                        print(f"                      Gemas restantes: {player_data['playerInfo']['cash']}")
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
                                        print(f"                    Gemas restantes: {player_data['playerInfo']['cash']}")
                                    else:
                                        print(f"[!] Sin gemas suficientes para speed_hatch en huevo {egg_id}")
                                else:
                                    print(f"[!] No se encontró la configuración para el dragón tipo {dragon_type}")
                            else:
                                print(f"[!] Huevo con ID {egg_id} no encontrado en el mapa.")

                    elif cmd == 'sync':
                        random_ping = args[0] if len(args) > 0 else "Desconocido"
                        
                        print(f"   [SYNC OK] Ping de sincronización recibido (Hash: {random_ping}).")
                        print(f"             Todo en orden. Devolviendo estado actual al cliente.")

                    elif cmd == 'ping':
                        print(f"   [PING OK] Señal de actividad (keep-alive) recibida del cliente.")

                    elif cmd == 'speed_breeding':
                        work_id = str(args[0])

                        work_dict = player_data.get('map', {}).get('work', {})

                        if work_id in work_dict:
                            work_data = work_dict[work_id]

                            dragon_type = str(work_data[4])

                            all_items = game_config.get('items', [])
                            if isinstance(all_items, dict):
                                dragon_conf = all_items.get(dragon_type)
                            else:
                                dragon_conf = next((i for i in all_items if str(i.get('id')) == dragon_type), None)

                            if dragon_conf:
                                breeding_time = int(dragon_conf.get('breeding_time', 0))
                                start_time = int(work_data[2])
                                current_ts = int(time.time())

                                elapsed_time = current_ts - start_time
                                time_remaining = max(0, breeding_time - elapsed_time)

                                gems_cost = max(1, (time_remaining + 3599) // 3600)

                                if player_data['playerInfo']['cash'] >= gems_cost:
                                    player_data['playerInfo']['cash'] -= gems_cost
                                    work_data[2] = current_ts - breeding_time

                                    comando_valido_procesado = True
                                    cmd_result = "ok"

                                    print(f"   [SPEED_BREEDING OK] se acelero el apareamiento. Costo: {gems_cost} gemas.")
                                    print(f"                       Gemas restantes: {player_data['playerInfo']['cash']}")
                                else:
                                    print(f"[!] Sin gemas suficientes para speed_breeding en work {work_id}")
                            else:
                                print(f"[!] No se encontró la configuración para el dragón tipo {dragon_type}")
                        else:
                            print(f"[!] No se encontró el work con ID {work_id}")
                                
                    elif cmd == 'finish_breeding2':
                        breeding_iso_id = str(args[0])
                        new_egg_uid = args[1]
                        hatchery_iso_id = str(args[2])
                        
                        work_data = player_data.get('map', {}).get('work', {}).get(breeding_iso_id)
                        
                        if work_data:
                            dragon_id = work_data[4]
                            
                            if 'eggs' not in player_data['map']:
                                player_data['map']['eggs'] = []
                            
                            new_egg = {
                                "id": new_egg_uid,
                                "type": dragon_id,
                                "name": random.choice(nombres_dragon),
                                "xp": 0,
                                "ts": int(time.time())
                            }
                            
                            player_data['map']['eggs'].append(new_egg)
                            
                            if len(work_data) >= 5:
                                active_games = game_config.get('collect_game', [])
                                if active_games:
                                    cg_cfg = active_games[0]
                                    island_type = cg_cfg.get('game_data', {}).get('islandType', 0)

                                    if island_type == 0:
                                        dragon_cfg = next((it for it in game_config.get('items', [])
                                                            if it.get('id') == dragon_id), None)
                                        if dragon_cfg:
                                            breeding_time = dragon_cfg.get('breeding_time', 0)
                                            minutes = breeding_time // 60
                                            if minutes > 0:
                                                breed_item = next((it for it in game_config.get('collect_game_items', [])
                                                                    if it.get('collect_game_id') == cg_cfg.get('id')
                                                                    and it.get('action') == 'GET FROM BREEDING'), None)
                                                if breed_item:
                                                    add_collect_game_item_progress(game_config, player_data, breed_item['type'], amount=minutes)
                            
                            del player_data['map']['work'][breeding_iso_id]

                            if breeding_iso_id in player_data['map'].get('items', {}):
                                player_data['map']['items'][breeding_iso_id][3] = 0

                            print(f"   [FINISH_BREEDING2 OK] En {breeding_iso_id}")
                            print(f"                         Huevo creado: {dragon_id} (UID: {new_egg_uid}) movido a Hatchery {hatchery_iso_id}")
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
                                print(f"                      Costo cobrado (Índice {cost_index}): {cost_obj}")
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
                                    print(f"                    Movido del habitat {old_habitat} al habitat {new_habitat_id}")
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
                                print(f"                         Costo: {price} gemas | Recompensa: +{amount} {res_type}.")
                                print(f"                         Gemas restantes: {player_data['playerInfo']['cash']}")
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
                        dragon_card_prizes = game_config.get('dragon_card_prizes', [])

                        if not dragon_card_prizes:
                            print(f"   [!] Error: 'dragon_card_prizes' no está definido en game_config.")
                        else:
                            is_paid = int(args[0]) if len(args) > 0 else 0
                            is_super = int(args[1]) if len(args) > 1 else 0

                            if is_super == 1:
                                cost = game_config.get('globals', {}).get('DRAGON_CARDS_SUPER_TRY', {}).get('value', 10)
                                player_data['playerInfo']['cash'] = max(0, player_data['playerInfo']['cash'] - cost)
                            elif is_paid == 1:
                                cost = game_config.get('globals', {}).get('DRAGON_CARDS_TRY', {}).get('value', 3)
                                player_data['playerInfo']['cash'] = max(0, player_data['playerInfo']['cash'] - cost)

                            weights = [p.get('price', 1) for p in dragon_card_prizes]
                            prize_id = random.choices(range(len(dragon_card_prizes)), weights=weights, k=1)[0]

                            if 'deus_cards' not in player_data['privateState']:
                                player_data['privateState']['deus_cards'] = {}

                            player_data['privateState']['deus_cards']['pending_prize'] = prize_id
                            player_data['privateState']['deus_cards']['reward'] = prize_id
                            player_data['privateState']['deus_cards']['charge'] = bool(is_paid or is_super)

                            cmd_result = prize_id
                            print(f"   [DEUS_CARDS_GENERATE OK] Tirada generada. Índice: {prize_id} | Reward: {dragon_card_prizes[prize_id].get('reward')}")
                        
                    elif cmd == 'deus_cards_claim':
                        dragon_card_prizes = game_config.get('dragon_card_prizes', [])
                        current_time = int(time.time())
                        deus_cards_state = player_data['privateState'].get('deus_cards', {})
                        prize_id = deus_cards_state.get('reward')

                        if prize_id is None or not (0 <= prize_id < len(dragon_card_prizes)):
                            print(f"   [!] Error: No hay premio pendiente valido para reclamar (index: {prize_id}).")
                        else:
                            prize_cfg = dragon_card_prizes[prize_id]
                            reward = prize_cfg.get('reward')

                            if isinstance(reward, dict):
                                gold_reward = reward.get('g', 0)
                                food_reward = reward.get('f', 0)
                                cash_reward = reward.get('c', 0)

                                player_data['playerInfo']['gold'] += gold_reward
                                player_data['playerInfo']['food'] += food_reward
                                player_data['playerInfo']['cash'] += cash_reward

                                print(f"   [DEUS_CARDS_CLAIM OK] Premio reclamado: Oro +{gold_reward} | Comida +{food_reward} | Gemas +{cash_reward}")

                            elif isinstance(reward, int):
                                if 'store' not in player_data['map']:
                                    player_data['map']['store'] = {}
                                if 'dragons' not in player_data['map']['store']:
                                    player_data['map']['store']['dragons'] = []

                                player_data['map']['store']['dragons'].append({
                                    "iid": reward,
                                    "lvl": 0
                                })
                                print(f"   [DEUS_CARDS_CLAIM OK] Premio reclamado: Dragón tipo {reward} añadido a store.dragons.")

                            elif reward == "retry":
                                print("   [DEUS_CARDS_CLAIM OK] Premio: Retry (tirada extra gratis, sin recompensa material)")

                            was_charged = deus_cards_state.get('charge', False)
                            if reward != "retry" and not was_charged:
                                player_data['privateState']['deus_cards']['lastFreeTry'] = current_time
                                player_data['privateState']['deusCardsLastTimestamp'] = current_time

                            player_data['privateState']['deus_cards']['reward'] = None
                            player_data['privateState']['deus_cards']['charge'] = False
                        
                    elif cmd == 'begin_tournament':
                        current_ts = int(time.time())
                        player_data['privateState']['beginTournamentTs'] = current_ts
                        
                        print(f"   [BEGIN_TOURNAMENT OK] Torneo iniciado. Timestamp guardado: {current_ts}")

                    elif cmd == 'end_tournament':
                        player_won = str(args[0]) == "1"
                        kills_log = json.loads(args[1]) if len(args) > 1 else {}
                        puntos = 50
                        
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
                                player_data['privateState']['achievement_points'] += puntos

                                active_games = game_config.get('collect_game', [])
                                if active_games:
                                    cg_id = active_games[0].get('id')
                                    tourney_item = next((it for it in game_config.get('collect_game_items', [])
                                                          if it.get('collect_game_id') == cg_id
                                                          and it.get('action') == 'TOURNAMENTS'), None)
                                    if tourney_item:
                                        add_collect_game_item_progress(game_config, player_data, tourney_item['type'], amount=1)
                                
                                print(f"   [END_TOURNAMENT OK] ¡Torneo {current_tourney} completado!")
                                print(f"                       Recompensas añadidas -> Oro: {gold_reward} | Comida: {food_reward} | Gemas: {cash_reward} | Puntos: {puntos}")
                                print(f"                       Siguiente torneo configurado: {player_data['privateState']['currentTournament']}")
                            else:
                                print(f"   [!] Error: El torneo {current_tourney} no existe en get_game_config.json")

                    elif cmd == 'admin_speed_tournament':
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
                            print(f"                               Nuevo endTournamentTs: {new_ts} | Gemas restantes: {player_data['playerInfo']['cash']}")
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
                                print(f"                       Gemas restantes: {player_data['playerInfo']['cash']}")
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
                        puntos = 75
                        
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
                                player_data['privateState']['achievement_points'] += puntos
                                
                                print(f"   [COMPLETE_COLLECTION OK] '{col_name}' (ID: {collection_id}) completada.")
                                print(f"                            Recompensas aplicadas -> Oro: +{gold_reward}, Comida: +{food_reward}, Gemas: +{cash_reward}, XP: +{xp_reward}, Puntos: +{puntos}")
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
                            
                            print(f"   [DRAGONARIUM_ADD OK] Pestaña {nombre_slot} se añadió un espacio con éxito.")
                            print(f"                        Estado actual del slot {nombre_slot}: {slots[slot_index]} espacios")
                            print(f"                        Gemas restantes: {player_data['playerInfo']['cash']}")
                        else:
                            print(f"   [!] Error: El índice de slot {slot_index} está fuera de rango para el Dragonario.")

                    elif cmd == 'dragonarium_hatch':
                        egg_uid = args[0]
                        dragon_name = args[1]

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

                                new_dragon = {
                                    "id": egg_uid,
                                    "type": dragon_type_id,
                                    "xp": 0,
                                    "habitatId": 0,
                                    "name": dragon_name,
                                    "ts": int(time.time()),
                                    "work_id": [],
                                    "nbKill": 0,
                                    "attack": attacks
                                }

                                category_index = 0
                                attributes = item_cfg.get('attributes', [])

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

                                if 'dragonariumSlot' not in player_data['privateState'] or len(player_data['privateState'].get('dragonariumSlot', [])) < 5:
                                    player_data['privateState']['dragonariumSlot'] = [2, 2, 2, 1, 1]

                                if 'dragonarium' not in player_data['privateState'] or len(player_data['privateState'].get('dragonarium', [])) < 5:
                                    player_data['privateState']['dragonarium'] = [[], [], [], [], []]

                                player_data['privateState']['dragonarium'][category_index].append(new_dragon)

                                if 'ownedDragons' not in player_data['map']:
                                    player_data['map']['ownedDragons'] = {}

                                id_str = str(dragon_type_id)
                                if id_str not in player_data['map']['ownedDragons']:
                                    player_data['map']['ownedDragons'][id_str] = [1, 0, 0]

                                print(f"   [DRAGONARIUM_HATCH OK] Dragón '{dragon_name}' (Tipo: {dragon_type_id}, UID: {egg_uid}) eclosionado directo al Dragonarium.")
                                print(f"                          XP ganado: {hatch_xp} | XP total: {player_data['playerInfo']['xp']}")
                                print(f"                          Guardado en Pestaña: {category_index}.")
                            else:
                                print(f"   [!] Error: Configuración para el dragón {dragon_type_id} no encontrada en game_config.")
                        else:
                            print(f"   [!] Error: No se encontró un huevo con UID {egg_uid} en 'eggs'.")
                            
                    elif cmd == 'set_help_map':
                        help_id = str(args[0])

                        if 'helpMap' not in player_data['privateState']:
                            player_data['privateState']['helpMap'] = []

                        if help_id not in player_data['privateState']['helpMap']:
                            player_data['privateState']['helpMap'].append(help_id)
                            print(f"   [SET_HELP_MAP OK] Ayuda '{help_id}' registrada correctamente en helpMap.")
                        else:
                            print(f"   [!] Aviso: El jugador ya había visto la ayuda '{help_id}'.")
                            
                    elif cmd == 'attack_player':
                        target_player_id = str(args[0])
                        current_time = int(time.time())

                        opponent = None
                        for league_page in player_data.get('privateState', {}).get('pvpLeagues', {}).values():
                            opponent = next((o for o in league_page if str(o.get('id')) == target_player_id), None)
                            if opponent:
                                break
                        if not opponent:
                            opponent = next((o for o in (load_pvp_isle() or []) if str(o.get('id')) == target_player_id), None)

                        if opponent:
                            opp_level = int(opponent.get('level', 12))
                        else:
                            opp_level = player_data['playerInfo'].get('level', 12)
                            print(f"   [!] Aviso: El oponente {target_player_id} no esta en ninguna liga, se usa el nivel del jugador ({opp_level}).")

                        units = build_pvp_team(target_player_id, opp_level, game_config)

                        if 'attacksSent' not in player_data['privateState']:
                            player_data['privateState']['attacksSent'] = []

                        player_data['privateState']['attacksSent'].append({
                            "victim_id": target_player_id,
                            "time": current_time
                        })

                        print(f"   [ATTACK_PLAYER OK] Combate PvP contra {target_player_id} (nivel {opp_level}, {len(units)} dragones).")
                        cmd_result = units
                            
                    elif cmd == 'end_attack_f':
                        target_player_id = str(args[0])
                        position = int(args[1])
                        win_status = int(args[2])
                        puntosPvp = 35
                        puntosLeague = 120

                        kills_log = {}
                        if len(args) > 3 and args[3]:
                            try:
                                kills_log = json.loads(args[3])
                            except Exception as e:
                                print(f"   [!] Error decodificando kills_log: {e}")

                        if win_status == 1:
                            if 'universAttackWin' not in player_data['map']:
                                player_data['map']['universAttackWin'] = []
                                
                            attack_win_list = player_data['map']['universAttackWin']
                            player_data['privateState']['achievement_points'] += puntosPvp
                            
                            target_found = False

                            for i, entry in enumerate(attack_win_list):
                                if isinstance(entry, list) and len(entry) >= 3:
                                    if str(entry[0]) == target_player_id:
                                        attack_win_list[i] = position
                                        target_found = True
                                        break

                            if not target_found:
                                attack_win_list.append(position)

                        if kills_log and 'dragons' in player_data['map']:
                            for dragon in player_data['map']['dragons']:
                                dragon_id_str = str(dragon.get('id'))
                                
                                if dragon_id_str in kills_log:
                                    kills_to_add = int(kills_log[dragon_id_str])
                                    current_kills = dragon.get('nbKill', 0)
                                    dragon['nbKill'] = current_kills + kills_to_add
                                    
                                    print(f"   [+] Dragón {dragon.get('name', 'Unknown')} (ID: {dragon_id_str}) suma {kills_to_add} kills. Total: {dragon['nbKill']}")

                        active_games = game_config.get('collect_game', [])
                        if active_games:
                            cg_id = active_games[0].get('id')
                            fight_item = next((it for it in game_config.get('collect_game_items', [])
                                                if it.get('collect_game_id') == cg_id
                                                and it.get('action') == 'FIGHT!'), None)
                            if fight_item:
                                add_collect_game_item_progress(game_config, player_data, fight_item['type'], amount=1)
                
                        resultado = "VICTORIA" if win_status == 1 else "DERROTA"
                        print(f"   [END_ATTACK_F OK] Combate contra {target_player_id} procesado ({resultado}).")
                        print(f"                     Puntos obtenidos {puntosPvp} | Puntos totales: {player_data['privateState']['achievement_points']}")
                        LEAGUE_WIN_THRESHOLD = 7
                        victories = len(player_data['map'].get('universAttackWin', []))

                        if win_status == 1 and victories >= LEAGUE_WIN_THRESHOLD:
                            current_pvp_level = player_data['playerInfo'].get('pvpLevel', 1)
                            player_data['playerInfo']['pvpLevel'] = current_pvp_level + 1
                            player_data['privateState']['achievement_points'] += puntosLeague
                            player_data['map']['universAttackWin'] = []
                            cmd_result = True
                            print(f"   [PVP] ¡Liga completada! Nueva pvpLevel={player_data['playerInfo']['pvpLevel']}")
                            print(f"         Puntos obtenidos {puntosLeague} | Puntos totales: {player_data['privateState']['achievement_points']}")
                        else:
                            cmd_result = None

                    elif cmd == 'end_attack':
                        target_player_id = str(args[0])
                        position = int(args[1])
                        win_status = int(args[2])
                        puntosPvp = 35
                        puntosLeague = 120

                        kills_log = {}
                        if len(args) > 3 and args[3]:
                            try:
                                kills_log = json.loads(args[3])
                            except Exception as e:
                                print(f"   [!] Error decodificando kills_log: {e}")

                        if win_status == 1:
                            if 'universAttackWin' not in player_data['map']:
                                player_data['map']['universAttackWin'] = []
                                
                            attack_win_list = player_data['map']['universAttackWin']
                            player_data['privateState']['achievement_points'] += puntosPvp
                            
                            target_found = False

                            for i, entry in enumerate(attack_win_list):
                                if isinstance(entry, list) and len(entry) >= 3:
                                    if str(entry[0]) == target_player_id:
                                        attack_win_list[i] = position
                                        target_found = True
                                        break

                            if not target_found:
                                attack_win_list.append(position)

                        if kills_log and 'dragons' in player_data['map']:
                            for dragon in player_data['map']['dragons']:
                                dragon_id_str = str(dragon.get('id'))
                                
                                if dragon_id_str in kills_log:
                                    kills_to_add = int(kills_log[dragon_id_str])
                                    current_kills = dragon.get('nbKill', 0)
                                    dragon['nbKill'] = current_kills + kills_to_add
                                    
                                    print(f"   [+] Dragón {dragon.get('name', 'Unknown')} (ID: {dragon_id_str}) suma {kills_to_add} kills. Total: {dragon['nbKill']}")

                        active_games = game_config.get('collect_game', [])
                        if active_games:
                            cg_id = active_games[0].get('id')
                            fight_item = next((it for it in game_config.get('collect_game_items', [])
                                                if it.get('collect_game_id') == cg_id
                                                and it.get('action') == 'FIGHT!'), None)
                            if fight_item:
                                add_collect_game_item_progress(game_config, player_data, fight_item['type'], amount=1)
                
                        resultado = "VICTORIA" if win_status == 1 else "DERROTA"
                        print(f"   [END_ATTACK_F OK] Combate contra {target_player_id} procesado ({resultado}).")
                        print(f"                     Puntos obtenidos {puntosPvp} | Puntos totales: {player_data['privateState']['achievement_points']}")
                        LEAGUE_WIN_THRESHOLD = 7
                        victories = len(player_data['map'].get('universAttackWin', []))

                        if win_status == 1 and victories >= LEAGUE_WIN_THRESHOLD:
                            current_pvp_level = player_data['playerInfo'].get('pvpLevel', 1)
                            player_data['playerInfo']['pvpLevel'] = current_pvp_level + 1
                            player_data['privateState']['achievement_points'] += puntosLeague
                            player_data['map']['universAttackWin'] = []
                            cmd_result = True
                            print(f"   [PVP] ¡Liga completada! Nueva pvpLevel={player_data['playerInfo']['pvpLevel']}")
                            print(f"         Puntos obtenidos {puntosLeague} | Puntos totales: {player_data['privateState']['achievement_points']}")
                        else:
                            cmd_result = None
                        
                    elif cmd == 'assist_neighbor':
                        target_player_id = str(args[0])
                        clicks = json.loads(args[1])
                        
                        victim_data = load_player(target_player_id)

                        victim_data.setdefault("map", {})
                        if not isinstance(victim_data["map"].get("receivedAssists"), dict):
                            victim_data["map"]["receivedAssists"] = {}
                     
                        key = "u" + str(user_id)
                        victim_data["map"]["receivedAssists"].setdefault(key, [])
                        victim_data["map"]["receivedAssists"][key].extend(clicks)
                     
                        save_player(victim_data, target_player_id)

                        print(f"   [ASSIST_NEIGHBOR OK] Vecino {victim_data['playerInfo']['name']} ayudado")
                        
                    elif cmd == 'clean_received_assists':
                        helper_pid = str(args[0])
                        key = "u" + helper_pid
                        received = player_data.get("map", {}).get("receivedAssists", {})
                        if isinstance(received, dict) and key in received:
                            del received[key]

                        print(f"   [CLEAN_RECEIVED_ASSISTS OK] Entrada de ayuda del vecino {helper_pid} eliminada")
                     
                    elif cmd == 'assist_receive':
                        item_type_id = int(args[0])

                        group_type = None
                        for item in game_config.get("items", []):
                            if item.get("id") == item_type_id:
                                group_type = item.get("group_type", "")
                                break
                     
                        REWARD_XP   = 10
                        REWARD_GOLD = 0
                        REWARD_FOOD = 0
                     
                        if group_type == "HABITAT":
                            REWARD_GOLD = 10
                        elif group_type == "FARM":
                            REWARD_FOOD = 10
                     
                        player_data["playerInfo"]["xp"]   += REWARD_XP
                        player_data["playerInfo"]["gold"] += REWARD_GOLD
                        player_data["playerInfo"]["food"] += REWARD_FOOD

                        print(f"   [ASSIST_RECEIVE OK] Ayuda de recursos añadida")
                        print(f"                       Recursos actuales: Comida:{player_data['playerInfo']['food']} Oro:{player_data['playerInfo']['gold']} XP:{player_data['playerInfo']['xp']}")

                    elif cmd == 'kompu_boxes_new_list':
                        price = 3
                        kompu_offers = game_config.get('kompu_offers', [])
                        unique_dragon_id = None
                        if kompu_offers and isinstance(kompu_offers, list):
                            rewards = kompu_offers[0].get('rewards', {})
                            if isinstance(rewards, dict):
                                unique_dragon_id = rewards.get('uniqueDragonId')

                        items = game_config.get('items', [])
                        dragons_cat_234 = []
                        dragons_cat_4 = []
                        dragons_cat_5 = []
                        
                        for item in items:
                            if item.get('group_type') == 'DRAGON':
                                cat = item.get('category', 1)
                                d_id = item.get('id')
                                if cat in [2, 3, 4]:
                                    dragons_cat_234.append(d_id)
                                if cat == 4:
                                    dragons_cat_4.append(d_id)
                                if cat == 5:
                                    dragons_cat_5.append(d_id)

                        pool_dragons = []

                        pool_dragons.extend(random.sample(dragons_cat_234, min(4, len(dragons_cat_234))))
                        while len(pool_dragons) < 4:
                            pool_dragons.append(random.choice(dragons_cat_234))

                        pool_dragons.append(random.choice(dragons_cat_4))

                        if unique_dragon_id and random.random() <= 0.10:
                            pool_dragons.append(unique_dragon_id)
                            print(f"   [★] ¡El uniqueDragonId ({unique_dragon_id}) apareció en el pool!")
                        else:
                            pool_dragons.append(random.choice(dragons_cat_5))

                        player_data['privateState']['kompuBoxesDragons'] = pool_dragons[:]

                        shuffled_dragons = pool_dragons[:]
                        random.shuffle(shuffled_dragons)
                        player_data['privateState']['kompuBoxesShuffledDragons'] = shuffled_dragons
                        player_data['playerInfo']['cash'] -= price
                        
                        cmd_result = {
                            "kompuBoxesDragons": player_data['privateState']['kompuBoxesDragons'],
                            "kompuBoxesShuffledDragons": player_data['privateState']['kompuBoxesShuffledDragons']
                        }
                        
                        print(f"   [KOMPU_BOXES_NEW_LIST OK] Nueva lista de dragones generada")

                    elif cmd == 'kompu_boxes_open_box':
                        current_opened = player_data['privateState'].get('kompuBoxesOpened', 0)

                        if current_opened == 0:
                            price = 20
                        else:
                            price = 10

                        player_data['playerInfo']['cash'] -= price

                        if current_opened < 6:
                            player_data['privateState']['kompuBoxesOpened'] = current_opened + 1
                            new_opened = player_data['privateState']['kompuBoxesOpened']

                            kompu_dragons = player_data['privateState'].get('kompuBoxesDragons', [])
                            prize_dragon_id = "Desconocido"
                            
                            if len(kompu_dragons) >= new_opened:
                                prize_dragon_id = kompu_dragons[new_opened - 1]
                                
                            print(f"   [KOMPU_BOXES_OPEN_BOX OK] Caja #{new_opened} abierta.")
                            print(f"                             ¡Premio a reclamar!: Dragón ID {prize_dragon_id}")
                            
                    elif cmd == 'kompu_boxes_claim_prize':
                        current_opened = player_data['privateState'].get('kompuBoxesOpened', 0)
                        kompu_dragons = player_data['privateState'].get('kompuBoxesDragons', [])
                        current_ts = int(time.time())

                        if 'store' not in player_data['map']:
                            player_data['map']['store'] = {}

                        if 'dragons' not in player_data['map']['store']:
                            player_data['map']['store']['dragons'] = []
                        
                        if current_opened > 0 and len(kompu_dragons) >= current_opened:
                            prize_dragon_id = kompu_dragons[current_opened - 1]
                                
                            player_data['map']['store']['dragons'].append({
                                "iid": prize_dragon_id,
                                "lvl": 0
                            })
                            print(f"   [KOMPU_BOXES_CLAIM_PRIZE OK] Dragón ID {prize_dragon_id} guardado en el almacén.")
                        else:
                            print(f"   [!] Error: kompuBoxesOpened es {current_opened}. Lista inválida para reclamar.")

                        player_data['privateState']['kompuBoxesOpened'] = 0

                        kompu_offers = game_config.get('kompu_offers', [])
                        unique_dragon_id = None
                        if kompu_offers and isinstance(kompu_offers, list):
                            rewards = kompu_offers[0].get('rewards', {})
                            if isinstance(rewards, dict):
                                unique_dragon_id = rewards.get('uniqueDragonId')

                        items = game_config.get('items', [])
                        dragons_cat_234 = []
                        dragons_cat_4 = []
                        dragons_cat_5 = []
                        
                        for item in items:
                            if item.get('group_type') == 'DRAGON':
                                cat = item.get('category', 1)
                                d_id = item.get('id')
                                if cat in [2, 3, 4]:
                                    dragons_cat_234.append(d_id)
                                if cat == 4:
                                    dragons_cat_4.append(d_id)
                                if cat == 5:
                                    dragons_cat_5.append(d_id)

                        pool_dragons = []

                        pool_dragons.extend(random.sample(dragons_cat_234, min(4, len(dragons_cat_234))))
                        while len(pool_dragons) < 4:
                            pool_dragons.append(random.choice(dragons_cat_234))

                        pool_dragons.append(random.choice(dragons_cat_4))

                        if unique_dragon_id and random.random() <= 0.10:
                            pool_dragons.append(unique_dragon_id)
                            print(f"                                [★] ¡El dragon especial ({unique_dragon_id}) apareció en el nuevo pool tras reclamar!")
                        else:
                            pool_dragons.append(random.choice(dragons_cat_5))

                        player_data['privateState']['kompuBoxesDragons'] = pool_dragons[:]
                        
                        shuffled_dragons = pool_dragons[:]
                        random.shuffle(shuffled_dragons)
                        player_data['privateState']['kompuBoxesShuffledDragons'] = shuffled_dragons
                        player_data['privateState']['kompuLastTimeStamp'] = current_ts

                        cmd_result = {
                            "kompuBoxesDragons": player_data['privateState']['kompuBoxesDragons'],
                            "kompuBoxesShuffledDragons": player_data['privateState']['kompuBoxesShuffledDragons']
                        }
                        
                        print(f"                                Tablero reiniciado con éxito.")

                    elif cmd == 'collect_game_add_item':
                        container_id = args[0]
                        quest_id     = args[1]
                        method       = args[2]

                        container_cfg = next((c for c in game_config.get('collect_game_item_containers', [])
                                               if str(c.get('id')) == str(container_id)
                                               and str(c.get('quest')) == str(quest_id)), None)

                        if container_cfg:
                            collect_period = container_cfg.get('collect_period', '-')

                            if collect_period != '-':
                                add_collect_game_item_progress(game_config, player_data, container_cfg.get('type'), amount=1)
                                print(f"   [COLLECT_GAME_ADD_ITEM OK] Container {container_id} ({container_cfg.get('name')})")

                            else:
                                quest_cfg = next((q for q in game_config.get('collect_game_quests', [])
                                                   if str(q.get('id')) == str(quest_id)), None)
                                collect_game_id = quest_cfg.get('collect_game') if quest_cfg else None
                                if collect_game_id is None:
                                    active_games = game_config.get('collect_game', [])
                                    if active_games:
                                        collect_game_id = active_games[0].get('id')

                                if collect_game_id is not None:
                                    cg_key = str(collect_game_id)
                                    item_type = str(container_cfg.get('type'))
                                    required  = container_cfg.get('required', 0)

                                    player_data.setdefault('privateState', {})
                                    player_data['privateState'].setdefault('collectGame', {})
                                    collect_game_save = player_data['privateState']['collectGame']
                                    collect_game_save.setdefault(cg_key, {
                                        "quests": {"status": {}, "rewardTryTime": 0},
                                        "formulaVars": {"playerLevelAtCollectGameStart": player_data['playerInfo'].get('level', 1)},
                                        "itemsContainers": [], "items": {}, "rewardsGiven": []
                                    })
                                    island_save = collect_game_save[cg_key]
                                    island_save.setdefault('items', {})
                                    island_save['items'].setdefault(item_type, {"amount": 0, "timestamp": 0})

                                    current_amount = island_save['items'][item_type]['amount']

                                    if method == 'cash':
                                        is_last = (current_amount + 1) >= required
                                        cost = container_cfg.get('cost_last_item', 0) if is_last else container_cfg.get('cost_item', 0)
                                        player_data['playerInfo']['cash'] = max(0, player_data['playerInfo']['cash'] - cost)
                                        print(f"   [-] Gemas cobradas: {cost} | Gemas restantes: {player_data['playerInfo']['cash']}")
                                    elif method == 'amount':
                                        print(f"   [-] Sumado sin costo (method=amount)")

                                    current_time = int(time.time())
                                    island_save['items'][item_type]['amount'] = current_amount + 1
                                    island_save['items'][item_type]['timestamp'] = current_time

                                    if island_save['items'][item_type]['amount'] >= required and container_id not in island_save['itemsContainers']:
                                        island_save['itemsContainers'].append(container_id)
                                        print(f"   [★] Container {container_id} COMPLETADO ({item_type}: {island_save['items'][item_type]['amount']}/{required})")

                                    print(f"   [COLLECT_GAME_ADD_ITEM OK] Isla {cg_key} | Container {container_id} ({container_cfg.get('name')}) | "
                                          f"Tipo {item_type}: {island_save['items'][item_type]['amount']}/{required}")

                                    check_reward_thresholds(game_config, player_data, collect_game_id, island_save)
                                    check_and_complete_quest(game_config, player_data, island_save, quest_id)
                                else:
                                    print(f"   [!] Error: no se pudo resolver el collect_game_id para quest {quest_id}")
                        else:
                            print(f"   [!] Error: container {container_id} no existe en collect_game_item_containers")
                            
                    elif cmd == 'collect_game_add_items_container':
                        container_id = args[0]
                        quest_id     = args[1]
                        method       = args[2]

                        TYPE_GOLD = 0
                        TYPE_FOOD = 1

                        container_cfg = next((c for c in game_config.get('collect_game_item_containers', [])
                                               if str(c.get('id')) == str(container_id)
                                               and str(c.get('quest')) == str(quest_id)), None)

                        if container_cfg:
                            quest_cfg = next((q for q in game_config.get('collect_game_quests', [])
                                               if str(q.get('id')) == str(quest_id)), None)

                            collect_game_id = quest_cfg.get('collect_game') if quest_cfg else None
                            if collect_game_id is None:
                                active_games = game_config.get('collect_game', [])
                                if active_games:
                                    collect_game_id = active_games[0].get('id')

                            if collect_game_id is not None and quest_cfg is not None:
                                cg_key = str(collect_game_id)
                                item_type = str(container_cfg.get('type'))
                                type_num  = container_cfg.get('type')

                                player_data.setdefault('privateState', {})
                                player_data['privateState'].setdefault('collectGame', {})
                                collect_game_save = player_data['privateState']['collectGame']

                                collect_game_save.setdefault(cg_key, {
                                    "quests": {"status": {}, "rewardTryTime": 0},
                                    "formulaVars": {
                                        "playerLevelAtCollectGameStart": player_data['playerInfo'].get('level', 1)
                                    },
                                    "itemsContainers": [],
                                    "items": {},
                                    "rewardsGiven": []
                                })
                                island_save = collect_game_save[cg_key]
                                island_save.setdefault('items', {})
                                island_save['items'].setdefault(item_type, {"amount": 0, "timestamp": 0})

                                user_starting_level = island_save.get('formulaVars', {}).get(
                                    'playerLevelAtCollectGameStart',
                                    player_data['playerInfo'].get('level', 1)
                                )

                                formula_params = quest_cfg.get('formula_parameters', {})
                                required = container_cfg.get('required', 0)

                                if method == 'cash':
                                    cost = container_cfg.get('cost', 0)
                                    if not isinstance(cost, (int, float)):
                                        cost = 0
                                    player_data['playerInfo']['cash'] = max(0, player_data['playerInfo']['cash'] - cost)
                                    print(f"   [-] Gemas cobradas: {cost} | Gemas restantes: {player_data['playerInfo']['cash']}")

                                elif method == 'amount':
                                    if type_num == TYPE_GOLD:
                                        gold_factor   = formula_params.get('goldFactorLevel', 0)
                                        gold_exponent = formula_params.get('goldExponent', 0)
                                        base = user_starting_level * gold_factor
                                        required = round(round((base ** gold_exponent) * 0.16 / 400) * 400 / 4)

                                        player_data['playerInfo']['gold'] = max(0, player_data['playerInfo']['gold'] - required)
                                        print(f"   [-] Oro cobrado: {required} | Oro restante: {player_data['playerInfo']['gold']} "
                                              f"(userStartingCollectLevel={user_starting_level})")

                                    elif type_num == TYPE_FOOD:
                                        required = calculate_food_container_cost(game_config, quest_cfg, user_starting_level)
                                        player_data['playerInfo']['food'] = max(0, player_data['playerInfo']['food'] - required)
                                        print(f"   [-] Comida cobrada: {required} | Comida restante: {player_data['playerInfo']['food']} "
                                              f"(farm_limit={get_element_limit(game_config, 'FARM', user_starting_level)}, userStartingLevel={user_starting_level})")
                                    else:
                                        print(f"   [-] Completado sin costo (method=amount, tipo {type_num})")

                                item_cfg_del_type = next((it for it in game_config.get('collect_game_items', [])
                                                           if it.get('collect_game_id') == collect_game_id
                                                           and it.get('type') == container_cfg.get('type')), None)

                                es_pasivo = item_cfg_del_type is not None and item_cfg_del_type.get('id') in PASSIVE_RESOURCE_ITEM_IDS

                                if es_pasivo:
                                    current = island_save['items'][item_type]['amount']
                                    island_save['items'][item_type]['amount'] = max(0, current - required)
                                    print(f"   [-{required}] Tipo {item_type} (pasivo) -> queda en {island_save['items'][item_type]['amount']}")
                                else:
                                    island_save['items'][item_type]['amount'] = required

                                island_save['items'][item_type]['timestamp'] = int(time.time())

                                if container_id not in island_save['itemsContainers']:
                                    island_save['itemsContainers'].append(container_id)

                                print(f"   [★] Container {container_id} ({container_cfg.get('name')}) COMPLETADO | quest {quest_id}")
                                check_reward_thresholds(game_config, player_data, collect_game_id, island_save)
                                check_and_complete_quest(game_config, player_data, island_save, quest_id)
                            else:
                                print(f"   [!] Error: no se pudo resolver el collect_game_id/quest para quest {quest_id}")
                        else:
                            print(f"   [!] Error: container {container_id} no existe en collect_game_item_containers")

                    elif cmd == 'lost_item_found':
                        LOST_ITEM_SLOT_TYPE = 2
                        add_collect_game_item_progress(game_config, player_data, LOST_ITEM_SLOT_TYPE, amount=1)
                        print(f"   [LOST_ITEM_FOUND OK]")

                    elif cmd == 'collect_game_begin_attack':
                        quest_id = args[0]
                        print(f"   [⚔️] Empezó pelea de quest {quest_id}")

                    elif cmd == 'collect_game_end_attack':
                        quest_id = args[0]
                        won = args[1]

                        quest_cfg = next((q for q in game_config.get('collect_game_quests', [])
                                           if str(q.get('id')) == str(quest_id)), None)

                        if quest_cfg is None:
                            print(f"   [!] Error: quest {quest_id} no existe en collect_game_quests")
                        else:
                            cg_key = str(quest_cfg.get('collect_game'))

                            player_data.setdefault('privateState', {})
                            player_data['privateState'].setdefault('collectGame', {})
                            collect_game_save = player_data['privateState']['collectGame']
                            collect_game_save.setdefault(cg_key, {
                                "quests": {"status": {}, "rewardTryTime": 0},
                                "formulaVars": {"playerLevelAtCollectGameStart": player_data['playerInfo'].get('level', 1)},
                                "itemsContainers": [], "items": {}, "rewardsGiven": []
                            })
                            island_save = collect_game_save[cg_key]
                            island_save.setdefault('quests', {}).setdefault('status', {})

                            quest_id_str = str(quest_id)

                            if won == 1:
                                island_save['quests']['status'][quest_id_str] = 'completed'
                                print(f"   [⚔️🏆] Ganaste! Quest {quest_id_str} ({quest_cfg.get('name')}) COMPLETED")

                                reward = quest_cfg.get('reward')
                                if isinstance(reward, int):
                                    grant_quest_reward(game_config, player_data, reward)
                            else:
                                island_save['quests']['rewardTryTime'] = int(time.time())
                                print(f"   [⚔️💀] Perdiste la pelea de quest {quest_id_str}, sin cambios")

                    elif cmd == 'spinning_try':
                        mode = str(args[0])

                        wheel_data_list = game_config.get('globals', {}).get('SPIN_WHEEL_DATA', {}).get('value', [])
                        mode_idx = int(mode)

                        if mode_idx >= len(wheel_data_list):
                            print(f"[!] Modo de rueda inválido: {mode}. Fallback a modo 0.")
                            mode_idx = 0

                        wheel_mode_data = wheel_data_list[mode_idx]
                        prizes = wheel_mode_data['prizes']
                        cost_gems = int(wheel_mode_data.get('cost', {}).get('c', 0))

                        if cost_gems > 0:
                            if player_data['playerInfo']['cash'] < cost_gems:
                                print(f"[!] Gemas insuficientes para spin royal (necesita {cost_gems}).")
                                cmd_result = "ok"
                                
                            player_data['playerInfo']['cash'] -= cost_gems

                        winning_index = random.randint(0, len(prizes) - 1)
                        prize_value = prizes[winning_index]
                        
                        current_spells = player_data['privateState']['kompuSpells']

                        if isinstance(prize_value, str):
                            if prize_value == "x0":
                                current_spells = 0
                            elif prize_value == "x2":
                                current_spells = current_spells * 2
                        else:
                            current_spells = current_spells + prize_value

                        player_data['privateState']['kompuSpells'] = current_spells
                        player_data['privateState']['kompuLastTimeStamp'] = int(time.time())
                        
                        check_kompu_rewards(player_data, game_config, 2)

                        print(f"   [SPINNING_TRY OK] modo={mode} | costo={cost_gems} gemas")
                        print(f"                     resultado: sector {winning_index} -> {prize_value}")
                        print(f"                     Fichas = {current_spells}")
                        
                        cmd_result = [winning_index, prize_value]

                    elif cmd == 'spin_hallo_wheel':
                        mode = str(args[0])

                        wheel_offer = next((o for o in game_config.get('kompu_offers', [])
                                             if o.get('game_type') == 3), None)
                        if wheel_offer is None:
                            print("[!] No hay oferta de rueda Halloween activa.")
                            cmd_result = "ok"
                        else:
                            mode_data = wheel_offer['rewards'][0][mode]
                            prizes = mode_data['prizes']
                            cost_gems = int(mode_data.get('cost', {}).get('c', 0))

                            if cost_gems > 0:
                                if player_data['playerInfo']['cash'] < cost_gems:
                                    print(f"[!] Gemas insuficientes para spin especial (necesita {cost_gems}).")
                                    cmd_result = "ok"
                                    
                                player_data['playerInfo']['cash'] -= cost_gems

                            dragon_idx, gem_idx, resource_idx = [], [], []
                            for i, p in enumerate(prizes):
                                if isinstance(p, list):
                                    dragon_idx.append(i)
                                elif isinstance(p, dict) and 'c' in p:
                                    gem_idx.append(i)
                                else:
                                    resource_idx.append(i)

                            if mode == '1':
                                weights = {'resource': 40, 'gem': 30, 'dragon': 30}
                            else:
                                weights = {'resource': 70, 'gem': 20, 'dragon': 10}

                            pools = {'resource': resource_idx, 'gem': gem_idx, 'dragon': dragon_idx}
                            categories = [c for c in pools if pools[c]]
                            cat_weights = [weights[c] for c in categories]
                            chosen_category = random.choices(categories, weights=cat_weights, k=1)[0]

                            winning_index = random.choice(pools[chosen_category])

                            prize_entry = prizes[winning_index]
                            is_unique = isinstance(prize_entry, list) and len(prize_entry) >= 2
                            if is_unique and player_data['privateState'].get('kompuHWUniqueGiven', False):
                                normal_dragons = [i for i in dragon_idx if not (
                                    isinstance(prizes[i], list) and len(prizes[i]) >= 2)]
                                if normal_dragons:
                                    winning_index = random.choice(normal_dragons)
                                    prize_entry = prizes[winning_index]
                                    is_unique = False

                            if isinstance(prize_entry, list):
                                dragon_id = prize_entry[0]
                                store = player_data.setdefault('map', {}).setdefault('store', {})
                                dragons_list = store.setdefault('dragons', [])
                                dragons_list.append({"iid": dragon_id, "lvl": 0})
                                if is_unique:
                                    player_data['privateState']['kompuHWUniqueGiven'] = True
                            else:
                                for key, amount in prize_entry.items():
                                    if key == 'g':
                                        player_data['playerInfo']['gold'] += amount
                                    elif key == 'c':
                                        player_data['playerInfo']['cash'] += amount
                                    elif key == 'f':
                                        player_data['playerInfo']['food'] += amount
                                    elif key == 'x':
                                        player_data['playerInfo']['xp'] += amount

                            print(f"   [SPIN_HALLO_WHEEL OK] modo={mode} | costo={cost_gems} gemas")
                            print(f"                         cayó en sector {winning_index} -> {prize_entry}")
                            
                            cmd_result = winning_index

                    elif cmd == 'kompu_hurry_up':
                        HURRY_UP_COST = 5

                        if player_data['playerInfo']['cash'] >= HURRY_UP_COST:
                            player_data['playerInfo']['cash'] -= HURRY_UP_COST

                            player_data['privateState']['kompuLastTimeStamp'] -= 21600

                            print(f"   [KOMPU_HURRY_UP OK] Se restaron 6 horas a kompuLastTimeStamp.")
                            print(f"                       Costo: {HURRY_UP_COST} gemas | Gemas restantes: {player_data['playerInfo']['cash']}")
                        else:
                            print(f"   [!] Error: Gemas insuficientes para 'kompu_hurry_up' ({HURRY_UP_COST} requeridas, tiene {player_data['playerInfo']['cash']}).")

                    elif cmd == 'breeding_sanctuary_activate':
                        ACTIVATION_COST = 25

                        if 'breedingSanctuary' not in player_data['privateState']:
                            player_data['privateState']['breedingSanctuary'] = {
                                "level": 1,
                                "stepsBought": 0,
                                "userLevelLastStep": 1,
                                "percentGoldLastStep": 1,
                                "activated": 0
                            }

                        sanctuary = player_data['privateState']['breedingSanctuary']

                        if sanctuary.get('activated', 0) == 1:
                            print(f"   [!] Aviso: El Santuario de Cría ya estaba activado.")
                        elif player_data['playerInfo']['cash'] >= ACTIVATION_COST:
                            player_data['playerInfo']['cash'] -= ACTIVATION_COST
                            sanctuary['activated'] = 1

                            print(f"   [BREEDING_SANCTUARY_ACTIVATE OK] Santuario de Cría activado.")
                            print(f"                                    Costo: {ACTIVATION_COST} gemas | Gemas restantes: {player_data['playerInfo']['cash']}")
                        else:
                            print(f"   [!] Error: Gemas insuficientes para activar el Santuario ({ACTIVATION_COST} requeridas, tiene {player_data['playerInfo']['cash']}).")

                    elif cmd == 'breeding_sanctuary_buy_step':
                        sanctuary_cfg = game_config.get('sanctuary_breeding', {})
                        general_cfg = sanctuary_cfg.get('general_config', {})
                        upgrades_cfg = sanctuary_cfg.get('upgrades_config', [])

                        sanctuary = player_data['privateState'].get('breedingSanctuary')

                        if not sanctuary:
                            print(f"   [!] Error: El jugador no tiene 'breedingSanctuary' en privateState.")
                        elif sanctuary.get('activated', 0) != 1:
                            print(f"   [!] Error: El Santuario de Cría no está activado, no se pueden comprar pasos.")
                        else:
                            current_level = sanctuary.get('level', 1)
                            level_cfg = next((lvl for lvl in upgrades_cfg if lvl.get('id') == current_level), None)

                            if not level_cfg:
                                print(f"   [!] Error: No se encontró configuración de 'upgrades_config' para el nivel {current_level}.")
                            elif sanctuary.get('stepsBought', 0) >= level_cfg.get('num_steps', 1):
                                print(f"   [!] Error: Ya se compraron todos los pasos de este nivel, falta mejorar con 'breeding_sanctuary_upgrade'.")
                            else:
                                user_level_last_step = sanctuary.get('userLevelLastStep', 1)
                                percent_gold_last_step = sanctuary.get('percentGoldLastStep', 1)
                                multiplier = level_cfg.get('multiplier', 1)

                                gold_factor_level = general_cfg.get('GOLD_FACTOR_LEVEL', 100)
                                gold_exponent = general_cfg.get('GOLD_EXPONENT', 1.1)
                                gold_multiplier = general_cfg.get('GOLD_MULTIPLIER', 0.8)
                                gold_coeficient = general_cfg.get('GOLD_COEFICIENT', 1)
                                gold_divisor = general_cfg.get('GOLD_DIVISOR', 0.2)
                                percent_accumulated_gold = general_cfg.get('PERCENT_OF_ACCUMULATED_GOLD', 1)

                                step_cost = round(math.pow(user_level_last_step * gold_factor_level, gold_exponent) * gold_multiplier / gold_coeficient)
                                step_cost = step_cost * gold_coeficient / gold_divisor + percent_gold_last_step
                                step_cost = int(int(round(step_cost * multiplier)) // 1000) * 1000

                                if player_data['playerInfo']['gold'] < step_cost:
                                    print(f"   [!] Error: Oro insuficiente para comprar paso ({step_cost} requerido, tiene {player_data['playerInfo']['gold']}).")
                                else:
                                    player_data['playerInfo']['gold'] -= step_cost

                                    sanctuary['stepsBought'] = sanctuary.get('stepsBought', 0) + 1
                                    sanctuary['userLevelLastStep'] = player_data['playerInfo'].get('level', 1)
                                    sanctuary['percentGoldLastStep'] = round(player_data['playerInfo']['gold'] * (percent_accumulated_gold / 100))

                                    print(f"   [BREEDING_SANCTUARY_BUY_STEP OK] Paso {sanctuary['stepsBought']}/{level_cfg.get('num_steps')} comprado.")
                                    print(f"                                    Costo: {step_cost} oro | Oro restante: {player_data['playerInfo']['gold']}")

                    elif cmd == 'breeding_sanctuary_upgrade':
                        sanctuary_cfg = game_config.get('sanctuary_breeding', {})
                        upgrades_cfg = sanctuary_cfg.get('upgrades_config', [])

                        sanctuary = player_data['privateState'].get('breedingSanctuary')

                        if not sanctuary:
                            print(f"   [!] Error: El jugador no tiene 'breedingSanctuary' en privateState.")
                        elif sanctuary.get('activated', 0) != 1:
                            print(f"   [!] Error: El Santuario de Cría no está activado.")
                        else:
                            current_level = sanctuary.get('level', 1)
                            level_cfg = next((lvl for lvl in upgrades_cfg if lvl.get('id') == current_level), None)

                            if not level_cfg:
                                print(f"   [!] Error: No se encontró configuración para el nivel {current_level} (¿nivel máximo?).")
                            else:
                                rebuild_cost = level_cfg.get('rebuild_cost', 0)
                                num_steps = level_cfg.get('num_steps', 1)
                                steps_bought = sanctuary.get('stepsBought', 0)

                                gem_cost = rebuild_cost - int(steps_bought * (rebuild_cost / num_steps))
                                gem_cost = max(0, gem_cost)

                                if player_data['playerInfo']['cash'] < gem_cost:
                                    print(f"   [!] Error: Gemas insuficientes para mejorar ({gem_cost} requeridas, tiene {player_data['playerInfo']['cash']}).")
                                else:
                                    player_data['playerInfo']['cash'] -= gem_cost

                                    item_cfg = get_item_config(game_config, level_cfg.get('item_id'))
                                    xp_reward = item_cfg.get('xp', 0) if item_cfg else 0
                                    player_data['playerInfo']['xp'] = player_data['playerInfo'].get('xp', 0) + xp_reward

                                    sanctuary['level'] = current_level + 1
                                    sanctuary['stepsBought'] = 0
                                    sanctuary['userLevelLastStep'] = player_data['playerInfo'].get('level', 1)
                                    percent_accumulated_gold = sanctuary_cfg.get('general_config', {}).get('PERCENT_OF_ACCUMULATED_GOLD', 5)
                                    sanctuary['percentGoldLastStep'] = round(player_data['playerInfo']['gold'] * (percent_accumulated_gold / 100))

                                    print(f"   [BREEDING_SANCTUARY_UPGRADE OK] Santuario subio a nivel {sanctuary['level']}.")
                                    print(f"                                   Costo: {gem_cost} gemas | Gemas restantes: {player_data['playerInfo']['cash']}")
                                    print(f"                                   XP otorgado: {xp_reward} | XP total: {player_data['playerInfo']['xp']}")

                                    building_uid = "152"
                                    if building_uid in player_data['map']['items']:
                                        item_data = player_data['map']['items'][building_uid]
                                        current_type_id = str(item_data[0])

                                        all_items = game_config.get('items', {})
                                        current_item_conf = all_items.get(current_type_id) if isinstance(all_items, dict) \
                                            else next((i for i in all_items if str(i.get('id')) == current_type_id), None)

                                        if current_item_conf and 'upgrades_to' in current_item_conf:
                                            new_type_id = str(current_item_conf['upgrades_to'])
                                            new_item_conf = all_items.get(new_type_id) if isinstance(all_items, dict) \
                                                else next((i for i in all_items if str(i.get('id')) == new_type_id), None)

                                            if new_item_conf:
                                                item_data[0] = int(new_type_id)
                                                print(f"   [-] Item del edificio {building_uid} actualizado de {current_type_id} a {new_type_id}.")
                                            else:
                                                print(f"   [!] Aviso: No se encontró config del nuevo item '{new_type_id}'.")
                                        else:
                                            print(f"   [!] Aviso: El item actual '{current_type_id}' no tiene 'upgrades_to' definido.")
                                    else:
                                        print(f"   [!] Aviso: No se encontró el item del edificio (uid '152') en map.items.")

                    elif cmd == 'deity_world_mine_start_production':
                        mine_uid = int(args[0])
 
                        dw = player_data.setdefault('deityWorld', {})
                        mine_instance = None
                        for m in dw.get('mines', []):
                            if int(m.get('uid', -1)) == mine_uid:
                                mine_instance = m
                                break
 
                        if mine_instance is None:
                            print(f"   [!] Error: no se encontró la mina con uid {mine_uid} en el jugador")
                        else:
                            mine_cfg = None
                            for m in game_config.get('deity_world_buildings', {}).get('mines', []):
                                if int(m.get('id')) == int(mine_instance.get('iid')):
                                    mine_cfg = m
                                    break
 
                            if mine_cfg is None:
                                print(f"   [!] Error: no se encontró la config de la mina iid {mine_instance.get('iid')}")
                            else:
                                crystals_config = game_config.get('deity_world_crystals', {}).get('crystals', [])
                                max_purity_id = mine_cfg.get('production_info_max_purity_crystal')
                                total_crystals = mine_cfg.get('production', [0])[0]
                                production_period = mine_cfg.get('production_period', 3600)
                                mining_cost = mine_cfg.get('production_cost', {})
                                gold_cost = mining_cost.get('g', 0)
                                current_ts = player_data.get('timestamp', int(time.time()))

                                reward = distribute_mine_crystals(
                                    total_crystals=total_crystals,
                                    max_purity_id=max_purity_id,
                                    crystals_config=crystals_config
                                )

                                player_data['playerInfo']['gold'] -= gold_cost
                                mine_instance['currentProduction'] = reward
                                mine_instance['productionStartsAt'] = current_ts
                                mine_instance['productionEndsAt'] = current_ts + production_period
 
                                cmd_result = reward
 
                                print(f"   [DEITY_WORLD_MINE_START_PRODUCTION OK] uid {mine_uid} | listo en {production_period}s | recompensa: {reward}")
 
                    elif cmd == 'deity_world_mine_collect_speed_up':
                        mine_uid = int(args[0])
 
                        dw = player_data.setdefault('deityWorld', {})
                        mine_instance = None
                        for m in dw.get('mines', []):
                            if int(m.get('uid', -1)) == mine_uid:
                                mine_instance = m
                                break
 
                        if mine_instance is None:
                            print(f"   [!] Error: no se encontró la mina con uid {mine_uid} en el jugador")
                        else:
                            mine_cfg = None
                            for m in game_config.get('deity_world_buildings', {}).get('mines', []):
                                if int(m.get('id')) == int(mine_instance.get('iid')):
                                    mine_cfg = m
                                    break

                            if mine_cfg is None:
                                print(f"   [!] Error: no se encontró la config de la mina {mine_instance.get('iid')}")
                            else:
                                production_time = mine_cfg.get('production_period')
                                current_ts = player_data.get('timestamp', int(time.time()))
                                start_time = mine_instance['productionStartsAt']

                                elapsed_time = current_ts - start_time
                                time_remaining = max(0, production_time - elapsed_time)

                                gems_cost = max(1, (time_remaining + 59) // 60)

                                if player_data['playerInfo']['cash'] >= gems_cost:
                                    player_data['playerInfo']['cash'] -= gems_cost

                                    mine_instance['productionEndsAt'] = current_ts - production_time
 
                                    print(f"   [DEITY_WORLD_MINE_COLLECT_SPEED_UP OK] se han usado gemas para adelantar la recolección de la mina")
                                    print(f"                                          Gemas usadas: {gems_cost} | Gemas totales: {player_data['playerInfo']['cash']}")

                    elif cmd == 'deity_world_mine_collect':
                        mine_uid = int(args[0])
 
                        dw = player_data.setdefault('deityWorld', {})
                        mine_instance = None
                        for m in dw.get('mines', []):
                            if int(m.get('uid', -1)) == mine_uid:
                                mine_instance = m
                                break
 
                        if mine_instance is None:
                            print(f"   [!] Error: no se encontró la mina con uid {mine_uid} en el jugador")
                        else:
                            production = mine_instance.get('currentProduction') or {}
                            crystal_bag = dw.setdefault('crystalBag', {})
 
                            for crystal_id_str, qty in production.items():
                                crystal_bag[crystal_id_str] = crystal_bag.get(crystal_id_str, 0) + int(qty)
 
                            mine_instance['currentProduction'] = None
                            mine_instance['productionEndsAt'] = 0
 
                            print(f"   [DEITY_WORLD_MINE_COLLECT OK] uid {mine_uid} | cristales entregados: {production}")

                    elif cmd == 'deity_world_building_upgrade':
                        item_uid = int(args[0])
                        group_type = str(args[1])
                        dw = player_data.setdefault('deityWorld', {})

                        if group_type == "DWMINES":
                            mine_instance = None
                            for m in dw.get('mines', []):
                                if int(m.get('uid', -1)) == item_uid:
                                    mine_instance = m
                                    break
     
                            if mine_instance is None:
                                print(f"   [!] Error: no se encontró la mina con uid {item_uid} en el jugador")
                            else:
                                mine_cfg = None
                                for m in game_config.get('deity_world_buildings', {}).get('mines', []):
                                    if int(m.get('id')) == int(mine_instance.get('iid')):
                                        mine_cfg = m
                                        break

                                if mine_cfg is None:
                                    print(f"   [!] Error: no se encontró la config de la mina {mine_instance.get('iid')}")
                                else:
                                    upgrade_cost = mine_cfg.get('upgrade_cost', {})
                                    platinum_cost = upgrade_cost.get('p', 0)
                                    upgrade_time = mine_cfg.get('upgrade_period', 3600)
                                    next_id = mine_cfg.get('upgrades_to')
                                    current_ts = player_data.get('timestamp', int(time.time()))

                                    player_data['playerInfo']['platinum'] -= platinum_cost
                                    mine_instance['upgradeStartsAt'] = current_ts
                                    mine_instance['upgradeEndsAt'] = current_ts + upgrade_time

                                    print(f"   [DEITY_WORLD_BUILDING_UPGRADE OK] {mine_cfg.get('name')} fue puesta a mejorar de nivel")
                                    
                        elif group_type == "DWHABITAT":
                            habitat_instance = None
                            for m in dw.get('habitats', []):
                                if int(m.get('uid', -1)) == item_uid:
                                    habitat_instance = m
                                    break
     
                            if habitat_instance is None:
                                print(f"   [!] Error: no se encontró el habitat con uid {item_uid} en el jugador")
                            else:
                                habitat_cfg = None
                                for h in game_config.get('deity_world_buildings', {}).get('habitats', []):
                                    if int(h.get('id')) == int(habitat_instance.get('iid')):
                                        habitat_cfg = h
                                        break

                                if habitat_cfg is None:
                                    print(f"   [!] Error: no se encontró la config del habitat {habitat_instance.get('iid')}")
                                else:
                                    upgrade_cost = habitat_cfg.get('upgrade_cost', {})
                                    platinum_cost = upgrade_cost.get('p', 0)
                                    upgrade_time = habitat_cfg.get('upgrade_period', 3600)
                                    next_id = habitat_cfg.get('upgrades_to')
                                    current_ts = player_data.get('timestamp', int(time.time()))

                                    player_data['playerInfo']['platinum'] -= platinum_cost
                                    habitat_instance['upgradeStartsAt'] = current_ts
                                    habitat_instance['upgradeEndsAt'] = current_ts + upgrade_time

                                    print(f"   [DEITY_WORLD_BUILDING_UPGRADE OK] {habitat_cfg.get('name')} fue puesto a mejorar de nivel")

                    elif cmd == 'deity_world_building_upgrade_finish':
                        item_uid = int(args[0])
                        group_type = str(args[1])
                        dw = player_data.setdefault('deityWorld', {})
 
                        if group_type == "DWMINES":
                            mine_instance = None
                            for m in dw.get('mines', []):
                                if int(m.get('uid', -1)) == item_uid:
                                    mine_instance = m
                                    break
     
                            if mine_instance is None:
                                print(f"   [!] Error: no se encontró la mina con uid {item_uid} en el jugador")
                            else:
                                mine_cfg = None
                                for m in game_config.get('deity_world_buildings', {}).get('mines', []):
                                    if int(m.get('id')) == int(mine_instance.get('iid')):
                                        mine_cfg = m
                                        break

                                if mine_cfg is None:
                                    print(f"   [!] Error: no se encontró la config de la mina {mine_instance.get('iid')}")
                                else:
                                    next_id = mine_cfg.get('upgrades_to')
                                    current_ts = player_data.get('timestamp', int(time.time()))

                                    mine_instance['iid'] = next_id
                                    mine_instance['upgradeEndsAt'] = 0
                                    mine_instance['upgradeStartsAt'] = 0

                                    print(f"   [DEITY_WORLD_BUILDING_UPGRADE OK] {mine_cfg.get('name')} ha completado su mejora")
                        else:
                            habitat_instance = None
                            for m in dw.get('habitats', []):
                                if int(m.get('uid', -1)) == item_uid:
                                    habitat_instance = m
                                    break
     
                            if habitat_instance is None:
                                print(f"   [!] Error: no se encontró el habitat con uid {item_uid} en el jugador")
                            else:
                                habitat_cfg = None
                                for h in game_config.get('deity_world_buildings', {}).get('habitats', []):
                                    if int(h.get('id')) == int(habitat_instance.get('iid')):
                                        habitat_cfg = h
                                        break

                                if habitat_cfg is None:
                                    print(f"   [!] Error: no se encontró la config del habitat {habitat_instance.get('iid')}")
                                else:
                                    next_id = habitat_cfg.get('upgrades_to')
                                    current_ts = player_data.get('timestamp', int(time.time()))

                                    habitat_instance['iid'] = next_id
                                    habitat_instance['upgradeEndsAt'] = 0
                                    habitat_instance['upgradeStartsAt'] = 0

                                    print(f"   [DEITY_WORLD_BUILDING_UPGRADE OK] {habitat_cfg.get('name')} ha completado su mejora")

                    elif cmd == 'deity_world_building_upgrade_speed_up':
                        item_uid = int(args[0])
                        group_type = str(args[1])
                        dw = player_data.setdefault('deityWorld', {})
 
                        if group_type == "DWMINES":
                            mine_instance = None
                            for m in dw.get('mines', []):
                                if int(m.get('uid', -1)) == item_uid:
                                    mine_instance = m
                                    break
     
                            if mine_instance is None:
                                print(f"   [!] Error: no se encontró la mina con uid {item_uid} en el jugador")
                            else:
                                mine_cfg = None
                                for m in game_config.get('deity_world_buildings', {}).get('mines', []):
                                    if int(m.get('id')) == int(mine_instance.get('iid')):
                                        mine_cfg = m
                                        break

                                if mine_cfg is None:
                                    print(f"   [!] Error: no se encontró la config de la mina {mine_instance.get('iid')}")
                                else:
                                    next_id = mine_cfg.get('upgrades_to')
                                    upgrade_time = mine_cfg.get('upgrade_period')
                                    current_ts = player_data.get('timestamp', int(time.time()))
                                    start_time = mine_instance['upgradeStartsAt']

                                    elapsed_time = current_ts - start_time
                                    time_remaining = max(0, upgrade_time - elapsed_time)

                                    gems_cost = max(1, (time_remaining + 3599) // 3600)

                                    if player_data['playerInfo']['cash'] >= gems_cost:
                                            player_data['playerInfo']['cash'] -= gems_cost
                                            
                                    mine_instance['iid'] = next_id
                                    mine_instance['upgradeEndsAt'] = 0
                                    mine_instance['upgradeStartsAt'] = 0

                                    print(f"   [DEITY_WORLD_BUILDING_UPGRADE_SPEED_UP OK] Se han usado gemas para adelantar la mejora de {mine_cfg.get('name')}")
                                    print(f"                                              Gemas usadas: {gems_cost} | Gemas totales: {player_data['playerInfo']['cash']}")

                        elif group_type == "DWHABITAT":
                            habitat_instance = None
                            for m in dw.get('habitats', []):
                                if int(m.get('uid', -1)) == item_uid:
                                    habitat_instance = m
                                    break
     
                            if habitat_instance is None:
                                print(f"   [!] Error: no se encontró el habitat con uid {item_uid} en el jugador")
                            else:
                                habitat_cfg = None
                                for h in game_config.get('deity_world_buildings', {}).get('habitats', []):
                                    if int(h.get('id')) == int(habitat_instance.get('iid')):
                                        habitat_cfg = h
                                        break

                                if habitat_cfg is None:
                                    print(f"   [!] Error: no se encontró la config del habitat {habitat_instance.get('iid')}")
                                else:
                                    next_id = habitat_cfg.get('upgrades_to')
                                    upgrade_time = habitat_cfg.get('upgrade_period')
                                    current_ts = player_data.get('timestamp', int(time.time()))
                                    start_time = habitat_instance['upgradeStartsAt']

                                    elapsed_time = current_ts - start_time
                                    time_remaining = max(0, upgrade_time - elapsed_time)

                                    gems_cost = max(1, (time_remaining + 3599) // 3600)

                                    if player_data['playerInfo']['cash'] >= gems_cost:
                                            player_data['playerInfo']['cash'] -= gems_cost
                                            
                                    habitat_instance['iid'] = next_id
                                    habitat_instance['upgradeEndsAt'] = 0
                                    habitat_instance['upgradeStartsAt'] = 0

                                    print(f"   [DEITY_WORLD_BUILDING_UPGRADE_SPEED_UP OK] Se han usado gemas para adelantar la mejora de {habitat_cfg.get('name')}")
                                    print(f"                                              Gemas usadas: {gems_cost} | Gemas totales: {player_data['playerInfo']['cash']}")

                    elif cmd == 'deity_world_summoning_start':
                        wall_uid = int(args[0])
                        dragon_id = int(args[1])
 
                        dw = player_data.setdefault('deityWorld', {})
                        wall_instance = None
                        for s in dw.get('summoningBuildings', []):
                            if int(s.get('uid', -1)) == wall_uid:
                                wall_instance = s
                                break
 
                        if wall_instance is None:
                            print(f"   [!] Error: no se encontró el summoning wall con uid {wall_uid}")
                        else:
                            dragon_cfg = None
                            for d in game_config.get('deity_world_dragons', {}).get('dragons', []):
                                if int(d.get('id')) == dragon_id:
                                    dragon_cfg = d
                                    break
 
                            if dragon_cfg is None:
                                print(f"   [!] Error: no se encontró el dragón con id {dragon_id} en deity_world_dragons")
                            else:
                                summon_period = dragon_cfg.get('summon_period', 3600)
                                current_ts = player_data.get('timestamp', int(time.time()))
 
                                wall_instance['summonDragonId'] = dragon_id
                                wall_instance['summonEndsAt'] = current_ts + summon_period
 
                                print(f"   [DEITY_WORLD_SUMMONING_START OK] wall uid {wall_uid} | dragón {dragon_cfg.get('name')} (id {dragon_id}) | listo en {summon_period}s")
 
                    elif cmd == 'deity_world_summoning_place_dragon':
                        wall_uid = int(args[0])
                        habitat_uid = int(args[1])
                        new_dragon_uid = int(args[2])
 
                        dw = player_data.setdefault('deityWorld', {})
                        wall_instance = None
                        for s in dw.get('summoningBuildings', []):
                            if int(s.get('uid', -1)) == wall_uid:
                                wall_instance = s
                                break
 
                        habitat_instance = None
                        for h in dw.get('habitats', []):
                            if int(h.get('uid', -1)) == habitat_uid:
                                habitat_instance = h
                                break
 
                        if wall_instance is None:
                            print(f"   [!] Error: no se encontró el summoning wall con uid {wall_uid}")
                        elif habitat_instance is None:
                            print(f"   [!] Error: no se encontró el hábitat con uid {habitat_uid}")
                        else:
                            dragon_id = wall_instance.get('summonDragonId')
                            current_ts = player_data.get('timestamp', int(time.time()))
 
                            habitat_instance.setdefault('dragons', [])
                            habitat_instance['dragons'].append({
                                "iid": dragon_id,
                                "uid": new_dragon_uid,
                                "habitatUid": habitat_uid
                            })

                            if habitat_instance.get('productionUpdateTime', 0) == 0:
                                habitat_instance['productionUpdateTime'] = current_ts
 
                            wall_instance['summonDragonId'] = -1
                            wall_instance['summonEndsAt'] = 0
 
                            print(f"   [DEITY_WORLD_SUMMONING_PLACE_DRAGON OK] dragón id {dragon_id} (uid {new_dragon_uid}) colocado en hábitat uid {habitat_uid}")

                    elif cmd == 'deity_world_habitat_collect':
                        habitat_uid = int(args[0])
                        platinum_amount = int(args[1])

                        dw = player_data.setdefault('deityWorld', {})
                        habitat_instance = None
                        for h in dw.get('habitats', []):
                            if int(h.get('uid', -1)) == habitat_uid:
                                habitat_instance = h
                                break

                        if habitat_instance is None:
                            print(f"   [!] Error: no se encontró el hábitat con uid {habitat_uid}")
                        else:
                            current_ts = player_data.get('timestamp', int(time.time()))

                            habitat_instance['productionUpdateTime'] = current_ts
                            player_data['playerInfo']['platinum'] += platinum_amount

                            print(f"   [DEITY_WORLD_HABITAT_COLLECT OK] uid {habitat_uid} | +{platinum_amount} platinum | platinum total: {player_data['playerInfo']['platinum']}")

                    elif cmd == 'deity_world_craft':
                        building_uid = int(args[0])
                        crystal_id = int(args[1])

                        dw = player_data.setdefault('deityWorld', {})
                        crystal_bag = dw.setdefault('crystalBag', {})

                        crystal_cfg = None
                        for c in game_config.get('deity_world_crystals', {}).get('crystals', []):
                            if int(c.get('id')) == crystal_id:
                                crystal_cfg = c
                                break

                        if crystal_cfg is None:
                            print(f"   [!] Error: no se encontró el cristal con id {crystal_id}")
                        else:
                            requirements = crystal_cfg.get('craft_crystals_requirements') or {}
                            platinum_cost = crystal_cfg.get('craft_resources', {}).get('p', 0)

                            for req_id, req_qty in requirements.items():
                                crystal_bag[req_id] = max(0, crystal_bag.get(req_id, 0) - int(req_qty))

                            crystal_bag[str(crystal_id)] = crystal_bag.get(str(crystal_id), 0) + 1
                            player_data['playerInfo']['platinum'] = max(0, player_data['playerInfo']['platinum'] - platinum_cost)

                            print(f"   [DEITY_WORLD_CRAFT OK] {crystal_cfg.get('name')} craftado en taller uid {building_uid}")
                            print(f"                          -{platinum_cost} platinum | requisitos consumidos: {requirements}")

                    elif cmd == 'deity_world_craft_filling_with_gems':
                        building_uid = int(args[0])
                        crystal_id = int(args[1])

                        dw = player_data.setdefault('deityWorld', {})
                        crystal_bag = dw.setdefault('crystalBag', {})

                        crystal_cfg = None
                        for c in game_config.get('deity_world_crystals', {}).get('crystals', []):
                            if int(c.get('id')) == crystal_id:
                                crystal_cfg = c
                                break

                        if crystal_cfg is None:
                            print(f"   [!] Error: no se encontró el cristal con id {crystal_id}")
                        else:
                            requirements = crystal_cfg.get('craft_crystals_requirements') or {}
                            gem_conversion = crystal_cfg.get('gem_conversion', 0)

                            for req_id, req_qty in requirements.items():
                                current_qty = crystal_bag.get(req_id, 0)
                                missing_qty = max(0, int(req_qty) - current_qty)
                                cost_per_unit = gem_conversion / int(req_qty)
                                gems_to_charge = int(round(missing_qty * cost_per_unit))

                                player_data['playerInfo']['cash'] = max(0, player_data['playerInfo']['cash'] - gems_to_charge)

                                crystal_bag[req_id] = 0

                                print(f"   [DEITY_WORLD_CRAFT_FILLING_WITH_GEMS] faltaban {missing_qty} de cristal {req_id} -> -{gems_to_charge} gemas")

                            crystal_bag[str(crystal_id)] = crystal_bag.get(str(crystal_id), 0) + 1

                            print(f"   [DEITY_WORLD_CRAFT_FILLING_WITH_GEMS OK] {crystal_cfg.get('name')} craftado con gemas en taller uid {building_uid}")

                    elif cmd == 'deity_world_fusion':
                        shrine_uid = int(args[0])
                        dragon_uid = int(args[1])

                        dw = player_data.setdefault('deityWorld', {})
                        crystal_bag = dw.setdefault('crystalBag', {})

                        dragon_instance = None
                        for h in dw.get('habitats', []):
                            for d_inst in h.get('dragons', []):
                                if int(d_inst.get('uid', -1)) == dragon_uid:
                                    dragon_instance = d_inst
                                    break
                            if dragon_instance:
                                break

                        if dragon_instance is None:
                            print(f"   [!] Error: no se encontró el dragón con uid {dragon_uid} en ningún hábitat")
                        else:
                            dragon_cfg = None
                            for d in game_config.get('deity_world_dragons', {}).get('dragons', []):
                                if int(d.get('id')) == int(dragon_instance.get('iid')):
                                    dragon_cfg = d
                                    break

                            if dragon_cfg is None:
                                print(f"   [!] Error: no se encontró la config del dragón iid {dragon_instance.get('iid')}")
                            else:
                                crystal_cost = dragon_cfg.get('fusion_crystal_cost') or {}
                                next_id = dragon_cfg.get('fusion_next_id')

                                for crys_id, qty in crystal_cost.items():
                                    crystal_bag[crys_id] = max(0, crystal_bag.get(crys_id, 0) - int(qty))

                                dragon_instance['iid'] = next_id

                                print(f"   [DEITY_WORLD_FUSION OK] dragón {dragon_cfg.get('name')} evolucionó de nivel {dragon_cfg.get('level')} a {dragon_cfg.get('level')+1}")
                                print(f"                           cristales consumidos: {crystal_cost} | crystalBag actual: {crystal_bag}")

                    elif cmd == 'deity_world_breeding_start':
                        breeding_uid = int(args[0])
                        parent1_uid  = int(args[1])
                        parent2_uid  = int(args[2])

                        dw = player_data.setdefault('deityWorld', {})

                        breeding_instance = None
                        for b in dw.get('breedingBuildings', []):
                            if int(b.get('uid', -1)) == breeding_uid:
                                breeding_instance = b
                                break
                            
                        dragon1_entry = None
                        dragon1_habitat = None
                        dragon2_entry = None
                        dragon2_habitat = None

                        for h in dw.get('habitats', []):
                            for dr in h.get('dragons', []):
                                dr_uid = int(dr.get('uid', -1))
                                if dr_uid == parent1_uid:
                                    dragon1_entry, dragon1_habitat = dr, h
                                elif dr_uid == parent2_uid:
                                    dragon2_entry, dragon2_habitat = dr, h

                        if breeding_instance is None:
                            print(f"   [!] Error: no se encontró el criadero (breedingBuilding) con uid {breeding_uid}")
                        elif dragon1_entry is None or dragon2_entry is None:
                            print(f"   [!] Error: no se encontraron ambos padres (uids {parent1_uid}, {parent2_uid}) "
                                  f"en los hábitats de deityWorld")
                        else:
                            dragon1_iid = dragon1_entry.get('iid')
                            dragon2_iid = dragon2_entry.get('iid')

                            dragon_db = build_dragon_db(game_config)

                            deity_config = game_config.get('deity_world_dragons', {})
                            deity_dragon_db = build_deity_dragon_db(deity_config)

                            outcome_id = get_ancient_breed_result(
                                dragon1_iid, dragon2_iid,
                                deity_dragon_db, dragon_db
                            )

                            current_ts = player_data.get('timestamp', int(time.time()))
                            breeding_time = dragon_db.get(outcome_id, {}).get('breeding_time', 57600)

                            dragon1_habitat['dragons'] = [
                                d for d in dragon1_habitat.get('dragons', [])
                                if int(d.get('uid', -1)) != parent1_uid
                            ]
                            dragon2_habitat['dragons'] = [
                                d for d in dragon2_habitat.get('dragons', [])
                                if int(d.get('uid', -1)) != parent2_uid
                            ]

                            breeding_instance['dragons'] = [dragon1_entry, dragon2_entry]
                            breeding_instance['result'] = outcome_id
                            breeding_instance['breedingEndsAt'] = current_ts + breeding_time

                            print(f"   [DEITY_WORLD_BREEDING_START OK] Criadero={breeding_uid} | "
                                  f"padres iid=({dragon1_iid},{dragon2_iid}) uids=({parent1_uid},{parent2_uid}) | "
                                  f"resultado={outcome_id} ({dragon_db.get(outcome_id, {}).get('name', '?')}) | "
                                  f"termina en {breeding_time}s")

                            cmd_result = outcome_id
                            
                    elif cmd == 'deity_world_breeding_speed_up':
                        breeding_uid = int(args[0])

                        dw = player_data.setdefault('deityWorld', {})
                        breeding_instance = None
                        for b in dw.get('breedingBuildings', []):
                            if int(b.get('uid', -1)) == breeding_uid:
                                breeding_instance = b
                                break

                        if breeding_instance is None:
                            print(f"[!] Error: no se encontró el criadero (breedingBuilding) con uid {breeding_uid}")
                        elif not breeding_instance.get('result'):
                            print(f"[!] Error: el criadero {breeding_uid} no tiene un cruce en curso.")
                        else:
                            outcome_id = breeding_instance['result']
                            dragon_db = build_dragon_db(game_config)
                            breeding_time = dragon_db.get(outcome_id, {}).get('breeding_time', 0)

                            current_ts = int(time.time())
                            ends_at = int(breeding_instance.get('breedingEndsAt', current_ts))
                            time_remaining = max(0, ends_at - current_ts)
                            gems_cost = max(1, (time_remaining + 3599) // 3600)

                            if player_data['playerInfo']['cash'] >= gems_cost:
                                player_data['playerInfo']['cash'] -= gems_cost

                                breeding_instance['breedingEndsAt'] = ends_at - breeding_time

                                print(f"   [DEITY_WORLD_BREEDING_SPEED_UP OK] se han usado gemas para acelerar el huevo {outcome_id}")
                                print(f"                                      Gemas usadas: {gems_cost} | Gemas totales:{player_data['playerInfo']['cash']}")
                            else:
                                print(f"[!] Sin gemas suficientes para deity_world_breeding_speed_up en criadero {breeding_uid}")

                    elif cmd == 'deity_world_breeding_finish':
                        breeding_uid     = int(args[0])
                        new_egg_uid      = args[1]
                        hatchery_iso_id  = str(args[2])

                        dw = player_data.setdefault('deityWorld', {})
                        breeding_instance = None
                        for b in dw.get('breedingBuildings', []):
                            if int(b.get('uid', -1)) == breeding_uid:
                                breeding_instance = b
                                break

                        if breeding_instance is None:
                            print(f"[!] Error: no se encontró el criadero (breedingBuilding) con uid {breeding_uid}")
                        elif not breeding_instance.get('result'):
                            print(f"[!] Error: el criadero {breeding_uid} no tiene un cruce en curso.")
                        else:
                            dragon_id = breeding_instance['result']

                            for parent_entry in breeding_instance.get('dragons', []):
                                target_habitat_uid = parent_entry.get('habitatUid')
                                target_habitat = None
                                for h in dw.get('habitats', []):
                                    if int(h.get('uid', -1)) == int(target_habitat_uid):
                                        target_habitat = h
                                        break
                                if target_habitat is not None:
                                    target_habitat.setdefault('dragons', [])
                                    target_habitat['dragons'].append(parent_entry)
                                else:
                                    print(f"[!] Aviso: no se encontró el hábitat original (uid {target_habitat_uid}) "
                                          f"para el padre uid {parent_entry.get('uid')}; no se pudo devolver.")

                            breeding_instance['dragons'] = []
                            breeding_instance['result'] = 0
                            breeding_instance['breedingEndsAt'] = 0

                            if 'eggs' not in player_data['map']:
                                player_data['map']['eggs'] = []

                            new_egg = {
                                "id": new_egg_uid,
                                "type": dragon_id,
                                "name": random.choice(nombres_dragon),
                                "xp": 0,
                                "ts": int(time.time())
                            }
                            player_data['map']['eggs'].append(new_egg)

                            dragon_db = build_dragon_db(game_config)
                            print(f"   [DEITY_WORLD_BREEDING_FINISH OK] Criadero={breeding_uid} | "
                                  f"                                    Huevo creado: {dragon_id} ({dragon_db.get(dragon_id, {}).get('name', '?')}) "
                                  f"                                    (UID: {new_egg_uid}) -> Hatchery {hatchery_iso_id}")

                            cmd_result = dragon_id

                    elif cmd == 'IslandTournamentStartBattle':
                        opponent_user_id = str(args[0])
                        boosted = bool(args[1])

                        game_config = load_game_config(user_id)
                        tvars = game_config.get('island_tournament', {}).get('variables', {})
                        energy_cost = int(tvars.get('ENERGY_BOOST_COST', 6)) if boosted else int(tvars.get('ENERGY_COST', 1))

                        state = player_data.setdefault('islandTournament', {})
                        state.setdefault('energy', {
                            'amount': int(tvars.get('MAX_ENERGY', 6)),
                            'timestamp': int(time.time())
                        })

                        if int(state['energy']['amount']) >= energy_cost:
                            state['energy']['amount'] = int(state['energy']['amount']) - energy_cost
                            print(f"   [ISLAND_TOURNAMENT_START_BATTLE OK] vs {opponent_user_id} | "
                                  f"boosted={boosted} | costo={energy_cost} energía | "
                                  f"restante={state['energy']['amount']}")
                        else:
                            print(f"[!] Energía insuficiente para pelear en Island Tournament "
                                  f"(tiene {state['energy']['amount']}, necesita {energy_cost})")

                        cmd_result = None

                    elif cmd == 'IslandTournamentEndBattle':
                        opponent_user_id = str(args[0])
                        won = bool(args[1])
                        score_raw = args[2]

                        try:
                            score_data = json.loads(score_raw) if isinstance(score_raw, str) else (score_raw or {})
                        except (ValueError, TypeError):
                            score_data = {}
                            print(f"[!] No se pudo parsear el score de IslandTournamentEndBattle: {score_raw!r}")

                        for dragon_uid_raw, kills in score_data.items():
                            try:
                                dragon_uid = int(dragon_uid_raw)
                                kills = int(kills)
                            except (ValueError, TypeError):
                                continue
                            for d in player_data.get('map', {}).get('dragons', []):
                                if d.get('id') == dragon_uid:
                                    d['nbKill'] = int(d.get('nbKill', 0)) + kills
                                    break

                        state = player_data.setdefault('islandTournament', {})
                        state.setdefault('wins', 0)
                        state.setdefault('streak', 0)
                        state.setdefault('score', 0)

                        if won:
                            state['wins'] = int(state['wins']) + 1
                            state['streak'] = int(state['streak']) + 1

                            game_config = load_game_config(user_id)
                            base_points = int(game_config.get('island_tournament', {}).get('variables', {}).get('BASE_POINTS_PER_WIN', 10))
                            state['score'] = int(state.get('score', 0)) + base_points
                        else:
                            state['streak'] = 0

                        print(f"   [ISLAND_TOURNAMENT_END_BATTLE OK] vs {opponent_user_id} | won={won} | "
                              f"wins={state['wins']} | streak={state['streak']} | score={state.get('score')} | "
                              f"kills_reportadas={score_data}")

                        cmd_result = None

                    elif cmd == 'combat_leagues_initialize':
                        ps = player_data.setdefault('privateState', {})
                        league = ps.get('combatLeague')

                        if not league:
                            league = build_combat_league(player_data, game_config, user_id)
                            ps['combatLeague'] = league
                            print(f"   [COMBAT_LEAGUES_INITIALIZE] Liga {league['id']} creada con {len(league['combats'])} combates.")
                        else:
                            if normalize_combat_league(league):
                                print(f"   [COMBAT_LEAGUES_INITIALIZE] Liga {league['id']} migrada de 'lvl' a 'level'.")
                            else:
                                print(f"   [COMBAT_LEAGUES_INITIALIZE] Liga {league['id']} existente devuelta.")

                        cmd_result = {
                            "initialized": True,
                            "currentLeague": league
                        }

                    elif cmd == 'combat_leagues_start_combat':
                        opponent_id = str(args[0])
                        ps = player_data.setdefault('privateState', {})
                        league = ps.get('combatLeague')

                        if not league:
                            print(f"   [!] Error: no hay liga de combate guardada para iniciar combate contra {opponent_id}.")
                        else:
                            now = int(time.time())
                            params, league_cfg = get_combat_league_config(game_config, int(league['id']))
                            cooldown = int(league_cfg.get('cooldown_time', 21600)) if league_cfg else 21600

                            cds = league.setdefault('cooldownsEndAt', [])
                            available = [i for i, t in enumerate(cds) if int(t) < now]

                            if not available:
                                print(f"   [!] Aviso: se inició un combate sin intentos disponibles (cooldownsEndAt={cds}).")
                            else:
                                was_last = len(available) == 1
                                idx = min(available, key=lambda i: int(cds[i]))
                                new_end = now + cooldown
                                cds[idx] = new_end

                                if was_last:
                                    for i, t in enumerate(cds):
                                        if int(t) >= now:
                                            cds[i] = new_end

                                ps['combatLeagueCurrentOpponent'] = opponent_id
                                left = len([t for t in cds if int(t) < now])
                                print(f"   [COMBAT_LEAGUES_START_COMBAT OK] Combate contra {opponent_id} iniciado.")
                                print(f"                                    Intentos restantes: {left} | recarga en {cooldown}s")
                    
                except Exception as e:
                    print(f"[!] Error en comando '{cmd}' (N: {cmd_number}): {e}")
                    traceback.print_exc()
                    
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
                print(f"[+] Juego guardado para usuario {player_data['playerInfo']['name']} con pid {user_id}...")
            else:
                print(f"[~] No se aplicaron cambios porque los comandos recibidos no están añadidos: {comandos_ignorados}")

            if user_id in jugadores_sse:
                jugadores_sse[user_id].put("JUEGO_GUARDADO")
            
        except Exception as e:
            print(f"[!] Error procesando packet.php: {e}")
            traceback.print_exc()

    response_data = {
        "result": True,
        "response": response_results,
        "ts": int(time.time()),
        "publishActions": 0
    }

    signed_response = sign_packet(response_data)
    return sign_packet(response_data)

@app.route('/delete_profile', methods=['POST'])
def delete_profile():
    try:
        data = request.get_json(force=True)
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({"status": "error", "msg": "user_id requerido"}), 400

        user_dir = os.path.join(SRV_DIR, str(user_id))

        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
            _CONFIG_VERIFIED_USERS.discard(str(user_id))
            print(f"[+] [BORRADO] Carpeta de guardado eliminada para el usuario {user_id}")
            return jsonify({"status": "ok", "deleted": True})
        else:
            print(f"[i] [BORRADO] No había carpeta de guardado para {user_id} (solo perfil de login).")
            return jsonify({"status": "ok", "deleted": False})

    except Exception as e:
        print(f"[!] Error en /delete_profile: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

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
        notificar_cliente(user_id, "REFRESH_RESOURCES")
 
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

print("[+] [Mercado] Cargando modulos y ofertas...")
def _ensure_private_state(player_data):
    if 'privateState' not in player_data or not isinstance(player_data['privateState'], dict):
        player_data['privateState'] = {}
    if 'achievement_points' not in player_data['privateState']:
        player_data['privateState']['achievement_points'] = 0
    return player_data

def _resource_cost(res_type, amount):
    rule = RESOURCE_RULES[res_type]
    if res_type == "gems":
        cost = int(round(amount * rule["per_unit"]))
    else:
        cost = int(amount // rule["per_unit"])
    return max(rule["min_cost"], min(rule["max_cost"], cost))

def _roll_resource_offer(res_type):
    rule = RESOURCE_RULES[res_type]
    if res_type == "gems":
        amount = random.randint(rule["min"], rule["max"])
    else:
        step = 50000 if res_type == "gold" else 10000
        amount = random.randrange(rule["min"], rule["max"] + 1, step)
    cost = _resource_cost(res_type, amount)
    return {"type": res_type, "amount": amount, "cost": cost}

def _build_market_dragon_pool(config_data):
    pool = []
    for item in config_data.get('items', []):
        if item.get('group_type') == 'DRAGON' and item.get('category', 0) >= 3:
            pool.append(item)
    return pool

def _dragon_cost(item_cfg):
    category = item_cfg.get('category', 3)
    base = DRAGON_BASE_COST_BY_CATEGORY.get(category)
    if base is None:
        base = 15000 + max(0, category - 5) * DRAGON_BASE_COST_DEFAULT_STEP
    surcharge = sum(ATTRIBUTE_SURCHARGE.get(attr, 0) for attr in item_cfg.get('attributes', []))
    return base + surcharge

def _roll_dragon_offer(dragon_pool, already_chosen_ids):
    candidatos = [d for d in dragon_pool if d['id'] not in already_chosen_ids]
    if not candidatos:
        candidatos = dragon_pool
    item_cfg = random.choice(candidatos)
    return {
        "type": "dragon",
        "dragon_id": item_cfg['id'],
        "name": item_cfg.get('name'),
        "img": item_cfg.get('img_name'),
        "category": item_cfg.get('category'),
        "attributes": item_cfg.get('attributes', []),
        "cost": _dragon_cost(item_cfg),
    }

def generate_market_offers(user_id):
    config_data = load_game_config(user_id)
    dragon_pool = _build_market_dragon_pool(config_data)

    dragon_offers = []
    chosen_dragon_ids = set()
    for _ in range(2):
        d_offer = _roll_dragon_offer(dragon_pool, chosen_dragon_ids)
        chosen_dragon_ids.add(d_offer['dragon_id'])
        dragon_offers.append(d_offer)

    gold_offers = [_roll_resource_offer("gold") for _ in range(2)]
    food_offers = [_roll_resource_offer("food") for _ in range(2)]
    gems_offers = [_roll_resource_offer("gems") for _ in range(2)]

    offers = [
        dragon_offers[0], gold_offers[0], food_offers[0], gems_offers[0],
        dragon_offers[1], gold_offers[1], food_offers[1], gems_offers[1],
    ]

    for idx, offer in enumerate(offers, start=1):
        offer['id'] = idx
        offer['sold'] = False

    market_data = {
        "user_id": str(user_id),
        "generated_at": int(time.time()),
        "next_refresh_at": int(time.time()) + MARKET_REFRESH_SECONDS,
        "offers": offers,
    }

    user_dir = os.path.join(SRV_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    with open(_market_path(user_id), 'w', encoding='utf-8') as f:
        json.dump(market_data, f, indent=2, ensure_ascii=False)

    return market_data

def load_or_create_market(user_id):
    path = _market_path(user_id)

    if not os.path.exists(path):
        return generate_market_offers(user_id)

    with open(path, 'r', encoding='utf-8') as f:
        market_data = json.load(f)

    if int(time.time()) >= market_data.get('next_refresh_at', 0):
        return generate_market_offers(user_id)

    return market_data

def _grant_dragon_to_player(player_data, offer):
    dragon_iid = offer.get("dragon_id")
    
    if not dragon_iid:
        print("[!] Error: La oferta no contiene un ID de dragón válido.")
        return

    if "map" not in player_data or isinstance(player_data["map"], list):
        player_data["map"] = {}

    if "store" not in player_data["map"] or isinstance(player_data["map"]["store"], list):
        player_data["map"]["store"] = {"items": {}, "dragons": []}

    if "dragons" not in player_data["map"]["store"] or not isinstance(player_data["map"]["store"]["dragons"], list):
        player_data["map"]["store"]["dragons"] = []

    nuevo_dragon = {
        "iid": dragon_iid,
        "lvl": 0
    }
    
    player_data["map"]["store"]["dragons"].append(nuevo_dragon)

@app.route('/market_data', methods=['GET'])
def market_data_endpoint():
    try:
        user_id = request.args.get('fb_sig_user')
        player_name = request.args.get('player_name', 'DragonMaster')

        if not user_id:
            return jsonify({"error": "fb_sig_user requerido"}), 400

        player_data = load_player(user_id)
        if 'playerInfo' not in player_data:
            return jsonify({"error": "Jugador no encontrado"}), 404

        player_data = _ensure_private_state(player_data)
        save_player(player_data, user_id)

        market_data = load_or_create_market(user_id)

        remaining = max(0, market_data.get('next_refresh_at', 0) - int(time.time()))

        return jsonify({
            "player_name": player_data['playerInfo'].get('name', player_name),
            "achievement_points": player_data['privateState']['achievement_points'],
            "next_refresh_seconds": remaining,
            "offers": market_data['offers'],
        })

    except Exception as e:
        print(f"[!] Error en /market_data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/market/redeem', methods=['POST'])
def market_redeem():
    try:
        data = request.get_json(force=True)
        user_id = data.get('fb_sig_user')
        offer_id = data.get('offer_id')

        if not user_id or offer_id is None:
            return jsonify({"error": "fb_sig_user y offer_id son requeridos"}), 400

        player_data = load_player(user_id)
        if 'playerInfo' not in player_data:
            return jsonify({"error": "Jugador no encontrado"}), 404

        player_data = _ensure_private_state(player_data)

        market_data = load_or_create_market(user_id)
        offer = next((o for o in market_data['offers'] if o['id'] == offer_id), None)

        if not offer:
            return jsonify({"error": "Oferta no encontrada"}), 404
        if offer.get('sold'):
            return jsonify({"error": "Esta oferta ya fue canjeada"}), 400

        points = player_data['privateState']['achievement_points']
        if points < offer['cost']:
            return jsonify({"error": "No tienes suficientes puntos"}), 400

        player_data['privateState']['achievement_points'] = points - offer['cost']

        message = ""
        if offer['type'] == 'gold':
            player_data['playerInfo']['gold'] += offer['amount']
            message = f"+{offer['amount']} de oro"

        elif offer['type'] == 'food':
            player_data['playerInfo']['food'] += offer['amount']
            message = f"+{offer['amount']} de comida"

        elif offer['type'] == 'gems':
            player_data['playerInfo']['cash'] += offer['amount']
            message = f"+{offer['amount']} gemas"

        elif offer['type'] == 'dragon':
            _grant_dragon_to_player(player_data, offer)
            message = f"¡Nuevo dragón: {offer['name']}!"

        offer['sold'] = True

        with open(_market_path(user_id), 'w', encoding='utf-8') as f:
            json.dump(market_data, f, indent=2, ensure_ascii=False)
        save_player(player_data, user_id)
        notificar_cliente(user_id, "REFRESH_RESOURCES")

        print(f"[+] [MERCADO] Usuario {user_id} canjeó oferta {offer_id} ({offer['type']}) "
              f"por {offer['cost']} puntos.")

        return jsonify({
            "status": "ok",
            "message": message,
            "new_points": player_data['privateState']['achievement_points'],
        })

    except Exception as e:
        print(f"[!] Error en /market/redeem: {e}")
        return jsonify({"error": str(e)}), 500

def _market_path(user_id):
    return os.path.join(SRV_DIR, str(user_id), 'market_data.json')

print("    -> Cargado correctamente...")
@app.route('/market.html')
def serve_market():
    return send_from_directory(TEMPLATES_DIR, 'market.html')

print("[+] [HERRAMIENTAS] Cargando Herramientas...")
print("    -> Disponible: 'Verificador de estructura'")
print("    -> Disponible: 'Acortar tiempo de torneo'")
print("    -> Disponible: 'Acortar tiempo de PvP'")
print("️ "*10 + "\n")
@app.route('/tools.html')
def serve_tools():
    return send_from_directory(TEMPLATES_DIR, 'tools.html')

@app.route('/verify_structure', methods=['POST'])
def verify_structure():
    try:
        data = request.get_json(force=True)
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({"status": "error", "msg": "user_id requerido"}), 400

        user_dir  = os.path.join(SRV_DIR, str(user_id))
        user_file = os.path.join(user_dir, f"{user_id}.json")
        template_file = os.path.join(SRV_DIR, 'player_info_structure_template.json')

        if not os.path.exists(user_file):
            return jsonify({"status": "error", "msg": "No se encontró la partida guardada de ese usuario."}), 404

        if not os.path.exists(template_file):
            return jsonify({"status": "error", "msg": "No se encontró la plantilla de estructura en el servidor."}), 500

        with open(template_file, 'r', encoding='utf-8') as f:
            template = json.load(f)

        with open(user_file, 'r', encoding='utf-8') as f:
            player_data = json.load(f)

        added_keys = []

        for root_key, root_value in template.items():
            if root_key not in player_data:
                player_data[root_key] = copy.deepcopy(root_value)
                added_keys.append(f"{root_key} (creado)")
            else:
                val_jugador = player_data[root_key]
                if isinstance(root_value, dict) and not isinstance(val_jugador, dict):
                    player_data[root_key] = copy.deepcopy(root_value)
                    added_keys.append(f"{root_key} (corregido: de {type(val_jugador).__name__} a dict)")
                elif isinstance(root_value, list) and not isinstance(val_jugador, list):
                    player_data[root_key] = copy.deepcopy(root_value)
                    added_keys.append(f"{root_key} (corregido: de {type(val_jugador).__name__} a list)")

        for block in ['map', 'playerInfo', 'privateState']:
            if block not in template or not isinstance(template[block], dict):
                continue
            if block not in player_data or not isinstance(player_data[block], dict):
                continue

            for sub_key, sub_value in template[block].items():
                if sub_key not in player_data[block]:
                    player_data[block][sub_key] = copy.deepcopy(sub_value)
                    added_keys.append(f"{block}.{sub_key} (creado)")
                else:
                    val_sub_jugador = player_data[block][sub_key]
                    if isinstance(sub_value, dict) and not isinstance(val_sub_jugador, dict):
                        player_data[block][sub_key] = copy.deepcopy(sub_value)
                        added_keys.append(f"{block}.{sub_key} (corregido: de {type(val_sub_jugador).__name__} a dict)")
                    elif isinstance(sub_value, list) and not isinstance(val_sub_jugador, list):
                        player_data[block][sub_key] = copy.deepcopy(sub_value)
                        added_keys.append(f"{block}.{sub_key} (corregido: de {type(val_sub_jugador).__name__} a list)")
                    
        SPECIAL_ITEM_KEY = "152"
        SPECIAL_ITEM_VALUE = [175, 15, 49, 0, 0, 0, {}]
        SPECIAL_ITEM_TYPE = 175

        map_items = player_data.get('map', {}).get('items')
        if isinstance(map_items, dict):
            existing_keys_int = [int(k) for k in map_items.keys() if k.isdigit()]
            current_max = max(existing_keys_int) if existing_keys_int else 0

            entrada_152 = map_items.get(SPECIAL_ITEM_KEY)
            ya_tiene_item_especial = (
                isinstance(entrada_152, list) and len(entrada_152) > 0 and entrada_152[0] == SPECIAL_ITEM_TYPE
            )

            if not ya_tiene_item_especial:
                if SPECIAL_ITEM_KEY in map_items:
                    nuevo_id_item_viejo = str(current_max + 1)
                    map_items[nuevo_id_item_viejo] = map_items[SPECIAL_ITEM_KEY]
                    added_keys.append(f"map.items.{nuevo_id_item_viejo} (reubicado desde 152)")
                    current_max += 1
                    
                map_items[SPECIAL_ITEM_KEY] = copy.deepcopy(SPECIAL_ITEM_VALUE)
                added_keys.append(f"map.items.{SPECIAL_ITEM_KEY}")

                building_value = max(current_max, 152)
            else:
                building_value = current_max

            player_data.setdefault('nextUid', {})
            if player_data['nextUid'].get('building') != building_value:
                player_data['nextUid']['building'] = building_value
                added_keys.append("nextUid.building")

        if added_keys:
            with open(user_file, 'w', encoding='utf-8') as f:
                json.dump(player_data, f, indent=2, ensure_ascii=False)
            print(f"[+] [VERIFICADOR] {len(added_keys)} clave(s) añadidas para el usuario {user_id}: {added_keys}")
        else:
            print(f"[i] [VERIFICADOR] Estructura del usuario {user_id} ya estaba completa.")

        return jsonify({
            "status": "ok",
            "added_keys": added_keys,
            "total_added": len(added_keys)
        })

    except Exception as e:
        print(f"[!] Error en /verify_structure: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route('/shorten_tournament', methods=['POST'])
def shorten_tournament():
    try:
        data = request.get_json(force=True)
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({"status": "error", "msg": "user_id requerido"}), 400

        user_dir  = os.path.join(SRV_DIR, str(user_id))
        user_file = os.path.join(user_dir, f"{user_id}.json")

        if not os.path.exists(user_file):
            return jsonify({"status": "error", "msg": "No se encontró la partida guardada de ese usuario."}), 404

        with open(user_file, 'r', encoding='utf-8') as f:
            player_data = json.load(f)

        private_state = player_data.get('privateState', {})
        SECONDS_12H = 12 * 3600

        if 'beginTournamentTs' not in private_state or 'endTournamentTs' not in private_state:
            return jsonify({"status": "error", "msg": "El jugador no tiene datos de torneo."}), 400

        private_state['beginTournamentTs'] = max(0, private_state['beginTournamentTs'] - SECONDS_12H)
        private_state['endTournamentTs']   = max(0, private_state['endTournamentTs'] - SECONDS_12H)

        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(player_data, f, indent=2, ensure_ascii=False)

        print(f"[+] [TORNEO] Tiempo acortado 12h para el usuario {user_id}")
        return jsonify({"status": "ok"})

    except Exception as e:
        print(f"[!] Error en /shorten_tournament: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route('/shorten_pvp', methods=['POST'])
def shorten_pvp():
    try:
        data = request.get_json(force=True)
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({"status": "error", "msg": "user_id requerido"}), 400

        user_dir  = os.path.join(SRV_DIR, str(user_id))
        user_file = os.path.join(user_dir, f"{user_id}.json")

        if not os.path.exists(user_file):
            return jsonify({"status": "error", "msg": "No se encontró la partida guardada de ese usuario."}), 404

        with open(user_file, 'r', encoding='utf-8') as f:
            player_data = json.load(f)

        private_state = player_data.get('privateState', {})
        attacks_sent = private_state.get('attacksSent', [])

        if not attacks_sent:
            return jsonify({"status": "error", "msg": "El jugador no tiene ataques PvP registrados."}), 400

        SECONDS_6H = 6 * 3600
        last_three = attacks_sent[-3:]

        for attack in last_three:
            if 'time' in attack:
                attack['time'] = max(0, attack['time'] - SECONDS_6H)

        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(player_data, f, indent=2, ensure_ascii=False)

        print(f"[+] [PVP] Tiempo acortado 6h para los últimos {len(last_three)} ataque(s) del usuario {user_id}")
        return jsonify({"status": "ok", "affected": len(last_three)})

    except Exception as e:
        print(f"[!] Error en /shorten_pvp: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500
        
if __name__ == '__main__':
    add_hosts()
    socket_policy_server_thread = threading.Thread(target=socket_policy_server, args=(5840,), daemon=True)
    socket_policy_server_thread.start()
    print("\n" + "★"*55)
    print("  EL SERVIDOR ESTÁ EN LÍNEA Y LISTO PARA JUGAR  ")
    print("   ¡Tenga un excelente juego, Maestro Dragón! ")
    print("★"*55 + "\n")
    app.run(host='127.0.0.1', port=80, debug=False, threaded=True)
