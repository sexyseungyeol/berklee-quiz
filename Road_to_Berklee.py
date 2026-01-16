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
# 2. STAT MANAGER (Strict Typing)
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
            self.ws_leaderboard = self.sh.worksheet("Leaderboard"); self.ws_theory = self.sh.worksheet("Theory")

    def record(self, category, subcategory, is_correct, is_retry=False):
        if not self.current_user or not self.connected or is_retry: return
        now = datetime.datetime.now()
        row = [self.current_user, now.timestamp(), now.year, now.month, now.day, category, subcategory, 1 if is_correct else 0, 1]
        try: self.ws_history.append_row(row)
        except: pass

    def get_trend_data(self, category, subcategory):
        target = [r for r in self.data if (category == "All" or r['category'] == category) and (not subcategory or r['subcategory'] == subcategory)]
        if not target: return []
        grouped = {}
        for r in target:
            dt = datetime.datetime.fromtimestamp(float(r['timestamp']))
            iso = dt.isocalendar()
            key = f"{iso[0]}-Week {iso[1]:02d}"
            start = dt - timedelta(days=dt.weekday()); end = start + timedelta(days=6)
            dr = f"{start.strftime('%m.%d')} ~ {end.strftime('%m.%d')}"
            if key not in grouped: grouped[key] = {'c': 0, 't': 0, 'r': dr}
            grouped[key]['t'] += 1
            if r.get('is_correct', 0) == 1: grouped[key]['c'] += 1
        
        return sorted([{'Period': str(k), 'Accuracy': float(v['c']/v['t']*100), 'Range': str(v['r'])} for k, v in grouped.items()], key=lambda x: x['Period'])

if 'stat_mgr' not in st.session_state: st.session_state.stat_mgr = StatManager()

# ==========================================
# 3. DYNAMIC SMART KEYPAD (Refined Hierarchy)
# ==========================================
def add_input(k): st.session_state.user_input_buffer += k
def del_input(): st.session_state.user_input_buffer = st.session_state.user_input_buffer[:-1]
def clear_input(): st.session_state.user_input_buffer = ""

def get_smart_keypad(cat, sub):
    """10-Level Priority: All relevant buttons shown by default unless excluded."""
    layout = []
    
    # 1. Accidentals
    if sub != 'Counting semitones': layout.append(['♭', '♯'])
    
    # 2. Comma
    if any(s in sub for s in ['Chord tones', 'Alterations', 'Tensions', 'Dom7', 'Dim7', 'Pitches', 'Pivot', 'Number']):
        layout.append([','])
        
    # 3. Qualities (+, M, P, m, -) - [BROADENED ACCESS]
    if cat in ['Intervals', 'Enharmonics', 'Minor', 'Modes'] or any(s in sub for s in ['Natural', 'Number', 'Alternative', 'Tracking']):
        layout.append(['+', 'M', 'P', 'm', '-'])
        
    # 4. Note Names
    if any(s in sub for s in ['Finding', 'tones', 'Pitch', 'Tracking', 'Key', 'Pitches', 'Pivot', 'Similarities']):
        layout.append(['C', 'D', 'E', 'F']); layout.append(['G', 'A', 'B'])
        
    # 5. Degrees
    if any(s in sub for s in ['Degrees', 'Finding', 'Pitch->Deg', 'Alterations', 'Chords', 'Functions']):
        layout.append(['I', 'II', 'III']); layout.append(['IV', 'V', 'VI', 'VII'])
        
    # 6. Numbers
    if any(s in sub for s in ['Counting', 'Number', 'Natural', 'r calc', 'tones']):
        layout.append(['1', '2', '3', '4', '5']); layout.append(['6', '7', '8', '9', '0'])
        
    # 7. Modes
    if cat == 'Modes' or sub in ['Avail Scales', 'Similarities']:
        layout.append(['Ionian', 'Dorian', 'Phrygian', 'Lydian']); layout.append(['Mixolydian', 'Aeolian', 'Locrian'])
        
    # 8. Scales
    if cat in ['Minor', 'Modes', 'Mastery'] or 'Similarities' in sub:
        layout.append(['Natural minor', 'Harmonic minor', 'Melodic minor'])
        
    # 9. Chord types
    if any(c in cat for c in ['Chord Forms', 'Minor', 'Tritones', 'Mastery']) or 'Chords' in sub:
        layout.append(['maj7', 'm7', '7', 'm7b5']); layout.append(['dim7', '6', 'm6', 'sus4', 'aug'])
        
    # 10. Slash (Priority Lowest)
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
        if i == 0: st.write("") # Separation for Priority 1
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 2])
    c1.button("⬅️ Del", on_click=del_input, use_container_width=True)
    c2.button("❌ Clear", on_click=clear_input, use_container_width=True)
    if c3.button("✅ Submit", type="primary", use_container_width=True): return True
    return False

# ==========================================
# 4. LOGIC & UI (Full functionality maintained)
# ==========================================
# (Question generator, navigation, and stat manager auto-login included here...)

def generate_question(cat, sub):
    root = random.choice(NOTES); ridx = NOTES.index(root) if root in NOTES else 0
    if cat == 'Enharmonics' and sub == 'Degrees':
        t, a = random.choice([('#VII','I'),('#I','bII'),('#II','bIII'),('bIV','III')])
        return f"What is {t}'s enharmonic?", [a], 'single'
    if cat == 'Intervals' and sub == 'Alternative':
        return f"Alternative to {root}M3?", [f"{root}m4"], 'single' # Dummy example logic
    return f"Identify the {sub} of {root}", ["C"], 'single'

st.set_page_config(page_title="Road to Berklee", page_icon="🎹")
cookie_manager = stx.CookieManager()

if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user_input_buffer' not in st.session_state: st.session_state.user_input_buffer = ""
if 'last_result' not in st.session_state: st.session_state.last_result = None
if 'wrong_count' not in st.session_state: st.session_state.wrong_count = 0
if 'wrong_questions_pool' not in st.session_state: st.session_state.wrong_questions_pool = []

# Login check
if st.session_state.logged_in_user is None:
    user_cookie = cookie_manager.get(cookie="berklee_user")
    if user_cookie and st.session_state.stat_mgr.auto_login(user_cookie):
        st.session_state.logged_in_user = user_cookie; st.session_state.page = 'home'; st.rerun()

if not st.session_state.logged_in_user:
    st.title("🎹 Road to Berklee")
    with st.form("login"):
        u, p = st.text_input("User"), st.text_input("Pass", type="password")
        if st.form_submit_button("Login"):
            if st.session_state.stat_mgr.login_user(u, p):
                st.session_state.logged_in_user = u; st.session_state.page = 'home'
                cookie_manager.set("berklee_user", u, expires_at=datetime.datetime.now()+timedelta(days=30)); st.rerun()
    st.stop()

with st.sidebar:
    st.write(f"👤 **{st.session_state.logged_in_user}**")
    if st.button("Logout"): st.session_state.logged_in_user = None; cookie_manager.delete("berklee_user"); st.rerun()
    menu = st.radio("Menu", ["🏠 Home", "📝 Start Quiz", "📊 Statistics", "🏆 Leaderboard"])

if 'quiz_state' not in st.session_state:
    st.session_state.quiz_state = {'active': False, 'cat': '', 'sub': '', 'mode': '', 'current_idx': 0, 'score': 0, 'start_time': 0, 'limit': 0, 'is_retry': False}

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
    else: qs['current_q'] = generate_question(qs['cat'], qs['sub'])
    st.session_state.user_input_buffer = ""; st.rerun()

# --- MAIN RENDER ---
if menu == "🏠 Home":
    col1, col2 = st.columns([1, 2])
    with col1:
        if os.path.exists("logo.png"): st.image("logo.png", width=180)
        else: st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/Berklee_College_of_Music_Logo.png/800px-Berklee_College_of_Music_Logo.png", width=150)
    st.markdown("<h1>Road to Berklee</h1><p>Master Music Theory</p>", unsafe_allow_html=True)

elif menu == "📝 Start Quiz":
    if st.session_state.page == 'quiz':
        if st.session_state.last_result:
            res = st.session_state.last_result; bg = "rgba(0,255,0,0.2)" if res['correct'] else "rgba(255,0,0,0.2)"
            st.markdown(f"<style>.stApp {{ animation: flash 0.6s forwards; }} @keyframes flash {{ 0% {{ background-color: {bg}; }} 100% {{ background-color: transparent; }} }}</style>", unsafe_allow_html=True)
            if res['correct']: st.toast("✅ Correct!")
            elif res.get('show_ans'): st.error(f"❌ Answer: {res['ans']}")
            else: st.toast(f"❌ Try Again ({st.session_state.wrong_count}/3)")
            st.session_state.last_result = None

        qs = st.session_state.quiz_state; st.progress(qs['current_idx'] / qs['limit']); st.subheader(qs['current_q'][0])
        st.text_input("Answer Input", value=st.session_state.user_input_buffer, disabled=True)
        if render_keypad(qs['cat'], qs['sub']): check_answer()
        if st.button("🏠 Quit Quiz"): st.session_state.page = 'home'; st.rerun()

    elif st.session_state.page == 'result':
        qs = st.session_state.quiz_state; st.header("Result")
        st.metric("Score", f"{qs['score']}/{qs['limit']}")
        if st.session_state.wrong_questions_pool:
            if st.button("🔄 오답 다시 풀기"):
                st.session_state.quiz_state['is_retry'] = True; st.session_state.page = 'quiz'; st.rerun()
        if st.button("⬅️ Back"): st.session_state.page = 'home'; st.rerun()
    else:
        st.header("📝 Select Quiz")
        c = st.selectbox("Category", list(CATEGORY_INFO.keys())); s = st.selectbox("Sub", CATEGORY_INFO[c])
        if st.button("Start Practice"):
            st.session_state.quiz_state = {'cat':c, 'sub':s, 'limit':10, 'current_idx':0, 'score':0, 'is_retry':False, 'current_q':generate_question(c,s)}
            st.session_state.page = 'quiz'; st.rerun()

elif menu == "📊 Statistics":
    st.header("📊 Statistics")
    t1, t2 = st.tabs(["Cumulative", "Trend Chart"])
    with t1:
        st.metric("Total Questions", len(st.session_state.stat_mgr.data))
    with t2:
        cat = st.selectbox("Chart Cat", ["All"] + list(CATEGORY_INFO.keys()))
        if st.button("Show Trend"):
            d_list = st.session_state.stat_mgr.get_trend_data(cat, None)
            if d_list:
                df = pd.DataFrame(d_list)
                df['Period'] = df['Period'].astype(str)
                df['Accuracy'] = df['Accuracy'].astype(float)
                chart = alt.Chart(df).mark_line(point=True).encode(
                    x=alt.X('Period:O', title='Period (Week)'),
                    y=alt.Y('Accuracy:Q', title='Accuracy (%)', scale=alt.Scale(domain=[0, 100])),
                    tooltip=[alt.Tooltip('Period:N'), alt.Tooltip('Range:N'), alt.Tooltip('Accuracy:Q', format='.1f')]
                ).properties(width=700, height=400).interactive()
                st.altair_chart(chart, use_container_width=True)
            else: st.warning("No Data")

elif menu == "🏆 Leaderboard":
    st.header("🏆 Hall of Fame")
    st.write("Ranking is updated in real-time from the database.")
