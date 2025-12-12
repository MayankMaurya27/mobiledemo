# n.py (voice-enabled version)
import streamlit as st
import pandas as pd
import datetime
from groq import Groq
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import bcrypt
import os
from audio_recorder_streamlit import audio_recorder
# utils.py should provide: speech_to_text, text_to_speech, autoplay_audio
from utils import speech_to_text, text_to_speech, autoplay_audio

# Connect to Google Sheet
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["service_account"], scope)
client_gs = gspread.authorize(creds)

sheet = client_gs.open("mindcare_users").sheet1

# ---- ✅ ADD THE TWO FUNCTIONS HERE ----

def register_user(username, email, password):
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    existing_users = sheet.col_values(1)
    if username in existing_users:
        return False, "Username already exists."
    sheet.append_row([username, email, password_hash])
    return True, "Account created successfully!"

def login_user(username, password):
    users = sheet.get_all_records()
    for user in users:
        # adjust column names depending on your sheet headers
        # assume sheet columns: username, email, password_hash
        if user.get("username") == username:
            if bcrypt.checkpw(password.encode(), user.get("password_hash").encode()):
                return True
    return False

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------- LOAD API KEY ----------
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

SYSTEM_PROMPT = """
You are a gentle, warm mental health support companion.
Your goal is to:
• Comfort the user
• Help them express feelings safely
• Suggest healthy coping strategies
• Support emotional well-being

Do NOT interrogate the user. Do NOT ask too many questions.
Speak in short, soft, supportive responses.

NEVER attempt to diagnose mental illness or mention clinical terms.
You are NOT a doctor.

If the user talks about:
• Stress
• Anxiety
• Sadness
• Overthinking
• Depression feelings
• Self-esteem issues
• Relationships
• Loneliness
• Motivation
• Joy
• Passion
• Goodness
• Kindness
• Love

→ Respond with emotional support, empathy, grounding advice, and reassurance.

If the user asks anything NOT related to emotional or mental well-being
(e.g., programming, homework, sex tips, medical advice, politics, finance, math):

→ Respond with:
"I'm here only to support emotional and mental well-being. If you want to share how you're feeling, I'm here with you. 💛"
"""

MODEL_NAME = "llama-3.1-8b-instant"

# ---------- MEMORY ----------
def update_memory(history, current_memory):
    if len(history) < 6 or len(history) % 4 != 0:
        return current_memory

    recent = history[-6:]
    convo_text = "\n".join([f"{m['role']}: {m['content']}" for m in recent])

    summary_prompt = f"""
Summarize emotional tone only. Keep gentle and short.

Current memory:
{current_memory}

Conversation:
{convo_text}
"""

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": summary_prompt}]
    )

    return completion.choices[0].message.content.strip()

# ---------- UI CONFIG ----------
st.set_page_config(
    page_title="MindCare Companion",
    page_icon="💛",
    layout="wide",
    initial_sidebar_state="auto"
)

st.markdown(""" ... (your custom CSS here) ... """, unsafe_allow_html=True)  # keep your existing CSS blocks

st.markdown("<h1 class='big-title'>💛 MindCare Companion</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Here to support you gently, one conversation at a time.</p>", unsafe_allow_html=True)

# ---------- SESSION ----------
if "memory" not in st.session_state:
    st.session_state.memory = "The user may be sharing emotional thoughts."

if "history" not in st.session_state:
    st.session_state.history = [
        {"role": "assistant", "content": "Hey, I'm here with you. What’s on your mind?"}
    ]

# ---------------------------- SIDEBAR (accounts, nav) ----------------------------
if "username" not in st.session_state:
    st.session_state.username = None

with st.sidebar:
    st.title("Account")
    if st.session_state.logged_in:
        st.success(f"Logged in as {st.session_state.username}")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()
    else:
        account_action = st.selectbox("Choose", ["Continue as Guest", "Login", "Sign Up"])
        if account_action == "Login":
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                if login_user(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid login!")
        elif account_action == "Sign Up":
            st.subheader("Create Account")
            username = st.text_input("Create Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.button("Sign Up"):
                ok, msg = register_user(username, email, password)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

with st.sidebar:
    st.title("Menu")
    page = st.radio("Navigate", ["💬 Chat", "📝 Mood Journal", "📊 Dashboard", "🧘 Coping Tools"])

# =========================================================
#                         CHAT (voice-enabled)
# =========================================================
if page == "💬 Chat":
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Talk to me")

    # show conversation
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # text input (existing)
    user_input = st.chat_input("Share whatever you're feeling...")

    # voice recording container (footer-style)
    footer_container = st.container()
    with footer_container:
        audio_bytes = audio_recorder()  # returns bytes if user recorded

    # If user typed text
    if user_input:
        st.session_state.history.append({"role": "user", "content": user_input})
        st.session_state.memory = update_memory(st.session_state.history, st.session_state.memory)

        # topic check
        check_prompt = f"""
Classify the topic of this message:

"{user_input}"

If the message expresses or discusses:
• feelings
• emotions
• mood
• joy
• sadness
• anxiety
• stress
• motivation
• love
• loneliness
• self-worth
• relationships
• personal reflection
• mental state

→ Reply: MENTAL

If the message is about:
• programming
• math/homework
• politics/news
• finance
• medical or health diagnosis
• sexual instructions
• technical knowledge questions

→ Reply: OTHER

Return only one word: MENTAL or OTHER.
"""

        check = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": check_prompt}]
        ).choices[0].message.content.strip()

        if check != "MENTAL":
            reply = "I'm here only to help with emotional and mental well-being. If you want to share your feelings, I'm here with you. 💛"
        else:
            prompt = f"""
{SYSTEM_PROMPT}

Memory:
{st.session_state.memory}

User: {user_input}
Assistant:
"""
            reply = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}]
            ).choices[0].message.content.strip()

        st.session_state.history.append({"role": "assistant", "content": reply})

        with st.chat_message("assistant"):
            st.write(reply)

        # generate audio response and autoplay
        try:
            with st.spinner("Generating audio response..."):
                audio_file = text_to_speech(reply)  # from utils
                autoplay_audio(audio_file)          # from utils: streamlit-friendly player
                # remove generated audio after playing
                try:
                    os.remove(audio_file)
                except:
                    pass
        except Exception as e:
            # don't break chat if TTS fails
            st.warning("Audio response unavailable.")

    # If user recorded voice
    if audio_bytes:
        # save bytes to a temp file (mp3/webm depending on recorder output)
        tmp_path = "temp_audio.webm"
        try:
            with open(tmp_path, "wb") as f:
                f.write(audio_bytes)

            with st.spinner("Transcribing..."):
                transcript = speech_to_text(tmp_path)  # from utils
            if transcript:
                # display user message and continue flow exactly like text input
                st.session_state.history.append({"role": "user", "content": transcript})
                with st.chat_message("user"):
                    st.write(transcript)

                st.session_state.memory = update_memory(st.session_state.history, st.session_state.memory)

                # Topic check & response generation (same as above)
                check_prompt = f"""
Classify the topic of this message:

"{transcript}"

If the message expresses or discusses:
• feelings
• emotions
• mood
• joy
• sadness
• anxiety
• stress
• motivation
• love
• loneliness
• self-worth
• relationships
• personal reflection
• mental state

→ Reply: MENTAL

If the message is about:
• programming
• math/homework
• politics/news
• finance
• medical or health diagnosis
• sexual instructions
• technical knowledge questions

→ Reply: OTHER

Return only one word: MENTAL or OTHER.
"""

                check = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": check_prompt}]
                ).choices[0].message.content.strip()

                if check != "MENTAL":
                    reply = "I'm here only to help with emotional and mental well-being. If you want to share your feelings, I'm here with you. 💛"
                else:
                    prompt = f"""
{SYSTEM_PROMPT}

Memory:
{st.session_state.memory}

User: {transcript}
Assistant:
"""
                    reply = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[{"role": "user", "content": prompt}]
                    ).choices[0].message.content.strip()

                st.session_state.history.append({"role": "assistant", "content": reply})

                with st.chat_message("assistant"):
                    st.write(reply)

                # TTS + autoplay
                try:
                    with st.spinner("Generating audio response..."):
                        audio_file = text_to_speech(reply)
                        autoplay_audio(audio_file)
                        try:
                            os.remove(audio_file)
                        except:
                            pass
                except Exception as e:
                    st.warning("Audio response unavailable.")
        finally:
            # cleanup temp upload
            try:
                os.remove(tmp_path)
            except:
                pass

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
#                     MOOD JOURNAL
# =========================================================
elif page == "📝 Mood Journal":
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("How are you feeling today?")

    moods = {"😄 Very Good": 5, "🙂 Good": 4, "😐 Okay": 3, "☹️ Bad": 2, "😢 Very Bad": 1}
    mood = st.selectbox("Select mood:", list(moods.keys()))
    note = st.text_area("Anything you want to express? (optional)")

    if st.button("Save"):
        entry = {"date": datetime.date.today().isoformat(), "mood": moods[mood], "note": note}
        try:
            df = pd.read_csv("journal.csv")
            df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
        except:
            df = pd.DataFrame([entry])
        df.to_csv("journal.csv", index=False)
        st.success("Saved 💛")

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
#                     DASHBOARD
# =========================================================
elif page == "📊 Dashboard":
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Your Mood Trend")

    try:
        df = pd.read_csv("journal.csv")
        df = df.set_index("date")
        st.line_chart(df["mood"])
        st.write(df)
    except:
        st.info("No entries yet. Add some from Mood Journal.")

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
#                     COPING TOOLS
# =========================================================
elif page == "🧘 Coping Tools":
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Grounding Exercises")

    st.write("### 4-6 Breathing")
    st.write("Inhale 4 seconds, exhale 6 seconds. Slow. Calm.")

    st.write("---")
    st.write("### 5-4-3-2-1 Grounding")
    st.write("""
5 things you can see  
4 things you can touch  
3 things you can hear  
2 things you can smell  
1 thing you feel inside  
""")
    st.markdown("</div>", unsafe_allow_html=True)
