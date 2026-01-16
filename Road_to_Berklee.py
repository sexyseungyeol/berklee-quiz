import streamlit as st
import random
import time
import datetime
from datetime import timedelta
import hashlib
import gspread
import os
import pandas as pd

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
        except: self.data = []

    def record(self, category, subcategory, is_correct, is_retry=False):
        if not self.current_user or not self.connected or is_retry: return
        row = [self.current_user, datetime.datetime.now().timestamp(), datetime.datetime.now().year, datetime.datetime.now().month, datetime.datetime.now().day, category, subcategory, 1 if is_correct else 0, 1]
        try: self.ws_history.append_row(row)
        except: pass

if 'stat_mgr' not in st.session_state: st.session_state.stat_mgr = StatManager()

# ==========================================
# 3. SMART KEYPAD (Fixed Logic for + and -)
# ==========================================
def add_input(k): st.session_state.user_input_buffer += k
def del_input(): st.session_state.user_input_buffer = st.session_state.user_input_buffer[:-1]
def clear_input(): st.session_state.user_input_buffer = ""

def get_smart_keypad(cat, sub):
    layout = []
    # 1. 임시표 (Priority 1)
    if sub != 'Counting semitones': layout.append(['♭', '♯'])
    
    # 2. 쉼표 (Priority 2)
    if any(s in sub for s in ['tones', 'Alterations', 'Tensions', 'Dom7', 'Dim7', 'Pitches', 'Pivot', 'Number']):
        layout.append([','])
    
    # 3. 음정 성질 (+, M, P, m, -) (Priority 3) - [FIX: Show by default unless Solfege]
    if sub != 'Solfege':
        layout.append(['+', 'M', 'P', 'm', '-'])
        
    # 4. 음 이름 (Priority 4)
    if any(s in sub for s in ['Finding', 'tones', 'Pitch', 'Tracking', 'Key', 'Pitches', 'Pivot']):
        layout.append(['C', 'D', 'E', 'F']); layout.append(['G', 'A', 'B'])
        
    # 5. 도수 (Priority 5)
    if any(s in sub for s in ['Degrees', 'Finding', 'Pitch->Deg', 'Alterations', 'Chords']):
        layout.append(['I', 'II', 'III']); layout.append(['IV', 'V', 'VI', 'VII'])
        
    # 6. 숫자 (Priority 6)
    if any(s in sub for s in ['Counting', 'Number', 'Natural', 'r calc', 'tones']):
        layout.append(['1', '2', '3', '4', '5']); layout.append(['6', '7', '8', '9', '0'])
        
    # 7. 모드 & 스케일
    if cat in ['Modes', 'Minor'] or sub in ['Avail Scales', 'Similarities']:
        layout.append(['Ionian', 'Dorian', 'Phrygian', 'Lydian'])
        layout.append(['Natural minor', 'Harmonic minor', 'Melodic minor'])
        
    # 8. 코드 타입 (Priority 8)
    if any(c in cat for c in ['Chord', 'Minor', 'Tritones']):
        layout.append(['maj7', 'm7', '7', 'm7b5']); layout.append(['dim7', '6', 'm6', 'sus4', 'aug'])
        
    # 9. 슬래시 (Priority 9)
    if any(s in sub for s in ['9 chord', 'Rootless', 'Pivot']):
        layout.append(['/'])

    if sub == 'Solfege':
        return [['Do','Re','Mi','Fa'], ['Sol','La','Ti'], ['Di','Ri','Fi','Si','Li'], ['Ra','Me','Se','Le','Te']]
    return layout

def render_keypad(cat, sub):
    key_rows = get_smart_keypad(cat, sub)
    st.markdown("""<style>div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] .stButton > button { width: 100% !important; height: 70px !important; font-size: 20px !important; font-weight: bold !important; border-radius: 12px !important; margin-bottom: 6px !important; }</style>""", unsafe_allow_html=True)
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
# 4. QUIZ ENGINE
# ==========================================
def generate_question(cat, sub):
    try:
        root = random.choice(NOTES)
        if cat == 'Enharmonics' and sub == 'Degrees':
            t, a = random.choice([('#VII','I'),('#I','bII'),('#II','bIII'),('bIV','III')])
            return f"What is {t}'s enharmonic?", [a], 'single'
        if cat == 'Warming up' and sub == 'Counting semitones':
            d = random.randint(1,13); return f"Which degree is {d} semitones away? (P1=1)", DISTANCE_TO_DEGREE[d], 'single'
        return f"Determine the {sub} for {root}", ["C"], 'single'
    except: return "Error", ["C"], 'single'

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
    st.stop()

with st.sidebar:
    st.write(f"👤 **{st.session_state.logged_in_user}**")
    if st.button("Logout"): st.session_state.logged_in_user = None; cookie_manager.delete("berklee_user"); st.rerun()
    st.markdown("---")
    menu = st.radio("Menu", ["🏠 Home", "📝 Start Quiz", "📊 Statistics", "ℹ️ Credits"])

if 'quiz_state' not in st.session_state:
    st.session_state.quiz_state = {'active': False, 'cat': '', 'sub': '', 'mode': '', 'current_idx': 0, 'score': 0, 'start_time': 0, 'limit': 0, 'is_retry': False}

def start_quiz(cat, sub, mode, limit=0, is_retry=False, retry_pool=None):
    st.session_state.quiz_state = {
        'active': True, 'cat': cat, 'sub': sub, 'mode': mode,
        'current_idx': 0, 'score': 0, 'start_time': time.time(),
        'limit': len(retry_pool) if is_retry else limit,
        'is_retry': is_retry, 'retry_pool': retry_pool,
        'current_q': retry_pool[0] if is_retry else generate_question(cat, sub)
    }
    st.session_state.wrong_count = 0; st.session_state.user_input_buffer = ""; st.session_state.last_result = None
    if not is_retry: st.session_state.wrong_questions_pool = []
    st.session_state.page = 'quiz'; st.rerun()

def check_answer():
    qs = st.session_state.quiz_state; q_data = qs['current_q']; q_text, ans_list, mode = q_data
    u_raw = st.session_state.user_input_buffer.lower().strip()
    is_correct = any(a.lower().strip() == u_raw for a in ans_list)
    
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
    if qs['current_idx'] >= qs['limit']: st.session_state.page = 'result'
    else: qs['current_q'] = qs['retry_pool'][qs['current_idx']] if qs['is_retry'] else generate_question(qs['cat'], qs['sub'])
    st.session_state.user_input_buffer = ""; st.rerun()

# --- RENDERING ---
if menu == "🏠 Home":
    col1, col2 = st.columns([1, 2])
    with col1:
        if os.path.exists("logo.png"): st.image("logo.png", width=180)
        else: st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/Berklee_College_of_Music_Logo.png/800px-Berklee_College_of_Music_Logo.png", width=150)
    # [FIXED: Description font size increased]
    st.markdown("<h1>Road to Berklee</h1><p style='font-size: 24px; font-weight: 500;'>Music Theory Practice Application</p>", unsafe_allow_html=True)

elif menu == "📝 Start Quiz":
    if st.session_state.page == 'quiz':
        if st.session_state.last_result:
            res = st.session_state.last_result; bg = "rgba(0,255,0,0.2)" if res['correct'] else "rgba(255,0,0,0.2)"
            st.markdown(f"<style>.stApp {{ animation: flash 0.6s forwards; }} @keyframes flash {{ 0% {{ background-color: {bg}; }} 100% {{ background-color: transparent; }} }}</style>", unsafe_allow_html=True)
            if res['correct']: st.toast("✅ Correct!")
            elif res.get('show_ans'): st.error(f"❌ Answer: {res['ans']}")
            else: st.toast(f"❌ Try Again ({st.session_state.wrong_count}/3)")
            st.session_state.last_result = None
        qs = st.session_state.quiz_state
        st.progress(qs['current_idx'] / qs['limit']); st.write(f"Question {qs['current_idx']+1} / {qs['limit']}")
        st.subheader(qs['current_q'][0]); st.text_input("Answer Input", value=st.session_state.user_input_buffer, disabled=True)
        if render_keypad(qs['cat'], qs['sub']): check_answer()
        if st.button("🏠 Quit Quiz"): st.session_state.page = 'home'; st.rerun()
    elif st.session_state.page == 'result':
        qs = st.session_state.quiz_state; st.header("Result")
        st.metric("Score", f"{qs['score']}/{qs['limit']}")
        if st.session_state.wrong_questions_pool:
            if st.button("🔄 오답 다시 풀기 (Retry Mistakes)", use_container_width=True):
                start_quiz(qs['cat'], qs['sub'], qs['mode'], is_retry=True, retry_pool=st.session_state.wrong_questions_pool)
        if st.button("⬅️ Back", use_container_width=True): st.session_state.page = 'home'; st.rerun()
    else:
        st.header("📝 Select Category")
        c = st.selectbox("Category", list(CATEGORY_INFO.keys())); s = st.selectbox("Sub", CATEGORY_INFO[c])
        if st.button("Start Practice"): start_quiz(c, s, 'practice', 10)

elif menu == "📊 Statistics":
    st.header("📊 Statistics")
    solved = len(st.session_state.stat_mgr.data)
    correct = sum(1 for r in st.session_state.stat_mgr.data if r.get('is_correct', 0) == 1)
    rate = (correct / solved * 100) if solved > 0 else 0
    # [FIXED: Metric label updated]
    st.metric(label=f"{solved} steps to Berklee College of Music", value=solved)
    st.metric("Accuracy", f"{rate:.1f}%")
    
    bd = {}
    for r in st.session_state.stat_mgr.data:
        c = r['category']; bd[c] = bd.get(c, {'t':0, 'c':0}); bd[c]['t'] += 1
        if r.get('is_correct', 0) == 1: bd[c]['c'] += 1
    for cat in sorted(bd.keys()):
        st.write(f"**{cat}**: {bd[cat]['c']}/{bd[cat]['t']} ({(bd[cat]['c']/bd[cat]['t']*100):.1f}%)")

elif menu == "ℹ️ Credits":
    st.header("ℹ️ Credits")
    st.write("### Road to Berklee")
    st.write("**Developed by:** Oh Seung-yeol")
    st.write("Keep practicing and good luck! 🎹")
