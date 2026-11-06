"""
Zyren - Premium Personal AI Assistant
A world-class, minimal, futuristic AI interface inspired by ChatGPT, Claude, and Gemini.
Engineered with Streamlit, Python, and the Google Gemini API.
"""

import os
import re
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from config import APP_NAME, APP_SUBTITLE, PROVIDERS_CONFIG, DEFAULT_PROVIDER, BASE_DIR
import database as db
import ai_engine

# --- Page Configuration ---
st.set_page_config(
    page_title="Zyren - Personal AI Assistant",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Load External CSS & Inject Advanced Theme ---
css_path = BASE_DIR / "assets" / "style.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- Browser Clipboard & Speech Synthesis Components ---
def copy_to_clipboard(text: str):
    """Executes a silent browser clipboard copy via JS component."""
    safe_text = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    js_code = f"""
    <script>
    navigator.clipboard.writeText(`{safe_text}`);
    </script>
    """
    components.html(js_code, height=0, width=0)

def render_speech_synthesizer(text: str):
    """
    Utilizes browser's native window.speechSynthesis API.
    Cleans markdown and code blocks for fluid voice playback.
    """
    clean_narration = re.sub(r'```[\s\S]*?```', ' [Code block omitted for voice playback] ', text)
    clean_narration = re.sub(r'[#*`_~]', '', clean_narration)
    safe_text = clean_narration.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$").replace("\n", " ").strip()
    
    if len(safe_text) > 850:
        safe_text = safe_text[:850] + "..."

    js_code = f"""
    <script>
    (function() {{
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            var utterance = new SpeechSynthesisUtterance(`{safe_text}`);
            utterance.rate = 1.05;
            utterance.pitch = 1.0;
            window.speechSynthesis.speak(utterance);
        }}
    }})();
    </script>
    """
    components.html(js_code, height=0, width=0)

# --- Session State Initialization ---
if "current_conv_id" not in st.session_state:
    conversations = db.get_conversations()
    if conversations:
        st.session_state.current_conv_id = conversations[0]["id"]
    else:
        st.session_state.current_conv_id = db.create_conversation("New Chat")

if "tts_text_to_speak" not in st.session_state:
    st.session_state.tts_text_to_speak = None

if "copied_text" not in st.session_state:
    st.session_state.copied_text = None

if "feedback_state" not in st.session_state:
    st.session_state.feedback_state = {}

if "attached_file_content" not in st.session_state:
    st.session_state.attached_file_content = None

if "attached_file_name" not in st.session_state:
    st.session_state.attached_file_name = None

# Ensure active conversation is valid
active_conv = db.get_conversation(st.session_state.current_conv_id)
if not active_conv:
    st.session_state.current_conv_id = db.create_conversation("New Chat")
    active_conv = db.get_conversation(st.session_state.current_conv_id)

# --- Trigger Background Helper Actions ---
if st.session_state.tts_text_to_speak:
    render_speech_synthesizer(st.session_state.tts_text_to_speak)
    st.session_state.tts_text_to_speak = None

if st.session_state.copied_text:
    copy_to_clipboard(st.session_state.copied_text)
    st.session_state.copied_text = None

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    # 1. Branding
    st.markdown("""
    <div class="zyren-brand-container">
        <span class="zyren-logo-icon">✨</span>
        <div>
            <div class="zyren-brand-text">Zyren</div>
            <div class="zyren-brand-sub">Intelligence • Reasoning • Code</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. New Chat Button
    st.markdown('<div class="new-chat-btn-wrapper">', unsafe_allow_html=True)
    if st.button("➕  New Chat", use_container_width=True, type="primary"):
        new_id = db.create_conversation("New Chat")
        st.session_state.current_conv_id = new_id
        st.session_state.tts_text_to_speak = None
        st.session_state.attached_file_content = None
        st.session_state.attached_file_name = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 0.6rem;'></div>", unsafe_allow_html=True)

    # 3. Search Conversations Input
    search_query = st.text_input(
        "Search conversations",
        placeholder="🔍 Search past chats...",
        label_visibility="collapsed"
    )

    # 4. Conversations List
    if search_query.strip():
        conversations = db.search_conversations(search_query.strip())
        st.caption(f"Found {len(conversations)} matching conversations")
    else:
        conversations = db.get_conversations()

    st.markdown("<div style='margin-bottom: 0.2rem;'></div>", unsafe_allow_html=True)
    
    if not conversations:
        st.caption("No conversations found.")
    else:
        for conv in conversations:
            is_active = conv["id"] == st.session_state.current_conv_id
            col1, col2 = st.columns([5, 1])
            with col1:
                label = f"{'● ' if is_active else ''}{conv['title']}"
                if st.button(label, key=f"conv_{conv['id']}", use_container_width=True):
                    st.session_state.current_conv_id = conv["id"]
                    st.session_state.tts_text_to_speak = None
                    st.session_state.attached_file_content = None
                    st.session_state.attached_file_name = None
                    st.rerun()
            with col2:
                if st.button("✕", key=f"del_{conv['id']}", help="Delete chat"):
                    db.delete_conversation(conv["id"])
                    if is_active:
                        remaining = db.get_conversations()
                        st.session_state.current_conv_id = remaining[0]["id"] if remaining else db.create_conversation("New Chat")
                    st.rerun()

    st.markdown("---")

    # 5. Persistent Long-Term Memory (Persistent Brain)
    memories = db.get_all_memories()
    with st.expander(f"🧠 Persistent Memory ({len(memories)})", expanded=False):
        st.caption("Facts Zyren persistently remembers across all chats:")
        if memories:
            for mem in memories:
                m_col1, m_col2 = st.columns([5, 1])
                with m_col1:
                    st.markdown(f"• {mem['fact']}")
                with m_col2:
                    if st.button("✕", key=f"mem_del_{mem['id']}", help="Delete memory"):
                        db.delete_memory(mem["id"])
                        st.rerun()
            if st.button("Clear All Memories", use_container_width=True):
                db.clear_all_memories()
                st.rerun()
        else:
            st.caption("No memories yet. Say *'Remember that I like Python'* in chat!")

        with st.form("add_memory_form", clear_on_submit=True):
            new_mem = st.text_input("Add memory manually:", placeholder="e.g. My timezone is EST")
            if st.form_submit_button("Save Memory", use_container_width=True):
                if new_mem.strip():
                    db.add_memory(new_mem.strip())
                    st.success("Saved!")
                    st.rerun()

    # 6. User Profile & Settings (Bottom of Sidebar)
    with st.popover("⚙️  Profile & Settings", use_container_width=True):
        st.markdown("#### 👤 Zyren User Settings")
        st.caption("Zyren Pro Plan • Active Session")
        st.markdown("---")

        provider_keys = list(PROVIDERS_CONFIG.keys())
        provider_labels = {k: PROVIDERS_CONFIG[k]["name"] for k in provider_keys}

        default_p_idx = provider_keys.index(DEFAULT_PROVIDER) if DEFAULT_PROVIDER in provider_keys else 0
        selected_provider = st.selectbox(
            "AI Processing Engine",
            options=provider_keys,
            format_func=lambda k: provider_labels.get(k, k),
            index=default_p_idx
        )

        curr_prov = PROVIDERS_CONFIG[selected_provider]

        model_options = [m["id"] for m in curr_prov["models"]]
        model_labels = {m["id"]: m["name"] for m in curr_prov["models"]}
        selected_model = st.selectbox(
            "Model Tier",
            options=model_options,
            format_func=lambda x: model_labels.get(x, x),
            index=0
        )

        enable_search = st.toggle(
            "🌐 Live Web Search",
            value=True,
            help="Allow Zyren to search the web for latest real-world info."
        )

        enable_tts = st.toggle(
            "🔊 Auto Read Aloud (TTS)",
            value=False,
            help="Speak assistant answers automatically."
        )

        st.markdown("---")
        
        # Clear all chats option
        if st.button("🗑️ Clear All Chat History", use_container_width=True):
            db.clear_all_conversations()
            st.session_state.current_conv_id = db.create_conversation("New Chat")
            st.rerun()

        # Advanced Key Settings (Concealed)
        with st.expander("🔒 Advanced Key Configuration", expanded=False):
            env_var_name = curr_prov["env_key"]
            custom_key = None
            if env_var_name:
                loaded_key = os.getenv(env_var_name, "").strip()
                if loaded_key and not loaded_key.startswith("your_"):
                    st.success("✅ System Key: Active & Authenticated")
                else:
                    st.warning("⚠️ No key active in environment")
                    custom_key = st.text_input(
                        "Session Key:",
                        type="password",
                        placeholder="Paste key...",
                        help="Stored strictly in memory."
                    )
            else:
                st.info("Runs fully offline without keys.")

# ==============================================================================
# MAIN CHAT INTERFACE
# ==============================================================================

# Fetch messages for current conversation
messages = db.get_messages(st.session_state.current_conv_id)
current_title = active_conv["title"] if active_conv else "New Chat"

# 1. Top Navigation Bar (Header)
col_nav_left, col_nav_right = st.columns([5, 5])

with col_nav_left:
    title_col1, title_col2 = st.columns([4, 1])
    with title_col1:
        st.markdown(f"<h3 style='margin: 0; padding-top: 0.15rem; font-weight: 700; font-size: 1.35rem;'>{current_title}</h3>", unsafe_allow_html=True)
    with title_col2:
        with st.popover("✏️", help="Rename chat"):
            new_title = st.text_input("New Title", value=current_title)
            if st.button("Save", key="save_title_btn"):
                if new_title.strip():
                    db.update_conversation_title(st.session_state.current_conv_id, new_title.strip())
                    st.rerun()

with col_nav_right:
    export_md = f"# {current_title}\n\n*Exported from Zyren AI Assistant*\n\n---\n\n"
    for m in messages:
        speaker = "🧑‍💻 User" if m["role"] == "user" else "✨ Zyren"
        export_md += f"### {speaker}\n\n{m['content']}\n\n---\n\n"

    btn1, btn2, btn3 = st.columns([2, 1, 3])
    with btn1:
        if messages:
            st.download_button(
                "📥 Export",
                data=export_md,
                file_name=f"{current_title.replace(' ', '_')}.md",
                mime="text/markdown",
                help="Download conversation as Markdown"
            )
    with btn2:
        if messages:
            if st.button("🧹", help="Clear messages in this chat"):
                db.clear_conversation_messages(st.session_state.current_conv_id)
                st.rerun()
    with btn3:
        model_display_name = model_labels.get(selected_model, "Zyren 3.5 Flash")
        short_name = model_display_name.split("(")[0].strip()
        st.markdown(f"<div style='text-align: right; padding-top: 0.2rem;'><span class='zyren-model-pill'>✨ {short_name}</span></div>", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

# 2. Welcome Screen with 4 Suggestion Cards (Empty State)
if not messages:
    st.markdown("""
    <div class="hero-container">
        <div class="hero-sparkle">✨</div>
        <h1 class="hero-title">How can Zyren help you today?</h1>
        <p class="hero-subtitle">Your intelligent personal AI assistant.</p>
    </div>
    """, unsafe_allow_html=True)

    # Four Attractive Cards Grid (Section 5 Requirement)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        <div style="margin-bottom: 0.6rem;">
            <div style="font-size: 0.82rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Knowledge & Analysis</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(
            "🔍 Explain anything\n\nExplain quantum computing using an everyday analogy",
            key="card_explain",
            use_container_width=True
        ):
            st.session_state["starter_prompt"] = "Explain quantum computing simply using an everyday analogy."
            st.rerun()

        if st.button(
            "💻 Debug code\n\nAnalyze and optimize a Python algorithm for maximum speed",
            key="card_debug",
            use_container_width=True
        ):
            st.session_state["starter_prompt"] = "Can you help me analyze, debug, and optimize a Python algorithm for maximum performance?"
            st.rerun()

    with c2:
        st.markdown("""
        <div style="margin-bottom: 0.6rem;">
            <div style="font-size: 0.82rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Writing & Discovery</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(
            "✍️ Write anything\n\nDraft an executive summary weekly project update email",
            key="card_write",
            use_container_width=True
        ):
            st.session_state["starter_prompt"] = "Draft a professional executive summary weekly project update email."
            st.rerun()

        if st.button(
            "🚀 Learn something new\n\nTeach me how modern transformer models work step-by-step",
            key="card_learn",
            use_container_width=True
        ):
            st.session_state["starter_prompt"] = "Teach me how modern transformer neural networks and attention mechanisms work step-by-step."
            st.rerun()

# 3. Message Display Loop
for idx, msg in enumerate(messages):
    is_user = msg["role"] == "user"
    with st.chat_message(msg["role"], avatar="🧑‍💻" if is_user else "✨"):
        st.markdown(msg["content"])
        
        # Assistant Message Actions Toolbar (TTS, Copy, Thumbs Up/Down, Regenerate)
        if not is_user:
            t1, t2, t3, t4, t5, _ = st.columns([1, 1, 1, 1, 1.3, 7])
            with t1:
                if st.button("🔊", key=f"speak_{msg['id']}", help="Read aloud"):
                    st.session_state.tts_text_to_speak = msg["content"]
                    st.rerun()
            with t2:
                if st.button("📋", key=f"copy_{msg['id']}", help="Copy response"):
                    st.session_state.copied_text = msg["content"]
                    st.toast("Copied to clipboard! 📋")
            with t3:
                # Thumbs Up Feedback
                is_liked = st.session_state.feedback_state.get(msg["id"]) == "up"
                if st.button("👍" if not is_liked else "✅", key=f"thumbup_{msg['id']}", help="Helpful response"):
                    st.session_state.feedback_state[msg["id"]] = "up"
                    st.toast("Thank you for your feedback! 👍")
                    st.rerun()
            with t4:
                # Thumbs Down Feedback
                is_disliked = st.session_state.feedback_state.get(msg["id"]) == "down"
                if st.button("👎" if not is_disliked else "❌", key=f"thumbdown_{msg['id']}", help="Not helpful"):
                    st.session_state.feedback_state[msg["id"]] = "down"
                    st.toast("Feedback recorded. We'll improve! 👎")
                    st.rerun()
            with t5:
                # Regenerate button (on the last assistant message)
                if idx == len(messages) - 1:
                    if st.button("🔄 Retry", key=f"regen_{msg['id']}", help="Regenerate this answer"):
                        db.delete_message(msg["id"])
                        user_history = [m for m in messages if m["role"] == "user"]
                        if user_history:
                            last_user = user_history[-1]
                            st.session_state["starter_prompt"] = last_user["content"]
                            db.delete_message(last_user["id"])
                        st.rerun()

# 4. Attachments Drawer (File Attachment + Voice Input)
with st.expander("📎 Attach Document / 🎙️ Voice Input Mode", expanded=False):
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        st.markdown("**📎 Attach Code or Document**")
        uploaded_file = st.file_uploader(
            "Upload code or text file",
            type=["py", "js", "ts", "txt", "md", "json", "csv", "html", "css", "sql", "cpp", "rs", "java"],
            label_visibility="collapsed"
        )
        if uploaded_file is not None:
            try:
                file_text = uploaded_file.read().decode("utf-8")
                st.session_state.attached_file_content = file_text
                st.session_state.attached_file_name = uploaded_file.name
                st.success(f"Attached: `{uploaded_file.name}` ({len(file_text.splitlines())} lines)")
            except Exception as e:
                st.error(f"Could not read file: {e}")

    with t_col2:
        st.markdown("**🎙️ Record Voice Query**")
        audio_record = st.audio_input("Record your voice", label_visibility="collapsed")
        if audio_record is not None:
            audio_bytes = audio_record.read()
            if audio_bytes:
                with st.spinner("Transcribing speech..."):
                    transcription = ai_engine.transcribe_audio_input(audio_bytes)
                    if transcription["success"]:
                        st.success(f"Transcribed: \"{transcription['text']}\"")
                        if st.button("Send Transcribed Query", key="send_audio_btn", type="primary"):
                            st.session_state["starter_prompt"] = transcription["text"]
                            st.rerun()
                    else:
                        st.error(transcription["error"])

# 5. Quick Action Pills (Floating above composer)
st.markdown("<div style='margin-top: 0.8rem;'></div>", unsafe_allow_html=True)
p1, p2, p3, p4 = st.columns(4)
with p1:
    if st.button("⚡ Summarize", use_container_width=True, help="Summarize main points"):
        st.session_state["starter_prompt"] = "Please summarize our discussion so far into key bullet points."
        st.rerun()
with p2:
    if st.button("💻 Debug Code", use_container_width=True, help="Analyze and fix code"):
        st.session_state["starter_prompt"] = "Can you help me analyze, debug, and fix this code:"
        st.rerun()
with p3:
    if st.button("📝 Explain Simply", use_container_width=True, help="Explain with analogies"):
        st.session_state["starter_prompt"] = "Explain this concept in simple terms with a practical example:"
        st.rerun()
with p4:
    if st.button("🌐 Web Search", use_container_width=True, help="Search live internet"):
        st.session_state["starter_prompt"] = "Search the web for the latest news and updates on:"
        st.rerun()

# 6. Message Composer (Chat Input)
starter_input = st.session_state.pop("starter_prompt", None)
chat_input_text = st.chat_input("Ask Zyren anything (or say 'Remember that...')...")

user_prompt = starter_input or chat_input_text

if user_prompt:
    prompt_str = user_prompt.strip()

    # Prepend any attached document content
    if st.session_state.attached_file_content:
        prompt_str = (
            f"📎 [Attached File: `{st.session_state.attached_file_name}`]\n"
            f"```\n{st.session_state.attached_file_content}\n```\n\n"
            f"{prompt_str}"
        )
        st.session_state.attached_file_content = None
        st.session_state.attached_file_name = None

    # Check for memory storage command
    memory_fact = ai_engine.detect_memory_command(prompt_str)
    memory_notice = ""
    if memory_fact:
        saved = db.add_memory(memory_fact)
        if saved:
            memory_notice = f"*(I have saved this to my persistent memory: \"{memory_fact}\")*\n\n"

    # Save user message to database
    db.add_message(st.session_state.current_conv_id, "user", prompt_str)

    # Auto-update conversation title if it's the first message
    if active_conv and (active_conv["title"] == "New Chat" or not messages):
        new_title = prompt_str[:32] + ("..." if len(prompt_str) > 32 else "")
        db.update_conversation_title(st.session_state.current_conv_id, new_title)

    # Display user message in UI
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt_str)

    # Generate assistant streaming response
    with st.chat_message("assistant", avatar="✨"):
        all_memories = [m["fact"] for m in db.get_all_memories()]
        history_msgs = db.get_messages(st.session_state.current_conv_id)[:-1]

        generator = ai_engine.stream_chat_response(
            history=history_msgs,
            user_prompt=prompt_str,
            provider=selected_provider,
            model=selected_model,
            enable_search=enable_search,
            memories=all_memories,
            api_key=custom_key
        )

        if memory_notice:
            st.info(f"🧠 Learned: {memory_fact}")

        full_response_text = st.write_stream(generator)

    # Save assistant response to DB
    if full_response_text:
        db.add_message(st.session_state.current_conv_id, "assistant", full_response_text)
        
        if enable_tts:
            st.session_state.tts_text_to_speak = full_response_text
            st.rerun()
