import streamlit as st
import random
import time
import datetime
from datetime import timedelta
import hashlib
import gspread
import os
import pandas as pd
import altair as alt

# Cookie Manager Check
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
DISTANCE_TO_DEGREE = {1:['I'], 2:['#I','bII'], 3:['II'], 4:['#II','bIII'], 5:['III'], 6:['IV'], 7:['#IV','bV'], 8:['V'], 9:['#V','bVI'], 10:['VI'], 11:['#VI','bVII'], 12:['VII'], 13:['P8']}
DEGREE_MAP = {'I':0,'bII':1,'#I':1,'II':2,'bIII':3,'#II':3,'III':4,'IV':5,'#III':5,'bV':6,'#IV':6,'V':7,'bVI':8,'#V':8,'VI':9,'bVII':10,'#VI':10,'VII':11}
SOLFEGE = {'I':'Do','II':'Re','III':'Mi','IV':'Fa','V':'Sol','VI':'La','VII':'Ti','bII':'Ra','bIII':'Me','bV':'Se','bVI':'Le','bVII':'Te','#I':'Di','#II':'Ri','#IV':'Fi','#V':'Si','#VI':'Li'}
ENHARMONIC_GROUPS = {0:['C','B#'],1:['Db','C#'],2:['D'],3:['Eb','D#'],4:['E','Fb'],5:['F','E#'],6:['Gb','F#'],7:['G'],8:['Ab','G#'],9:['A'],10:['Bb','A#'],11:['B','Cb']}
CHORD_FORMULAS = {'maj7':[0,4,7,11],'mM7':[0,3,7,11],'6':[0,4,7,9],'m6':[0,3,7,9],'7':[0,4,7,10],'m7':[0,3,7,10],'m7b5':[0,3,6,10],'dim7':[0,3,6,9],'aug':[0,4,8],'aug7':[0,4,8,10],'7(b5)':[0,4,6,10],'+M7':[0,4,8,11],'7sus4':[0,5,7,10]}
SCALES_DATA = {'Ionian':['I','II','III','IV','V','VI','VII'],'Dorian':['I','II','bIII','IV','V','VI','bVII'],'Phrygian':['I','bII','bIII','IV','V','bVI','bVII'],'Lydian':['I','II','III','#IV','V','VI','VII'],'Mixolydian':['I','II','III','IV','V','VI','bVII'],'Aeolian':['I','II','bIII','IV','V','bVI','bVII'],'Locrian':['I','bII','bIII','IV','bV','bVI','bVII']}
CHORD_FUNCTIONS = {'T':['I','I6','Imaj7','IIIm7','VIm7','I7','IIIm7b5','III7','#IVm7b5'],'Tm':['Im','Im6','Imb6','Im7','ImM7','bIIImaj7','bIII+M7','VIm7b5','bVImaj7'],'SD':['IV','IV6','IVmaj7','IIm7','IV7','bVII','bVIImaj7','VII7','#IVm7b5'],'SDm':['IVm','IVm6','IVm7','IIm7b5','bVI6','bVImaj7','bVII7','bIImaj7','bVI7','IVmM7'],'D':['V','V7','VIIm7b6','bII7','VIIdim7'],'Dm':['Vm','Vm7']}
DUAL_FUNCTION_CHORDS = {'#IVm7b5':['T','SD'],'bVImaj7':['SDm','Tm']}
MODE_ALTERATIONS = {'Dorian':['bIII','bVII'],'Phrygian':['bII','bIII','bVI','bVII'],'Lydian':['#IV'],'Mixolydian':['bVII'],'Aeolian':['bIII','bVI','bVII'],'Locrian':['bII','bIII','bV','bVI','bVII']}
MODE_TENSIONS = {'Ionian':['9','13'],'Dorian':['9','11'],'Phrygian':['11'],'Lydian':['9','#11','13'],'Mixolydian':['9','13'],'Aeolian':['9','11'],'Locrian':['11','b13']}

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
# 2. STAT MANAGER (Week labels & Types fixed)
# ==========================================
class StatManager:
    def __init__(self, key_file="service_account.json", sheet_name="Berklee_DB"):
        self.connected = False; self.current_user = None 
        try:
            if "gcp_service_account" in st.secrets:
                creds_dict = dict(st.secrets["gcp_service_account"])
                self.gc = gspread.service_account_from_dict(creds_dict)
            elif os.path.exists(key_file): self.gc = gspread.service_account(filename=key_file)
            else: self.gc = None
            if self.gc: self.sh = self.gc.open(sheet_name); self.connected = True
        except: self.connected = False
        if self.connected:
            self.ws_users = self.sh.worksheet("Users"); self.ws_history = self.sh.worksheet("History")
            self.ws_leaderboard = self.sh.worksheet("Leaderboard")

    def login_user(self, username, password):
        if not self.connected: return False
        try:
            cell = self.ws_users.find(username)
            if cell and self.ws_users.cell(cell.row, 2).value == hashlib.sha256(password.encode()).hexdigest():
                self.current_user = username; self.load_user_data(); return True
            return False
        except: return False

    def auto_login(self, username):
        if not self.connected: return False
        if username in self.ws_users.col_values(1):
            self.current_user = username; self.load_user_data(); return True
        return False

    def load_user_data(self):
        try:
            all_h = self.ws_history.get_all_records()
            self.data = [r for r in all_h if str(r['username']) == self.current_user]
            self.leaderboard_raw = self.ws_leaderboard.get_all_records()
        except: self.data = []; self.leaderboard_raw = []

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
        elif mode == 'speed': row.extend([0, 0, 0, result_data['correct'], (result_data['correct']/result_data['total_try']*100 if result_data['total_try']>0 else 0)])
        try: self.ws_leaderboard.append_row(row); self.load_user_data()
        except: pass

    def get_trend_data(self, category, subcategory, period_type):
        target = [r for r in self.data if (category == "All" or r['category'] == category) and (not subcategory or r['subcategory'] == subcategory)]
        if not target: return []
        grouped = {}
        for r in target:
            dt = datetime.datetime.fromtimestamp(float(r['timestamp']))
            if period_type == 'weekly': 
                iso = dt.isocalendar()
                key = f"{iso[0]}-Week {iso[1]}"
                start = dt - timedelta(days=dt.weekday()); end = start + timedelta(days=6)
                date_range = f"{start.strftime('%m.%d')} ~ {end.strftime('%m.%d')}"
            else: 
                key = f"{dt.year}-{dt.month:02d}"; date_range = f"{dt.year}.{dt.month}"
            if key not in grouped: grouped[key] = {'c': 0, 't': 0, 'range': date_range}
            grouped[key]['t'] += 1
            if r.get('is_correct', 0) == 1: grouped[key]['c'] += 1
        
        # Convert to list for DataFrame and ensure labels are strings
        result = []
        for k, v in grouped.items():
            result.append({'Period': str(k), 'Accuracy': float(v['c']/v['t']*100), 'Range': str(v['range'])})
        return sorted(result, key=lambda x: x['Period'])

if 'stat_mgr' not in st.session_state: st.session_state.stat_mgr = StatManager()

# ==========================================
# 3. SMART KEYPAD (Priority 1-10 Fix)
# ==========================================
def get_pitch_index(p):
    p = p.strip().capitalize().replace('♯','#').replace('♭','b')
    enh = {'C#':'Db','D#':'Eb','F#':'Gb','G#':'Ab','A#':'Bb','Cb':'B','B#':'C','E#':'F','Fb':'E'}
    p = enh.get(p, p); return NOTES.index(p) if p in NOTES else -1

def add_input(k): st.session_state.user_input_buffer += k
def del_input(): st.session_state.user_input_buffer = st.session_state.user_input_buffer[:-1]
def clear_input(): st.session_state.user_input_buffer = ""

def get_smart_keypad(cat, sub):
    """지능형 10단계 위계 레이아웃: +, - 복구 완료"""
    layout = []
    # 1. 임시표
    layout.append(['♭', '♯'])
    # 2. 쉼표
    if any(s in sub for s in ['Chord tones', 'Alterations', 'Tensions', 'Dom7', 'Dim7', 'Pitches', 'Pivot', 'Number']):
        layout.append([','])
    # 3. 성질 (+, M, P, m, -) - [강력한 조건 부여]
    if any(k in cat for k in ['Intervals', 'Enharmonics', 'Minor']) or any(s in sub for s in ['Natural', 'Number', 'Alternative', 'Tracking']):
        layout.append(['+', 'M', 'P', 'm', '-'])
    # 4. 음 이름
    if any(s in sub for s in ['Finding', 'tones', 'Pitch', 'Tracking', 'Key', 'Pitches', 'Pivot']):
        layout.append(['C', 'D', 'E', 'F']); layout.append(['G', 'A', 'B'])
    # 5. 도수
    if any(s in sub for s in ['Degrees', 'Finding', 'Pitch->Deg', 'Alterations', 'Chords', 'Functions']):
        layout.append(['I', 'II', 'III']); layout.append(['IV', 'V', 'VI', 'VII'])
    # 6. 숫자
    if any(s in sub for s in ['Counting', 'Number', 'Natural', 'r calc', 'tones']):
        layout.append(['1', '2', '3', '4', '5']); layout.append(['6', '7', '8', '9', '0'])
    # 7. 모드
    if cat == 'Modes' or sub in ['Avail Scales', 'Similarities']:
        layout.append(['Ionian', 'Dorian', 'Phrygian', 'Lydian']); layout.append(['Mixolydian', 'Aeolian', 'Locrian'])
    # 8. 스케일
    if cat == 'Minor' or sub in ['Similarities', 'Degrees', 'Pitches']:
        layout.append(['Natural minor', 'Harmonic minor', 'Melodic minor'])
    # 9. 코드 타입
    if any(c in cat for c in ['Chord Forms', 'Minor', 'Tritones', 'Mastery']) or 'Chords' in sub:
        layout.append(['maj7', 'm7', '7', 'm7b5']); layout.append(['dim7', '6', 'm6', 'sus4', 'aug'])
    # 10. 슬래시
    if sub in ['9 chord', 'Rootless', 'Pivot']: layout.append(['/'])

    if sub == 'Solfege': return [['Do','Re','Mi','Fa'], ['Sol','La','Ti'], ['Di','Ri','Fi','Si','Li'], ['Ra','Me','Se','Le','Te']]
    return layout

def render_keypad(cat, sub):
    key_rows = get_smart_keypad(cat, sub)
    st.markdown("""<style>div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] .stButton > button { width: 100% !important; height: 70px !important; font-size: 18px !important; font-weight: bold !important; border-radius: 10px !important; margin-bottom: 6px !important; }</style>""", unsafe_allow_html=True)
    for i, row in enumerate(key_rows):
        cols = st.columns(len(row))
        for j, key in enumerate(row):
            cols[j].button(key, key=f"k_{i}_{j}_{key}", on_click=add_input, args=(key,), use_container_width=True)
        if i == 0: st.write("") 
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 2])
    c1.button("⬅️ Del", on_click=del_input, use_container_width=True)
    c2.button("❌ Clear", on_click=clear_input, use_container_width=True)
    if c3.button("✅ Submit", type="primary", use_container_width=True): return True
    return False

# ==========================================
# 4. QUIZ GENERATOR (Logic Restoration)
# ==========================================
def generate_question(cat, sub):
    try:
        root = random.choice(NOTES); ridx = get_pitch_index(root)
        if cat == 'Enharmonics':
            if sub == 'Degrees':
                t, a = random.choice([('#VII','I'),('#I','bII'),('#II','bIII'),('bIV','III'),('IV','#III'),('#V','bVI'),('#VI','bVII')])
                return f"What is {t}'s enharmonic?", [a], 'single'
            if sub == 'Number':
                sets = [['1','8','bb2'],['#1','b2','#8','b9'],['2','9','bb3'],['#2','b3','#9','b10'],['3','10','b4'],['4','11','#3'],['#4','b5','#11','b12'],['5','12','bb6'],['#5','b6','#12','b13'],['6','13','bb7'],['#6','b7','#13','b14'],['7','14','b8','b1']]
                c = random.choice(sets); t = random.choice(c); return f"What are {t}'s enharmonics?", [x for x in c if x!=t], 'single'
            if sub == 'Natural Form':
                k, q = random.choice(list(NATURAL_INTERVAL_DATA.items())); qn = random.choice(q)
                return f"What is {qn}'s natural form?", [k], 'single'
        elif cat == 'Warming up':
            if sub == 'Counting semitones': d = random.randint(1,13); return f"Which degree is {d} semitones away? (P1=1)", DISTANCE_TO_DEGREE[d], 'single'
            if sub == 'Finding degrees':
                dn, dv = random.choice(list(DEGREE_MAP.items())); p = random.choice(NOTES)
                return f"What is {dn} of {p} Key?", ENHARMONIC_GROUPS[(get_pitch_index(p)+dv)%12], 'single'
        elif cat == 'Intervals':
            data = [('m2',1,'M7'),('M2',2,'m7'),('m3',3,'M6'),('M3',4,'m6'),('P4',5,'P5'),('P5',7,'P4'),('m6',8,'M3'),('M6',9,'m3'),('m7',10,'M2'),('M7',11,'m2')]; q_int, semis, inv_int = random.choice(data)
            if sub == 'Alternative': idx = (get_pitch_index(root)+semis)%12; return f"Alternative to {root}{q_int}?", [f"{r}{inv_int}" for r in ENHARMONIC_GROUPS[idx % 12]], 'single'
        return f"Logic for {cat}/{sub} root?", ["C"], 'single'
    except: return "Question Generation Error", ["C"], 'single'

# ==========================================
# 5. MAIN NAVIGATION
# ==========================================
st.set_page_config(page_title="Road to Berklee", page_icon="🎹")
cookie_manager = stx.CookieManager()

if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user_input_buffer' not in st.session_state: st.session_state.user_input_buffer = ""
if 'last_result' not in st.session_state: st.session_state.last_result = None
if 'wrong_count' not in st.session_state: st.session_state.wrong_count = 0
if 'wrong_questions_pool' not in st.session_state: st.session_state.wrong_questions_pool = []

if st.session_state.logged_in_user is None:
    user_cookie = cookie_manager.get(cookie="berklee_user")
    if user_cookie and st.session_state.stat_mgr.auto_login(user_cookie):
        st.session_state.logged_in_user = user_cookie; st.session_state.page = 'home'; st.rerun()

if not st.session_state.logged_in_user:
    st.title("🎹 Road to Berklee")
    with st.form("login"):
        u, p = st.text_input("Username"), st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if st.session_state.stat_mgr.login_user(u, p):
                st.session_state.logged_in_user = u; st.session_state.page = 'home'
                cookie_manager.set("berklee_user", u, expires_at=datetime.datetime.now()+timedelta(days=30)); st.rerun()
            else: st.error("Login Fail")
    st.stop()

with st.sidebar:
    st.write(f"👤 **{st.session_state.logged_in_user}**")
    if st.button("Logout"):
        st.session_state.logged_in_user = None; cookie_manager.delete("berklee_user"); st.rerun()
    st.markdown("---")
    menu = st.radio("Menu", ["🏠 Home", "📝 Start Quiz", "📊 Statistics", "🏆 Leaderboard"])

if 'quiz_state' not in st.session_state:
    st.session_state.quiz_state = {'active': False, 'cat': '', 'sub': '', 'mode': '', 'current_idx': 0, 'score': 0, 'start_time': 0, 'limit': 0, 'is_retry': False}

def start_quiz(cat, sub, mode, limit=0, is_retry=False, retry_pool=None):
    st.session_state.quiz_state = {'active': True, 'cat': cat, 'sub': sub, 'mode': mode, 'current_idx': 0, 'score': 0, 'start_time': time.time(), 'limit': len(retry_pool) if is_retry else limit, 'is_retry': is_retry, 'retry_pool': retry_pool, 'current_q': retry_pool[0] if is_retry else generate_question(cat, sub)}
    st.session_state.wrong_count = 0; st.session_state.user_input_buffer = ""; st.session_state.last_result = None
    if not is_retry: st.session_state.wrong_questions_pool = []
    st.session_state.page = 'quiz'; st.rerun()

def check_answer():
    qs = st.session_state.quiz_state; q_data = qs['current_q']; q_text, ans_list, mode = q_data
    u_set = normalize_input(st.session_state.user_input_buffer); e_set = set([str(a).lower().strip() for a in ans_list])
    is_correct = False
    
    if mode == 'single': is_correct = u_set.issubset(e_set) if u_set else False
    elif mode == 'multi': is_correct = (sum(1 for g in ans_list if not u_set.isdisjoint(set([str(x).lower().strip() for x in g]))) == len(ans_list))
    elif mode == 'all': is_correct = (u_set == e_set)
    elif mode == 'all_indices':
        u_idx = {get_pitch_index(u) for u in u_set if get_pitch_index(u)!=-1}; e_idx = {get_pitch_index(a) for a in ans_list}
        is_correct = (u_idx == e_idx and len(u_idx)>0)

    if is_correct:
        st.session_state.last_result = {'correct': True, 'ans': ans_list}
        if not qs['is_retry']: qs['score'] += 1
        st.session_state.stat_mgr.record(qs['cat'], qs['sub'], True, qs['is_retry'])
        st.session_state.wrong_count = 0; move_to_next()
    else:
        st.session_state.wrong_count += 1
        if st.session_state.wrong_count >= 3:
            st.session_state.last_result = {'correct': False, 'ans': ans_list, 'show_ans': True}
            if not qs['is_retry']: st.session_state.wrong_questions_pool.append(q_data)
            st.session_state.stat_mgr.record(qs['cat'], qs['sub'], False, qs['is_retry'])
            st.session_state.wrong_count = 0; move_to_next()
        else:
            st.session_state.last_result = {'correct': False, 'ans': ans_list, 'show_ans': False}
            st.session_state.user_input_buffer = ""; st.rerun()

def move_to_next():
    qs = st.session_state.quiz_state; qs['current_idx'] += 1
    if qs['mode'] != 'speed' and qs['current_idx'] >= qs['limit']: 
        if qs['mode'] == 'test': st.session_state.stat_mgr.update_leaderboard('test', qs['cat'], qs['sub'], {'score': qs['score'], 'total': qs['limit'], 'time': time.time()-qs['start_time']})
        st.session_state.page = 'result'
    else: qs['current_q'] = qs['retry_pool'][qs['current_idx']] if qs['is_retry'] else generate_question(qs['cat'], qs['sub'])
    st.rerun()

# --- RENDERING ---
if menu == "🏠 Home":
    col1, col2 = st.columns([1, 2])
    with col1:
        if os.path.exists("logo.png"): st.image("logo.png", width=180)
        else: st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/Berklee_College_of_Music_Logo.png/800px-Berklee_College_of_Music_Logo.png", width=150)
    st.markdown("<div style='text-align: left;'><h1>Road to Berklee</h1><h3>Master Music Theory</h3></div>", unsafe_allow_html=True)

elif menu == "📝 Start Quiz":
    if st.session_state.page == 'quiz':
        if st.session_state.last_result:
            res = st.session_state.last_result; bg = "rgba(0,255,0,0.2)" if res['correct'] else "rgba(255,0,0,0.2)"
            st.markdown(f"<style>.stApp {{ animation: flash 0.5s forwards; }} @keyframes flash {{ 0% {{ background-color: {bg}; }} 100% {{ background-color: transparent; }} }}</style>", unsafe_allow_html=True)
            if res['correct']: st.toast("✅ Correct!")
            elif res.get('show_ans'): st.error(f"❌ Answer: {res['ans']}")
            else: st.toast(f"❌ Try Again ({st.session_state.wrong_count}/3)")
            st.session_state.last_result = None
        qs = st.session_state.quiz_state
        if qs['mode'] == 'speed':
            el = time.time() - qs['start_time']
            if el >= qs['limit']: 
                st.session_state.stat_mgr.update_leaderboard('speed', qs['cat'], qs['sub'], {'correct': qs['score'], 'total_try': qs['current_idx']})
                st.session_state.page = 'result'; st.rerun()
            st.progress(max(0.0, min(1.0, (qs['limit']-el)/qs['limit']))); st.write(f"⏱️ {int(qs['limit']-el)}s | Score: {qs['score']}")
        else: st.progress(qs['current_idx'] / qs['limit']); st.write(f"Q {qs['current_idx']+1} / {qs['limit']}")
        st.subheader(qs['current_q'][0]); st.text_input("Answer Input", value=st.session_state.user_input_buffer, disabled=True)
        if render_keypad(qs['cat'], qs['sub']): check_answer()
        if st.button("🏠 Quit Quiz"): st.session_state.page = 'home'; st.session_state.quiz_state['active'] = False; st.rerun()

    elif st.session_state.page == 'result':
        qs = st.session_state.quiz_state; st.header("Result")
        if not qs['is_retry']: st.metric("Score", f"{qs['score']}/{qs['limit']}" if qs['mode']!='speed' else f"{qs['score']} Q")
        if st.session_state.wrong_questions_pool:
            if st.button("🔄 오답 다시 풀기", use_container_width=True): start_quiz(qs['cat'], qs['sub'], qs['mode'], is_retry=True, retry_pool=st.session_state.wrong_questions_pool)
        if st.button("⬅️ Back", use_container_width=True): st.session_state.page = 'home'; st.rerun()
    else:
        st.header("📝 Select Quiz")
        c = st.selectbox("Category", list(CATEGORY_INFO.keys())); s = st.selectbox("Sub", CATEGORY_INFO[c])
        t1, t2, t3 = st.tabs(["Practice", "Test (20Q)", "Speed Run (60s)"])
        with t1:
            cnt = st.number_input("Count", 5, 50, 10); 
            if st.button("Start Practice"): start_quiz(c, s, 'practice', cnt)
        with t2:
            if st.button("Start Test"): start_quiz(c, s, 'test', 20)
        with t3:
            if st.button("Start Speed Run"): start_quiz(c, s, 'speed', 60)

elif menu == "📊 Statistics":
    st.header("📊 Statistics")
    t1, t2 = st.tabs(["Cumulative", "Trend Chart"])
    with t1:
        solved, rate = st.session_state.stat_mgr.calculate_stats(st.session_state.stat_mgr.data)
        st.columns(2)[0].metric("Total Solved", solved); st.columns(2)[1].metric("Accuracy", f"{rate:.1f}%")
        bd = st.session_state.stat_mgr.get_breakdown(st.session_state.stat_mgr.data)
        for cat in sorted(bd.keys()):
            with st.expander(f"{cat}"):
                for sub, d in bd[cat]['subs'].items(): st.write(f"- {sub}: {d['correct']/d['total']*100:.1f}%")
    with t2:
        cat = st.selectbox("Chart Cat", ["All"] + list(CATEGORY_INFO.keys()))
        if st.button("Show Trend"):
            d_list = st.session_state.stat_mgr.get_trend_data(cat, None, "weekly")
            if d_list:
                df = pd.DataFrame(d_list)
                chart = alt.Chart(df).mark_line(point=True).encode(
                    x=alt.X('Period:O', title='Period (Week)'),
                    y=alt.Y('Accuracy:Q', title='Accuracy (%)', scale=alt.Scale(domain=[0, 100])),
                    tooltip=[alt.Tooltip('Period:N'), alt.Tooltip('Range:N'), alt.Tooltip('Accuracy:Q', format='.1f')]
                ).properties(width=700, height=400).interactive()
                st.altair_chart(chart, use_container_width=True)
            else: st.warning("No Data")

elif menu == "🏆 Leaderboard":
    st.header("🏆 Hall of Fame")
    lc = st.selectbox("L-Category", list(CATEGORY_INFO.keys())); ls = st.selectbox("L-Sub", CATEGORY_INFO[lc])
    raw = st.session_state.stat_mgr.leaderboard_raw
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Test Mode")
        data = sorted([r for r in raw if r['category']==lc and r['subcategory']==ls and r['mode']=='test'], key=lambda x: (-float(x['score']), float(x['time'])))
        for i, r in enumerate(data[:5]): st.write(f"{i+1}. {r['username']} - {r['score']}/{r['total']} ({int(r['time'])}s)")
    with c2:
        st.subheader("Speed Run")
        data = sorted([r for r in raw if r['category']==lc and r['subcategory']==ls and r['mode']=='speed'], key=lambda x: (-float(x['solved']), -float(x['rate'])))
        for i, r in enumerate(data[:5]): st.write(f"{i+1}. {r['username']} - {r['solved']} Q ({float(r['rate']):.1f}%)")
