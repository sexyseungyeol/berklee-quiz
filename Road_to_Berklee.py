# deploy ping 2026-01-16

st.caption("BUILD-ID: 2026-01-16-01")

# ==============================
# PART B1 — IMPORTS & CONFIG
# ==============================

import streamlit as st
import random
import time
import datetime
from datetime import timedelta
import hashlib
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Dict

import pandas as pd
import matplotlib.pyplot as plt

try:
    import gspread
except Exception:
    gspread = None

try:
    import extra_streamlit_components as stx
except Exception:
    stx = None


# ------------------------------
# App Config
# ------------------------------
st.set_page_config(
    page_title="Road to Berklee",
    page_icon="🎹",
    layout="wide"
)

OWNER_USERNAME = st.secrets.get("OWNER_USERNAME", "") if hasattr(st, "secrets") else ""

WS_USERS = "Users"
WS_HISTORY = "History"
WS_THEORY = "Theory"
WS_CHECKLIST = "Checklist"
WS_WEIGHTS = "QuizWeights"

# ==============================
# PART B2 — MUSIC UTILS & NORMALIZATION
# ==============================

# -------- normalize --------
def normalize_user_input(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = (s.replace("＋", "+")
           .replace("－", "-")
           .replace("–", "-")
           .replace("—", "-")
           .replace("♯", "#")
           .replace("♭", "b")
           .replace("𝄪", "##")
           .replace("𝄫", "bb"))
    s = re.sub(r"\s+", " ", s)
    return s.strip()


# -------- pitch / note --------
NOTES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
NOTE_TO_IDX = {n: i for i, n in enumerate(NOTES)}
ENH_PITCH = {'C#':'Db','D#':'Eb','F#':'Gb','G#':'Ab','A#':'Bb','Cb':'B','B#':'C','E#':'F','Fb':'E'}

def norm_pitch(p: str) -> str:
    s = normalize_user_input(p).replace(" ", "")
    if not s:
        return s
    s = s[0].upper() + s[1:]
    s = ENH_PITCH.get(s, s)
    return s

def pitch_idx(p: str) -> int:
    return NOTE_TO_IDX.get(norm_pitch(p), -1)

def idx_to_pitch(i: int) -> str:
    return NOTES[i % 12]

def transpose_pitch(p: str, semitones: int) -> str:
    i = pitch_idx(p)
    if i < 0:
        return norm_pitch(p)
    return idx_to_pitch(i + semitones)


# -------- degree --------
DEGREE_MAP = {
    'I':0,'bII':1,'#I':1,'II':2,'bIII':3,'#II':3,'III':4,'bIV':4,
    'IV':5,'#III':5,'bV':6,'#IV':6,'V':7,'bVI':8,'#V':8,
    'VI':9,'bVII':10,'#VI':10,'VII':11,'bI':11
}

def degree_to_semitone(deg: str) -> int:
    d = normalize_user_input(deg).replace(" ", "")
    return DEGREE_MAP.get(d, 0)

def degree_to_pitch_in_C(deg: str) -> str:
    return transpose_pitch("C", degree_to_semitone(deg))


# -------- interval --------
def interval_to_semitones(q: str, n: int) -> int:
    base = {1:0,2:2,3:4,4:5,5:7,6:9,7:11}
    octs = (n - 1) // 7
    deg = ((n - 1) % 7) + 1
    semi = base[deg] + 12 * octs
    if q == "m": return semi - 1
    if q == "+": return semi + 1
    if q == "-": return semi - 1
    return semi

def interval_to_pitch_from_C(itv: str) -> str:
    itv = normalize_user_input(itv).replace(" ", "").replace("P.", "P")
    if itv and itv[0] in ["+","-"] and itv[1:].isdigit():
        return transpose_pitch("C", int(itv))
    q = itv[0]
    n = int(itv[1:]) if itv[1:].isdigit() else 1
    return transpose_pitch("C", interval_to_semitones(q, n))


# -------- circle of 5th --------
CYCLE = ["C","G","D","A","E","B","Gb","Db","Ab","Eb","Bb","F"]
CYCLE_INDEX = {p: i for i, p in enumerate(CYCLE)}
_ENH_TO_CYCLE = {"F#":"Gb","C#":"Db","G#":"Ab","D#":"Eb","A#":"Bb","Cb":"B","B#":"C","E#":"F","Fb":"E"}

def _to_cycle_pitch(p: str) -> str:
    p = norm_pitch(p)
    return _ENH_TO_CYCLE.get(p, p)

def cycle_r_steps_to_pitch(p: str) -> int:
    return CYCLE_INDEX.get(_to_cycle_pitch(p), 0)


# -------- tension --------
_TENSION_TO_SEMI = {"b9":1,"9":2,"#9":3,"11":5,"#11":6,"b13":8,"13":9}

def tension_to_pitch_from_C(t: str) -> str:
    t = normalize_user_input(t).replace(" ", "")
    return transpose_pitch("C", _TENSION_TO_SEMI.get(t, 2))


# -------- helpers --------
def relative_minor(maj: str) -> str:
    return transpose_pitch(maj, -3)

def semitone_distance(a: str, b: str) -> int:
    ia, ib = pitch_idx(a), pitch_idx(b)
    if ia < 0 or ib < 0:
        return 0
    return (ib - ia) % 12
# ==============================
# PART B3 — DATA TABLES + QUESTION MODEL + GENERATORS
# ==============================

# tables
DISTANCE_TO_DEGREE = {
    1:['I'], 2:['#I','bII'], 3:['II'], 4:['#II','bIII'], 5:['III','bIV'], 6:['IV','#III'],
    7:['#IV','bV'], 8:['V'], 9:['#V','bVI'], 10:['VI'], 11:['#VI','bVII'], 12:['VII','bI'], 13:['P8']
}

SOLFEGE = {
    'I':'Do','II':'Re','III':'Mi','IV':'Fa','V':'Sol','VI':'La','VII':'Ti',
    'bII':'Ra','bIII':'Me','bV':'Se','bVI':'Le','bVII':'Te',
    '#I':'Di','#II':'Ri','#IV':'Fi','#V':'Si','#VI':'Li','bI':'Ti'
}

CHORD_FORMULAS = {
    'maj7':[0,4,7,11],'mM7':[0,3,7,11],'6':[0,4,7,9],'m6':[0,3,7,9],
    '7':[0,4,7,10],'m7':[0,3,7,10],'m7b5':[0,3,6,10],'dim7':[0,3,6,9],
    'aug':[0,4,8],'aug7':[0,4,8,10],'7(b5)':[0,4,6,10],'+M7':[0,4,8,11],'7sus4':[0,5,7,10]
}

MAJOR_BY_FLATS = {0:"C",1:"F",2:"Bb",3:"Eb",4:"Ab",5:"Db",6:"Gb",7:"Cb"}
MAJOR_BY_SHARPS = {0:"C",1:"G",2:"D",3:"A",4:"E",5:"B",6:"F#",7:"C#"}

CATEGORY_INFO = {
    'Enharmonics': ['Degrees', 'Number', 'Natural Form'],
    'Warming up': ['Counting keys', 'Finding degrees', 'Chord tones', 'Key signatures', 'Solfege'],
    'Intervals': ['Alternative', 'Tracking'],
    'Chord Forms': ['Relationships', 'Extract (Degree)', '9 chord', 'Rootless'],
    'Cycle of 5th': ['P5 down', 'P5 up', 'r calc', '2-5-1'],
    'Locations': ['Deg->Pitch', 'Pitch->Deg'],
    'Tritones': ['Pitch', 'Degree', 'Dom7', 'Dim7'],
    'Modes': ['Alterations', 'Tensions', 'Chords(Deg)', 'Chords(Key)'],
    'Minor': ['Chords', 'Tensions', 'Pitch'],
    'Mastery': ['Functions', 'Degrees', 'Pitches', 'Avail Scales', 'Pivot', 'Similarities']
}

# Enharmonics
ENH_DEGREE_PAIRS = [
    ("#VII", "I"), ("#I", "bII"), ("#II", "bIII"), ("bIV", "III"),
    ("IV", "#III"), ("#V", "bVI"), ("#VI", "bVII"), ("VII", "bI")
]
ENH_NUMBER_GROUPS = [
    ["1","8","#7"], ["#1","b2","#8","b9"], ["2","9"], ["#2","b3","#9","b10"],
    ["3","b4","10","b11"], ["4","#3","11","#10"], ["#4","b5","#11","b12"], ["5","12"],
    ["#5","b6","#12","b13"], ["6","13"], ["#6","b7","#13","b14"], ["7","b8","14"]
]
ENH_INTERVAL_GROUPS = [
    ["P1","+7","-2","P8","-9"], ["m2","+1","m9","+8"], ["M2","-3","M9","-10"],
    ["m3","+2","m10","+9"], ["M3","-4","M10","-11"], ["P4","+3","P11","+10"],
    ["+4","-5","+11","-12"], ["P5","-6","P12","-13"], ["m6","+5","m13","+12"],
    ["M6","-7","M13","-14"], ["m7","+6","m14","+13"], ["M7","-8","M14"]
]

# Modes / Minor / Mastery
MODE_ALTERATIONS = {
    "Dorian": ["bIII","bVII"],
    "Phrygian": ["bII","bIII","bVI","bVII"],
    "Lydian": ["#IV"],
    "Mixolydian": ["bVII"],
    "Aeolian": ["bII","bIII","bVI","bVII"],
    "Locrian": ["bII","bIII","bV","bVI","bVII"],
}
MODE_TENSIONS = {
    "Ionian": ["9","13"],
    "Dorian": ["9","11"],
    "Phrygian": ["11"],
    "Lydian": ["#4"],
    "Mixolydian": ["9","13"],
    "Aeolian": ["9","11"],
    "Locrian": ["11","b13"],
}
MODE_7TH_CHORDS_DEG = {
    "Ionian": ["Imaj7","IIm7","IIIm7","IVmaj7","V7","VIm7","VIIm7b5"],
    "Dorian": ["Im7","IIm7","bIIImaj7","IV7","Vm7","VIm7b5","bVIImaj7"],
    "Phrygian": ["Im7","bIImaj7","bIII7","IVm7","Vm7b5","bVImaj7","bVIIm7"],
    "Lydian": ["Imaj7","II7","IIIm7","#IVm7b5","Vmaj7","VIm7","VIIm7"],
    "Mixolydian": ["I7","IIm7","IIIm7b5","IVmaj7","Vm7","VIm7","bVIImaj7"],
    "Aeolian": ["Im7","IIm7b5","bIIImaj7","IVm7","Vm7","bVImaj7","bVII7"],
    "Locrian": ["Im7b5","bIImaj7","bIIIm7","IVm7","bVmaj7","bVI7","bVIIm7"],
}

MINOR_DEGREES = {
    "Natural minor": ["I","II","bIII","IV","V","bVI","bVII"],
    "Harmonic minor": ["I","II","bIII","IV","V","bVI","VII"],
    "Melodic minor": ["I","II","bIII","IV","V","VI","VII"],
}
MINOR_CHORD_FORMS = {
    "Natural minor": ["m7","m7b5","maj7","m7","m7","maj7","7"],
    "Harmonic minor": ["mM7","m7b5","+M7","m7","7","maj7","dim7"],
    "Melodic minor": ["mM7","m7","+M7","7","7","m7b5","m7b5"],
}
MINOR_TENSIONS = {
    "Natural minor": [["9","11"],["11","b13"],["9","13"],["9","11"],["11"],["9","#11"],["9","13"]],
    "Harmonic minor": [["9","11"],["11","13"],["9"],["9","#11"],["9","#11"],["9","b13"],["9","11"]],
    "Melodic minor": [["9","11","13"],["11","13"],["9","#11","13"],["9","#11","13"],["9","b13"],["9","11","b13"],["11","b13"]],
}

FUNCTIONS = {
    'T': set(['I','I6','Imaj7','IIIm7','VIm7','I7','IIIm7b5','III7']),
    'Tm': set(['Im','Im6','Imb6','Im7','ImM7','bIIImaj7','bIII+M7','VIm7b5']),
    'SD': set(['IV','IV6','IVmaj7','IIm7','IV7','bVII','bVIImaj7','VII7']),
    'SDm': set(['IVm','IVm6','IVm7','IIm7b5','bVI6','bVImaj7','bVII7','bIImaj7','bVI7','IVmM7']),
    'D': set(['V','V7','VIIm7b6','bII7','VIIdim7']),
    'Dm': set(['Vm','Vm7']),
}
FUNCTION_OVERRIDES = {'#IVm7b5':['T','SD'], 'bVImaj7':['SDm','Tm']}

SCALE_DEGREES = {
    "Ionian": ["I","II","III","IV","V","VI","VII"],
    "Dorian": ["I","II","bIII","IV","V","VI","bVII"],
    "Phrygian": ["I","bII","bIII","IV","V","bVI","bVII"],
    "Lydian": ["I","II","III","#IV","V","VI","VII"],
    "Mixolydian": ["I","II","III","IV","V","VI","bVII"],
    "Aeolian": ["I","bII","bIII","IV","V","bVI","bVII"],
    "Locrian": ["I","bII","bIII","IV","bV","bVI","bVII"],
    "Natural minor": ["I","II","bIII","IV","V","bVI","bVII"],
    "Harmonic minor": ["I","II","bIII","IV","V","bVI","VII"],
    "Melodic minor": ["I","II","bIII","IV","V","VI","VII"],
}
AVAILABLE_SCALES = {
    "Ionian": ['I','I6','Imaj7'],
    "Dorian": ['IVm','IVm6','IVm7','IIm7'],
    "Phrygian": ['IIIm7'],
    "Lydian": ['IV','IVmaj7','bVII','bVIImaj7','bVImaj7','bIImaj7','bIIImaj7'],
    "Mixolydian": ['V','bVII7','V7/IV','V7/V','V7'],
    "Aeolian": ['VIm7'],
    "Locrian": ['VIIm7b5','#IVm7b5','IIm7b5'],
    "All": ['I7'],
    "Lydian b7": ['IV7','bVII7','bVI7','bII7','IV6'],
    "Altered": ['VII7'],
    "HmP5↓": ['V7'],
    "Combination of Diminished": ['V7','bII7','bVII7'],
}

_ROMAN_RE = re.compile(r"^(b|#)?(I|II|III|IV|V|VI|VII)(.*)$")

def degchord_to_pitchchord(key: str, degch: str) -> str:
    m = _ROMAN_RE.match(degch)
    if not m:
        return f"{key}{degch}"
    acc = m.group(1) or ""
    roman = m.group(2)
    qual = m.group(3) or ""
    deg = f"{acc}{roman}"
    root = transpose_pitch(key, degree_to_semitone(deg))
    return f"{root}{qual}"

def ord_suffix(n: int) -> str:
    return {1:"Ist",2:"IInd",3:"IIIrd",4:"IVth",5:"Vth",6:"VIth",7:"VIIth"}.get(n, f"{n}th")

def inv_degree_from_semi(semi: int) -> str:
    semi %= 12
    cands = [k for k,v in DEGREE_MAP.items() if v == semi]
    return cands[0] if cands else "I"


# model
@dataclass
class Question:
    category: str
    subcategory: str
    prompt: str
    answers: List[str]
    kind: str
    sep: Optional[str] = None
    rule: str = ""


def qbuild(cat: str, sub: str, prompt: str, answers: List[str], kind: str, sep: Optional[str] = None, rule: str = "") -> Question:
    return Question(cat, sub, prompt, answers, kind, sep, rule)


# generators
def gen_enh_degrees() -> Question:
    a, b = random.choice(ENH_DEGREE_PAIRS)
    ask = random.choice([a, b])
    ans = b if ask == a else a
    return qbuild("Enharmonics", "Degrees", f"What is {ask}'s enharmonic?", [ans], "degree")

def gen_enh_number() -> Question:
    group = random.choice(ENH_NUMBER_GROUPS)
    shown = random.choice(group)
    expected = [x for x in group if x != shown]
    return qbuild("Enharmonics", "Number", f"What are {shown}'s enharmonics?", expected, "number", sep=",")

def gen_enh_interval() -> Question:
    group = random.choice(ENH_INTERVAL_GROUPS)
    shown = random.choice(group)
    expected = [x for x in group if x != shown]
    return qbuild("Enharmonics", "Natural Form", f"What are {shown}'s enharmonics?", expected, "interval", sep=",")

def gen_warm_counting_keys() -> Question:
    keynum = random.randint(1, 24)
    d = ((keynum - 1) % 13) + 1
    return qbuild("Warming up","Counting keys", f"What degree has {keynum}keys?", DISTANCE_TO_DEGREE.get(d, ["I"]), "degree")

def gen_warm_finding_degrees() -> Question:
    root = random.choice(NOTES)
    deg = random.choice(list(DEGREE_MAP.keys()))
    ans = transpose_pitch(root, degree_to_semitone(deg))
    return qbuild("Warming up","Finding degrees", f"What pitch is {deg} of {root}Key?", [ans], "pitch")

def gen_warm_chord_tones() -> Question:
    root = random.choice(NOTES)
    chord = random.choice(list(CHORD_FORMULAS.keys()))
    tones = [transpose_pitch(root, s) for s in CHORD_FORMULAS[chord]]
    return qbuild("Warming up","Chord tones", f"What are the Chord tones of {root}{chord}?", tones, "pitch", sep=",")

def gen_warm_key_signatures() -> Question:
    is_major = random.choice([True, False])
    t = random.choice(["#", "b"])
    n = random.randint(0, 7)
    sig = (t * n) if n > 0 else ""
    maj = MAJOR_BY_FLATS.get(n, "C") if t == "b" else MAJOR_BY_SHARPS.get(n, "C")
    ans = maj if is_major else relative_minor(maj)
    qtype = "major" if is_major else "minor"
    return qbuild("Warming up","Key signatures", f"What {qtype} key has ({sig})?", [norm_pitch(ans)], "pitch")

def gen_warm_solfege() -> Question:
    deg = random.choice(list(SOLFEGE.keys()))
    return qbuild("Warming up","Solfege", f"What is {deg}'s solfege?", [SOLFEGE[deg]], "solfege")

def gen_cycle_r_calc() -> Question:
    form = random.choice([1,2,3])
    if form == 1:
        deg = random.choice(list(DEGREE_MAP.keys()))
        p = degree_to_pitch_in_C(deg)
        ans = str(cycle_r_steps_to_pitch(p))
        return qbuild("Cycle of 5th","r calc", f"How many 'r's do you need to get {deg}?", [ans], "number")
    if form == 2:
        itv = random.choice(["m2","M2","m3","M3","P4","P5","m6","M6","m7","M7","+11","-2","+7","-12"])
        p = interval_to_pitch_from_C(itv)
        ans = str(cycle_r_steps_to_pitch(p))
        return qbuild("Cycle of 5th","r calc", f"How many 'r's do you need to get {itv}?", [ans], "number")
    t = random.choice(list(_TENSION_TO_SEMI.keys()))
    p = tension_to_pitch_from_C(t)
    ans = str(cycle_r_steps_to_pitch(p))
    return qbuild("Cycle of 5th","r calc", f"How many 'r's do you need to get {t}?", [ans], "number")

def gen_modes_alterations() -> Question:
    mode = random.choice(list(MODE_ALTERATIONS.keys()))
    return qbuild("Modes","Alterations", f"What degree should be flatted or sharped in {mode} scale?", MODE_ALTERATIONS[mode], "degree", sep=",")

def gen_modes_tensions() -> Question:
    mode = random.choice(list(MODE_TENSIONS.keys()))
    return qbuild("Modes","Tensions", f"What are the tension notes of {mode}?", MODE_TENSIONS[mode], "tension", sep=",")

def gen_modes_chords_deg() -> Question:
    mode = random.choice(list(MODE_7TH_CHORDS_DEG.keys()))
    n = random.randint(1, 7)
    ans = MODE_7TH_CHORDS_DEG[mode][n-1]
    return qbuild("Modes","Chords(Deg)", f"What is {ord_suffix(n)} 7th chord in {mode}?", [ans], "degree")

def gen_modes_chords_key() -> Question:
    mode = random.choice(list(MODE_7TH_CHORDS_DEG.keys()))
    key = random.choice(NOTES)
    n = random.randint(1, 7)
    degch = MODE_7TH_CHORDS_DEG[mode][n-1]
    ans = degchord_to_pitchchord(key, degch)
    return qbuild("Modes","Chords(Key)", f"What is {ord_suffix(n)} 7th chord in {key}{mode}?", [ans], "chord")

def gen_mastery_pivot() -> Question:
    chord_type = random.choice(["maj7","7","m7","m7b5"])
    deg = random.choice(list(DEGREE_MAP.keys()))
    semi = degree_to_semitone(deg)
    outs: List[str] = []
    if chord_type == "maj7":
        outs = [inv_degree_from_semi(semi + 7), inv_degree_from_semi(semi)]
    elif chord_type == "7":
        outs = [inv_degree_from_semi(semi + 5)]
    elif chord_type == "m7":
        outs = [inv_degree_from_semi(semi + 10), inv_degree_from_semi(semi + 8), inv_degree_from_semi(semi + 3)]
    else:
        outs = [inv_degree_from_semi(semi + 1)]
    outs = list(dict.fromkeys(outs))
    return qbuild("Mastery","Pivot", f"What keys have {deg}{chord_type} chord as a pivot chord?", outs, "degree", sep=",")

def gen_locations_deg_to_pitch() -> Question:
    key = random.choice(NOTES)
    deg = random.choice(list(DEGREE_MAP.keys()))
    ans = transpose_pitch(key, degree_to_semitone(deg))
    return qbuild("Locations", "Deg->Pitch", f"{key}Key에서 {deg}는 어떤 Pitch?", [ans], "pitch")

def gen_locations_pitch_to_deg() -> Question:
    key = random.choice(NOTES)
    deg = random.choice(list(DEGREE_MAP.keys()))
    pitch = transpose_pitch(key, degree_to_semitone(deg))
    return qbuild("Locations", "Pitch->Deg", f"{key}Key에서 {pitch}는 어떤 Degree?", [deg], "degree")

def gen_tritone_pitch() -> Question:
    p = random.choice(NOTES)
    ans = transpose_pitch(p, 6)
    return qbuild("Tritones", "Pitch", f"What is the tritone of {p}?", [ans], "pitch")

def gen_tritone_degree() -> Question:
    deg = random.choice(list(DEGREE_MAP.keys()))
    semi = (degree_to_semitone(deg) + 6) % 12
    ans = inv_degree_from_semi(semi)
    return qbuild("Tritones", "Degree", f"What is the tritone degree of {deg}?", [ans], "degree")

def gen_tritone_dom7() -> Question:
    root = random.choice(NOTES)
    ans = f"{transpose_pitch(root, 6)}7"
    return qbuild("Tritones", "Dom7", f"What is the tritone substitution of {root}7?", [ans], "chord")

def gen_tritone_dim7() -> Question:
    root = random.choice(NOTES)
    ans = transpose_pitch(root, 6)
    return qbuild("Tritones", "Dim7", f"In {root}dim7, what note is a tritone away from the root?", [ans], "pitch")

def gen_cycle_p5_down() -> Question:
    p = random.choice(NOTES)
    ans = transpose_pitch(p, -7)
    return qbuild("Cycle of 5th","P5 down", f"P5 down from {p} is?", [ans], "pitch")

def gen_cycle_p5_up() -> Question:
    p = random.choice(NOTES)
    ans = transpose_pitch(p, +7)
    return qbuild("Cycle of 5th","P5 up", f"P5 up from {p} is?", [ans], "pitch")

def gen_cycle_251() -> Question:
    key = random.choice(NOTES)
    ii = degchord_to_pitchchord(key, "IIm7")
    v = degchord_to_pitchchord(key, "V7")
    i = degchord_to_pitchchord(key, "Imaj7")
    return qbuild("Cycle of 5th","2-5-1", f"Write 2-5-1 in key of {key} (comma-separated)", [ii, v, i], "chord", sep=",")

def gen_minor_chords() -> Question:
    scale = random.choice(list(MINOR_CHORD_FORMS.keys()))
    n = random.randint(1, 7)
    deg = MINOR_DEGREES[scale][n-1]
    form = MINOR_CHORD_FORMS[scale][n-1]
    ans = f"{deg}{form}"
    return qbuild("Minor","Chords", f"What is {ord_suffix(n)} chord in {scale}?", [ans], "degree")

def gen_minor_tensions() -> Question:
    scale = random.choice(list(MINOR_TENSIONS.keys()))
    n = random.randint(1, 7)
    ans = MINOR_TENSIONS[scale][n-1]
    return qbuild("Minor","Tensions", f"What are the tensions of {ord_suffix(n)} chord in {scale}?", ans, "tension", sep=",")

def gen_minor_pitch() -> Question:
    scale = random.choice(list(MINOR_DEGREES.keys()))
    key = random.choice(NOTES)
    deg = random.choice(MINOR_DEGREES[scale])
    ans = transpose_pitch(key, degree_to_semitone(deg))
    return qbuild("Minor","Pitch", f"In {key}{scale}, what pitch is {deg}?", [ans], "pitch")

def _interval_groups_for_alternative() -> List[List[str]]:
    # 같은 음(동일 pitch class)을 만드는 서로 다른 표기들
    return [
        ["P1","+7","-2","P8","-9"],
        ["m2","+1","m9","+8"],
        ["M2","-3","M9","-10"],
        ["m3","+2","m10","+9"],
        ["M3","-4","M10","-11"],
        ["P4","+3","P11","+10"],
        ["+4","-5","+11","-12"],
        ["P5","-6","P12","-13"],
        ["m6","+5","m13","+12"],
        ["M6","-7","M13","-14"],
        ["m7","+6","m14","+13"],
        ["M7","-8","M14"],
    ]

def gen_intervals_alternative() -> Question:
    group = random.choice(_interval_groups_for_alternative())
    shown = random.choice(group)
    expected = [x for x in group if x != shown]
    return qbuild("Intervals", "Alternative", f"What are {shown}'s alternative intervals? (comma-separated)", expected, "interval", sep=",")

def gen_intervals_tracking() -> Question:
    root = random.choice(NOTES)
    q = random.choice(["m","M","P","+","-"])
    n = random.choice([1,2,3,4,5,6,7,8,9,10,11,12,13,14])
    itv = f"{q}{n}" if q in ["m","M","P"] else f"{q}{interval_to_semitones(q, n)}"
    ans = transpose_pitch(root, semitone_distance("C", interval_to_pitch_from_C(itv)))
    return qbuild("Intervals", "Tracking", f"From {root}, what is {itv}?", [ans], "pitch")

CHORD_LIST = list(CHORD_FORMULAS.keys())

def _chord_tones(root: str, form: str) -> List[str]:
    return [transpose_pitch(root, s) for s in CHORD_FORMULAS[form]]

def gen_chord_relationships() -> Question:
    a, b = random.sample(CHORD_LIST, 2)
    shared = set(CHORD_FORMULAS[a]).intersection(set(CHORD_FORMULAS[b]))
    prompt = f"Do {a} and {b} share any common chord tones? (yes/no)"
    ans = ["yes"] if len(shared) > 0 else ["no"]
    return qbuild("Chord Forms", "Relationships", prompt, ans, "text")

def gen_chord_extract_degree() -> Question:
    form = random.choice(CHORD_LIST)
    deg = random.choice(list(DEGREE_MAP.keys()))
    root = degree_to_pitch_in_C(deg)
    tones = _chord_tones(root, form)
    return qbuild("Chord Forms", "Extract (Degree)", f"Chord tones of {deg}{form} in C (comma-separated)", tones, "pitch", sep=",")

def gen_chord_9() -> Question:
    root = random.choice(NOTES)
    form = random.choice(["maj7","m7","7","m7b5"])
    base = CHORD_FORMULAS[form]
    ninth = 14  # 9th = 14 semitones from root
    tones = [transpose_pitch(root, s) for s in (base + [ninth])]
    return qbuild("Chord Forms", "9 chord", f"What are the chord tones of {root}{form}(9)? (comma-separated)", tones, "pitch", sep=",")

def gen_chord_rootless() -> Question:
    root = random.choice(NOTES)
    form = random.choice(["7","m7","maj7","m7b5"])
    tones = _chord_tones(root, form)
    tones_no_root = [t for i, t in enumerate(tones) if i != 0]
    return qbuild("Chord Forms", "Rootless", f"Rootless voicing tones of {root}{form} (comma-separated)", tones_no_root, "pitch", sep=",")

def _function_of(ch: str) -> List[str]:
    if ch in FUNCTION_OVERRIDES:
        return FUNCTION_OVERRIDES[ch]
    outs = []
    for fn, s in FUNCTIONS.items():
        if ch in s:
            outs.append(fn)
    return outs or ["T"]

def gen_mastery_functions() -> Question:
    ch = random.choice(sum([list(v) for v in FUNCTIONS.values()], []))
    ans = _function_of(ch)
    return qbuild("Mastery","Functions", f"What is the function of {ch}?", ans, "text", sep="," if len(ans) > 1 else None)

def gen_mastery_degrees() -> Question:
    scale = random.choice(list(SCALE_DEGREES.keys()))
    n = random.randint(1, 7)
    ans = SCALE_DEGREES[scale][n-1]
    return qbuild("Mastery","Degrees", f"In {scale}, what is the {ord_suffix(n)} degree?", [ans], "degree")

def gen_mastery_pitches() -> Question:
    key = random.choice(NOTES)
    scale = random.choice(list(SCALE_DEGREES.keys()))
    deg = random.choice(SCALE_DEGREES[scale])
    ans = transpose_pitch(key, degree_to_semitone(deg))
    return qbuild("Mastery","Pitches", f"In {key}{scale}, what pitch is {deg}?", [ans], "pitch")

def gen_mastery_avail_scales() -> Question:
    scale = random.choice(list(AVAILABLE_SCALES.keys()))
    ch = random.choice(AVAILABLE_SCALES[scale])
    return qbuild("Mastery","Avail Scales", f"What scale includes chord {ch}?", [scale], "text")

def gen_mastery_similarities() -> Question:
    a, b = random.sample(list(SCALE_DEGREES.keys()), 2)
    sa, sb = set(SCALE_DEGREES[a]), set(SCALE_DEGREES[b])
    common = sorted(list(sa.intersection(sb)))
    if not common:
        common = ["(none)"]
    return qbuild("Mastery","Similarities", f"Common degrees between {a} and {b}? (comma-separated)", common, "degree", sep="," if common != ["(none)"] else None)


# dispatcher
GEN_DISPATCH: Dict[tuple, callable] = {
    ("Enharmonics","Degrees"): gen_enh_degrees,
    ("Enharmonics","Number"): gen_enh_number,
    ("Enharmonics","Natural Form"): gen_enh_interval,
    ("Warming up","Counting keys"): gen_warm_counting_keys,
    ("Warming up","Finding degrees"): gen_warm_finding_degrees,
    ("Warming up","Chord tones"): gen_warm_chord_tones,
    ("Warming up","Key signatures"): gen_warm_key_signatures,
    ("Warming up","Solfege"): gen_warm_solfege,
    ("Cycle of 5th","r calc"): gen_cycle_r_calc,
    ("Modes","Alterations"): gen_modes_alterations,
    ("Modes","Tensions"): gen_modes_tensions,
    ("Modes","Chords(Deg)"): gen_modes_chords_deg,
    ("Modes","Chords(Key)"): gen_modes_chords_key,
    ("Mastery","Pivot"): gen_mastery_pivot,
    ("Locations","Deg->Pitch"): gen_locations_deg_to_pitch,
    ("Locations","Pitch->Deg"): gen_locations_pitch_to_deg,
    ("Tritones","Pitch"): gen_tritone_pitch,
    ("Tritones","Degree"): gen_tritone_degree,
    ("Tritones","Dom7"): gen_tritone_dom7,
    ("Tritones","Dim7"): gen_tritone_dim7,
    ("Cycle of 5th","P5 down"): gen_cycle_p5_down,
    ("Cycle of 5th","P5 up"): gen_cycle_p5_up,
    ("Cycle of 5th","2-5-1"): gen_cycle_251,
    ("Minor","Chords"): gen_minor_chords,
    ("Minor","Tensions"): gen_minor_tensions,
    ("Minor","Pitch"): gen_minor_pitch,
    ("Intervals","Alternative"): gen_intervals_alternative,
    ("Intervals","Tracking"): gen_intervals_tracking,
    ("Chord Forms","Relationships"): gen_chord_relationships,
    ("Chord Forms","Extract (Degree)"): gen_chord_extract_degree,
    ("Chord Forms","9 chord"): gen_chord_9,
    ("Chord Forms","Rootless"): gen_chord_rootless,
    ("Mastery","Functions"): gen_mastery_functions,
    ("Mastery","Degrees"): gen_mastery_degrees,
    ("Mastery","Pitches"): gen_mastery_pitches,
    ("Mastery","Avail Scales"): gen_mastery_avail_scales,
    ("Mastery","Similarities"): gen_mastery_similarities,

}

def generate_question(cat: str, sub: str) -> Question:
    fn = GEN_DISPATCH.get((cat, sub))
    if fn:
        return fn()
    return qbuild(cat, sub, f"Determine the {sub}.", ["C"], "text")

def _weights_map() -> Dict[tuple, float]:
    base = {(c, s): 1.0 for c, subs in CATEGORY_INFO.items() for s in subs}
    df = st.session_state.stat_mgr.load_weights_df() if "stat_mgr" in st.session_state else pd.DataFrame()
    if df is None or df.empty:
        return base
    for _, r in df.iterrows():
        c = str(r.get("category", ""))
        s = str(r.get("subcategory", ""))
        if (c, s) in base:
            try:
                base[(c, s)] = max(0.0, float(r.get("weight", 1.0)))
            except Exception:
                base[(c, s)] = 1.0
    return base

def generate_question_weighted() -> Question:
    wm = _weights_map()
    pairs = list(wm.keys())
    ws = [wm[p] for p in pairs]
    if sum(ws) <= 0:
        cat, sub = random.choice(pairs)
        return generate_question(cat, sub)
    cat, sub = random.choices(pairs, weights=ws, k=1)[0]
    return generate_question(cat, sub)

# ==============================
# PART B4 — GRADING + SMART KEYPAD
# ==============================

# -------- grading --------
def tokenize_answer(s: str, sep: Optional[str]) -> List[str]:
    s = normalize_user_input(s)
    if not sep:
        return [s]
    parts = [p.strip() for p in s.split(sep)]
    return [p for p in parts if p]

def is_answer_correct(q: Question, user_input: str) -> bool:
    user_tokens = tokenize_answer(user_input, q.sep)
    exp = [normalize_user_input(a) for a in q.answers]

    if q.sep:
        return set(user_tokens) == set(exp)
    return any(normalize_user_input(user_input) == e for e in exp)


# -------- keypad sets --------
KEYPAD_SETS = {
    "pitch": [
        ["♭","♯"], ["C","D","E","F"], ["G","A","B"], [","], ["⬅️","❌","✅"]
    ],
    "degree": [
        ["♭","♯"], ["I","II","III"], ["IV","V","VI","VII"], [","], ["⬅️","❌","✅"]
    ],
    "number": [
        ["+","-"], ["1","2","3","4","5"], ["6","7","8","9","0"], [","], ["⬅️","❌","✅"]
    ],
    "interval": [
        ["+","-","m","M","P"], ["1","2","3","4","5"], ["6","7","8","9"], [","], ["⬅️","❌","✅"]
    ],
    "solfege": [
        ["Do","Re","Mi","Fa"], ["Sol","La","Ti"],
        ["Di","Ri","Fi","Si","Li"], ["Ra","Me","Se","Le","Te"], ["⬅️","❌","✅"]
    ],
    "tension": [
        ["♭","♯"], ["b9","9","#9"], ["11","#11"], ["b13","13"], [","], ["⬅️","❌","✅"]
    ],
    "chord": [
        ["♭","♯"], ["C","D","E","F"], ["G","A","B"],
        ["maj7","m7","7","m7b5"], ["dim7","aug","+M7","sus4"],
        ["/",","], ["⬅️","❌","✅"]
    ],
    "text": [
        ["C","D","E","F","G","A","B"], ["⬅️","❌","✅"]
    ]
}

def keypad_for_kind(kind: str):
    return KEYPAD_SETS.get(kind, KEYPAD_SETS["text"])

def add_input(k):
    st.session_state.user_input_buffer += k

def del_input():
    st.session_state.user_input_buffer = st.session_state.user_input_buffer[:-1]

def clear_input():
    st.session_state.user_input_buffer = ""

def render_keypad_for_question(q: Question) -> bool:
    rows = keypad_for_kind(q.kind)
    st.markdown(
        "<style>.stButton>button{height:64px;font-size:18px;font-weight:600}</style>",
        unsafe_allow_html=True
    )
    submit = False
    for r in rows:
        cols = st.columns(len(r))
        for i, key in enumerate(r):
            if key == "⬅️":
                cols[i].button(key, on_click=del_input, use_container_width=True)
            elif key == "❌":
                cols[i].button(key, on_click=clear_input, use_container_width=True)
            elif key == "✅":
                submit = cols[i].button(key, type="primary", use_container_width=True)
            else:
                cols[i].button(key, on_click=add_input, args=(key,), use_container_width=True)
    return submit
# ==============================
# PART B5 — STORAGE (StatManager) + STATS DATA
# ==============================

def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")

class StatManager:
    def __init__(self, key_file="service_account.json", sheet_name="Berklee_DB"):
        self.connected = False
        self.current_user = None
        self.sh = None
        self.ws_users = None
        self.ws_history = None
        self.ws_theory = None
        self.ws_checklist = None

        if gspread is None:
            return
        try:
            if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
                creds = dict(st.secrets["gcp_service_account"])
                gc = gspread.service_account_from_dict(creds)
            elif os.path.exists(key_file):
                gc = gspread.service_account(filename=key_file)
            else:
                return

            self.sh = gc.open(sheet_name)
            self.ws_users = self.sh.worksheet(WS_USERS)
            self.ws_history = self.sh.worksheet(WS_HISTORY)
            self.ws_theory = self._ensure_ws(WS_THEORY, ["category","subcategory","content","updated_at","updated_by"])
            self.ws_checklist = self._ensure_ws(WS_CHECKLIST, ["section","item","checked","updated_at","updated_by"])
            self.ws_weights = self._ensure_ws(WS_WEIGHTS, ["category","subcategory","weight","updated_at","updated_by"])
            self.connected = True
        except Exception:
            self.connected = False

        self.data = []

    def _ensure_ws(self, title: str, headers: List[str]):
        try:
            return self.sh.worksheet(title)
        except Exception:
            ws = self.sh.add_worksheet(title=title, rows=2000, cols=max(10, len(headers)+2))
            ws.append_row(headers)
            return ws

    def login_user(self, username: str, password: str) -> bool:
        if not self.connected:
            return False
        try:
            cell = self.ws_users.find(username)
            if not cell:
                return False
            stored = self.ws_users.cell(cell.row, 2).value
            if stored == hashlib.sha256(password.encode()).hexdigest():
                self.current_user = username
                self.load_user_data()
                return True
            return False
        except Exception:
            return False

    def auto_login(self, username: str) -> bool:
        if not self.connected:
            return False
        try:
            if username in self.ws_users.col_values(1):
                self.current_user = username
                self.load_user_data()
                return True
        except Exception:
            pass
        return False

    def logout(self):
        self.current_user = None
        self.data = []

    def load_user_data(self):
        if not self.connected:
            self.data = []
            return
        try:
            rows = self.ws_history.get_all_records()
            self.data = [r for r in rows if str(r.get("username")) == str(self.current_user)]
        except Exception:
            self.data = []

    def record(self, category: str, subcategory: str, is_correct: bool, is_retry: bool):
        if not self.connected or not self.current_user or is_retry:
            return
        now = datetime.datetime.now()
        row = [
            self.current_user,
            float(now.timestamp()),
            now.year, now.month, now.day,
            category, subcategory,
            1 if is_correct else 0,
            1
        ]
        try:
            self.ws_history.append_row(row)
        except Exception:
            pass

    # Theory
    def load_theory_df(self) -> pd.DataFrame:
        cols = ["category","subcategory","content","updated_at","updated_by"]
        if not self.connected:
            return pd.DataFrame(columns=cols)
        try:
            df = pd.DataFrame(self.ws_theory.get_all_records())
            for c in cols:
                if c not in df.columns:
                    df[c] = ""
            return df[cols]
        except Exception:
            return pd.DataFrame(columns=cols)

    def upsert_theory(self, cat: str, sub: str, content: str, by: str) -> bool:
        if not self.connected:
            return False
        try:
            rows = self.ws_theory.get_all_records()
            ts = now_iso()
            for i, r in enumerate(rows, start=2):
                if str(r.get("category")) == str(cat) and str(r.get("subcategory")) == str(sub):
                    self.ws_theory.update(f"C{i}:E{i}", [[content, ts, by]])
                    return True
            self.ws_theory.append_row([cat, sub, content, ts, by])
            return True
        except Exception:
            return False

    # Checklist
    def load_checklist_df(self) -> pd.DataFrame:
        cols = ["section","item","checked","updated_at","updated_by"]
        if not self.connected:
            return pd.DataFrame(columns=cols)
        try:
            df = pd.DataFrame(self.ws_checklist.get_all_records())
            for c in cols:
                if c not in df.columns:
                    df[c] = ""
            df["checked"] = pd.to_numeric(df["checked"], errors="coerce").fillna(0).astype(int)
            return df[cols]
        except Exception:
            return pd.DataFrame(columns=cols)

    def set_checklist_item(self, section: str, item: str, checked: int, by: str) -> bool:
        if not self.connected:
            return False
        try:
            rows = self.ws_checklist.get_all_records()
            ts = now_iso()
            for i, r in enumerate(rows, start=2):
                if str(r.get("section")) == str(section) and str(r.get("item")) == str(item):
                    self.ws_checklist.update(f"C{i}:E{i}", [[int(checked), ts, by]])
                    return True
            self.ws_checklist.append_row([section, item, int(checked), ts, by])
            return True
        except Exception:
            return False

    def delete_checklist_item(self, section: str, item: str) -> bool:
        if not self.connected:
            return False
        try:
            rows = self.ws_checklist.get_all_records()
            for i, r in enumerate(rows, start=2):
                if str(r.get("section")) == str(section) and str(r.get("item")) == str(item):
                    self.ws_checklist.delete_rows(i)
                    return True
            return False
        except Exception:
            return False

    # Weights
    def load_weights_df(self) -> pd.DataFrame:
        cols = ["category","subcategory","weight","updated_at","updated_by"]
        if not self.connected:
            return pd.DataFrame(columns=cols)
        try:
            df = pd.DataFrame(self.ws_weights.get_all_records())
            for c in cols:
                if c not in df.columns:
                    df[c] = ""
            df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(1.0)
            return df[cols]
        except Exception:
            return pd.DataFrame(columns=cols)

    def upsert_weight(self, cat: str, sub: str, weight: float, by: str) -> bool:
        if not self.connected:
            return False
        try:
            rows = self.ws_weights.get_all_records()
            ts = now_iso()
            for i, r in enumerate(rows, start=2):
                if str(r.get("category")) == str(cat) and str(r.get("subcategory")) == str(sub):
                    self.ws_weights.update(f"C{i}:E{i}", [[float(weight), ts, by]])
                    return True
            self.ws_weights.append_row([cat, sub, float(weight), ts, by])
            return True
        except Exception:
            return False


def stat_df_from_history(rows: List[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["ts","category","subcategory","is_correct"])
    df = pd.DataFrame(rows)
    if "timestamp" in df.columns:
        df["ts"] = pd.to_datetime(df["timestamp"], unit="s", errors="coerce")
    else:
        df["ts"] = pd.to_datetime(
            df[["year","month","day"]].astype(str).agg("-".join, axis=1),
            errors="coerce"
        )
    df["is_correct"] = pd.to_numeric(df.get("is_correct", 0), errors="coerce").fillna(0).astype(int)
    df["category"] = df.get("category", "").astype(str)
    df["subcategory"] = df.get("subcategory", "").astype(str)
    return df[["ts","category","subcategory","is_correct"]].dropna(subset=["ts"])
# ==============================
# PART B6A — SESSION + LOGIN + QUIZ ENGINE + SIDEBAR
# ==============================

if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None
if "user_input_buffer" not in st.session_state:
    st.session_state.user_input_buffer = ""
if "wrong_count" not in st.session_state:
    st.session_state.wrong_count = 0
if "wrong_pool" not in st.session_state:
    st.session_state.wrong_pool = []
if "page" not in st.session_state:
    st.session_state.page = "home"
if "quiz" not in st.session_state:
    st.session_state.quiz = {
        "active": False,
        "cat": "",
        "sub": "",
        "idx": 0,
        "score": 0,
        "limit": 10,
        "is_retry": False,
        "retry_pool": [],
        "q": None
    }

def is_owner() -> bool:
    return str(st.session_state.get("logged_in_user","")) == str(OWNER_USERNAME) and OWNER_USERNAME != ""

def ensure_cookie_manager():
    if stx is None:
        return None
    if "cookie_mgr" not in st.session_state:
        st.session_state.cookie_mgr = stx.CookieManager()
    return st.session_state.cookie_mgr

def try_auto_login():
    cm = ensure_cookie_manager()
    if cm is None:
        return
    if st.session_state.logged_in_user is not None:
        return
    user_cookie = cm.get(cookie="berklee_user")
    if user_cookie and st.session_state.stat_mgr.auto_login(user_cookie):
        st.session_state.logged_in_user = user_cookie

try_auto_login()

def render_login():
    st.title("🎹 Road to Berklee")
    if stx is None:
        st.error("extra_streamlit_components가 필요해. requirements.txt에 추가해줘.")
        st.stop()

    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if st.session_state.stat_mgr.login_user(u, p):
                st.session_state.logged_in_user = u
                cm = ensure_cookie_manager()
                if cm:
                    cm.set("berklee_user", u, expires_at=datetime.datetime.now()+timedelta(days=30))
                st.rerun()
            else:
                st.error("Login failed.")

def logout():
    st.session_state.stat_mgr.logout()
    st.session_state.logged_in_user = None
    cm = ensure_cookie_manager()
    if cm:
        cm.delete("berklee_user")
    st.rerun()

def start_quiz(cat: str, sub: str, limit: int = 10, is_retry: bool = False, retry_pool: Optional[List[Question]] = None, mode: str = "fixed"):
    st.session_state.user_input_buffer = ""
    st.session_state.wrong_count = 0
    if not is_retry:
        st.session_state.wrong_pool = []

    pool = retry_pool or []
    if is_retry and pool:
        q = pool[0]
    else:
        q = generate_question(cat, sub) if mode == "fixed" else generate_question_weighted()

    st.session_state.quiz = {
        "active": True,
        "cat": cat,
        "sub": sub,
        "idx": 0,
        "score": 0,
        "limit": len(pool) if is_retry else limit,
        "is_retry": is_retry,
        "retry_pool": pool,
        "q": q,
        "mode": mode
    }
    st.session_state.page = "quiz"
    st.rerun()

def next_question():
    qs = st.session_state.quiz
    qs["idx"] += 1
    if qs["idx"] >= qs["limit"]:
        st.session_state.page = "result"
        st.rerun()

    if qs["is_retry"]:
        qs["q"] = qs["retry_pool"][qs["idx"]]
    else:
        qs["q"] = generate_question(qs["cat"], qs["sub"]) if qs.get("mode","fixed") == "fixed" else generate_question_weighted()

    st.session_state.user_input_buffer = ""
    st.rerun()

def check_answer():
    qs = st.session_state.quiz
    q = qs["q"]
    ok = is_answer_correct(q, st.session_state.user_input_buffer)

    if ok:
        if not qs["is_retry"]:
            qs["score"] += 1
        st.session_state.stat_mgr.record(q.category, q.subcategory, True, qs["is_retry"])
        st.session_state.wrong_count = 0
        next_question()
    else:
        st.session_state.wrong_count += 1
        if st.session_state.wrong_count >= 3:
            st.session_state.stat_mgr.record(q.category, q.subcategory, False, qs["is_retry"])
            if not qs["is_retry"]:
                st.session_state.wrong_pool.append(q)
            st.session_state.wrong_count = 0
            next_question()
        else:
            st.session_state.user_input_buffer = ""

def sidebar_menu() -> str:
    with st.sidebar:
        st.write(f"👤 **{st.session_state.logged_in_user}**")
        if st.button("Logout"):
            logout()
        st.markdown("---")
        items = ["🏠 Home", "📝 Start Quiz", "📊 Statistics", "📘 Theory", "✅ Checklist", "ℹ️ Credits"]
        if is_owner():
            items += ["🧪 Diagnostic", "⚖️ Weights"]
        return st.radio("Menu", items)

# ==============================
# PART B6B — PAGES + ROUTER (FINAL)
# ==============================

def render_home():
    st.title("🎹 Road to Berklee")
    st.write("Music theory practice app.")


def render_quiz_page():
    qs = st.session_state.quiz
    q: Question = qs["q"]
    st.progress(qs["idx"] / max(1, qs["limit"]))
    st.write(f"Question {qs['idx']+1} / {qs['limit']}")
    st.subheader(q.prompt)
    st.text_input("Answer", value=st.session_state.user_input_buffer, disabled=True)

    if render_keypad_for_question(q):
        check_answer()

    if st.button("🏠 Quit"):
        st.session_state.page = "home"
        st.rerun()


def render_result_page():
    qs = st.session_state.quiz
    st.header("Result")
    st.metric("Score", f"{qs['score']}/{qs['limit']}")
    if st.session_state.wrong_pool:
        if st.button("🔄 Retry mistakes", use_container_width=True):
            start_quiz(qs["cat"], qs["sub"], is_retry=True, retry_pool=st.session_state.wrong_pool)
    if st.button("⬅️ Back", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()


def render_start_quiz():
    st.header("📝 Start Quiz")

    mode_label = st.radio("Mode", ["Selected topic", "Random (Weighted)"], horizontal=True)
    limit = st.slider("Number of questions", 5, 50, 10, 5)

    if mode_label == "Selected topic":
        cat = st.selectbox("Category", list(CATEGORY_INFO.keys()))
        sub = st.selectbox("Subcategory", CATEGORY_INFO.get(cat, []))
        if st.button("Start"):
            start_quiz(cat, sub, limit=limit, mode="fixed")
    else:
        st.caption("Weights sheet values control how often each topic appears.")
        if st.button("Start Random (Weighted)"):
            start_quiz("(Random)", "(Weighted)", limit=limit, mode="weighted")


def _plot_accuracy_over_time(df: pd.DataFrame, freq: str):
    if df.empty:
        st.info("No data.")
        return
    d = df.copy()
    d = d.set_index("ts")
    grp = d.resample(freq)["is_correct"].mean() * 100.0
    fig = plt.figure()
    plt.plot(grp.index, grp.values)
    plt.ylabel("Accuracy (%)")
    plt.xlabel("Date")
    st.pyplot(fig, clear_figure=True)

def _topic_features(df: pd.DataFrame, days: int) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["category","subcategory","solved","acc","recent_solved","recent_acc","wrong_streak","last_seen_days"])

    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(days=int(days))

    d = df.copy()
    d["ts"] = pd.to_datetime(d["ts"], errors="coerce")
    d = d.dropna(subset=["ts"])
    d["is_correct"] = pd.to_numeric(d["is_correct"], errors="coerce").fillna(0).astype(int)

    g_all = d.groupby(["category","subcategory"])["is_correct"].agg(["count","mean"]).reset_index()
    g_all.rename(columns={"count":"solved","mean":"acc"}, inplace=True)
    g_all["acc"] = (g_all["acc"] * 100.0).fillna(0.0)

    d_recent = d[d["ts"] >= cutoff].copy()
    if d_recent.empty:
        g_all["recent_solved"] = 0
        g_all["recent_acc"] = 0.0
    else:
        g_recent = d_recent.groupby(["category","subcategory"])["is_correct"].agg(["count","mean"]).reset_index()
        g_recent.rename(columns={"count":"recent_solved","mean":"recent_acc"}, inplace=True)
        g_recent["recent_acc"] = (g_recent["recent_acc"] * 100.0).fillna(0.0)
        g_all = g_all.merge(g_recent, on=["category","subcategory"], how="left")
        g_all["recent_solved"] = pd.to_numeric(g_all["recent_solved"], errors="coerce").fillna(0).astype(int)
        g_all["recent_acc"] = pd.to_numeric(g_all["recent_acc"], errors="coerce").fillna(0.0)

    # last_seen_days
    last_ts = d.groupby(["category","subcategory"])["ts"].max().reset_index().rename(columns={"ts":"last_ts"})
    g_all = g_all.merge(last_ts, on=["category","subcategory"], how="left")
    g_all["last_seen_days"] = (now - g_all["last_ts"]).dt.days.fillna(999).astype(int)
    g_all = g_all.drop(columns=["last_ts"], errors="ignore")

    # wrong_streak: consecutive wrong answers at the end of history for each topic
    d_sorted = d.sort_values("ts")
    streak_map = {}
    for (cat, sub), grp in d_sorted.groupby(["category","subcategory"]):
        streak = 0
        for v in grp["is_correct"].tolist()[::-1]:
            if int(v) == 0:
                streak += 1
            else:
                break
        streak_map[(cat, sub)] = streak
    g_all["wrong_streak"] = g_all.apply(lambda r: int(streak_map.get((r["category"], r["subcategory"]), 0)), axis=1)

    return g_all[["category","subcategory","solved","acc","recent_solved","recent_acc","wrong_streak","last_seen_days"]]


def _clamp(x: float, lo: float, hi: float) -> float:
    return float(min(hi, max(lo, x)))


def _recommend_weights(features: pd.DataFrame, base: float = 1.0, floor: float = 0.0, ceil: float = 5.0) -> Dict[tuple, float]:
    rec = {(c, s): base for c, subs in CATEGORY_INFO.items() for s in subs}
    if features.empty:
        return rec

    for _, r in features.iterrows():
        cat = str(r["category"])
        sub = str(r["subcategory"])
        if (cat, sub) not in rec:
            continue

        solved = int(r["solved"])
        acc = float(r["acc"])
        recent_solved = int(r["recent_solved"])
        recent_acc = float(r["recent_acc"])
        wrong_streak = int(r["wrong_streak"])
        last_seen_days = int(r["last_seen_days"])

        w = base

        # 1) Not enough data → keep near base
        if solved < 8:
            w = base
        else:
            # 2) Core weakness by accuracy (prefer recent accuracy if we have enough recent samples)
            eff_acc = recent_acc if recent_solved >= 5 else acc

            if eff_acc < 45:
                w += 2.0
            elif eff_acc < 65:
                w += 1.2
            elif eff_acc < 80:
                w += 0.5
            elif eff_acc >= 92:
                w -= 0.6
            elif eff_acc >= 87:
                w -= 0.3

            # 3) Volume confidence: more solved → stronger effect
            if solved >= 60:
                w += 0.3 if eff_acc < 70 else -0.2
            elif solved >= 30:
                w += 0.15 if eff_acc < 70 else -0.1

        # 4) Wrong streak boost (recent repeated failure)
        if wrong_streak >= 4:
            w += 0.8
        elif wrong_streak == 3:
            w += 0.5
        elif wrong_streak == 2:
            w += 0.25

        # 5) Recency: if not seen for long time, gently boost to avoid forgetting
        if last_seen_days >= 30:
            w += 0.35
        elif last_seen_days >= 14:
            w += 0.2

        rec[(cat, sub)] = _clamp(w, floor, ceil)

    return rec


def _render_weight_recommendation(df_history: pd.DataFrame):
    st.subheader("Weight recommendation (weakness-aware)")

    days = st.selectbox("Analysis window (days)", [7, 14, 30, 90], index=2, key="wr_days")
    base = st.slider("Base weight", 0.0, 3.0, 1.0, 0.5, key="wr_base")
    floor = st.slider("Minimum weight", 0.0, 2.0, 0.0, 0.5, key="wr_floor")
    ceil = st.slider("Maximum weight", 3.0, 8.0, 5.0, 0.5, key="wr_ceil")

    feats = _topic_features(df_history, days=int(days))
    if feats.empty:
        st.info("No history found yet.")
        return

    rec = _recommend_weights(feats, base=float(base), floor=float(floor), ceil=float(ceil))

    view = feats.copy()
    view["recommended_weight"] = view.apply(
        lambda r: rec.get((str(r["category"]), str(r["subcategory"])), float(base)),
        axis=1
    )

    # Prioritize: low effective accuracy + high wrong streak + enough recent attempts
    view["priority"] = (
        (100.0 - view["recent_acc"].where(view["recent_solved"] >= 5, view["acc"])) +
        (view["wrong_streak"] * 8.0) +
        (view["last_seen_days"].clip(0, 60) * 0.2)
    )
    view = view.sort_values(["priority","recent_solved","solved"], ascending=[False, False, False])

    st.dataframe(
        view[["category","subcategory","solved","acc","recent_solved","recent_acc","wrong_streak","last_seen_days","recommended_weight"]],
        use_container_width=True
    )

    st.caption("Logic: lower accuracy, higher recent wrong streak, and long time since last practice increase the recommended weight.")

    if not is_owner():
        st.info("Only the owner can apply these weights to Google Sheets.")
        return

    if st.button("Apply recommended weights to Google Sheets"):
        ok_all = True
        for (cat, sub), w in rec.items():
            ok_all = ok_all and st.session_state.stat_mgr.upsert_weight(cat, sub, float(w), st.session_state.logged_in_user)
        st.success("Applied successfully." if ok_all else "Applied with some failures (check sheet permissions).")


    rec = _recommend_weights(topic, base=base)

    view = topic.copy()
    view["recommended_weight"] = view.apply(lambda r: rec.get((str(r["category"]), str(r["subcategory"])), base), axis=1)
    view = view.sort_values(["acc","solved"], ascending=[True, False])

    st.dataframe(view[["category","subcategory","solved","acc","recommended_weight"]], use_container_width=True)

    if not is_owner():
        st.caption("Owner only can apply these weights to Google Sheet.")
        return

    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("💾 Apply recommended weights"):
            ok_all = True
            for (cat, sub), w in rec.items():
                ok_all = ok_all and st.session_state.stat_mgr.upsert_weight(cat, sub, float(w), st.session_state.logged_in_user)
            st.success("Applied." if ok_all else "Some saves failed.")
    with c2:
        st.caption("Tip: accuracy 낮은 토픽이 자동으로 weight↑, 높은 토픽은 weight↓로 추천돼.")

def render_statistics():
    st.header("📊 Statistics")
    rows = st.session_state.stat_mgr.data
    df = stat_df_from_history(rows)

    solved = int(df.shape[0])
    correct = int(df["is_correct"].sum()) if solved else 0
    acc = (correct / solved * 100.0) if solved else 0.0

    st.markdown(f"### {solved} steps to Berklee College of Music")
    st.write(f"Total Accuracy: **{acc:.1f}%**")

    if df.empty:
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        days = st.selectbox("Period", [7, 14, 30, 90, 365], index=2)
    with c2:
        freq = st.selectbox("Graph unit", [("Daily","D"),("Weekly","W"),("Monthly","M")], index=1, format_func=lambda x: x[0])[1]
    with c3:
        cat_filter = st.selectbox("Category filter", ["(All)"] + list(CATEGORY_INFO.keys()))

    cutoff = datetime.datetime.now() - datetime.timedelta(days=int(days))
    dff = df[df["ts"] >= cutoff]
    if cat_filter != "(All)":
        dff = dff[dff["category"] == cat_filter]

    st.subheader("Accuracy over time")
    _plot_accuracy_over_time(dff, freq)

    st.subheader("By category")
    by = dff.groupby("category")["is_correct"].agg(["count","sum"])
    by["acc"] = (by["sum"] / by["count"] * 100.0).fillna(0.0)
    st.dataframe(by.rename(columns={"count":"solved","sum":"correct","acc":"accuracy%"}), use_container_width=True)
    _render_weight_recommendation(df)



def render_theory():
    st.header("📘 Theory")
    if "theory_df" not in st.session_state:
        st.session_state.theory_df = st.session_state.stat_mgr.load_theory_df()
    df = st.session_state.theory_df

    cat = st.selectbox("Category", list(CATEGORY_INFO.keys()), key="th_cat")
    sub = st.selectbox("Subcategory", CATEGORY_INFO.get(cat, []), key="th_sub")

    content = ""
    if not df.empty:
        m = (df["category"].astype(str) == str(cat)) & (df["subcategory"].astype(str) == str(sub))
        if m.any():
            content = str(df[m].iloc[0]["content"] or "")

    if is_owner():
        new = st.text_area("Owner editor", value=content, height=260)
        c1, c2 = st.columns([1,2])
        with c1:
            if st.button("💾 Save"):
                ok = st.session_state.stat_mgr.upsert_theory(cat, sub, new, st.session_state.logged_in_user)
                if ok:
                    st.session_state.theory_df = st.session_state.stat_mgr.load_theory_df()
                    st.success("Saved.")
                else:
                    st.error("Save failed.")
        with c2:
            if st.button("🔄 Reload"):
                st.session_state.theory_df = st.session_state.stat_mgr.load_theory_df()
                st.rerun()
    else:
        if content.strip():
            st.markdown(content)
        else:
            st.info("No notes yet.")


def render_checklist():
    st.header("✅ Checklist")
    if "checklist_df" not in st.session_state:
        st.session_state.checklist_df = st.session_state.stat_mgr.load_checklist_df()
    df = st.session_state.checklist_df

    if df.empty:
        st.info("No checklist items yet.")
    else:
        for section in df["section"].astype(str).unique():
            st.subheader(section)
            subdf = df[df["section"].astype(str) == str(section)]
            for _, r in subdf.iterrows():
                item = str(r["item"])
                checked = int(r["checked"]) == 1
                key = f"chk_{section}_{item}"
                new_val = st.checkbox(item, value=checked, key=key)
                if new_val != checked:
                    st.session_state.stat_mgr.set_checklist_item(section, item, 1 if new_val else 0, st.session_state.logged_in_user)
                    st.session_state.checklist_df = st.session_state.stat_mgr.load_checklist_df()
                    st.rerun()

    if is_owner():
        st.markdown("---")
        st.subheader("Owner: Add / Delete")
        sec = st.text_input("Section", key="chk_sec")
        item = st.text_input("Item", key="chk_item")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("➕ Add"):
                if sec.strip() and item.strip():
                    st.session_state.stat_mgr.set_checklist_item(sec.strip(), item.strip(), 0, st.session_state.logged_in_user)
                    st.session_state.checklist_df = st.session_state.stat_mgr.load_checklist_df()
                    st.rerun()
        with c2:
            if st.button("🗑️ Delete"):
                if sec.strip() and item.strip():
                    st.session_state.stat_mgr.delete_checklist_item(sec.strip(), item.strip())
                    st.session_state.checklist_df = st.session_state.stat_mgr.load_checklist_df()
                    st.rerun()


def render_diagnostic():
    st.header("🧪 Diagnostic")
    if not is_owner():
        st.warning("Owner only.")
        return
    cat = st.selectbox("Category", list(CATEGORY_INFO.keys()), key="dg_cat")
    sub = st.selectbox("Subcategory", CATEGORY_INFO.get(cat, []), key="dg_sub")
    if st.button("🎲 Generate"):
        st.session_state.dg_q = generate_question(cat, sub)
    q = st.session_state.get("dg_q")
    if not q:
        return
    st.subheader(q.prompt)
    st.write(f"kind: `{q.kind}`  | sep: `{q.sep}`")
    st.code(", ".join(q.answers))


def render_weights():
    st.header("⚖️ Weights")
    if not is_owner():
        st.warning("Owner only.")
        return
    df = st.session_state.stat_mgr.load_weights_df()
    weights = {}
    for cat, subs in CATEGORY_INFO.items():
        for sub in subs:
            weights[(cat, sub)] = 1.0
    if not df.empty:
        for _, r in df.iterrows():
            weights[(str(r["category"]), str(r["subcategory"]))] = float(r["weight"])

    cat = st.selectbox("Category", list(CATEGORY_INFO.keys()), key="wg_cat")
    changed = False
    for sub in CATEGORY_INFO.get(cat, []):
        key = f"w_{cat}_{sub}"
        new = st.slider(sub, 0.0, 5.0, float(weights[(cat, sub)]), 0.5, key=key)
        if float(new) != float(weights[(cat, sub)]):
            weights[(cat, sub)] = float(new)
            changed = True

    if st.button("💾 Save weights"):
        ok_all = True
        for sub in CATEGORY_INFO.get(cat, []):
            ok_all = ok_all and st.session_state.stat_mgr.upsert_weight(cat, sub, weights[(cat, sub)], st.session_state.logged_in_user)
        st.success("Saved." if ok_all else "Some saves failed.")


# Router
if st.session_state.logged_in_user is None:
    render_login()
    st.stop()

menu = sidebar_menu()

if menu == "🏠 Home":
    render_home()
elif menu == "📝 Start Quiz":
    if st.session_state.page == "quiz":
        render_quiz_page()
    elif st.session_state.page == "result":
        render_result_page()
    else:
        render_start_quiz()
elif menu == "📊 Statistics":
    render_statistics()
elif menu == "📘 Theory":
    render_theory()
elif menu == "✅ Checklist":
    render_checklist()
elif menu == "🧪 Diagnostic":
    render_diagnostic()
elif menu == "⚖️ Weights":
    render_weights()
elif menu == "ℹ️ Credits":
    st.header("ℹ️ Credits")
    st.write("### Road to Berklee")
    st.write("Developed by: Oh Seung-yeol")


