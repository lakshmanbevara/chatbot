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

# --- 1. Speed & Startup Optimization: Cached CSS Loading ---
@st.cache_data(show_spinner=False)
def get_cached_theme_css() -> str:
    """Caches CSS in memory to eliminate repeated disk reads on each rerun."""
    css_file = BASE_DIR / "assets" / "style.css"
    if css_file.exists():
        with open(css_file, "r", encoding="utf-8") as f:
            return f.read()
    return ""

cached_css = get_cached_theme_css()
if cached_css:
    st.markdown(f"<style>{cached_css}</style>", unsafe_allow_html=True)

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

if "active_persona" not in st.session_state:
    st.session_state.active_persona = "general"

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

if "attached_image_bytes" not in st.session_state:
    st.session_state.attached_image_bytes = None

if "attached_image_name" not in st.session_state:
    st.session_state.attached_image_name = None

if "attached_image_mime" not in st.session_state:
    st.session_state.attached_image_mime = None

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
    # 1. Subtle Animated Zyren Branding
    st.markdown("""
    <div class="zyren-brand-container">
        <div class="zyren-logo-badge">✨</div>
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
        st.session_state.attached_image_bytes = None
        st.session_state.attached_image_name = None
        st.session_state.attached_image_mime = None
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

    st.markdown("<div class='sidebar-section-header'>💬 Recent Conversations</div>", unsafe_allow_html=True)
    
    if not conversations:
        st.caption("No conversations yet.")
    else:
        for conv in conversations:
            is_active = conv["id"] == st.session_state.current_conv_id
            col1, col2 = st.columns([5, 1])
            with col1:
                item_class = "sidebar-chat-item-active" if is_active else "sidebar-chat-item"
                st.markdown(f'<div class="{item_class}">', unsafe_allow_html=True)
                label = f"{'● ' if is_active else '💬 '}{conv['title']}"
                if st.button(label, key=f"conv_{conv['id']}", use_container_width=True):
                    st.session_state.current_conv_id = conv["id"]
                    st.session_state.tts_text_to_speak = None
                    st.session_state.attached_file_content = None
                    st.session_state.attached_file_name = None
                    st.session_state.attached_image_bytes = None
                    st.session_state.attached_image_name = None
                    st.session_state.attached_image_mime = None
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="sidebar-del-btn">', unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_{conv['id']}", help="Delete chat"):
                    db.delete_conversation(conv["id"])
                    if is_active:
                        remaining = db.get_conversations()
                        st.session_state.current_conv_id = remaining[0]["id"] if remaining else db.create_conversation("New Chat")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 1.1rem;'></div>", unsafe_allow_html=True)
    st.markdown("---")

    # 5. Persistent Long-Term Memory (Persistent Brain)
    memories = db.get_all_memories()
    with st.expander(f"🧠 Persistent Memory ({len(memories)})", expanded=False):
        st.caption("Facts Zyren remembers across conversations:")
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

# Persona dictionary for mode switching
persona_dict = {
    "general": ("✨ General", "Balanced everyday AI assistant"),
    "coder": ("💻 Coder", "Expert software engineer with clean code"),
    "tutor": ("📚 Tutor", "Socratic study mentor with step-by-step breakdowns"),
    "writer": ("✍️ Writer", "Executive editor for clear, polished prose")
}

# 1. Top Navigation Bar (Header)
col_nav_left, col_nav_right = st.columns([6, 4])

with col_nav_left:
    t_c1, t_c2, t_c3 = st.columns([3.8, 0.8, 2.4])
    with t_c1:
        st.markdown(f"<h3 style='margin: 0; padding-top: 0.15rem; font-weight: 700; font-size: 1.35rem; color: #f8fafc;'>{current_title}</h3>", unsafe_allow_html=True)
    with t_c2:
        with st.popover("✏️", help="Rename chat"):
            new_title = st.text_input("New Title", value=current_title)
            if st.button("Save", key="save_title_btn"):
                if new_title.strip():
                    db.update_conversation_title(st.session_state.current_conv_id, new_title.strip())
                    st.rerun()
    with t_c3:
        active_persona_name = persona_dict.get(st.session_state.active_persona, ("✨ General", ""))[0]
        with st.popover(f"🎭 {active_persona_name}", help="Switch AI Persona Mode"):
            st.caption("Select Zyren's thinking mode:")
            for p_key, (p_name, p_desc) in persona_dict.items():
                if st.button(f"{p_name}\n{p_desc}", key=f"persona_btn_{p_key}", use_container_width=True):
                    st.session_state.active_persona = p_key
                    st.rerun()

with col_nav_right:
    export_md = f"# {current_title}\n\n*Exported from Zyren AI Assistant*\n\n---\n\n"
    for m in messages:
        speaker = "🧑‍💻 User" if m["role"] == "user" else "✨ Zyren"
        export_md += f"### {speaker}\n\n{m['content']}\n\n---\n\n"

    model_display_name = model_labels.get(selected_model, "Zyren 3.5 Flash")
    short_name = model_display_name.split("(")[0].strip()

    if messages:
        b1, b2, b3 = st.columns([2.5, 1.8, 1.4])
        with b1:
            st.markdown(f"<div style='text-align: right; padding-top: 0.25rem;'><span class='zyren-model-pill'>✨ {short_name}</span></div>", unsafe_allow_html=True)
        with b2:
            st.download_button(
                "📥 Export",
                data=export_md,
                file_name=f"{current_title.replace(' ', '_')}.md",
                mime="text/markdown",
                help="Download conversation as Markdown",
                use_container_width=True
            )
        with b3:
            if st.button("🧹 Clear", key="clear_chat_top", help="Clear messages in this chat", use_container_width=True):
                db.clear_conversation_messages(st.session_state.current_conv_id)
                st.rerun()
    else:
        st.markdown(f"<div style='text-align: right; padding-top: 0.25rem;'><span class='zyren-model-pill'>✨ {short_name}</span></div>", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

# 2. Welcome Screen with 4 Suggestion Cards (Empty State)
if not messages:
    st.markdown("""
    <div class="hero-container">
        <div class="hero-sparkle">✨</div>
        <h1 class="hero-title">How can Zyren help you today?</h1>
        <p class="hero-subtitle">Your intelligent personal AI assistant.</p>
    </div>
    """, unsafe_allow_html=True)

    # Four Attractive Cards Grid (Section 1 Requirement)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="zyren-suggestion-card">', unsafe_allow_html=True)
        if st.button(
            "💡 Explain anything\nQuantum computing with an everyday analogy",
            key="card_explain",
            use_container_width=True
        ):
            st.session_state["starter_prompt"] = "Explain quantum computing simply using an everyday analogy."
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="zyren-suggestion-card">', unsafe_allow_html=True)
        if st.button(
            "💻 Debug code\nAnalyze and optimize Python algorithms for performance",
            key="card_debug",
            use_container_width=True
        ):
            st.session_state["starter_prompt"] = "Can you help me analyze, debug, and optimize a Python algorithm for maximum performance?"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="zyren-suggestion-card">', unsafe_allow_html=True)
        if st.button(
            "✍️ Write anything\nDraft a concise executive weekly project update",
            key="card_write",
            use_container_width=True
        ):
            st.session_state["starter_prompt"] = "Draft a professional executive summary weekly project update email."
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="zyren-suggestion-card">', unsafe_allow_html=True)
        if st.button(
            "🧠 Learn something new\nHow transformer models & self-attention work step-by-step",
            key="card_learn",
            use_container_width=True
        ):
            st.session_state["starter_prompt"] = "Teach me how modern transformer neural networks and attention mechanisms work step-by-step."
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# 3. Message Display Loop
for idx, msg in enumerate(messages):
    is_user = msg["role"] == "user"
    with st.chat_message(msg["role"], avatar="🧑‍💻" if is_user else "✨"):
        st.markdown(msg["content"])
        
        # User message actions: Edit previous message
        if is_user:
            u1, _ = st.columns([1.2, 8.8])
            with u1:
                st.markdown('<div class="msg-action-btn">', unsafe_allow_html=True)
                with st.popover("✏️ Edit", help="Edit message and regenerate response"):
                    edited_msg = st.text_area("Edit your message:", value=msg["content"], key=f"edit_val_{msg['id']}", height=100)
                    if st.button("Save & Resubmit", key=f"save_edit_{msg['id']}", type="primary", use_container_width=True):
                        if edited_msg.strip():
                            db.delete_messages_after(st.session_state.current_conv_id, msg["created_at"])
                            st.session_state["starter_prompt"] = edited_msg.strip()
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # Assistant Message Actions Toolbar (TTS, Copy, Thumbs Up/Down, Regenerate)
        if not is_user:
            t1, t2, t3, t4, t5, _ = st.columns([1, 1, 1, 1, 1.4, 6.6])
            with t1:
                st.markdown('<div class="msg-action-btn">', unsafe_allow_html=True)
                if st.button("🔊", key=f"speak_{msg['id']}", help="Read aloud"):
                    st.session_state.tts_text_to_speak = msg["content"]
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with t2:
                st.markdown('<div class="msg-action-btn">', unsafe_allow_html=True)
                if st.button("📋", key=f"copy_{msg['id']}", help="Copy response"):
                    st.session_state.copied_text = msg["content"]
                    st.toast("Copied to clipboard! 📋")
                st.markdown('</div>', unsafe_allow_html=True)
            with t3:
                is_liked = st.session_state.feedback_state.get(msg["id"]) == "up"
                btn_class = "msg-action-btn-active" if is_liked else "msg-action-btn"
                st.markdown(f'<div class="{btn_class}">', unsafe_allow_html=True)
                if st.button("👍" if not is_liked else "✅", key=f"thumbup_{msg['id']}", help="Helpful response"):
                    st.session_state.feedback_state[msg["id"]] = "up"
                    st.toast("Thank you for your feedback! 👍")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with t4:
                is_disliked = st.session_state.feedback_state.get(msg["id"]) == "down"
                btn_class = "msg-action-btn-active" if is_disliked else "msg-action-btn"
                st.markdown(f'<div class="{btn_class}">', unsafe_allow_html=True)
                if st.button("👎" if not is_disliked else "❌", key=f"thumbdown_{msg['id']}", help="Not helpful"):
                    st.session_state.feedback_state[msg["id"]] = "down"
                    st.toast("Feedback recorded. We'll improve! 👎")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with t5:
                # Regenerate button (on the last assistant message)
                if idx == len(messages) - 1:
                    st.markdown('<div class="msg-action-btn">', unsafe_allow_html=True)
                    if st.button("🔄 Retry", key=f"regen_{msg['id']}", help="Regenerate this answer"):
                        db.delete_message(msg["id"])
                        user_history = [m for m in messages if m["role"] == "user"]
                        if user_history:
                            last_user = user_history[-1]
                            st.session_state["starter_prompt"] = last_user["content"]
                            db.delete_message(last_user["id"])
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

# 4. Attached File & Image Banners (if any staged)
if st.session_state.attached_image_bytes:
    img_col1, img_col2 = st.columns([6, 1])
    with img_col1:
        st.markdown(
            f"<div class='attached-image-badge'>"
            f"🖼️ Attached Image: <b>{st.session_state.attached_image_name}</b>"
            f"</div>",
            unsafe_allow_html=True
        )
    with img_col2:
        if st.button("✕ Remove", key="remove_image_btn", help="Detach image"):
            st.session_state.attached_image_bytes = None
            st.session_state.attached_image_name = None
            st.session_state.attached_image_mime = None
            st.rerun()

if st.session_state.attached_file_content:
    af_col1, af_col2 = st.columns([6, 1])
    with af_col1:
        line_count = len(st.session_state.attached_file_content.splitlines())
        st.markdown(
            f"<div class='attached-file-badge'>"
            f"📎 Attached: <b>{st.session_state.attached_file_name}</b> ({line_count} lines)"
            f"</div>",
            unsafe_allow_html=True
        )
    with af_col2:
        if st.button("✕ Remove", key="remove_attachment_btn", help="Detach file"):
            st.session_state.attached_file_content = None
            st.session_state.attached_file_name = None
            st.rerun()

# 5. Integrated Composer Accessory Toolbar (Attach File, Voice Input, Quick Actions)
st.markdown('<div class="composer-accessory-toolbar">', unsafe_allow_html=True)
acc_c1, acc_c2, acc_c3 = st.columns([1.5, 1.5, 5])

with acc_c1:
    with st.popover("📎 Attach File", help="Upload images, PDF documents, or code"):
        st.caption("Upload image, PDF, or text file:")
        uploaded_file = st.file_uploader(
            "Upload document or image",
            type=["png", "jpg", "jpeg", "webp", "pdf", "py", "js", "ts", "txt", "md", "json", "csv", "html", "css", "sql", "cpp", "rs", "java"],
            label_visibility="collapsed",
            key="file_uploader_popover"
        )
        if uploaded_file is not None:
            file_name = uploaded_file.name
            file_ext = file_name.split(".")[-1].lower()
            
            # 2. Image/Vision processing
            if file_ext in ["png", "jpg", "jpeg", "webp"]:
                st.session_state.attached_image_bytes = uploaded_file.read()
                st.session_state.attached_image_name = file_name
                st.session_state.attached_image_mime = uploaded_file.type or "image/jpeg"
                st.success(f"Attached image: `{file_name}`")
                st.rerun()
            # 3. PDF document processing
            elif file_ext == "pdf":
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(uploaded_file)
                    extracted_pages = []
                    for p_idx, page in enumerate(reader.pages[:20]):
                        t = page.extract_text()
                        if t:
                            extracted_pages.append(f"--- Page {p_idx+1} ---\n{t.strip()}")
                    file_text = "\n\n".join(extracted_pages)
                    st.session_state.attached_file_content = file_text
                    st.session_state.attached_file_name = file_name
                    st.success(f"Attached PDF: `{file_name}` ({len(reader.pages)} pages)")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not read PDF: {e}")
            # Text / code file processing
            else:
                try:
                    file_text = uploaded_file.read().decode("utf-8")
                    st.session_state.attached_file_content = file_text
                    st.session_state.attached_file_name = file_name
                    st.success(f"Attached: `{file_name}`")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not read file: {e}")

with acc_c2:
    with st.popover("🎙️ Voice Input", help="Record audio query"):
        st.caption("Record voice using your microphone:")
        audio_record = st.audio_input("Record audio", label_visibility="collapsed", key="audio_recorder_popover")
        if audio_record is not None:
            audio_bytes = audio_record.read()
            if audio_bytes:
                with st.spinner("Transcribing speech..."):
                    transcription = ai_engine.transcribe_audio_input(audio_bytes)
                    if transcription["success"]:
                        st.success(f"Transcribed: \"{transcription['text']}\"")
                        if st.button("Send Speech Query", key="send_audio_btn", type="primary"):
                            st.session_state["starter_prompt"] = transcription["text"]
                            st.rerun()
                    else:
                        st.error(transcription["error"])

with acc_c3:
    with st.popover("⚡ Quick Actions", help="Instant prompts: Summarize, Debug, Search"):
        q1, q2 = st.columns(2)
        with q1:
            if st.button("⚡ Summarize Chat", use_container_width=True):
                st.session_state["starter_prompt"] = "Please summarize our discussion so far into key bullet points."
                st.rerun()
            if st.button("💻 Debug Code", use_container_width=True):
                st.session_state["starter_prompt"] = "Can you help me analyze, debug, and fix this code:"
                st.rerun()
        with q2:
            if st.button("📝 Explain Simply", use_container_width=True):
                st.session_state["starter_prompt"] = "Explain this concept in simple terms with a practical example:"
                st.rerun()
            if st.button("🌐 Web Search", use_container_width=True):
                st.session_state["starter_prompt"] = "Search the web for the latest news and updates on:"
                st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# 6. Message Composer (Chat Input)
starter_input = st.session_state.pop("starter_prompt", None)
chat_input_text = st.chat_input("Ask Zyren anything (or say 'Remember that...')...")

user_prompt = starter_input or chat_input_text

if user_prompt:
    prompt_str = user_prompt.strip()

    # Prepend any attached document or PDF content
    if st.session_state.attached_file_content:
        prompt_str = (
            f"📎 [Attached File: `{st.session_state.attached_file_name}`]\n"
            f"```\n{st.session_state.attached_file_content}\n```\n\n"
            f"{prompt_str}"
        )
        st.session_state.attached_file_content = None
        st.session_state.attached_file_name = None

    # Capture and reset any staged image
    cur_img_bytes = st.session_state.attached_image_bytes
    cur_img_mime = st.session_state.attached_image_mime
    cur_img_name = st.session_state.attached_image_name
    st.session_state.attached_image_bytes = None
    st.session_state.attached_image_mime = None
    st.session_state.attached_image_name = None

    # Check for memory storage command
    memory_fact = ai_engine.detect_memory_command(prompt_str)
    memory_notice = ""
    if memory_fact:
        saved = db.add_memory(memory_fact)
        if saved:
            memory_notice = f"*(I have saved this to my persistent memory: \"{memory_fact}\")*\n\n"

    # Save user message to database
    db_save_text = prompt_str
    if cur_img_name:
        db_save_text = f"[Attached Image: {cur_img_name}]\n\n{prompt_str}"
    db.add_message(st.session_state.current_conv_id, "user", db_save_text)

    # Auto-update conversation title if it's the first message
    if active_conv and (active_conv["title"] == "New Chat" or not messages):
        new_title = prompt_str[:32] + ("..." if len(prompt_str) > 32 else "")
        db.update_conversation_title(st.session_state.current_conv_id, new_title)

    # Display user message in UI
    with st.chat_message("user", avatar="🧑‍💻"):
        if cur_img_bytes:
            st.image(cur_img_bytes, caption=cur_img_name, width=280)
        st.markdown(prompt_str)

    # Generate assistant streaming response
    with st.chat_message("assistant", avatar="✨"):
        all_memories = [m["fact"] for m in db.get_all_memories()]
        history_msgs = db.get_messages(st.session_state.current_conv_id)[:-1]

        if memory_notice:
            st.info(f"🧠 Learned: {memory_fact}")

        generator = ai_engine.stream_chat_response(
            history=history_msgs,
            user_prompt=prompt_str,
            provider=selected_provider,
            model=selected_model,
            enable_search=enable_search,
            memories=all_memories,
            api_key=custom_key,
            image_bytes=cur_img_bytes,
            image_mime=cur_img_mime,
            persona=st.session_state.active_persona
        )

        response_placeholder = st.empty()
        full_response_text = ""

        stop_placeholder = st.empty()
        stop_clicked = False
        with stop_placeholder:
            st.markdown('<div class="stop-btn-wrapper">', unsafe_allow_html=True)
            if st.button("⏹️ Stop Generating", key="stop_generating_btn", help="Interrupt response generation"):
                stop_clicked = True
            st.markdown('</div>', unsafe_allow_html=True)

        try:
            for chunk in generator:
                if stop_clicked:
                    break
                full_response_text += chunk
                response_placeholder.markdown(full_response_text + " ▌")
        except Exception as e:
            full_response_text += f"\n\n*(Generation interrupted: {str(e)})*"

        # Final render without cursor
        response_placeholder.markdown(full_response_text)
        stop_placeholder.empty()

    # Save assistant response to DB
    if full_response_text:
        db.add_message(st.session_state.current_conv_id, "assistant", full_response_text)
        
        if enable_tts:
            st.session_state.tts_text_to_speak = full_response_text
            st.rerun()
