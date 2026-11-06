"""
Zyren - Next-Generation AI Assistant
A modern, Claude- and ChatGPT-inspired AI assistant with live streaming,
persistent memory, voice transcription, text-to-speech, and web search.
"""

import os
import streamlit as st
import streamlit.components.v1 as components
from config import APP_NAME, APP_SUBTITLE, PROVIDERS_CONFIG, DEFAULT_PROVIDER
import database as db
import ai_engine

# --- Page Configuration ---
st.set_page_config(
    page_title="Zyren - Next-Gen AI Assistant",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling (ChatGPT / Claude / Gemini Aesthetic) ---
st.markdown("""
<style>
    /* Google Inter font styling */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Modern sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #111317;
        border-right: 1px solid rgba(255, 255, 255, 0.07);
    }
    
    /* Clean sidebar typography */
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #f1f5f9;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    /* New Chat Button (ChatGPT & Claude Style) */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb, #3b82f6);
        color: #ffffff;
        border: none;
        border-radius: 12px;
        padding: 0.65rem 1.1rem;
        font-weight: 600;
        letter-spacing: 0.2px;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1d4ed8, #2563eb);
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
        transform: translateY(-1px);
    }

    /* Secondary buttons */
    .stButton > button:not([kind="primary"]) {
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(255, 255, 255, 0.04);
        transition: all 0.15s ease;
    }
    .stButton > button:not([kind="primary"]):hover {
        background: rgba(255, 255, 255, 0.09);
        border-color: rgba(255, 255, 255, 0.2);
    }
    
    /* Message bubble styling */
    [data-testid="stChatMessage"] {
        border-radius: 16px;
        padding: 1.15rem 1.35rem;
        margin-bottom: 0.85rem;
        border: 1px solid rgba(255, 255, 255, 0.06);
        background-color: rgba(255, 255, 255, 0.02);
    }
    
    /* Model Badge Pill */
    .zyren-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        background: linear-gradient(135deg, rgba(37, 99, 235, 0.15), rgba(147, 51, 234, 0.15));
        color: #60a5fa;
        border: 1px solid rgba(96, 165, 250, 0.3);
    }

    /* Quick Action Pills */
    .quick-pill button {
        border-radius: 24px !important;
        font-size: 0.82rem !important;
        padding: 0.4rem 0.8rem !important;
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    .quick-pill button:hover {
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
    }
    
    /* Clean chat header */
    .chat-header-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 0.75rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* User Profile Pill at bottom of sidebar */
    .user-profile-box {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.6rem 0.8rem;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.07);
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Browser Text-To-Speech (TTS) Component ---
def render_speech_synthesizer(text: str, trigger_id: str):
    """
    Renders a hidden script utilizing the browser's native window.speechSynthesis.
    Cleans code blocks and markdown symbols for natural, smooth narration.
    """
    import re
    # Remove code blocks so TTS doesn't read out syntax verbatim
    clean_narration = re.sub(r'```[\s\S]*?```', ' [Code block omitted for voice playback] ', text)
    # Remove markdown headers and emphasis symbols
    clean_narration = re.sub(r'[#*`_~]', '', clean_narration)
    # Sanitize for JS template literal
    safe_text = clean_narration.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$").replace("\n", " ").strip()
    
    if len(safe_text) > 800:
        safe_text = safe_text[:800] + "..."

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

if "last_transcribed_text" not in st.session_state:
    st.session_state.last_transcribed_text = ""

# Ensure active conversation is valid
active_conv = db.get_conversation(st.session_state.current_conv_id)
if not active_conv:
    st.session_state.current_conv_id = db.create_conversation("New Chat")
    active_conv = db.get_conversation(st.session_state.current_conv_id)

# --- Sidebar ---
with st.sidebar:
    # Sleek Zyren Branding
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-top: -10px; margin-bottom: 2px;">
        <span style="font-size: 26px;">✨</span>
        <span style="font-size: 24px; font-weight: 800; color: #f8fafc; letter-spacing: -0.5px;">Zyren</span>
    </div>
    <div style="font-size: 12px; color: #94a3b8; margin-bottom: 14px;">Next-Gen AI Assistant</div>
    """, unsafe_allow_html=True)

    # New Chat Button
    if st.button("➕  New Chat", use_container_width=True, type="primary"):
        new_id = db.create_conversation("New Chat")
        st.session_state.current_conv_id = new_id
        st.session_state.tts_text_to_speak = None
        st.rerun()

    st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)

    # --- Conversation History List ---
    st.markdown("##### 💬 Chats")
    conversations = db.get_conversations()
    if not conversations:
        st.caption("No conversations yet. Start chatting!")
    else:
        for conv in conversations:
            is_active = conv["id"] == st.session_state.current_conv_id
            col1, col2 = st.columns([5, 1])
            with col1:
                label = f"{'● ' if is_active else ''}{conv['title']}"
                if st.button(label, key=f"conv_{conv['id']}", use_container_width=True):
                    st.session_state.current_conv_id = conv["id"]
                    st.session_state.tts_text_to_speak = None
                    st.rerun()
            with col2:
                if st.button("✕", key=f"del_{conv['id']}", help="Delete chat"):
                    db.delete_conversation(conv["id"])
                    if is_active:
                        remaining = db.get_conversations()
                        st.session_state.current_conv_id = remaining[0]["id"] if remaining else db.create_conversation("New Chat")
                    st.rerun()

    st.markdown("---")

    # --- Long-Term Memory (Persistent Brain) ---
    with st.expander("🧠 Persistent Memory", expanded=False):
        st.caption("Facts Zyren remembers across all sessions:")
        memories = db.get_all_memories()
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

    # --- COVERED / HIDDEN SETTINGS & PROFILE (Bottom of Sidebar like Claude & ChatGPT) ---
    with st.popover("⚙️  Profile & Settings", use_container_width=True):
        st.markdown("#### ⚙️ Zyren System Preferences")

        # Provider Selector (Names masked to look sleek and proprietary)
        provider_keys = list(PROVIDERS_CONFIG.keys())
        provider_labels = {k: PROVIDERS_CONFIG[k]["name"] for k in provider_keys}

        default_p_idx = provider_keys.index(DEFAULT_PROVIDER) if DEFAULT_PROVIDER in provider_keys else 0
        selected_provider = st.selectbox(
            "Core Engine",
            options=provider_keys,
            format_func=lambda k: provider_labels.get(k, k),
            index=default_p_idx,
            help="Select the AI processing engine."
        )

        curr_prov = PROVIDERS_CONFIG[selected_provider]

        # Model Selector for chosen provider
        model_options = [m["id"] for m in curr_prov["models"]]
        model_labels = {m["id"]: m["name"] for m in curr_prov["models"]}
        selected_model = st.selectbox(
            "Zyren Model Tier",
            options=model_options,
            format_func=lambda x: model_labels.get(x, x),
            index=0,
            help="Choose model capability tier."
        )

        # Web Search Toggle
        enable_search = st.toggle(
            "🌐 Live Web Search",
            value=True,
            help="Allow Zyren to retrieve current internet information."
        )

        # Auto Text-To-Speech Toggle
        enable_tts = st.toggle(
            "🔊 Auto Read Aloud (TTS)",
            value=False,
            help="Read answers out loud automatically."
        )

        # Advanced Developer Key Configuration (Hidden inside sub-expander)
        with st.expander("🔒 Advanced Key Settings", expanded=False):
            env_var_name = curr_prov["env_key"]
            custom_key = None
            if env_var_name:
                loaded_key = os.getenv(env_var_name, "").strip()
                if loaded_key and not loaded_key.startswith("your_"):
                    st.success("✅ System Key: Active & Authenticated")
                else:
                    st.warning("⚠️ No active key configured")
                    custom_key = st.text_input(
                        "Session Key:",
                        type="password",
                        placeholder="Paste key...",
                        help="Key is only kept in temporary session memory."
                    )
            else:
                st.info("Runs fully offline without keys.")

# --- Main Chat Area ---

# Fetch messages for current conversation
messages = db.get_messages(st.session_state.current_conv_id)
current_title = active_conv["title"] if active_conv else "New Chat"

# Clean Header Bar (ChatGPT / Claude Style)
col_header_left, col_header_right = st.columns([3, 2])

with col_header_left:
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown(f"### {current_title}")
    with h_col2:
        with st.popover("✏️", help="Rename conversation"):
            new_title = st.text_input("New Title", value=current_title)
            if st.button("Save", key="save_title_btn"):
                if new_title.strip():
                    db.update_conversation_title(st.session_state.current_conv_id, new_title.strip())
                    st.rerun()

with col_header_right:
    # Format export Markdown
    export_md = f"# {current_title}\n\n*Exported from Zyren AI Assistant*\n\n---\n\n"
    for m in messages:
        speaker = "🧑‍💻 User" if m["role"] == "user" else "✨ Zyren"
        export_md += f"### {speaker}\n\n{m['content']}\n\n---\n\n"

    act_col1, act_col2, act_col3 = st.columns([2, 1, 3])
    with act_col1:
        st.download_button(
            "📥 Export",
            data=export_md,
            file_name=f"{current_title.replace(' ', '_')}.md",
            mime="text/markdown",
            help="Download chat as Markdown"
        )
    with act_col2:
        if st.button("🧹", help="Clear messages in this chat"):
            db.clear_conversation_messages(st.session_state.current_conv_id)
            st.rerun()
    with act_col3:
        # Display elegant Zyren Pill
        model_display_name = model_labels.get(selected_model, "Zyren 3.5 Flash")
        short_name = model_display_name.split("(")[0].strip()
        st.markdown(f"<div style='text-align: right; padding-top: 0.35rem;'><span class='zyren-pill'>✨ {short_name}</span></div>", unsafe_allow_html=True)

# If conversation is empty, display welcome starter cards
if not messages:
    st.markdown("""
    <div style="text-align: center; margin: 3rem 0 2rem 0;">
        <h1 style="font-size: 2.3rem; font-weight: 700; margin-bottom: 0.5rem; letter-spacing: -0.02em;">How can Zyren help you today?</h1>
        <p style="color: #94a3b8; font-size: 1.05rem;">Direct answers, deep reasoning, clean code generation, and real-time knowledge.</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💻 Explain Python async/await with clean examples", use_container_width=True):
            st.session_state["starter_prompt"] = "Explain Python async/await with clean examples and best practices."
            st.rerun()
        if st.button("🔬 Explain quantum computing to a 10-year-old", use_container_width=True):
            st.session_state["starter_prompt"] = "Explain quantum computing to a 10-year-old simply with an analogy."
            st.rerun()
    with c2:
        if st.button("📝 Draft a clear, professional weekly update email", use_container_width=True):
            st.session_state["starter_prompt"] = "Help me draft a clear, professional weekly project update email."
            st.rerun()
        if st.button("🧠 Remember that my preferred programming language is Python", use_container_width=True):
            st.session_state["starter_prompt"] = "Remember that my preferred programming language is Python."
            st.rerun()

# Display chat history
for idx, msg in enumerate(messages):
    with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "✨"):
        st.markdown(msg["content"])
        
        # Action toolbar for assistant messages (TTS & Regenerate)
        if msg["role"] == "assistant":
            btn_col1, btn_col2, _ = st.columns([1, 1.4, 8])
            with btn_col1:
                if st.button("🔊", key=f"speak_{msg['id']}", help="Read aloud"):
                    st.session_state.tts_text_to_speak = msg["content"]
                    st.rerun()
            # If this is the last message in chat, offer a Regenerate button
            if idx == len(messages) - 1:
                with btn_col2:
                    if st.button("🔄 Retry", key=f"regen_{msg['id']}", help="Regenerate this answer"):
                        db.delete_message(msg["id"])
                        user_history = [m for m in messages if m["role"] == "user"]
                        if user_history:
                            last_user = user_history[-1]
                            st.session_state["starter_prompt"] = last_user["content"]
                            db.delete_message(last_user["id"])
                        st.rerun()

# Voice input widget in an expander
with st.expander("🎙️ Voice Input (Speech-to-Text)", expanded=False):
    st.caption("Record your voice using your microphone. Audio is automatically transcribed into your prompt.")
    audio_record = st.audio_input("Record voice question")
    if audio_record is not None:
        audio_bytes = audio_record.read()
        if audio_bytes:
            with st.spinner("Transcribing your speech..."):
                transcription = ai_engine.transcribe_audio_input(audio_bytes)
                if transcription["success"]:
                    st.success(f"Transcribed: \"{transcription['text']}\"")
                    if st.button("Send Voice Message", key="send_audio_btn", type="primary"):
                        st.session_state["starter_prompt"] = transcription["text"]
                        st.rerun()
                else:
                    st.error(transcription["error"])

# Trigger TTS if requested
if st.session_state.tts_text_to_speak:
    render_speech_synthesizer(st.session_state.tts_text_to_speak, trigger_id="tts_trigger")
    st.session_state.tts_text_to_speak = None

# Quick Action Pills (Claude & ChatGPT Style)
st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
p1, p2, p3, p4 = st.columns(4)
with p1:
    if st.button("⚡ Summarize", use_container_width=True, help="Summarize key points"):
        st.session_state["starter_prompt"] = "Please summarize our discussion so far into key bullet points."
        st.rerun()
with p2:
    if st.button("💻 Debug Code", use_container_width=True, help="Analyze and fix code"):
        st.session_state["starter_prompt"] = "Can you help me debug and fix this code:"
        st.rerun()
with p3:
    if st.button("📝 Explain Simply", use_container_width=True, help="Explain with practical examples"):
        st.session_state["starter_prompt"] = "Explain this concept in simple terms with a real-world example:"
        st.rerun()
with p4:
    if st.button("🌐 Web Search", use_container_width=True, help="Search the live internet"):
        st.session_state["starter_prompt"] = "Search the web for the latest updates and news on:"
        st.rerun()

# Handle user input from either chat_input or starter cards
starter_input = st.session_state.pop("starter_prompt", None)
chat_input_text = st.chat_input("Ask Zyren anything (or say 'Remember that...')...")

user_prompt = starter_input or chat_input_text

if user_prompt:
    prompt_str = user_prompt.strip()

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
        # Load all persistent memories to inject into system prompt
        all_memories = [m["fact"] for m in db.get_all_memories()]

        # Prepare messages history (excluding current user message which is passed directly)
        history_msgs = db.get_messages(st.session_state.current_conv_id)[:-1]

        # Use write_stream for live streaming typewriter effect
        response_placeholder = st.empty()
        full_response_text = ""

        # Stream generator from ai_engine
        generator = ai_engine.stream_chat_response(
            history=history_msgs,
            user_prompt=prompt_str,
            provider=selected_provider,
            model=selected_model,
            enable_search=enable_search,
            memories=all_memories,
            api_key=custom_key
        )

        # Prepend memory notification if detected
        if memory_notice:
            st.info(f"🧠 Learned: {memory_fact}")

        full_response_text = st.write_stream(generator)

    # Save assistant response to DB
    if full_response_text:
        db.add_message(st.session_state.current_conv_id, "assistant", full_response_text)
        
        # If auto-TTS is enabled, trigger speech synthesis
        if enable_tts:
            st.session_state.tts_text_to_speak = full_response_text
            st.rerun()
