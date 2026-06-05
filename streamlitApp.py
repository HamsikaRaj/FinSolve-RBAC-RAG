import requests
import streamlit as st

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="FinSolve AI Assistant",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* ── Global ── */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
  }

  .stApp {
    background: #0f1117;
  }

  /* ── Hide Streamlit chrome ── */
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding: 0 !important; max-width: 100% !important; }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
    background: #16191f !important;
    border-right: 1px solid #2a2d35 !important;
    padding: 0 !important;
  }
  [data-testid="stSidebar"] > div:first-child {
    padding: 0 !important;
  }

  /* ── Sidebar inner content padding ── */
  .sidebar-inner { padding: 24px 20px; }

  /* ── Brand header ── */
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 24px 20px 20px;
    border-bottom: 1px solid #2a2d35;
    margin-bottom: 8px;
  }
  .brand-icon {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
  }
  .brand-name { font-size: 16px; font-weight: 700; color: #f1f5f9; }
  .brand-sub  { font-size: 11px; color: #64748b; margin-top: 1px; }

  /* ── User profile card ── */
  .profile-card {
    background: #1e2129;
    border: 1px solid #2a2d35;
    border-radius: 12px;
    padding: 14px 16px;
    margin: 12px 20px;
  }
  .profile-name { font-size: 14px; font-weight: 600; color: #f1f5f9; }
  .profile-id   { font-size: 11px; color: #64748b; margin-top: 2px; }
  .profile-badges { display: flex; gap: 6px; margin-top: 10px; flex-wrap: wrap; }

  .badge {
    font-size: 10px; font-weight: 600;
    padding: 3px 8px; border-radius: 20px;
    text-transform: uppercase; letter-spacing: 0.5px;
  }
  .badge-role    { background: #312e81; color: #a5b4fc; }
  .badge-dept    { background: #14532d; color: #86efac; }
  .badge-exec    { background: #7c2d12; color: #fdba74; }

  /* ── Access scope box ── */
  .access-box {
    background: #1a1f2e;
    border: 1px solid #2a2d35;
    border-left: 3px solid #6366f1;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 0 20px 12px;
    font-size: 12px;
    color: #94a3b8;
  }
  .access-box strong { color: #c7d2fe; display: block; margin-bottom: 4px; }
  .access-tag {
    display: inline-block;
    background: #1e2940;
    color: #7dd3fc;
    border: 1px solid #1d4ed8;
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 10px;
    margin: 2px 2px 0 0;
  }

  /* ── Input fields ── */
  .stTextInput > div > div > input {
    background: #1e2129 !important;
    border: 1px solid #2a2d35 !important;
    color: #f1f5f9 !important;
    border-radius: 8px !important;
    font-size: 13px !important;
  }
  .stTextInput > div > div > input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.2) !important;
  }
  .stTextInput label { color: #94a3b8 !important; font-size: 12px !important; font-weight: 500 !important; }

  /* ── Buttons ── */
  .stButton > button {
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 8px 16px !important;
    transition: all 0.15s ease !important;
    border: none !important;
  }
  div[data-testid="column"]:first-child .stButton > button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
  }
  div[data-testid="column"]:first-child .stButton > button:hover {
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
  }
  div[data-testid="column"]:last-child .stButton > button {
    background: #1e2129 !important;
    color: #94a3b8 !important;
    border: 1px solid #2a2d35 !important;
  }
  div[data-testid="column"]:last-child .stButton > button:hover {
    background: #252a35 !important;
    color: #f1f5f9 !important;
  }

  /* ── Main chat area ── */
  .chat-area {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background: #0f1117;
  }

  /* ── Top bar ── */
  .topbar {
    background: #16191f;
    border-bottom: 1px solid #2a2d35;
    padding: 14px 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .topbar-title { font-size: 15px; font-weight: 600; color: #f1f5f9; }
  .topbar-sub   { font-size: 12px; color: #64748b; }
  .status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #22c55e;
    display: inline-block; margin-right: 6px;
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  /* ── Chat messages ── */
  .msg-wrapper { padding: 24px 32px; }

  .msg-user {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 20px;
  }
  .msg-user .bubble {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: white;
    padding: 12px 16px;
    border-radius: 18px 18px 4px 18px;
    max-width: 65%;
    font-size: 14px;
    line-height: 1.5;
    box-shadow: 0 2px 12px rgba(99,102,241,0.3);
  }

  .msg-assistant { margin-bottom: 24px; }
  .msg-assistant .avatar {
    width: 32px; height: 32px;
    background: linear-gradient(135deg, #0ea5e9, #6366f1);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 15px;
    flex-shrink: 0;
    margin-bottom: 8px;
  }
  .msg-assistant .bubble {
    background: #1e2129;
    border: 1px solid #2a2d35;
    color: #e2e8f0;
    padding: 16px 18px;
    border-radius: 4px 18px 18px 18px;
    max-width: 80%;
    font-size: 14px;
    line-height: 1.6;
  }

  /* ── Source citations ── */
  .sources-section {
    margin-top: 12px;
    max-width: 80%;
  }
  .sources-label {
    font-size: 11px;
    font-weight: 600;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 6px;
  }
  .source-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: #1a1f2e;
    border: 1px solid #1e3a5f;
    color: #7dd3fc;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    margin: 3px 4px 3px 0;
  }
  .source-chip .dot { width: 5px; height: 5px; border-radius: 50%; background: #3b82f6; }

  /* ── No-info message ── */
  .no-info {
    background: #1c1a14;
    border: 1px solid #44310a;
    border-left: 3px solid #f59e0b;
    border-radius: 8px;
    padding: 12px 16px;
    color: #fbbf24;
    font-size: 13px;
    max-width: 80%;
    margin-bottom: 24px;
  }

  /* ── Empty state ── */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 60vh;
    color: #475569;
    text-align: center;
    padding: 32px;
  }
  .empty-icon { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }
  .empty-title { font-size: 18px; font-weight: 600; color: #64748b; margin-bottom: 8px; }
  .empty-sub   { font-size: 13px; color: #374151; max-width: 360px; line-height: 1.6; }

  /* ── Suggestion chips ── */
  .suggestions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 20px; }
  .suggestion-chip {
    background: #1e2129;
    border: 1px solid #2a2d35;
    color: #94a3b8;
    border-radius: 20px;
    padding: 7px 14px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.15s;
  }

  /* ── Login prompt ── */
  .login-prompt {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 80vh;
    color: #64748b;
    text-align: center;
  }
  .login-prompt .icon { font-size: 56px; margin-bottom: 20px; }
  .login-prompt h2 { font-size: 22px; font-weight: 700; color: #94a3b8; margin-bottom: 8px; }
  .login-prompt p  { font-size: 14px; color: #475569; max-width: 300px; line-height: 1.6; }

  /* ── Chat input override ── */
  [data-testid="stChatInput"] {
    background: #16191f !important;
    border-top: 1px solid #2a2d35 !important;
    padding: 16px 32px !important;
  }
  [data-testid="stChatInput"] textarea {
    background: #1e2129 !important;
    border: 1px solid #2a2d35 !important;
    color: #f1f5f9 !important;
    border-radius: 12px !important;
    font-size: 14px !important;
  }
  [data-testid="stChatInput"] textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.2) !important;
  }

  /* ── Alert / toast ── */
  .stAlert { border-radius: 8px !important; font-size: 13px !important; }

  /* ── Divider ── */
  hr { border-color: #2a2d35 !important; margin: 8px 0 !important; }

  /* ── Spinner ── */
  .stSpinner > div { border-top-color: #6366f1 !important; }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #2a2d35; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ── Session state ────────────────────────────────────────────────────────────
for key, default in [("token", None), ("user", None), ("messages", [])]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Helper: role metadata ─────────────────────────────────────────────────────
ROLE_META = {
    "exec":        {"label": "Executive",    "icon": "👑", "badge": "badge-exec"},
    "finance":     {"label": "Finance",      "icon": "💰", "badge": "badge-role"},
    "marketing":   {"label": "Marketing",    "icon": "📣", "badge": "badge-role"},
    "hr":          {"label": "HR",           "icon": "👥", "badge": "badge-role"},
    "engineering": {"label": "Engineering",  "icon": "⚙️", "badge": "badge-role"},
    "employee":    {"label": "Employee",     "icon": "🏢", "badge": "badge-role"},
}

DEPT_ACCESS = {
    "exec":        ["Finance", "Marketing", "HR", "Engineering", "General"],
    "finance":     ["Finance", "General"],
    "marketing":   ["Marketing", "General"],
    "hr":          ["HR", "General"],
    "engineering": ["Engineering", "General"],
    "employee":    ["General"],
}

SUGGESTIONS = {
    "finance":     ["Q1 2024 revenue?", "What is the gross margin?", "Cash flow summary"],
    "marketing":   ["Q2 marketing spend?", "Campaign ROI?", "Customer acquisition targets"],
    "hr":          ["Employee attendance stats", "Performance ratings", "Leave balances"],
    "engineering": ["Microservices architecture?", "CI/CD pipeline", "Security model"],
    "employee":    ["What is the leave policy?", "Work hours policy", "Code of conduct"],
    "exec":        ["Q1 2024 revenue?", "Microservices architecture?", "Employee attendance"],
}


def group_sources(sources):
    grouped = {}
    for s in sources:
        src = s.get("source", "")
        dept = s.get("department", "")
        if src not in grouped:
            grouped[src] = {"dept": dept, "chunks": []}
        cid = s.get("chunkId")
        if cid is not None and cid not in grouped[src]["chunks"]:
            grouped[src]["chunks"].append(cid)
    for src in grouped:
        grouped[src]["chunks"] = sorted(grouped[src]["chunks"])
    return grouped


def is_no_info(answer: str) -> bool:
    return "don't have enough information" in answer.lower() or "no information" in answer.lower()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Brand
    st.markdown("""
    <div class="brand">
      <div class="brand-icon">💼</div>
      <div>
        <div class="brand-name">FinSolve AI</div>
        <div class="brand-sub">Internal Assistant</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.user:
        user = st.session_state.user
        role = user.get("role", "employee")
        meta = ROLE_META.get(role, ROLE_META["employee"])
        dept = user.get("department", "")
        accessible = DEPT_ACCESS.get(role, ["General"])

        # Profile card
        st.markdown(f"""
        <div class="profile-card">
          <div class="profile-name">{meta['icon']} {user.get('fullName', '')}</div>
          <div class="profile-id">{user.get('employeeId', '')}</div>
          <div class="profile-badges">
            <span class="badge {meta['badge']}">{meta['label']}</span>
            <span class="badge badge-dept">{dept}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Access scope
        tags_html = "".join(f'<span class="access-tag">{d}</span>' for d in accessible)
        st.markdown(f"""
        <div class="access-box">
          <strong>Data Access Scope</strong>
          {tags_html}
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        col1, col2 = st.columns(2)
        with col2:
            if st.button("Logout", use_container_width=True):
                st.session_state.token = None
                st.session_state.user = None
                st.session_state.messages = []
                st.rerun()

        st.divider()
        st.markdown('<div style="padding: 0 20px;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;">Chat History</div>', unsafe_allow_html=True)
        if st.session_state.messages:
            if st.button("🗑️ Clear conversation", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        else:
            st.markdown('<div style="font-size:12px;color:#374151;">No messages yet.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        # Login form
        st.markdown('<div class="sidebar-inner">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:13px;font-weight:600;color:#94a3b8;margin-bottom:16px;">Sign in to continue</div>', unsafe_allow_html=True)

        employee_id = st.text_input("Employee ID", placeholder="e.g. FINEMP1001")
        password    = st.text_input("Password", type="password", placeholder="Fin@XXXX")

        col1, col2 = st.columns(2)
        with col1:
            login_clicked = st.button("Login", use_container_width=True)

        if login_clicked:
            if not employee_id or not password:
                st.error("Please enter both fields.")
            else:
                with st.spinner("Authenticating..."):
                    try:
                        resp = requests.post(
                            f"{API_BASE}/login",
                            json={"employeeId": employee_id, "password": password},
                            timeout=20,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            st.session_state.token = data["accessToken"]
                            st.session_state.user  = data
                            st.rerun()
                        else:
                            st.error("Invalid credentials. Try again.")
                    except Exception as e:
                        st.error(f"Connection error: {e}")

        st.markdown('<div style="margin-top:20px;padding:12px;background:#1a1f2e;border:1px solid #1e3a5f;border-radius:8px;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:11px;color:#7dd3fc;font-weight:600;margin-bottom:6px;">Demo Credentials</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:11px;color:#475569;line-height:1.7;">Password pattern:<br><code style="color:#94a3b8;background:#0f1117;padding:1px 4px;border-radius:3px;">Fin@&lt;last4digits&gt;</code><br><br>e.g. <code style="color:#94a3b8;background:#0f1117;padding:1px 4px;border-radius:3px;">FINEMP1001</code> → <code style="color:#94a3b8;background:#0f1117;padding:1px 4px;border-radius:3px;">Fin@1001</code></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ── Main area ─────────────────────────────────────────────────────────────────
if not st.session_state.token:
    st.markdown("""
    <div class="login-prompt">
      <div class="icon">🔐</div>
      <h2>FinSolve AI Assistant</h2>
      <p>Sign in with your employee credentials to access your personalised knowledge assistant.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

user     = st.session_state.user or {}
role     = user.get("role", "employee")
messages = st.session_state.messages

# Top bar
st.markdown(f"""
<div class="topbar">
  <div>
    <div class="topbar-title">💬 AI Assistant</div>
    <div class="topbar-sub">Answers sourced only from documents you're authorised to view</div>
  </div>
  <div style="font-size:12px;color:#64748b;">
    <span class="status-dot"></span>Claude Sonnet
  </div>
</div>
""", unsafe_allow_html=True)

# ── Messages ─────────────────────────────────────────────────────────────────
if not messages:
    role_suggestions = SUGGESTIONS.get(role, SUGGESTIONS["employee"])
    chips = "".join(f'<div class="suggestion-chip">{s}</div>' for s in role_suggestions)
    st.markdown(f"""
    <div class="empty-state">
      <div class="empty-icon">🤖</div>
      <div class="empty-title">How can I help you today?</div>
      <div class="empty-sub">Ask anything about documents within your access scope. I'll only answer from authorised sources.</div>
      <div class="suggestions">{chips}</div>
    </div>
    """, unsafe_allow_html=True)
else:
    for m in messages:
        if m["role"] == "user":
            st.markdown(f"""
            <div class="msg-wrapper" style="padding-bottom:0">
              <div class="msg-user"><div class="bubble">{m["content"]}</div></div>
            </div>
            """, unsafe_allow_html=True)
        else:
            answer  = m["content"]
            sources = m.get("sources", [])

            if is_no_info(answer):
                st.markdown(f"""
                <div class="msg-wrapper" style="padding-top:8px">
                  <div class="no-info">⚠️ {answer}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="msg-wrapper" style="padding-top:8px">
                  <div class="msg-assistant">
                    <div class="avatar">🤖</div>
                    <div class="bubble">{answer}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                if sources:
                    grouped = group_sources(sources)
                    chips_html = ""
                    for src, info in grouped.items():
                        short = src.split("/")[-1].replace(".md", "").replace("_", " ").title()
                        dept  = info.get("dept", "")
                        chips_html += f'<span class="source-chip"><span class="dot"></span>{short} <span style="color:#475569;">({dept})</span></span>'

                    st.markdown(f"""
                    <div class="msg-wrapper" style="padding-top:0">
                      <div class="sources-section">
                        <div class="sources-label">Sources</div>
                        <div>{chips_html}</div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

# ── Chat input ────────────────────────────────────────────────────────────────
prompt = st.chat_input("Ask a question about your company data...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Thinking..."):
        try:
            resp = requests.post(
                f"{API_BASE}/chat",
                json={"message": prompt},
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                timeout=60,
            )
            data    = resp.json()
            answer  = data.get("answer", "An error occurred.")
            sources = data.get("sources", [])
        except Exception as e:
            answer  = f"Connection error: {e}"
            sources = []

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
    })
    st.rerun()
