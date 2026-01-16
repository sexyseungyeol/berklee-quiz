import streamlit as st
import random
import time
import json
import os
import datetime
from datetime import timedelta
import hashlib
import gspread

# Cookie Manager Check
try:
    import extra_streamlit_components as stx
except ImportError:
    st.error("⚠️ Please install 'extra-streamlit-components' in requirements.txt")
    st.stop()

# ==========================================
# 1. DATA DEFINITIONS
# ==========================================
NOTES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
NATURAL_INTERVAL_DATA = {'P1': ['-2', '+7', 'P8', '+14'], 'm2': ['+1', 'm9', '+8'], 'M2': ['-3', 'M9', '-10'], 'm3': ['+2', 'm10', '+9'], 'M3': ['-4', 'M10', '-11'], 'P4': ['+3', 'P11', '+10'], 'Tritone': ['+11', '-12'], 'P5': ['-6', 'P12', '-13'], 'm6': ['+5', 'm13', '+12'], 'M6': ['-7', 'M13', '-14'], 'm7': ['+6', 'm14', '+13'], 'M7': ['-8', 'M14']}
DISTANCE_TO_DEGREE = {1:['I'],2:['#I','bII'],3:['II'],4:['#II','bIII'],5:['III'],6:['IV'],7:['#IV','bV'],8:['V'],9:['#V','bVI'],10:['VI'],11:['#VI','bVII'],12:['VII']}
DEGREE_MAP = {'I':0,'bII':1,'#I':1,'II':2,'bIII':3,'#II':3,'III':4,'IV':5,'#III':5,'bV':6,'#IV':6,'V':7,'bVI':8,'#V':8,'VI':9,'bVII':10,'#VI':10,'VII':11}
ENHARMONIC_GROUPS = {0:['C','B#'],1:['Db','C#'],2:['D'],3:['Eb','D#'],4:['E','Fb'],5:['F','E#'],6:['Gb','F#'],7:['G'],8:['Ab','G#'],9:['A'],10:['Bb','A#'],11:['B','Cb']}
SOLFEGE = {'I':'Do','II':'Re','III':'Mi','IV':'Fa','V':'Sol','VI':'La','VII':'Ti','bII':'Ra','bIII':'Me','bV':'Se','bVI':'Le','bVII':'Te','#I':'Di','#II':'Ri','#IV':'Fi','#V':'Si','#VI':'Li'}
KEY_SIGS_MAJOR = {'C':'','G':'#','D':'##','A':'###','E':'####','B':'#####','F#':'######','F':'b','Bb':'bb','Eb':'bbb','Ab':'bbbb','Db':'bbbbb','Gb':'bbbbbb'}
KEY_SIGS_MINOR = {'A':'','E':'#','B':'##','F#':'###','C#':'####','G#':'#####','D#':'######','D':'b','G':'bb','C':'bbb','F':'bbbb','Bb':'bbbbb','Eb':'bbbbbb'}
CHORD_FORMULAS = {'maj7':[0,4,7,11],'mM7':[0,3,7,11],'6':[0,4,7,9],'m6':[0,3,7,9],'7':[0,4,7,10],'m7':[0,3,7,10],'m7b5':[0,3,6,10],'dim7':[0,3,6,9],'aug':[0,4,8],'aug7':[0,4,8,10],'7(b5)':[0,4,6,10],'+M7':[0,4,8,11],'7sus4':[0,5,7,10]}
SCALES_DATA = {'Ionian':['I','II','III','IV','V','VI','VII'],'Dorian':['I','II','bIII','IV','V','VI','bVII'],'Phrygian':['I','bII','bIII','IV','V','bVI','bVII'],'Lydian':['I','II','III','#IV','V','VI','VII'],'Mixolydian':['I','II','III','IV','V','VI','bVII'],'Aeolian':['I','II','bIII','IV','V','bVI','bVII'],'Locrian':['I','bII','bIII','IV','bV','bVI','bVII'],'Natural minor':['I','II','bIII','IV','V','bVI','bVII'],'Harmonic minor':['I','II','bIII','IV','V','bVI','VII'],'Melodic minor':['I','II','bIII','IV','V','VI','VII']}
MODE_ALTERATIONS = {'Dorian':['bIII','bVII'],'Phrygian':['bII','bIII','bVI','bVII'],'Lydian':['#IV'],'Mixolydian':['bVII'],'Aeolian':['bIII','bVI','bVII'],'Locrian':['bII','bIII','bV','bVI','bVII']}
AVAILABLE_SCALES_MAP = {'Ionian':['I','I6','Imaj7'],'Dorian':['IVm','IVm6','IVm7','IIm7','Vm','Vm7'],'Phrygian':['IIIm7'],'Lydian':['IV','IVmaj7','bVII','bVIImaj7','bVImaj7','bIImaj7','bIIImaj7','IV6'],'Mixolydian':['V','bVII7','V7/IV','V7/V'],'Aeolian':['VIm7'],'Locrian':['VIIm7b5','#IVm7b5','IIm7b5'],'All':['I7'],'Altered':['VII7']}
CHORD_FUNCTIONS = {'T':['I','I6','Imaj7','IIIm7','VIm7','I7','IIIm7b5','III7','#IVm7b5'],'Tm':['Im','Im6','Imb6','Im7','ImM7','bIIImaj7','bIII+M7','VIm7b5','bVImaj7'],'SD':['IV','IV6','IVmaj7','IIm7','IV7','bVII','bVIImaj7','VII7','#IVm7b5'],'SDm':['IVm','IVm6','IVm7','IIm7b5','bVI6','bVImaj7','bVII7','bIImaj7','bVI7','IVmM7'],'D':['V','V7','VIIm7b6','bII7','VIIdim7'],'Dm':['Vm','Vm7']}
DUAL_FUNCTION_CHORDS = {'#IVm7b5':['T','SD'],'bVImaj7':['SDm','Tm']}
MODE_TENSIONS = {'Ionian':['9','13'],'Dorian':['9','11'],'Phrygian':['11'],'Lydian':['9','#11','13'],'Mixolydian':['9','13'],'Aeolian':['9','11'],'Locrian':['11','b13']}
MINOR_DATA = {'Natural minor':{'degrees':['I','II','bIII'],'chords':['m7','m7b5','maj7'],'tens':[['9','11'],['11','b13'],['9','13']]},'Harmonic minor':{'degrees':['I','V','VII'],'chords':['mM7','7','dim7'],'tens':[['9','11'],['9','b13'],['9','11']]},'Melodic minor':{'degrees':['I','IV','V'],'chords':['mM7','7','7'],'tens':[['9','11','13'],['9','#11','13'],['9','b13']]}}
MODE_OFFSET_MAP = {'Ionian':0,'Dorian':2,'Phrygian':4,'Lydian':5,'Mixolydian':7,'Aeolian':9,'Locrian':11}

CATEGORY_INFO = {
    'Enharmonics': ['Degrees', 'Number', 'Natural Form'],
    'Warming up': ['Counting semitones', 'Finding degrees', 'Chord tones', 'Key signatures', 'Solfege'],
    'Intervals': ['Alternative', 'Tracking'],
    'Chord Forms': ['Relationships', 'Extract (Degree)', 'Extract (Pitch)', '9 chord', 'Rootless'],
    'Cycle of 5th': ['P5 down', 'P5 up', 'r calc', '2-5-1'],
    'Locations': ['Deg->Pitch', 'Pitch->Deg'],
    'Tritones': ['Pitch', 'Degree', 'Dom7', 'Dim7'],
    'Modes': ['Alterations', 'Tensions', 'Chords(Deg)', 'Chords(Key)'],
    'Minor': ['Chords', 'Tensions', 'Pitch'],
    'Mastery': ['Functions', 'Degrees', 'Pitches', 'Avail Scales', 'Pivot', 'Similarities']
}

# --- UPDATED THEORY DATA (Natural Form & Semitones Fixed) ---
THEORY_DATA = {
    'Enharmonics': {
        'Degrees': "### Enharmonic Degrees\n\nNotes that share the same pitch but have different names.\n\n| Sharp | Flat | Relation |\n| :--- | :--- | :--- |\n| #I | bII | Root # ↔ Super b |\n| #II | bIII | Super # ↔ Mediant b |\n| #IV | bV | Tritone |",
        'Number': "### Enharmonic Interval Numbers\n\nIdentifying compound intervals and rare interval names.\n\n| Semitones | Simple | Compound | Rare |\n| :--- | :--- | :--- | :--- |\n| 2 | 2 (M2) | 9 | bb3 |\n| 5 | 4 (P4) | 11 | #3 |",
        'Natural Form': "### Natural Form\n\nIdentifying the fundamental interval quality from altered or compound notations. Just like identifying the 'Root' of a complex chord.\n\n| Code | Meaning | **Natural Form** |\n| :--- | :--- | :--- |\n| **+7** | Octave - 1 | **P8** (Target) |\n| **-2** | Octave - 2 | **b7** |\n| **+1** | Root + 1 | **m2** |\n| **+8** | Octave + 1 | **m9** (same as m2) |\n| **+14** | Octave + 2 | **M9** (same as M2) |\n\n**Tip:** Convert everything to the simple interval (1-7) to find the answer."
    },
    'Warming up': {
        'Counting semitones': "### Semitones Map (Counting from 1)\n\nWe count the **Root as 1** (the starting point).\n\n| Count | Interval | Degree |\n| :--- | :--- | :--- |\n| **1** | Perfect Unison | **P1** |\n| **2** | Minor 2nd | **b2** |\n| **3** | Major 2nd | **M2** |\n| **4** | Minor 3rd | **b3** |\n| **5** | Major 3rd | **M3** |\n| **6** | Perfect 4th | **P4** |\n| **7** | Tritone | **b5/#4** |\n| **8** | Perfect 5th | **P5** |\n| **9** | Minor 6th | **b6** |\n| **10** | Major 6th | **M6** |\n| **11** | Minor 7th | **b7** |\n| **12** | Major 7th | **M7** |\n| **13** | Octave | **P8** |",
        'Finding degrees': "### Finding Degrees\n\nFinding the specific degree within a given major key.\n* Example: What is the IV of C? -> **F**",
        'Chord tones': "### Chord Formulas\n\n* **Maj7:** 1-3-5-7\n* **7:** 1-3-5-b7\n* **m7:** 1-b3-5-b7\n* **m7b5:** 1-b3-b5-b7\n* **dim7:** 1-b3-b5-bb7",
        'Key signatures': "### Key Signatures\n\n**Sharps:** F-C-G-D-A-E-B\n**Flats:** B-E-A-D-G-C-F",
        'Solfege': "### Chromatic Solfege\n\n* Di, Ri, Fi, Si, Li (Sharps)\n* Ra, Me, Se, Le, Te (Flats)"
    },
    'Intervals': {
        'Alternative': "### Alternative Intervals (Inversions)\n\n* **Major ↔ Minor**\n* **Aug ↔ Dim**\n* **Perfect ↔ Perfect**",
        'Tracking': "### Interval Tracking\n\n1. Count letters (C to E is a 3rd).\n2. Check semitones."
    },
    'Chord Forms': {
        'Relationships': "### Related Chords\n\n* **Cm7 -> C6:** Lower b7 to 6.\n* **Cm7 -> Cm7b5:** Lower 5 to b5.\n* **Cmaj7 -> C7:** Lower 7 to b7.\n* **Cdim7 -> C7(b9):** Lower any note by 1 semitone.",
        'Extract (Degree)': "### Upper Structures\n\n* **Cmaj9** (3rd to 9th) = **Em7**\n* **C13** (b7 to 13) = **Bbmaj7#5**"
    },
    'Cycle of 5th': {
        'P5 down': "### Cycle of Fifths\n\n**C - F - Bb - Eb - Ab - Db - Gb - B - E - A - D - G**\n\nAdds one Flat (b) each step.",
        '2-5-1': "### II-V-I\n\nFrom Target (I):\n* **II:** Whole step up.\n* **V:** Perfect 5th up."
    },
    'Tritones': {
        'Pitch': "### Tritone\n\nInterval of 3 Whole Steps.\n* C - F#\n* F - B\n* Bb - E\n* Eb - A",
        'Dom7': "### Dom7 & Tritone\n\nTritone is between 3rd and b7.\n* Inwards resolution -> **Imaj7**\n* Outwards resolution -> **Gbmaj7** (Tritone Sub)"
    },
    'Modes': {
        'Alterations': "### Mode Colors\n\n* **Ionian:** Natural\n* **Dorian:** Natural 6\n* **Phrygian:** b2\n* **Lydian:** #4\n* **Mixolydian:** b7\n* **Aeolian:** b6\n* **Locrian:** b2, b5",
        'Tensions': "### Tensions\n\nAvoid b9 intervals with chord tones.\n* **Ionian:** 9, 13\n* **Dorian:** 9, 11\n* **Phrygian:** 11, b13\n* **Lydian:** 9, #11, 13\n* **Mixolydian:** 9, 13\n* **Aeolian:** 9, 11\n* **Locrian:** 11, b13"
    },
    'Minor': {
        'Chords': "### Minor Harmony\n\n* **Natural:** Im7, IIm7b5, bIIImaj7...\n* **Harmonic:** V7(b9,b13), VIIdim7\n* **Melodic:** ImM7, IV7, V7",
        'Tensions': "### Minor Tensions\n\n**V7** in minor keys uses **b9, b13**."
    },
    'Mastery': {
        'Functions': "### Functions\n\n* **Tonic:** Imaj7, IIIm7, VIm7\n* **Sub-Dom:** IVmaj7, IIm7\n* **Dominant:** V7, VIIdim7",
        'Avail Scales': "### Chord Scales\n\n* **Imaj7:** Ionian, Lydian\n* **Im7:** Dorian, Aeolian\n* **V7:** Mixolydian, Altered\n* **m7b5:** Locrian"
    }
}

DEFAULT_THEORY = "### Practice Makes Perfect!\n\nNo specific theory content is available for this section yet.\nIf you are **Oh Seung-yeol**, you can edit this text."

# ==========================================
# 2. STAT MANAGER
# ==========================================
class StatManager:
    def __init__(self, key_file="service_account.json", sheet_name="Berklee_DB"):
        self.connected = False
        self.current_user = None 
        try:
            if "gcp_service_account" in st.secrets:
                creds_dict = dict(st.secrets["gcp_service_account"])
                self.gc = gspread.service_account_from_dict(creds_dict)
            elif os.path.exists(key_file):
                self.gc = gspread.service_account(filename=key_file)
            else: self.gc = None
            if self.gc:
                self.sh = self.gc.open(sheet_name)
                self.connected = True
        except: self.connected = False
        if self.connected:
            try: self.ws_users = self.sh.worksheet("Users")
            except: self.ws_users = self.sh.add_worksheet(title="Users", rows="100", cols="3")
            try: self.ws_history = self.sh.worksheet("History")
            except: self.ws_history = self.sh.add_worksheet(title="History", rows="1000", cols="10")
            try: self.ws_leaderboard = self.sh.worksheet("Leaderboard")
            except: self.ws_leaderboard = self.sh.add_worksheet(title="Leaderboard", rows="1000", cols="10")
            try: self.ws_theory = self.sh.worksheet("Theory")
            except: self.ws_theory = self.sh.add_worksheet(title="Theory", rows="200", cols="3")

    def hash_password(self, password): return hashlib.sha256(password.encode()).hexdigest()
    def create_user(self, username, password):
        if not self.connected: return False, "Database not connected."
        users = self.ws_users.col_values(1)
        if username in users: return False, "Username already exists."
        self.ws_users.append_row([username, self.hash_password(password), datetime.datetime.now().strftime("%Y-%m-%d")])
        return True, "User created successfully!"
    def login_user(self, username, password):
        if not self.connected: return False
        try:
            cell = self.ws_users.find(username)
            if cell and self.ws_users.cell(cell.row, 2).value == self.hash_password(password):
                self.current_user = username; self.load_user_data(); return True
            return False
        except: return False
    def auto_login(self, username):
        if not self.connected: return False
        try:
            if username in self.ws_users.col_values(1):
                self.current_user = username; self.load_user_data(); return True
            return False
        except: return False
    def load_user_data(self):
        try: self.data = [r for r in self.ws_history.get_all_records() if str(r['username']) == self.current_user]
        except: self.data = []
        try: self.leaderboard_raw = self.ws_leaderboard.get_all_records()
        except: self.leaderboard_raw = []
    def get_theory(self, category, subcategory):
        if not self.connected: return THEORY_DATA.get(category, {}).get(subcategory, DEFAULT_THEORY)
        try:
            for r in self.ws_theory.get_all_records():
                if r['category'] == category and r['subcategory'] == subcategory and str(r['content']).strip(): return r['content']
            return THEORY_DATA.get(category, {}).get(subcategory, DEFAULT_THEORY)
        except: return DEFAULT_THEORY
    def save_theory(self, category, subcategory, content):
        if not self.connected: return False
        try:
            records = self.ws_theory.get_all_records()
            row_idx = next((i+2 for i, r in enumerate(records) if r['category'] == category and r['subcategory'] == subcategory), None)
            if row_idx: self.ws_theory.update_cell(row_idx, 3, content)
            else: self.ws_theory.append_row([category, subcategory, content])
            return True
        except: return False
    def record(self, category, subcategory, is_correct, is_retry=False):
        if not self.current_user or not self.connected: return
        now = datetime.datetime.now()
        row = [self.current_user, now.timestamp(), now.year, now.month, now.day, category, subcategory, 1 if (is_correct and not is_retry) else 0, 1 if (is_correct or is_retry) else 0]
        try: self.ws_history.append_row(row)
        except: pass
    def update_leaderboard(self, mode, category, subcategory, result_data):
        if not self.current_user or not self.connected: return
        row = [self.current_user, category, subcategory, mode, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")]
        if mode == 'test': row.extend([result_data['score'], result_data['total'], result_data['time'], 0, 0])
        elif mode == 'speed': row.extend([0, 0, 0, result_data['correct'], (result_data['correct']/result_data['total_try']*100) if result_data['total_try']>0 else 0])
        try: self.ws_leaderboard.append_row(row)
        except: pass
    def calculate_stats(self, data):
        if not data: return 0, 0.0
        solved = sum(1 for r in data if r.get('is_solved', 0) == 1)
        rate = (sum(1 for r in data if r.get('is_correct', 0) == 1) / len(data) * 100) if data else 0.0
        return solved, rate
    def get_breakdown(self, data):
        bd = {}
        for r in data:
            c, s = r['category'], r['subcategory']
            if c not in bd: bd[c] = {'total': 0, 'correct': 0, 'subs': {}}
            if s not in bd[c]['subs']: bd[c]['subs'][s] = {'total': 0, 'correct': 0}
            bd[c]['total'] += 1; bd[c]['subs'][s]['total'] += 1
            if r.get('is_correct', 0) == 1: bd[c]['correct'] += 1; bd[c]['subs'][s]['correct'] += 1
        return bd
    def get_trend_data(self, category, subcategory, period):
        target = [r for r in self.data if (category == "All" or r['category'] == category) and (not subcategory or r['subcategory'] == subcategory)]
        if not target: return []
        grouped = {}
        for r in target:
            key = f"{r['year']}-W{datetime.datetime.fromtimestamp(r['timestamp']).isocalendar()[1]:02d}"
            if key not in grouped: grouped[key] = {'c': 0, 't': 0}
            grouped[key]['t'] += 1
            if r.get('is_correct', 0) == 1: grouped[key]['c'] += 1
        return sorted([(k, (v['c']/v['t']*100)) for k, v in grouped.items()])

if 'stat_mgr' not in st.session_state: st.session_state.stat_mgr = StatManager()

# ==========================================
# 3. UTILS & GENERATOR & KEYPAD
# ==========================================
def get_enharmonic_names(idx): return ENHARMONIC_GROUPS.get(idx % 12, [])
def get_pitch_index(p):
    p = p.strip().capitalize()
    enh = {'C#':'Db','D#':'Eb','F#':'Gb','G#':'Ab','A#':'Bb','Cb':'B','B#':'C','E#':'F','Fb':'E'}
    p = enh.get(p, p)
    return NOTES.index(p) if p in NOTES else -1
def get_pitch_from_index(idx): return NOTES[idx % 12]
def get_valid_answers(idx, suf=""): return [f"{r}{suf}" for r in get_enharmonic_names(idx)]
def get_slash_answers(ridx, suf, bidx): return [f"{r}{suf}/{b}" for r in get_enharmonic_names(ridx) for b in get_enharmonic_names(bidx)]
def normalize_input(text):
    text = text.replace('♭', 'b').replace('♯', '#')
    return set([p.strip().lower() for p in text.replace('/',',').split(',') if p.strip()])

def get_keypad_keys(cat, sub):
    if (cat == 'Enharmonics' and sub == 'Degrees') or \
       (cat == 'Warming up' and sub == 'Finding degrees') or \
       (cat == 'Locations' and sub == 'Pitch->Deg') or \
       (cat == 'Modes' and sub == 'Alterations') or \
       (cat == 'Mastery' and sub == 'Degrees'):
       return [['♭', '♯'], ['I','II','III','IV'], ['V','VI','VII']]
    if cat == 'Intervals' or \
       (cat == 'Enharmonics' and sub == 'Natural Form') or \
       (cat == 'Enharmonics' and sub == 'Number'):
       return [['m','M','P'], ['1','2','3','4'], ['5','6','7','8'], ['+','-']]
    if (cat == 'Modes' and sub != 'Chords(Deg)' and sub != 'Chords(Key)') or \
       (cat == 'Mastery' and sub == 'Avail Scales'):
       return [['Ionian','Dorian'], ['Phrygian','Lydian'], ['Mixolydian','Aeolian'], ['Locrian']]
    if cat == 'Warming up' and sub == 'Solfege':
        return [['Do','Re','Mi','Fa'], ['Sol','La','Ti'], ['Di','Ri','Fi','Si','Li'], ['Ra','Me','Se','Le','Te']]
    rows = [['♭','♯', '/'], ['C','D','E','F'], ['G','A','B']]
    if cat == 'Chord Forms' or cat == 'Minor' or cat == 'Tritones' or cat == 'Modes':
        rows.append(['maj7','m7','7','m7b5'])
        rows.append(['dim7','6','m6','sus4','aug'])
    return rows

# [STYLE FIX: Targeted CSS for Keypad Buttons Only]
def render_keypad(cat, sub):
    key_rows = get_keypad_keys(cat, sub)
    
    st.markdown("""
        <style>
        /* Keypad Buttons specific styling */
        div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] .stButton > button {
            width: 100% !important;
            height: 70px !important;
            font-size: 24px !important;
            font-weight: bold !important;
            border-radius: 10px !important;
            margin: 0px !important;
        }
        /* Sidebar Button Reset */
        section[data-testid="stSidebar"] .stButton > button {
            height: auto !important;
            width: auto !important;
            font-size: inherit !important;
        }
        div[data-testid="column"] {
            padding: 2px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    for row in key_rows:
        cols = st.columns(len(row))
        for i, key in enumerate(row):
            if cols[i].button(key, key=f"k_{key}"):
                st.session_state.user_input_buffer += key
                st.rerun()
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if st.button("⬅️ Del"): st.session_state.user_input_buffer = st.session_state.user_input_buffer[:-1]; st.rerun()
    with c2:
        if st.button("❌ Clear"): st.session_state.user_input_buffer = ""; st.rerun()
    with c3:
        if st.button("✅ Submit", type="primary"): return True
    return False

def generate_question(cat, sub):
    try:
        if cat == 'Enharmonics':
            if sub == 'Degrees':
                pairs = [('#VII','I'),('#I','bII'),('#II','bIII'),('bIV','III'),('IV','#III'),('#V','bVI'),('#VI','bVII')]
                t, a = random.choice(pairs)
                return f"What is {t}'s enharmonic?", [a], 'single'
            elif sub == 'Number':
                sets = [
                    ['1','8','bb2'],['#1','b2','#8','b9'],['2','9','bb3'],['#2','b3','#9','b10'],
                    ['3','10','b4'],['4','11','#3'],['#4','b5','#11','b12'],['5','12','bb6'],
                    ['#5','b6','#12','b13'],['6','13','bb7'],['#6','b7','#13','b14'],['7','14','b8','b1']
                ]
                c = random.choice(sets); t = random.choice(c); ans = [x for x in c if x!=t]
                return f"What are {t}'s enharmonics?", ans, 'single'
            elif sub == 'Natural Form':
                k = random.choice(list(NATURAL_INTERVAL_DATA.keys()))
                q = random.choice(NATURAL_INTERVAL_DATA[k])
                return f"What is {q}'s natural form?", [k], 'single'
        elif cat == 'Warming up':
            if sub == 'Counting semitones':
                d = random.randint(1,12); return f"Which degree is {d} semitones away?", DISTANCE_TO_DEGREE[d], 'single'
            elif sub == 'Finding degrees':
                dn, dv = random.choice(list(DEGREE_MAP.items())); p = random.choice(NOTES)
                idx = (get_pitch_index(p) + dv) % 12; return f"What is {dn} of {p} Key?", get_enharmonic_names(idx), 'single'
            elif sub == 'Chord tones':
                p=random.choice(NOTES); ct=random.choice(list(CHORD_FORMULAS.keys())); idx=get_pitch_index(p)
                ans=[]; 
                for interval in CHORD_FORMULAS[ct]: ans.append(get_pitch_from_index((idx+interval)%12))
                return f"What are the Chord tones of {p}{ct}? (Separate by comma)", ans, 'all_indices'
            elif sub == 'Key signatures':
                is_maj=random.choice([True,False]); k,v=random.choice(list(KEY_SIGS_MAJOR.items() if is_maj else KEY_SIGS_MINOR.items()))
                return f"What {'major' if is_maj else 'minor'} key has ({v if v else 'none'})?", [k], 'single'
            elif sub == 'Solfege':
                k,v = random.choice(list(SOLFEGE.items())); return f"What is {k}'s solfege?", [v], 'single'
        elif cat == 'Intervals':
            root = random.choice(NOTES)
            data = [('m2',1,'M7'),('M2',2,'m7'),('m3',3,'M6'),('M3',4,'m6'),('P4',5,'P5'),('P5',7,'P4'),('m6',8,'M3'),('M6',9,'m3'),('m7',10,'M2'),('M7',11,'m2')]
            q_int, semis, inv_int = random.choice(data)
            if sub == 'Alternative':
                idx = (get_pitch_index(root)+semis)%12; return f"What's the alternative to {root}{q_int}?", get_valid_answers(idx, inv_int), 'single'
            elif sub == 'Tracking':
                idx = (get_pitch_index(root)+semis)%12; return f"What is the pitch {q_int} up from {root}?", get_enharmonic_names(idx), 'single'
        elif cat == 'Chord Forms':
            root = random.choice(NOTES); ridx = get_pitch_index(root)
            if sub == 'Relationships':
                q_type = random.randint(1, 4)
                if q_type == 1: return f"How do you change {root}m7 into a 6th chord?", get_valid_answers(ridx + 3, "6"), 'single'
                elif q_type == 2: return f"How do you change {root}m7b5 into a m6 chord and 6#11 chord? (Separate by comma)", [get_valid_answers(ridx + 3, "m6"), get_valid_answers(ridx + 6, "6#11")], 'multi'
                elif q_type == 3: return (f"How do you change {root}m6 into a m7b5 chord?", get_valid_answers(ridx - 3, "m7b5"), 'single') if random.choice([True,False]) else (f"How do you change {root}6 into a m7 chord?", get_valid_answers(ridx - 3, "m7"), 'single')
                elif q_type == 4: return f"How do you change {root}6#11 into a m7b5 chord?", get_valid_answers(ridx + 6, "m7b5"), 'single'
            elif sub == 'Extract (Degree)':
                d_name, d_val = random.choice(list(DEGREE_MAP.items()))
                target = (d_val + 4) % 12; ans = [f"{k}m7b5" for k, v in DEGREE_MAP.items() if v == target]
                return f"Which m7b5 chord can be extracted from {d_name}7(9)?", ans, 'single'
            elif sub == 'Extract (Pitch)':
                return f"Which m7b5 chord can be extracted from {root}7?", get_valid_answers((ridx + 4) % 12, "m7b5"), 'single'
            elif sub == '9 chord':
                qt = random.choice(['maj7', '7', 'm7'])
                if qt == 'maj7': return f"How can {root}maj7(9) be expanded? (Separate by comma)", [get_slash_answers(ridx+4, "m7", ridx), get_slash_answers(ridx+7, "6", ridx)], 'multi'
                elif qt == '7': return f"How can {root}7(9) be expanded? (Separate by comma)", [get_slash_answers(ridx+4, "m7b5", ridx), get_slash_answers(ridx+10, "6#11", ridx)], 'multi'
                else: return f"How can {root}m7(9) be expanded?", get_slash_answers(ridx+3, "maj7", ridx), 'single'
            elif sub == 'Rootless':
                return f"What is the 7sus4 chord for Rootless {root}6(9)?", get_valid_answers(ridx - 3, "7sus4"), 'single'
        elif cat == 'Cycle of 5th':
            p=random.choice(NOTES); idx=get_pitch_index(p)
            if sub == 'P5 down': return f"Pitch P5 down from {p}?", get_enharmonic_names(idx-7), 'single'
            if sub == 'P5 up': return f"Pitch P5 up from {p}?", get_enharmonic_names(idx+7), 'single'
            if sub == 'r calc': k=random.choice(list(R_CALC_MAP.keys())); return f"How many 'r's for {k}?", [str(R_CALC_MAP[k])], 'single'
            if sub == '2-5-1':
                d=random.choice(['bV','I','V']); ans={'I':['II','V'],'bV':['bVI','bII'],'V':['VI','II']}[d]
                return f"What are 2, 5 for {d}?", ans, 'single'
        elif cat == 'Locations':
            k=random.choice(NOTES)
            if sub == 'Deg->Pitch':
                dn, dv = random.choice(list(DEGREE_MAP.items())); idx=(get_pitch_index(k)+dv)%12
                return f"What pitch is {dn} of {k}?", get_enharmonic_names(idx), 'single'
            if sub == 'Pitch->Deg':
                t=random.choice(NOTES); diff=(get_pitch_index(t)-get_pitch_index(k))%12
                return f"What degree is {t} of {k} scale?", [key for key,v in DEGREE_MAP.items() if v==diff], 'single'
        elif cat == 'Tritones':
            p=random.choice(NOTES); pidx=get_pitch_index(p)
            if sub == 'Pitch': return f"What is the tritone of {p}?", get_enharmonic_names(pidx+6), 'single'
            if sub == 'Degree':
                dn, dv = random.choice(list(DEGREE_MAP.items()))
                return f"What is the tritone of {dn}?", [k for k,v in DEGREE_MAP.items() if v==(dv+6)%12], 'single'
            if sub == 'Dom7':
                p1=p; p2=get_pitch_from_index(pidx+6); r1=(pidx-4)%12; r2=(pidx+2)%12 
                return f"What Dom7 from ({p1}, {p2})? (Separate by comma)", [get_valid_answers(r1,'7'), get_valid_answers(r2,'7')], 'multi'
            if sub == 'Dim7':
                g1=[f"{r}, {t}" for r in get_enharmonic_names(pidx) for t in get_enharmonic_names(pidx+6)]
                g2=[f"{r}, {t}" for r in get_enharmonic_names(pidx+3) for t in get_enharmonic_names(pidx+9)]
                return f"Tritones from {p}dim7? (Separate pairs)", [g1, g2], 'multi'
        elif cat == 'Modes':
            m = random.choice(list(SCALES_DATA.keys())[:7])
            if sub == 'Alterations':
                if m=='Ionian': return generate_question(cat, sub)
                return f"Alterations in {m}?", MODE_ALTERATIONS.get(m,[]), 'all'
            if sub == 'Tensions': return f"Tensions of {m}?", MODE_TENSIONS.get(m,[]), 'all'
            if sub == 'Chords(Deg)':
                idx=random.randint(0,6); ords=['Ist','IInd','IIIrd','IVth','Vth','VIth','VIIth']
                quals=['maj7','m7','m7','maj7','7','m7','m7b5']; shift=list(SCALES_DATA.keys()).index(m)
                return f"What is {ords[idx]} chord in {m}?", [f"{SCALES_DATA[m][idx]}{quals[(idx+shift)%7]}"], 'single'
            if sub == 'Chords(Key)':
                k=random.choice(NOTES); idx=random.randint(0,6); ords=['Ist','IInd','IIIrd','IVth','Vth','VIth','VIIth']
                quals=['maj7','m7','m7','maj7','7','m7','m7b5']; shift=list(SCALES_DATA.keys()).index(m)
                d_val = DEGREE_MAP[SCALES_DATA[m][idx]]; tidx=(get_pitch_index(k)+d_val)%12
                return f"{ords[idx]} chord in {k} {m}?", get_valid_answers(tidx, quals[(idx+shift)%7]), 'single'
        elif cat == 'Minor':
            mt = random.choice(list(MINOR_DATA.keys())); idx=random.randint(0,2)
            d = MINOR_DATA[mt]['degrees'][idx]; q = MINOR_DATA[mt]['chords'][idx]
            if sub == 'Chords': return f"{d} chord in {mt} scale?", [f"{d}{q}"], 'single'
            if sub == 'Tensions': return f"Tensions of {d}{q} in {mt}?", MINOR_DATA[mt]['tens'][idx], 'all'
            if sub == 'Pitch':
                k=random.choice(NOTES); tidx=(get_pitch_index(k)+DEGREE_MAP[d])%12
                return f"{d} chord in {k} {mt}?", get_valid_answers(tidx, q), 'single'
        elif cat == 'Mastery':
            if sub == 'Functions':
                f=random.choice(list(CHORD_FUNCTIONS.keys())); c=random.choice(CHORD_FUNCTIONS[f])
                return f"Function of {c}?", DUAL_FUNCTION_CHORDS.get(c, [f]), 'all' if c in DUAL_FUNCTION_CHORDS else 'single'
            if sub == 'Degrees':
                s=random.choice(list(SCALES_DATA.keys())); return f"Degrees of {s}?", SCALES_DATA[s], 'all'
            if sub == 'Pitches':
                s=random.choice(list(SCALES_DATA.keys())); k=random.choice(NOTES); kidx=get_pitch_index(k)
                ans = [get_pitch_from_index(kidx+DEGREE_MAP.get(d,0)) for d in SCALES_DATA[s]]
                return f"Pitches of {k} {s}?", ans, 'all_indices'
            if sub == 'Avail Scales':
                s=random.choice(list(AVAILABLE_SCALES_MAP.keys())); c=random.choice(AVAILABLE_SCALES_MAP[s])
                return f"Which scale uses {c}?", [s], 'single'
            if sub == 'Pivot':
                ct=random.choice(['maj7','7','m7','m7b5']); sdn=random.choice(list(DEGREE_MAP.keys())); sdv=DEGREE_MAP[sdn]
                offsets={'maj7':[0,7],'m7':[10,8,3,0,5,7],'7':[5,10],'m7b5':[11,2,6]}[ct]
                ans = [k for k,v in DEGREE_MAP.items() if v in [(sdv+o)%12 for o in offsets]]
                return f"Keys having {sdn}{ct} as pivot?", ans, 'all'
            if sub == 'Similarities':
                sm=random.choice(list(MODE_OFFSET_MAP.keys())); tm=random.choice(list(MODE_OFFSET_MAP.keys()))
                sp=random.choice(NOTES); diff = MODE_OFFSET_MAP[tm] - MODE_OFFSET_MAP[sm]
                tidx = (get_pitch_index(sp)+diff)%12
                return f"Which {tm} shares tones with {sp} {sm}?", [f"{p} {tm}" for p in get_enharmonic_names(tidx)], 'single'
    except Exception as e: return f"Error: {e}", [], 'single'
    return None, [], 'single'

# ==========================================
# 4. APP UI
# ==========================================
st.set_page_config(page_title="Road to Berklee", page_icon="🎹")
cookie_manager = stx.CookieManager()

if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user_input_buffer' not in st.session_state: st.session_state.user_input_buffer = ""
if 'edit_mode' not in st.session_state: st.session_state.edit_mode = False

if st.session_state.logged_in_user is None:
    user_cookie = cookie_manager.get(cookie="berklee_user")
    if user_cookie:
        if st.session_state.stat_mgr.auto_login(user_cookie):
            st.session_state.logged_in_user = user_cookie
            st.session_state.page = 'home'
            time.sleep(0.5)
            st.rerun()

# --- LOGIN / SIGNUP ---
if not st.session_state.logged_in_user:
    st.title("🎹 Road to Berklee")
    st.subheader("Login / Sign Up")
    if not st.session_state.stat_mgr.connected: st.error("❌ Database Not Connected.")
    else:
        tab1, tab2 = st.tabs(["Login", "Create Account"])
        with tab1:
            with st.form("login_form"):
                user = st.text_input("Username")
                pwd = st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    if st.session_state.stat_mgr.login_user(user, pwd):
                        st.session_state.logged_in_user = user
                        st.session_state.page = 'home'
                        cookie_manager.set("berklee_user", user, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                        st.success(f"Welcome, {user}!"); time.sleep(1); st.rerun()
                    else: st.error("Invalid Username or Password.")
        with tab2:
            with st.form("signup_form"):
                new_user = st.text_input("New Username")
                new_pwd = st.text_input("New Password", type="password")
                if st.form_submit_button("Create Account"):
                    success, msg = st.session_state.stat_mgr.create_user(new_user, new_pwd)
                    if success: st.success(msg)
                    else: st.error(msg)
    st.stop()

# --- MAIN MENU ---
with st.sidebar:
    st.write(f"👤 **{st.session_state.logged_in_user}**")
    
    if st.session_state.logged_in_user == '오승열':
        st.caption("👑 Owner Mode Active")

    if st.button("Logout"):
        st.session_state.logged_in_user = None
        st.session_state.page = 'login'
        cookie_manager.delete("berklee_user") 
        st.rerun()
    st.markdown("---")
    menu = st.radio("Menu", ["🏠 Home", "📝 Start Quiz", "📊 Statistics", "🏆 Leaderboard", "📚 Theory", "ℹ️ Credits"])

# --- PAGE ROUTING ---
if 'quiz_state' not in st.session_state:
    st.session_state.quiz_state = {
        'active': False, 'cat': '', 'sub': '', 'mode': '', 
        'q_list': [], 'current_idx': 0, 'score': 0, 'start_time': 0,
        'wrong_list': [], 'answers': [], 'limit': 0, 'feedback': None
    }

def start_quiz(cat, sub, mode, limit=0):
    st.session_state.quiz_state = {
        'active': True, 'cat': cat, 'sub': sub, 'mode': mode,
        'current_idx': 0, 'score': 0, 'start_time': time.time(),
        'wrong_list': [], 'answers': [], 'limit': limit,
        'current_q': generate_question(cat, sub),
        'feedback': None
    }
    st.session_state.user_input_buffer = "" 
    st.session_state.page = 'quiz'
    st.rerun()

def check_answer(user_input):
    qs = st.session_state.quiz_state
    q_text, ans_list, mode = qs['current_q']
    
    user_set = normalize_input(user_input)
    expected_set = set([str(a).lower().strip() for a in ans_list])
    is_correct = False
    
    if mode == 'single':
        if user_set and user_set.issubset(expected_set): is_correct = True
    elif mode == 'multi':
        matched = 0
        for group in ans_list:
            g_set = set([str(g).lower().strip() for g in group])
            if not user_set.isdisjoint(g_set): matched += 1
        if matched == len(ans_list): is_correct = True
    elif mode == 'all':
        if user_set == expected_set: is_correct = True
    elif mode == 'all_indices':
        u_idxs = {get_pitch_index(u) for u in user_set if get_pitch_index(u)!=-1}
        e_idxs = {get_pitch_index(a) for a in ans_list}
        if u_idxs and u_idxs == e_idxs: is_correct = True
        
    if qs['mode'] == 'practice':
        qs['feedback'] = {'is_correct': is_correct, 'user_input': user_input, 'answers': ans_list, 'mode': mode}
        st.session_state.stat_mgr.record(qs['cat'], qs['sub'], is_correct, is_retry=False)
        st.rerun()
    else:
        qs['answers'].append({'q': q_text, 'u': user_input, 'a': ans_list, 'c': is_correct, 'm': mode})
        if is_correct: qs['score'] += 1
        else: qs['wrong_list'].append((q_text, ans_list, mode))
        st.session_state.stat_mgr.record(qs['cat'], qs['sub'], is_correct, is_retry=False)
        next_question()

def next_question():
    qs = st.session_state.quiz_state
    qs['current_idx'] += 1
    qs['feedback'] = None
    st.session_state.user_input_buffer = "" 
    is_finished = False
    if qs['mode'] == 'speed':
        if time.time() - qs['start_time'] >= qs['limit']: is_finished = True
    else:
        if qs['current_idx'] >= qs['limit']: is_finished = True
    if is_finished: finish_quiz()
    else:
        qs['current_q'] = generate_question(qs['cat'], qs['sub'])
        st.rerun()

def finish_quiz():
    qs = st.session_state.quiz_state
    elapsed = time.time() - qs['start_time']
    if qs['mode'] == 'test':
        st.session_state.stat_mgr.update_leaderboard('test', qs['cat'], qs['sub'], {'score': qs['score'], 'total': qs['limit'], 'time': elapsed})
    elif qs['mode'] == 'speed':
        st.session_state.stat_mgr.update_leaderboard('speed', qs['cat'], qs['sub'], {'correct': qs['score'], 'total_try': qs['current_idx']})
    st.session_state.page = 'result'
    st.rerun()

# 1. REAL HOME PAGE
if menu == "🏠 Home":
    col1, col2 = st.columns([1, 2])
    with col1:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=200)
        else:
            st.markdown(
                """
                <div style="background-color: white; padding: 10px; border-radius: 10px; width: fit-content;">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/Berklee_College_of_Music_Logo.png/800px-Berklee_College_of_Music_Logo.png" width="150">
                </div>
                """, 
                unsafe_allow_html=True
            )
    
    st.markdown("""
    <div style='text-align: left;'>
        <h1>Road to Berklee</h1>
        <h3>Music Theory practicing application</h3>
        <br>
        <p>Master your intervals, chords, scales, and more.</p>
    </div>
    """, unsafe_allow_html=True)

# 2. QUIZ SELECTION
elif menu == "📝 Start Quiz":
    if st.session_state.page == 'quiz':
        qs = st.session_state.quiz_state
        if qs['mode'] == 'speed':
            rem = qs['limit'] - (time.time() - qs['start_time'])
            if rem <= 0: finish_quiz()
            st.progress(max(0.0, min(1.0, rem / qs['limit']))); st.caption(f"{int(rem)}s")
        else: st.progress(qs['current_idx'] / qs['limit']); st.caption(f"Q {qs['current_idx']+1}")

        st.subheader(qs['current_q'][0])

        if qs.get('feedback'):
            fb = qs['feedback']
            if fb['is_correct']: st.success(f"Correct! ({fb['user_input']})")
            else:
                ans = fb['answers']; d = ', '.join(list(ans)[:3]) if fb['mode']!='multi' else ', '.join([g[0] for g in ans])
                st.error(f"Wrong! ({fb['user_input']})"); st.info(f"Answer: {d}")
            if st.button("Next Question", type="primary"): next_question()
        else:
            st.text_input("Answer Input (Use buttons below)", value=st.session_state.user_input_buffer, disabled=True, key="display_buffer")
            submitted = render_keypad(qs['cat'], qs['sub'])
            c1, c2 = st.columns(2)
            with c1:
                if st.button("⏩ Skip"): check_answer("skip")
            with c2:
                if st.button("🏠 Quit"): st.session_state.page = 'home'; st.rerun()
            if submitted: check_answer(st.session_state.user_input_buffer)

    elif st.session_state.page == 'result':
        qs = st.session_state.quiz_state
        st.header("Result")
        elapsed = time.time() - qs['start_time']; m, s = divmod(int(elapsed), 60)
        st.write(f"Time: {m:02d}:{s:02d}")
        sc = qs['score']; tot = len(qs['answers']) if qs['mode']!='speed' else qs['current_idx']
        st.metric("Score", f"{sc}/{tot}", f"{(sc/tot*100) if tot>0 else 0:.1f}%")
        st.subheader("Review")
        for r in qs['answers']:
            c = "green" if r['c'] else "red"; i = "✅" if r['c'] else "❌"
            with st.expander(f"{i} {r['q']}"):
                st.write(f"Your: {r['u']}"); st.write(f"Ans: {r['a']}")
        if st.button("Home"): st.session_state.page = 'home'; st.rerun()

    else:
        st.header("📝 Select Category") 
        cat_names = list(CATEGORY_INFO.keys())
        sel_cat = st.selectbox("Category", cat_names)
        if sel_cat:
            sel_sub = st.selectbox("Subcategory", CATEGORY_INFO[sel_cat])
            st.subheader("Quiz Mode")
            m1, m2, m3 = st.tabs(["Practice", "Test (20Q)", "Speed Run (60s)"])
            with m1:
                cnt = st.number_input("Count", 5)
                if st.button("Start Practice"): start_quiz(sel_cat, sel_sub, 'practice', cnt)
            with m2:
                st.write("20 Questions, No Feedback.")
                if st.button("Start Test"): start_quiz(sel_cat, sel_sub, 'test', 20)
            with m3:
                st.write("60 Seconds.")
                if st.button("Start Speed Run"): start_quiz(sel_cat, sel_sub, 'speed', 60)

elif menu == "📊 Statistics":
    st.header("📊 Statistics") 
    t1, t2 = st.tabs(["Cumulative", "Trend"])
    with t1:
        solved, rate = st.session_state.stat_mgr.calculate_stats(st.session_state.stat_mgr.data)
        st.metric("Solved", solved); st.metric("Accuracy", f"{rate:.1f}%")
        bd = st.session_state.stat_mgr.get_breakdown(st.session_state.stat_mgr.data)
        for c in sorted(bd.keys()):
            with st.expander(f"{c} ({bd[c]['correct']}/{bd[c]['total']})"):
                for s in bd[c]['subs']:
                    sd = bd[c]['subs'][s]
                    st.write(f"- {s}: {(sd['correct']/sd['total']*100 if sd['total']>0 else 0):.1f}%")
    with t2:
        st.subheader("Trend")
        t_cat = st.selectbox("Category", ["All"] + list(CATEGORY_INFO.keys()))
        t_sub = None
        if t_cat != "All": t_sub = st.selectbox("Sub", ["All"] + CATEGORY_INFO[t_cat])
        if t_sub == "All": t_sub = None
        if st.button("Analyze"):
            d = st.session_state.stat_mgr.get_trend_data(t_cat, t_sub, "weekly") 
            if d: st.line_chart({x[0]: x[1] for x in d})
            else: st.warning("No Data")

elif menu == "🏆 Leaderboard":
    st.header("🏆 Hall of Fame") 
    l_cat = st.selectbox("Category", list(CATEGORY_INFO.keys()))
    l_sub = st.selectbox("Subcategory", CATEGORY_INFO[l_cat])
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Test")
        d = st.session_state.stat_mgr.leaderboard.get(l_cat, {}).get(l_sub, {}).get('test', [])
        for i, r in enumerate(d):
            m,s = divmod(int(r['time']),60)
            st.write(f"**{i+1}. {r.get('username','?')}**: {r['score']}/{r['total']} ({m:02d}:{s:02d})")
    with c2:
        st.subheader("Speed")
        d = st.session_state.stat_mgr.leaderboard.get(l_cat, {}).get(l_sub, {}).get('speed', [])
        for i, r in enumerate(d): st.write(f"**{i+1}. {r.get('username','?')}**: {r['solved']} ({r['rate']:.1f}%)")

elif menu == "📚 Theory":
    st.header("📚 Music Theory") 
    
    col1, col2 = st.columns([8, 2])
    t_cat = col1.selectbox("Category", list(CATEGORY_INFO.keys()))
    t_sub = col1.selectbox("Subcategory", CATEGORY_INFO[t_cat])
    
    if st.session_state.logged_in_user == '오승열':
        if not st.session_state.edit_mode:
            if col2.button("✏️ Edit"):
                st.session_state.edit_mode = True
                st.rerun()

    st.markdown("---")
    current_content = st.session_state.stat_mgr.get_theory(t_cat, t_sub)
    
    if st.session_state.edit_mode and st.session_state.logged_in_user == '오승열':
        st.warning("🛠️ Editing Mode")
        new_content = st.text_area("Markdown Content", value=current_content, height=400)
        
        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            if st.button("💾 Save"):
                if st.session_state.stat_mgr.save_theory(t_cat, t_sub, new_content):
                    st.success("Saved!")
                    st.session_state.edit_mode = False
                    time.sleep(0.5)
                    st.rerun()
                else: st.error("Error saving.")
        with c2:
            if st.button("🔄 Reset"):
                default_text = THEORY_DATA.get(t_cat, {}).get(t_sub, DEFAULT_THEORY)
                if st.session_state.stat_mgr.save_theory(t_cat, t_sub, default_text):
                    st.success("Reset to Default (English)!")
                    st.session_state.edit_mode = False
                    time.sleep(0.5)
                    st.rerun()
        with c3:
            if st.button("❌ Cancel"):
                st.session_state.edit_mode = False
                st.rerun()
    else:
        st.markdown(current_content, unsafe_allow_html=True)

elif menu == "ℹ️ Credits":
    st.header("ℹ️ Credits")
    st.write("Created by: Oh Seung-yeol")
