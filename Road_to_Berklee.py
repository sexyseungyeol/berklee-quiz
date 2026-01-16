import streamlit as st
import random
import time
import datetime
from datetime import timedelta
import hashlib
import gspread
import os

# Cookie Manager Exception Handling
try:
    import extra_streamlit_components as stx
except ImportError:
    st.error("⚠️ 'extra-streamlit-components' is missing. Please update requirements.txt")
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
    
    def record(self, category, subcategory, is_correct, is_retry=False):
        if not self.current_user or not self.connected or is_retry: return
        now = datetime.datetime.now()
        row = [self.current_user, now.timestamp(), now.year, now.month, now.day, category, subcategory, 1 if is_correct else 0, 1]
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

# [CALLBACKS]
def add_input(k): st.session_state.user_input_buffer += k
def del_input(): st.session_state.user_input_buffer = st.session_state.user_input_buffer[:-1]
def clear_input(): st.session_state.user_input_buffer = ""

def get_keypad_keys(cat, sub):
    if (cat == 'Enharmonics' and sub == 'Degrees') or \
       (cat == 'Warming up' and sub == 'Finding degrees') or \
       (cat == 'Locations' and sub == 'Pitch->Deg') or \
       (cat == 'Modes' and sub == 'Alterations') or \
       (cat == 'Mastery' and sub == 'Degrees'):
       return [['♭', '♯'], ['I','II','III'], ['IV','V','VI','VII']]
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

def render_keypad(cat, sub):
    key_rows = get_keypad_keys(cat, sub)
    st.markdown("""
        <style>
        div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] .stButton > button {
            width: 100% !important; height: 70px !important; font-size: 24px !important;
            font-weight: bold !important; border-radius: 12px !important; margin-bottom: 8px !important;
        }
        section[data-testid="stSidebar"] .stButton > button { height: auto !important; width: auto !important; font-size: inherit !important; }
        div[data-testid="column"] { padding: 2px !important; }
        </style>
    """, unsafe_allow_html=True)
    for row in key_rows:
        cols = st.columns(len(row))
        for i, key in enumerate(row):
            cols[i].button(key, key=f"k_{key}", on_click=add_input, args=(key,), use_container_width=True)
        if '♭' in row and '♯' in row: st.write("")
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 2])
    c1.button("⬅️ Del", on_click=del_input)
    c2.button("❌ Clear", on_click=clear_input)
    if c3.button("✅ Submit", type="primary", use_container_width=True): return True
    return False

def generate_question(cat, sub):
    try:
        if cat == 'Enharmonics':
            if sub == 'Degrees':
                t, a = random.choice([('#VII','I'),('#I','bII'),('#II','bIII'),('bIV','III'),('IV','#III'),('#V','bVI'),('#VI','bVII')])
                return f"What is {t}'s enharmonic?", [a], 'single'
            elif sub == 'Number':
                sets = [['1','8','bb2'],['#1','b2','#8','b9'],['2','9','bb3'],['#2','b3','#9','b10'],['3','10','b4'],['4','11','#3'],['#4','b5','#11','b12'],['5','12','bb6'],['#5','b6','#12','b13'],['6','13','bb7'],['#6','b7','#13','b14'],['7','14','b8','b1']]
                c = random.choice(sets); t = random.choice(c); return f"What are {t}'s enharmonics?", [x for x in c if x!=t], 'single'
            elif sub == 'Natural Form':
                k = random.choice(list(NATURAL_INTERVAL_DATA.keys())); q = random.choice(NATURAL_INTERVAL_DATA[k])
                return f"What is {q}'s natural form?", [k], 'single'
        elif cat == 'Warming up':
            if sub == 'Counting semitones': d = random.randint(1,12); return f"Which degree is {d} semitones away?", DISTANCE_TO_DEGREE[d], 'single'
            elif sub == 'Finding degrees':
                dn, dv = random.choice(list(DEGREE_MAP.items())); p = random.choice(NOTES)
                return f"What is {dn} of {p} Key?", get_enharmonic_names((get_pitch_index(p)+dv)%12), 'single'
            elif sub == 'Chord tones':
                p, ct = random.choice(NOTES), random.choice(list(CHORD_FORMULAS.keys())); idx = get_pitch_index(p); ans = [get_pitch_from_index((idx+interval)%12) for interval in CHORD_FORMULAS[ct]]
                return f"What are the Chord tones of {p}{ct}?", ans, 'all_indices'
            elif sub == 'Key signatures':
                is_maj = random.choice([True,False]); k,v = random.choice(list(KEY_SIGS_MAJOR.items() if is_maj else KEY_SIGS_MINOR.items()))
                return f"What {'major' if is_maj else 'minor'} key has ({v if v else 'none'})?", [k], 'single'
            elif sub == 'Solfege': k,v = random.choice(list(SOLFEGE.items())); return f"What is {k}'s solfege?", [v], 'single'
        elif cat == 'Intervals':
            root = random.choice(NOTES); data = [('m2',1,'M7'),('M2',2,'m7'),('m3',3,'M6'),('M3',4,'m6'),('P4',5,'P5'),('P5',7,'P4'),('m6',8,'M3'),('M6',9,'m3'),('m7',10,'M2'),('M7',11,'m2')]; q_int, semis, inv_int = random.choice(data)
            if sub == 'Alternative': idx = (get_pitch_index(root)+semis)%12; return f"What's the alternative to {root}{q_int}?", get_valid_answers(idx, inv_int), 'single'
            elif sub == 'Tracking': idx = (get_pitch_index(root)+semis)%12; return f"What is the pitch {q_int} up from {root}?", get_enharmonic_names(idx), 'single'
        elif cat == 'Chord Forms':
            root = random.choice(NOTES); ridx = get_pitch_index(root)
            if sub == 'Relationships':
                q_type = random.randint(1, 4)
                if q_type == 1: return f"How do you change {root}m7 into a 6th chord?", get_valid_answers(ridx + 3, "6"), 'single'
                elif q_type == 2: return f"How do you change {root}m7b5 into a m6 chord and 6#11 chord? (Separate by comma)", [get_valid_answers(ridx + 3, "m6"), get_valid_answers(ridx + 6, "6#11")], 'multi'
                elif q_type == 3: return (f"How do you change {root}m6 into a m7b5 chord?", get_valid_answers(ridx - 3, "m7b5"), 'single') if random.choice([True,False]) else (f"How do you change {root}6 into a m7 chord?", get_valid_answers(ridx - 3, "m7"), 'single')
                elif q_type == 4: return f"How do you change {root}6#11 into a m7b5 chord?", get_valid_answers(ridx + 6, "m7b5"), 'single'
            elif sub == 'Extract (Degree)': d_name, d_val = random.choice(list(DEGREE_MAP.items())); target = (d_val + 4) % 12; ans = [f"{k}m7b5" for k, v in DEGREE_MAP.items() if v == target]; return f"Which m7b5 chord can be extracted from {d_name}7(9)?", ans, 'single'
            elif sub == 'Extract (Pitch)': return f"Which m7b5 chord can be extracted from {root}7?", get_valid_answers((ridx + 4) % 12, "m7b5"), 'single'
            elif sub == '9 chord':
                qt = random.choice(['maj7', '7', 'm7'])
                if qt == 'maj7': return f"How can {root}maj7(9) be expanded? (Separate by comma)", [get_slash_answers(ridx+4, "m7", ridx), get_slash_answers(ridx+7, "6", ridx)], 'multi'
                elif qt == '7': return f"How can {root}7(9) be expanded? (Separate by comma)", [get_slash_answers(ridx+4, "m7b5", ridx), get_slash_answers(ridx+10, "6#11", ridx)], 'multi'
                else: return f"How can {root}m7(9) be expanded?", get_slash_answers(ridx+3, "maj7", ridx), 'single'
            elif sub == 'Rootless': return f"What is the 7sus4 chord for Rootless {root}6(9)?", get_valid_answers(ridx - 3, "7sus4"), 'single'
        elif cat == 'Cycle of 5th':
            p=random.choice(NOTES); idx=get_pitch_index(p)
            if sub == 'P5 down': return f"Pitch P5 down from {p}?", get_enharmonic_names(idx-7), 'single'
            if sub == 'P5 up': return f"Pitch P5 up from {p}?", get_enharmonic_names(idx+7), 'single'
            if sub == 'r calc': k=random.choice(list(R_CALC_MAP.keys())); return f"How many 'r's for {k}?", [str(R_CALC_MAP[k])], 'single'
            if sub == '2-5-1': d=random.choice(['bV','I','V']); ans={'I':['II','V'],'bV':['bVI','bII'],'V':['VI','II']}[d]; return f"What are 2, 5 for {d}?", ans, 'single'
        elif cat == 'Locations':
            k=random.choice(NOTES)
            if sub == 'Deg->Pitch': dn, dv = random.choice(list(DEGREE_MAP.items())); idx=(get_pitch_index(k)+dv)%12; return f"What pitch is {dn} of {k}?", get_enharmonic_names(idx), 'single'
            if sub == 'Pitch->Deg': t=random.choice(NOTES); diff=(get_pitch_index(t)-get_pitch_index(k))%12; return f"What degree is {t} of {k} scale?", [key for key,v in DEGREE_MAP.items() if v==diff], 'single'
        elif cat == 'Tritones':
            p=random.choice(NOTES); pidx=get_pitch_index(p)
            if sub == 'Pitch': return f"What is the tritone of {p}?", get_enharmonic_names(pidx+6), 'single'
            if sub == 'Degree': dn, dv = random.choice(list(DEGREE_MAP.items())); return f"What is the tritone of {dn}?", [k for k,v in DEGREE_MAP.items() if v==(dv+6)%12], 'single'
            if sub == 'Dom7': p1=p; p2=get_pitch_from_index(pidx+6); r1=(pidx-4)%12; r2=(pidx+2)%12; return f"What Dom7 from ({p1}, {p2})? (Separate by comma)", [get_valid_answers(r1,'7'), get_valid_answers(r2,'7')], 'multi'
            if sub == 'Dim7': g1=[f"{r}, {t}" for r in get_enharmonic_names(pidx) for t in get_enharmonic_names(pidx+6)]; g2=[f"{r}, {t}" for r in get_enharmonic_names(pidx+3) for t in get_enharmonic_names(pidx+9)]; return f"Tritones from {p}dim7? (Separate pairs)", [g1, g2], 'multi'
        elif cat == 'Modes':
            m = random.choice(list(SCALES_DATA.keys())[:7])
            if sub == 'Alterations': return f"Alterations in {m}?", MODE_ALTERATIONS.get(m,[]), 'all'
            if sub == 'Tensions': return f"Tensions of {m}?", MODE_TENSIONS.get(m,[]), 'all'
            if sub == 'Chords(Deg)': idx=random.randint(0,6); ords=['Ist','IInd','IIIrd','IVth','Vth','VIth','VIIth']; quals=['maj7','m7','m7','maj7','7','m7','m7b5']; shift=list(SCALES_DATA.keys()).index(m); return f"What is {ords[idx]} chord in {m}?", [f"{SCALES_DATA[m][idx]}{quals[(idx+shift)%7]}"], 'single'
            if sub == 'Chords(Key)': k=random.choice(NOTES); idx=random.randint(0,6); ords=['Ist','IInd','IIIrd','IVth','Vth','VIth','VIIth']; quals=['maj7','m7','m7','maj7','7','m7','m7b5']; shift=list(SCALES_DATA.keys()).index(m); d_val = DEGREE_MAP[SCALES_DATA[m][idx]]; tidx=(get_pitch_index(k)+d_val)%12; return f"{ords[idx]} chord in {k} {m}?", get_valid_answers(tidx, quals[(idx+shift)%7]), 'single'
        elif cat == 'Minor':
            mt = random.choice(list(MINOR_DATA.keys())); idx=random.randint(0,2); d = MINOR_DATA[mt]['degrees'][idx]; q = MINOR_DATA[mt]['chords'][idx]
            if sub == 'Chords': return f"{d} chord in {mt} scale?", [f"{d}{q}"], 'single'
            if sub == 'Tensions': return f"Tensions of {d}{q} in {mt}?", MINOR_DATA[mt]['tens'][idx], 'all'
            if sub == 'Pitch': k=random.choice(NOTES); tidx=(get_pitch_index(k)+DEGREE_MAP[d])%12; return f"{d} chord in {k} {mt}?", get_valid_answers(tidx, q), 'single'
        elif cat == 'Mastery':
            if sub == 'Functions': f=random.choice(list(CHORD_FUNCTIONS.keys())); c=random.choice(CHORD_FUNCTIONS[f]); return f"Function of {c}?", DUAL_FUNCTION_CHORDS.get(c, [f]), 'all' if c in DUAL_FUNCTION_CHORDS else 'single'
            if sub == 'Degrees': s=random.choice(list(SCALES_DATA.keys())); return f"Degrees of {s}?", SCALES_DATA[s], 'all'
            if sub == 'Pitches': s=random.choice(list(SCALES_DATA.keys())); k=random.choice(NOTES); kidx=get_pitch_index(k); ans = [get_pitch_from_index(kidx+DEGREE_MAP.get(d,0)) for d in SCALES_DATA[s]]; return f"Pitches of {k} {s}?", ans, 'all_indices'
            if sub == 'Avail Scales': s=random.choice(list(AVAILABLE_SCALES_MAP.keys())); c=random.choice(AVAILABLE_SCALES_MAP[s]); return f"Which scale uses {c}?", [s], 'single'
            if sub == 'Pivot': ct=random.choice(['maj7','7','m7','m7b5']); sdn=random.choice(list(DEGREE_MAP.keys())); sdv=DEGREE_MAP[sdn]; offsets={'maj7':[0,7],'m7':[10,8,3,0,5,7],'7':[5,10],'m7b5':[11,2,6]}[ct]; ans = [k for k,v in DEGREE_MAP.items() if v in [(sdv+o)%12 for o in offsets]]; return f"Keys having {sdn}{ct} as pivot?", ans, 'all'
            if sub == 'Similarities': sm=random.choice(list(MODE_OFFSET_MAP.keys())); tm=random.choice(list(MODE_OFFSET_MAP.keys())); sp=random.choice(NOTES); diff = MODE_OFFSET_MAP[tm] - MODE_OFFSET_MAP[sm]; tidx = (get_pitch_index(sp)+diff)%12; return f"Which {tm} shares tones with {sp} {sm}?", [f"{p} {tm}" for p in get_enharmonic_names(tidx)], 'single'
        return "Not Implemented", [], 'single'
    except: return "Error", [], 'single'

# ==========================================
# 4. APP UI
# ==========================================
st.set_page_config(page_title="Road to Berklee", page_icon="🎹")
cookie_manager = stx.CookieManager()

# Init Session States
if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user_input_buffer' not in st.session_state: st.session_state.user_input_buffer = ""
if 'last_result' not in st.session_state: st.session_state.last_result = None
if 'wrong_count' not in st.session_state: st.session_state.wrong_count = 0
if 'wrong_questions_pool' not in st.session_state: st.session_state.wrong_questions_pool = []

if st.session_state.logged_in_user is None:
    user_cookie = cookie_manager.get(cookie="berklee_user")
    if user_cookie and st.session_state.stat_mgr.auto_login(user_cookie):
        st.session_state.logged_in_user = user_cookie; st.session_state.page = 'home'; time.sleep(0.5); st.rerun()

if not st.session_state.logged_in_user:
    st.title("🎹 Road to Berklee")
    tab1, tab2 = st.tabs(["Login", "Create Account"])
    with tab1:
        with st.form("login"):
            u = st.text_input("Username"); p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if st.session_state.stat_mgr.login_user(u, p):
                    st.session_state.logged_in_user = u; st.session_state.page = 'home'
                    cookie_manager.set("berklee_user", u, expires_at=datetime.datetime.now()+timedelta(days=30)); st.rerun()
                else: st.error("Login Failed")
    with tab2:
        with st.form("signup"):
            nu = st.text_input("New Username"); npw = st.text_input("New Password", type="password")
            if st.form_submit_button("Create Account"):
                s, m = st.session_state.stat_mgr.create_user(nu, npw)
                if s: st.success(m)
                else: st.error(m)
    st.stop()

with st.sidebar:
    st.write(f"👤 **{st.session_state.logged_in_user}**")
    if st.session_state.logged_in_user == '오승열': st.caption("👑 Owner Mode Active")
    if st.button("Logout"):
        st.session_state.logged_in_user = None; cookie_manager.delete("berklee_user"); st.rerun()
    st.markdown("---")
    menu = st.radio("Menu", ["🏠 Home", "📝 Start Quiz", "📊 Statistics", "🏆 Leaderboard", "ℹ️ Credits"])

if 'quiz_state' not in st.session_state:
    st.session_state.quiz_state = {'active': False, 'cat': '', 'sub': '', 'mode': '', 'q_list': [], 'current_idx': 0, 'score': 0, 'start_time': 0, 'answers': [], 'limit': 0, 'is_retry': False}

def start_quiz(cat, sub, mode, limit=0, is_retry=False, retry_pool=None):
    st.session_state.quiz_state = {
        'active': True, 'cat': cat, 'sub': sub, 'mode': mode,
        'current_idx': 0, 'score': 0, 'start_time': time.time(),
        'answers': [], 'limit': len(retry_pool) if is_retry else limit,
        'is_retry': is_retry,
        'retry_pool': retry_pool,
        'current_q': retry_pool[0] if is_retry else generate_question(cat, sub)
    }
    st.session_state.wrong_count = 0
    st.session_state.user_input_buffer = ""
    st.session_state.last_result = None
    if not is_retry: st.session_state.wrong_questions_pool = []
    st.session_state.page = 'quiz'; st.rerun()

def check_answer():
    qs = st.session_state.quiz_state
    q_data = qs['current_q']
    q_text, ans_list, mode = q_data
    user_set = normalize_input(st.session_state.user_input_buffer)
    expected_set = set([str(a).lower().strip() for a in ans_list])
    is_correct = False
    
    # Validation
    if mode == 'single': is_correct = user_set.issubset(expected_set) if user_set else False
    elif mode == 'multi':
        matched = sum(1 for group in ans_list if not user_set.isdisjoint(set([str(g).lower().strip() for g in group])))
        is_correct = (matched == len(ans_list))
    elif mode == 'all': is_correct = (user_set == expected_set)
    elif mode == 'all_indices':
        u_idxs = {get_pitch_index(u) for u in user_set if get_pitch_index(u)!=-1}
        e_idxs = {get_pitch_index(a) for a in ans_list}
        is_correct = (u_idxs == e_idxs and len(u_idxs) > 0)

    if is_correct:
        st.session_state.last_result = {'correct': True, 'ans': ans_list}
        if not qs['is_retry']: qs['score'] += 1
        st.session_state.wrong_count = 0
        st.session_state.stat_mgr.record(qs['cat'], qs['sub'], True, qs['is_retry'])
        move_to_next()
    else:
        st.session_state.wrong_count += 1
        if st.session_state.wrong_count >= 3:
            st.session_state.last_result = {'correct': False, 'ans': ans_list, 'show_ans': True}
            if not qs['is_retry']: 
                st.session_state.wrong_questions_pool.append(q_data)
            st.session_state.stat_mgr.record(qs['cat'], qs['sub'], False, qs['is_retry'])
            st.session_state.wrong_count = 0
            move_to_next()
        else:
            st.session_state.last_result = {'correct': False, 'ans': ans_list, 'show_ans': False}
            st.session_state.user_input_buffer = ""
            st.rerun()

def move_to_next():
    qs = st.session_state.quiz_state
    qs['current_idx'] += 1
    qs['answers'].append({'q': qs['current_q'][0], 'c': st.session_state.last_result['correct']})
    
    is_finished = (qs['current_idx'] >= qs['limit'])
    if is_finished:
        st.session_state.page = 'result'
    else:
        qs['current_q'] = qs['retry_pool'][qs['current_idx']] if qs['is_retry'] else generate_question(qs['cat'], qs['sub'])
    st.rerun()

# 1. HOME
if menu == "🏠 Home":
    col1, col2 = st.columns([1, 2])
    with col1:
        if os.path.exists("logo.png"): st.image("logo.png", width=200)
        else: st.markdown("""<div style="background-color: white; padding: 10px; border-radius: 10px; width: fit-content;"><img src="https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/Berklee_College_of_Music_Logo.png/800px-Berklee_College_of_Music_Logo.png" width="150"></div>""", unsafe_allow_html=True)
    st.markdown("<div style='text-align: left;'><h1>Road to Berklee</h1><h3>Music Theory practicing application</h3><br><p>Master your intervals, chords, scales, and more.</p></div>", unsafe_allow_html=True)

# 2. QUIZ
elif menu == "📝 Start Quiz":
    if st.session_state.page == 'quiz':
        if st.session_state.last_result:
            res = st.session_state.last_result
            bg_color = "rgba(0, 255, 0, 0.2)" if res['correct'] else "rgba(255, 0, 0, 0.2)"
            st.markdown(f"""<style>.stApp {{ animation: flash 0.6s forwards; }} @keyframes flash {{ 0% {{ background-color: {bg_color}; }} 100% {{ background-color: transparent; }} }}</style>""", unsafe_allow_html=True)
            if res['correct']: st.toast("✅ Correct!", icon="🎉")
            elif res.get('show_ans'): st.error(f"❌ Answer: {res['ans']}")
            else: st.toast(f"❌ Try Again ({st.session_state.wrong_count}/3)", icon="🤔")
            st.session_state.last_result = None

        qs = st.session_state.quiz_state
        st.progress(qs['current_idx'] / qs['limit'])
        st.write(f"Question {qs['current_idx']+1} / {qs['limit']} {'(Retry Mode)' if qs['is_retry'] else ''}")
        st.subheader(qs['current_q'][0])
        st.text_input("Answer Input", value=st.session_state.user_input_buffer, disabled=True)
        if render_keypad(qs['cat'], qs['sub']): check_answer()
        if st.button("🏠 Quit Quiz"): st.session_state.page = 'home'; st.rerun()

    elif st.session_state.page == 'result':
        qs = st.session_state.quiz_state
        st.header("Quiz Result")
        if not qs['is_retry']:
            st.metric("Score", f"{qs['score']}/{qs['limit']}", f"{qs['score']/qs['limit']*100:.1f}%")
        else:
            st.info("Retry mode: Statistics not updated.")
        
        if st.session_state.wrong_questions_pool:
            st.warning(f"You have {len(st.session_state.wrong_questions_pool)} wrong answers.")
            if st.button("🔄 오답 다시 풀기 (Retry Wrong Answers)"):
                start_quiz(qs['cat'], qs['sub'], qs['mode'], is_retry=True, retry_pool=st.session_state.wrong_questions_pool)
        
        if st.button("🏠 Back Home"): st.session_state.page = 'home'; st.rerun()
    else:
        st.header("📝 Select Category") 
        c = st.selectbox("Category", list(CATEGORY_INFO.keys())); s = st.selectbox("Subcategory", CATEGORY_INFO[c])
        st.subheader("Quiz Mode")
        m1, m2 = st.tabs(["Practice", "Test (20Q)"])
        with m1:
            cnt = st.number_input("Count", 5, 50, 10)
            if st.button("Start Practice"): start_quiz(c, s, 'practice', cnt)
        with m2:
            if st.button("Start Test"): start_quiz(c, s, 'test', 20)

# 3. STATISTICS
elif menu == "📊 Statistics":
    st.header("📊 Statistics") 
    solved, rate = st.session_state.stat_mgr.calculate_stats(st.session_state.stat_mgr.data)
    st.columns(2)[0].metric("Total Solved", solved)
    st.columns(2)[1].metric("Accuracy", f"{rate:.1f}%")

# 4. LEADERBOARD
elif menu == "🏆 Leaderboard":
    st.header("🏆 Hall of Fame"); st.write("Ranking functionality under maintenance.")

# 5. CREDITS
elif menu == "ℹ️ Credits":
    st.header("ℹ️ Credits"); st.write("Created by: Oh Seung-yeol")
