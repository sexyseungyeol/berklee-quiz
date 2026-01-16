import streamlit as st
import random
import time
import json
import os
import datetime
from datetime import timedelta
import hashlib
import gspread

# ==========================================
# 1. 데이터 정의 (Data Definitions)
# ==========================================
NOTES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
NATURAL_INTERVAL_DATA = {'P1': ['-2', '+7', 'P8', '+14'], 'm2': ['+1', 'm9', '+8'], 'M2': ['-3', 'M9', '-10'], 'm3': ['+2', 'm10', '+9'], 'M3': ['-4', 'M10', '-11'], 'P4': ['+3', 'P11', '+10'], 'Tritone': ['+11', '-12'], 'P5': ['-6', 'P12', '-13'], 'm6': ['+5', 'm13', '+12'], 'M6': ['-7', 'M13', '-14'], 'm7': ['+6', 'm14', '+13'], 'M7': ['-8', 'M14']}
DISTANCE_TO_DEGREE = {1:['I'],2:['#I','bII'],3:['II'],4:['#II','bIII'],5:['III'],6:['IV'],7:['#IV','bV'],8:['V'],9:['#V','bVI'],10:['VI'],11:['#VI','bVII'],12:['VII']}
DEGREE_MAP = {'I':0,'bII':1,'#I':1,'II':2,'bIII':3,'#II':3,'III':4,'IV':5,'#III':5,'bV':6,'#IV':6,'V':7,'bVI':8,'#V':8,'VI':9,'bVII':10,'#VI':10,'VII':11}
R_CALC_MAP = {'I':0,'P1':0,'V':1,'P5':1,'II':2,'M2':2,'9':2,'VI':3,'M6':3,'13':3,'III':4,'M3':4,'VII':5,'M7':5,'#IV':6,'bV':6,'#11':6,'bII':7,'#I':7,'b9':7,'bVI':8,'#V':8,'b13':8,'bIII':9,'#II':9,'m3':9,'#9':9,'bVII':10,'m7':10,'IV':11,'P4':11,'11':11}
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
    'Enharmonics': ['Degrees', 'Number', 'Interval'],
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

# --- Theory Data (New Feature) ---
THEORY_DATA = {
    'Enharmonics': {
        'Degrees': "### Enharmonic Degrees\n\n같은 음이지만 이름이 다른 도수(Degree)입니다.\n\n* **#I = bII** (예: C# = Db)\n* **#II = bIII** (예: D# = Eb)\n* **#IV = bV** (예: F# = Gb)\n* **#V = bVI** (예: G# = Ab)\n* **#VI = bVII** (예: A# = Bb)\n* **bIV = III** (예: Fb = E)",
        'Number': "### Enharmonic Numbers\n\n음정 숫자(Interval Number)의 이명동음 관계입니다.\n\n* **Aug 1 (#1) = Minor 2 (b2)**\n* **Aug 2 (#2) = Minor 3 (b3)**\n* **Aug 4 (#4) = Dim 5 (b5)** (Tritone)\n* **Aug 5 (#5) = Minor 6 (b6)**\n* **Dim 7 (bb7) = Major 6 (6)**",
        'Interval': "### Natural Interval Forms\n\n변화표가 없는 기본적인 음정 관계입니다.\n\n* **P1 (완전1도):** 0 semitones\n* **m2 (단2도):** 1 semitone\n* **M2 (장2도):** 2 semitones\n* **m3 (단3도):** 3 semitones\n* **M3 (장3도):** 4 semitones\n* **P4 (완전4도):** 5 semitones\n* **Tritone:** 6 semitones\n* **P5 (완전5도):** 7 semitones"
    },
    'Warming up': {
        'Counting semitones': "### Semitones Distance\n\n기준음(Root)으로부터의 반음 개수입니다.\n\n* **1 (b2):** 1개\n* **2 (2):** 2개\n* **3 (b3):** 3개\n* **4 (3):** 4개\n* **5 (4):** 5개\n* **6 (b5):** 6개\n* **7 (5):** 7개\n* **8 (b6):** 8개\n* **9 (6):** 9개\n* **10 (b7):** 10개\n* **11 (7):** 11개",
        'Chord tones': "### Chord Formulas\n\n코드를 구성하는 도수 공식입니다.\n\n* **Major 7:** 1, 3, 5, 7\n* **Dominant 7:** 1, 3, 5, b7\n* **Minor 7:** 1, b3, 5, b7\n* **m7(b5):** 1, b3, b5, b7\n* **Diminished 7:** 1, b3, b5, bb7 (6)\n* **Augmented:** 1, 3, #5",
        'Key signatures': "### Key Signatures (조표)\n\n**[Sharps #]** 파 - 도 - 솔 - 레 - 라 - 미 - 시\n**[Flats b]** 시 - 미 - 라 - 레 - 솔 - 도 - 파\n\n* **C Major:** 0\n* **G / F:** 1\n* **D / Bb:** 2\n* **A / Eb:** 3\n* **E / Ab:** 4\n* **B / Db:** 5\n* **F# / Gb:** 6",
        'Solfege': "### Fixed Do Solfege\n\n* **I:** Do\n* **II:** Re\n* **III:** Mi\n* **IV:** Fa\n* **V:** Sol\n* **VI:** La\n* **VII:** Ti\n* **bII:** Ra, **bIII:** Me, **bV:** Se..."
    },
    'Modes': {
        'Alterations': "### Mode Character Notes\n\n각 모드를 결정짓는 특징음(Alterations)입니다.\n\n* **Ionian:** -\n* **Dorian:** b3, b7 (Natural Minor에서 6가 제자리)\n* **Phrygian:** b2, b3, b6, b7\n* **Lydian:** #4\n* **Mixolydian:** b7\n* **Aeolian:** b3, b6, b7\n* **Locrian:** b2, b3, b5, b6, b7",
        'Tensions': "### Available Tensions\n\n* **Ionian:** 9, 13 (11 is Avoid)\n* **Dorian:** 9, 11 (13 is Avoid usually)\n* **Phrygian:** 11, b13\n* **Lydian:** 9, #11, 13\n* **Mixolydian:** 9, 13 (11 is Avoid)\n* **Aeolian:** 9, 11\n* **Locrian:** 11, b13"
    },
    'Chord Forms': {
        'Relationships': "### Chord Conversion\n\n* **m7 -> 6:** 7음(b7)을 반음 내림 -> 6\n* **m7 -> m7b5:** 5음(5)을 반음 내림 -> b5\n* **maj7 -> 7:** 7음(7)을 반음 내림 -> b7",
        'Extract (Degree)': "### Chord extraction\n\n어떤 복잡한 코드 안에는 더 단순한 코드가 숨어 있습니다.\n\n예: **Cmaj9** (C E G B D) -> 3음(E)부터 쌓으면 **Em7** (E G B D)가 됩니다.\n이런 식으로 'Upper Structure'를 찾는 연습입니다."
    },
    'Cycle of 5th': {
        'P5 down': "### Circle of Fifths (Down)\n\n완전 5도 하행 (4도 상행)은 **Flats (b)**가 늘어나는 방향입니다.\n\nC -> F -> Bb -> Eb -> Ab -> Db -> Gb...",
        'P5 up': "### Circle of Fifths (Up)\n\n완전 5도 상행은 **Sharps (#)**가 늘어나는 방향입니다.\n\nC -> G -> D -> A -> E -> B -> F#..."
    },
    'Tritones': {
        'Pitch': "### Tritone (3 whole steps)\n\n증4도(Aug 4) 또는 감5도(Dim 5)입니다. 옥타브를 정확히 절반으로 나눕니다.\n\n* C - F#\n* F - B\n* G - Db\n* **Tritone Substitution:** 도미넌트 7 코드는 Tritone 관계에 있는 다른 도미넌트 7으로 대리 가능합니다. (예: G7 <-> Db7)",
        'Dom7': "### Dominant 7 Tritone\n\nDom7 코드의 가이드톤(3음, 7음)은 Tritone 관계입니다.\n\n예: **G7** (G **B** D **F**) -> B와 F는 Tritone입니다."
    }
}
# (다른 카테고리는 기본 안내 문구 출력)
DEFAULT_THEORY = "### Practice Makes Perfect!\n\n이 카테고리는 다양한 조(Key)와 음(Note)에서 즉각적으로 반응하는 연습이 필요합니다. \n\n**Tip:** 머리로 계산하기보다, 건반의 모양이나 악보상의 위치를 이미지로 기억하려고 노력해보세요."

# ==========================================
# 2. StatManager
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
            except: 
                self.ws_users = self.sh.add_worksheet(title="Users", rows="100", cols="3")
                self.ws_users.append_row(["username", "password_hash", "created_at"])
            try: self.ws_history = self.sh.worksheet("History")
            except: 
                self.ws_history = self.sh.add_worksheet(title="History", rows="1000", cols="10")
                self.ws_history.append_row(["username", "timestamp", "year", "month", "day", "category", "subcategory", "is_correct", "is_solved"])
            try: self.ws_leaderboard = self.sh.worksheet("Leaderboard")
            except: 
                self.ws_leaderboard = self.sh.add_worksheet(title="Leaderboard", rows="1000", cols="10")
                self.ws_leaderboard.append_row(["username", "category", "subcategory", "mode", "date", "score", "total", "time", "solved", "rate"])

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(self, username, password):
        if not self.connected: return False, "Database not connected."
        users = self.ws_users.col_values(1)
        if username in users: return False, "Username already exists."
        pwd_hash = self.hash_password(password)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d")
        self.ws_users.append_row([username, pwd_hash, now_str])
        return True, "User created successfully! Please login."

    def login_user(self, username, password):
        if not self.connected: return False
        try:
            cell = self.ws_users.find(username)
            if not cell: return False
            stored_hash = self.ws_users.cell(cell.row, 2).value
            if stored_hash == self.hash_password(password):
                self.current_user = username
                self.load_user_data()
                return True
            return False
        except: return False

    def load_user_data(self):
        try:
            all_hist = self.ws_history.get_all_records()
            self.data = [r for r in all_hist if str(r['username']) == self.current_user]
        except: self.data = []
        try:
            self.leaderboard_raw = self.ws_leaderboard.get_all_records()
            self.leaderboard = {}
            for r in self.leaderboard_raw:
                cat, sub, mode = r['category'], r['subcategory'], r['mode']
                if cat not in self.leaderboard: self.leaderboard[cat] = {}
                if sub not in self.leaderboard[cat]: self.leaderboard[cat][sub] = {}
                if mode not in self.leaderboard[cat][sub]: self.leaderboard[cat][sub][mode] = []
                item = r.copy()
                del item['category']; del item['subcategory']; del item['mode']
                self.leaderboard[cat][sub][mode].append(item)
            for c in self.leaderboard:
                for s in self.leaderboard[c]:
                    for m in self.leaderboard[c][s]:
                        lst = self.leaderboard[c][s][m]
                        if m == 'test': lst.sort(key=lambda x: (-x['score'], x['time']))
                        elif m == 'speed': lst.sort(key=lambda x: (-x['solved'], -x['rate']))
                        self.leaderboard[c][s][m] = lst[:5]
        except: self.leaderboard = {}

    def record(self, category, subcategory, is_correct, is_retry=False):
        if not self.current_user or not self.connected: return
        now = datetime.datetime.now()
        record = {
            "username": self.current_user, "timestamp": now.timestamp(), "year": now.year, "month": now.month, "day": now.day,
            "category": category, "subcategory": subcategory, "is_correct": 1 if (is_correct and not is_retry) else 0, "is_solved": 1 if (is_correct or is_retry) else 0
        }
        self.data.append(record)
        try:
            row = [self.current_user, record['timestamp'], record['year'], record['month'], record['day'], 
                   record['category'], record['subcategory'], record['is_correct'], record['is_solved']]
            self.ws_history.append_row(row)
        except: pass

    def update_leaderboard(self, mode, category, subcategory, result_data):
        if not self.current_user or not self.connected: return
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        row_data = [self.current_user, category, subcategory, mode, now_str]
        if mode == 'test': row_data.extend([result_data['score'], result_data['total'], result_data['time'], 0, 0])
        elif mode == 'speed': 
            rate = (result_data['correct'] / result_data['total_try'] * 100) if result_data['total_try'] > 0 else 0
            row_data.extend([0, 0, 0, result_data['correct'], rate])
        try:
            self.ws_leaderboard.append_row(row_data)
            self.load_user_data()
        except: pass

    def calculate_stats(self, filtered_data):
        if not filtered_data: return 0, 0.0
        correct = sum(1 for r in filtered_data if r.get('is_correct', 0) == 1)
        solved = sum(1 for r in filtered_data if r.get('is_solved', 0) == 1)
        total = len(filtered_data)
        rate = (correct / total * 100) if total > 0 else 0.0
        return solved, rate

    def get_breakdown(self, filtered_data):
        breakdown = {}
        for r in filtered_data:
            cat = r['category']; sub = r['subcategory']
            if cat not in breakdown: breakdown[cat] = {'total': 0, 'correct': 0, 'subs': {}}
            if sub not in breakdown[cat]['subs']: breakdown[cat]['subs'][sub] = {'total': 0, 'correct': 0}
            breakdown[cat]['total'] += 1
            breakdown[cat]['subs'][sub]['total'] += 1
            if r.get('is_correct', 0) == 1:
                breakdown[cat]['correct'] += 1
                breakdown[cat]['subs'][sub]['correct'] += 1
        return breakdown
    
    def get_trend_data(self, category, subcategory, period_type):
        target_data = []
        for r in self.data:
            if category != "All":
                if r['category'] != category: continue
                if subcategory and r['subcategory'] != subcategory: continue
            target_data.append(r)
        if not target_data: return []
        grouped = {}
        for r in target_data:
            dt = datetime.datetime.fromtimestamp(r['timestamp'])
            key = ""
            if period_type == 'yearly': key = str(r['year'])
            elif period_type == 'monthly': key = f"{r['year']}-{r['month']:02d}"
            elif period_type == 'weekly':
                wn, _, _ = self.get_custom_week(dt)
                key = f"{r['year']}-W{wn:02d}"
            if key not in grouped: grouped[key] = {'correct': 0, 'total': 0}
            grouped[key]['total'] += 1
            if r.get('is_correct', 0) == 1: grouped[key]['correct'] += 1
        result = []
        for k in sorted(grouped.keys()):
            rate = (grouped[k]['correct'] / grouped[k]['total'] * 100)
            result.append((k, rate))
        return result

    def get_custom_week(self, date_obj):
        year = date_obj.year
        jan1 = datetime.date(year, 1, 1)
        first_sunday = jan1 + timedelta(days=(6 - jan1.weekday()))
        if date_obj.date() <= first_sunday: return 1, jan1, first_sunday
        days_after = (date_obj.date() - first_sunday).days
        return 2 + (days_after - 1) // 7, None, None

if 'stat_mgr' not in st.session_state: st.session_state.stat_mgr = StatManager()

# ==========================================
# 3. 유틸리티, 키패드 및 문제 생성
# ==========================================
def get_enharmonic_names(idx): return ENHARMONIC_GROUPS.get(idx % 12, [])
def get_pitch_index(pitch):
    pitch = pitch.strip().capitalize()
    enharmonics = {'C#':'Db','D#':'Eb','F#':'Gb','G#':'Ab','A#':'Bb','Cb':'B','B#':'C','E#':'F','Fb':'E'}
    if pitch in enharmonics: pitch = enharmonics[pitch]
    return NOTES.index(pitch) if pitch in NOTES else -1
def get_pitch_from_index(idx): return NOTES[idx % 12]
def get_valid_answers(idx, suffix=""): return [f"{r}{suffix}" for r in get_enharmonic_names(idx)]
def get_slash_answers(ridx, suf, bidx): return [f"{r}{suf}/{b}" for r in get_enharmonic_names(ridx) for b in get_enharmonic_names(bidx)]

def normalize_input(text):
    text = text.replace('♭', 'b').replace('♯', '#')
    return set([p.strip().lower() for p in text.replace('/',',').split(',') if p.strip()])

# --- Virtual Keypad Logic ---
def get_keypad_keys(cat, sub):
    if (cat == 'Enharmonics' and sub == 'Degrees') or \
       (cat == 'Warming up' and sub == 'Finding degrees') or \
       (cat == 'Locations' and sub == 'Pitch->Deg') or \
       (cat == 'Modes' and sub == 'Alterations') or \
       (cat == 'Mastery' and sub == 'Degrees'):
       return [['♭', '♯'], ['I','II','III','IV'], ['V','VI','VII']]

    if cat == 'Intervals' or \
       (cat == 'Enharmonics' and sub == 'Interval') or \
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
    
    # [Updated CSS for Wide Buttons & Minimized Gaps]
    st.markdown("""
        <style>
        div.stButton > button {
            width: 100% !important;
            height: 50px;
            margin: 0px !important;
            font-size: 18px;
        }
        [data-testid="column"] {
            padding: 0px 5px !important;
            min-width: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    for row_keys in key_rows:
        cols = st.columns(len(row_keys)) 
        for i, key in enumerate(row_keys):
            if cols[i].button(key, key=f"btn_{key}"):
                st.session_state.user_input_buffer += key
                st.rerun()

    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if st.button("⬅️ Del"):
            st.session_state.user_input_buffer = st.session_state.user_input_buffer[:-1]; st.rerun()
    with c2:
        if st.button("❌ Clear"):
            st.session_state.user_input_buffer = ""; st.rerun()
    with c3:
        if st.button("✅ Submit", type="primary", use_container_width=True): return True
    return False

# --- Question Generation (Same) ---
def generate_question(cat, sub):
    try:
        if cat == 'Enharmonics':
            if sub == 'Degrees':
                pairs = [('#VII','I'),('#I','bII'),('#II','bIII'),('bIV','III'),('IV','#III'),('#V','bVI'),('#VI','bVII')]
                t, a = random.choice(pairs)
                return f"What is {t}'s enharmonic?", [a], 'single'
            elif sub == 'Number':
                sets = [['1','8','#7'],['#1','b2','#8','b9'],['2','9'],['#2','b3','#9','b10'],['3','b4','10','b11']]
                c = random.choice(sets); t = random.choice(c); ans = [x for x in c if x!=t]
                return f"What are {t}'s enharmonics?", ans, 'single'
            elif sub == 'Interval':
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
# 4. Streamlit UI Logic
# ==========================================
st.set_page_config(page_title="Road to Berklee", page_icon="🎹")

if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user_input_buffer' not in st.session_state: st.session_state.user_input_buffer = "" # Keypad Buffer

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

# --- MAIN APP ---
with st.sidebar:
    st.write(f"👤 **{st.session_state.logged_in_user}**")
    if st.button("Logout"):
        st.session_state.logged_in_user = None
        st.session_state.page = 'login'
        st.rerun()
    st.markdown("---")
    menu = st.radio("Menu", ["Home", "Statistics", "Leaderboard", "Theory", "Credits"]) # Theory Added

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
    st.session_state.user_input_buffer = "" # Clear buffer
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
    st.session_state.user_input_buffer = "" # Clear buffer
    
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

# --- Pages ---
if st.session_state.page == 'home' or menu != 'Home':
    if menu == "Home":
        st.header("Select Category")
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
                st.write("20 Questions, No Feedback."); 
                if st.button("Start Test"): start_quiz(sel_cat, sel_sub, 'test', 20)
            with m3:
                st.write("60 Seconds."); 
                if st.button("Start Speed Run"): start_quiz(sel_cat, sel_sub, 'speed', 60)
    elif menu == "Statistics":
        st.header("Statistics")
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
                d = st.session_state.stat_mgr.get_trend_data(t_cat, t_sub, "weekly") # Default weekly
                if d: st.line_chart({x[0]: x[1] for x in d})
                else: st.warning("No Data")
    elif menu == "Leaderboard":
        st.header("🏆 Hall of Fame")
        l_cat = st.selectbox("Cat", list(CATEGORY_INFO.keys()))
        l_sub = st.selectbox("Sub", CATEGORY_INFO[l_cat])
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
    
    # --- THEORY PAGE (New Feature) ---
    elif menu == "Theory":
        st.header("📚 Music Theory")
        t_cat = st.selectbox("Category", list(CATEGORY_INFO.keys()))
        t_sub = st.selectbox("Subcategory", CATEGORY_INFO[t_cat])
        
        st.markdown("---")
        # 이론 데이터 가져오기 (없으면 기본 메시지)
        theory_text = THEORY_DATA.get(t_cat, {}).get(t_sub, DEFAULT_THEORY)
        st.markdown(theory_text)

    elif menu == "Credits":
        st.header("Credits"); st.write("Created by: Oh Seung-yeol")

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
        # --- Virtual Keypad UI ---
        st.text_input("Answer Input (Use buttons below)", value=st.session_state.user_input_buffer, disabled=True, key="display_buffer")
        submitted = render_keypad(qs['cat'], qs['sub'])
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⏩ Skip"): check_answer("skip")
        with c2:
            if st.button("🏠 Quit"): st.session_state.page = 'home'; st.rerun()
        if submitted: check_answer(st.session_state.user_input_buffer)

if st.session_state.page == 'result':
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