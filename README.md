# ✨ Zyren – Next-Generation AI Assistant

**Zyren** is a modern personal AI assistant inspired by **ChatGPT**, **Claude**, and **Gemini**. Built with Python and Streamlit, it features live streaming responses, persistent long-term memory, voice transcription, spoken responses (TTS), real-time internet search, and a sleek, private UI.

---

## 🌟 Key Highlights

- **✨ Proprietary Aesthetic**: Styled like ChatGPT and Claude with Plus Jakarta Sans typography, sleek dark slate tones, and a clean interface.
- **🔒 Covered Settings**: All API key information and provider details are tucked away inside a discreet **Profile & Settings** popover at the bottom of the sidebar. Nobody looking at your screen can see where the API key is from!
- **⚡ Real-Time Streaming**: High-speed typewriter token streaming using your free Google Gemini API key (`gemini-3.5-flash`).
- **💬 Full Context Awareness**: Remembers follow-up questions across turns.
- **🧠 Persistent Long-Term Memory**: Automatically captures facts (e.g., *"Remember that I prefer Python"*) and saves them to SQLite.
- **🔄 Regenerate & Retry**: 1-click retry button on assistant responses.
- **📥 Export Conversation**: 1-click Markdown download button to save your chat notes.
- **✏️ Rename Chats**: Inline renaming for conversation titles.
- **🎙️ Voice Mode**: Built-in speech-to-text recording.
- **🔊 Read Aloud (TTS)**: Clean spoken audio using your browser's speech synthesizer.

---

## 🚀 Running Zyren

### Method 1: Double-Click
Double-click **`run.bat`** in `D:\chatbot`.

### Method 2: Via Terminal
```powershell
.\venv\Scripts\activate
streamlit run app.py --server.port 8502
```

Open **`http://localhost:8502`** in your browser.
