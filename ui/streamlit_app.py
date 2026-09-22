"""
Emerson Enterprise AI Assistant — Streamlit UI v2
Enhancements:
  - Description panel on login screen
  - Role-based document upload with inline ingestion
  - Sidebar with system info, role capabilities, and upload panel
  - Chat with source badges and response type indicators
  - Admin: audit logs + collection browser
"""

import streamlit as st
import requests

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="Emerson Enterprise AI Assistant",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Role badge pills */
.role-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.badge-hr        { background:#dbeafe; color:#1e40af; }
.badge-finance   { background:#dcfce7; color:#15803d; }
.badge-engineering { background:#fef9c3; color:#854d0e; }
.badge-marketing { background:#fce7f3; color:#9d174d; }
.badge-admin     { background:#f3e8ff; color:#6b21a8; }

/* Description card on login */
.desc-card {
    background: linear-gradient(135deg, #1e3a5f 0%, #0f2744 100%);
    border-radius: 12px;
    padding: 28px 32px;
    color: white;
    margin-bottom: 24px;
}
.desc-card h3 { color: #93c5fd; margin-bottom: 12px; font-size: 18px; }
.desc-card p  { color: #cbd5e1; font-size: 14px; line-height: 1.7; margin: 0; }
.feature-row { display:flex; gap:16px; margin-top:16px; flex-wrap:wrap; }
.feature-item {
    background: rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    color: #e2e8f0;
    flex: 1;
    min-width: 140px;
}
.feature-item .icon { font-size: 18px; margin-bottom: 4px; }

/* Source tag */
.src-tag {
    display: inline-block;
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    color: #475569;
    margin: 2px;
}
</style>
""", unsafe_allow_html=True)

# ── Session state init ─────────────────────────────────────────────────────
for key, val in {
    "token": None, "role": None, "username": None,
    "chat_history": [], "upload_success": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

ROLE_COLORS = {
    "hr": "badge-hr",
    "finance": "badge-finance",
    "engineering": "badge-engineering",
    "marketing": "badge-marketing",
    "admin": "badge-admin",
}

ROLE_CAPABILITIES = {
    "hr": {
        "icon": "👥",
        "desc": "Access employee handbook, HR master data, attendance records, and people policies.",
        "sample_queries": [
            "What are the types of leaves available?",
            "How are performance appraisals conducted?",
            "What is the onboarding process for new joiners?",
        ],
    },
    "finance": {
        "icon": "💰",
        "desc": "Access financial summaries, quarterly reports, revenue data, and budget information.",
        "sample_queries": [
            "What was the total revenue in Q4?",
            "What are the key financial risks this year?",
            "What is the net profit margin?",
        ],
    },
    "engineering": {
        "icon": "⚙️",
        "desc": "Access engineering standards, architecture blueprints, CI/CD, and technical guidelines.",
        "sample_queries": [
            "What are the system architecture standards?",
            "What CI/CD tools are used?",
            "What is the disaster recovery strategy?",
        ],
    },
    "marketing": {
        "icon": "📣",
        "desc": "Access marketing reports, campaign data, ROI analysis, and quarterly performance.",
        "sample_queries": [
            "What were the key marketing highlights in 2024?",
            "Which marketing channel had the highest ROI?",
            "What was the Q1 marketing performance?",
        ],
    },
    "admin": {
        "icon": "🔐",
        "desc": "Full access to all documents, audit logs, collection browser, and user management.",
        "sample_queries": [
            "What access permissions does the HR role have?",
            "Show me leave policy and Q4 financial summary.",
            "Which roles have access to financial documents?",
        ],
    },
}


# ══════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════
if not st.session_state.token:

    col_left, col_right = st.columns([1.2, 1], gap="large")

    with col_left:
        # ── System description card ────────────────────────────────────
        st.markdown("""
        <div class="desc-card">
            <h3>🏭 Emerson Enterprise AI Assistant</h3>
            <p>
                A secure, role-aware AI knowledge management system built for Emerson Automation Solutions.
                It uses <strong>Retrieval-Augmented Generation (RAG)</strong> to answer questions grounded
                in your organisation's actual documents — not hallucinated answers.
            </p>
            <p style="margin-top:12px;">
                Every query is filtered through <strong>Role-Based Access Control (RBAC)</strong>,
                ensuring each user can only access documents relevant to their department.
                All interactions are audit-logged for compliance and security monitoring.
            </p>
            <div class="feature-row">
                <div class="feature-item"><div class="icon">🔒</div>Role-Based Access Control</div>
                <div class="feature-item"><div class="icon">📄</div>Document Upload &amp; Ingestion</div>
                <div class="feature-item"><div class="icon">🧠</div>LLM-Powered Answers</div>
                <div class="feature-item"><div class="icon">🛡️</div>Prompt Injection Guardrails</div>
                <div class="feature-item"><div class="icon">📋</div>Full Audit Logging</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Roles overview ─────────────────────────────────────────────
        st.markdown("#### Roles & Permissions")
        roles_data = {
            "Finance Team":    "Financial reports, expenses, budget, reimbursements",
            "Marketing Team":  "Campaign data, customer feedback, sales metrics",
            "HR Team":         "Employee data, attendance, payroll, performance reviews",
            "Engineering":     "Technical architecture, dev processes, guidelines",
            "Admin":           "Full access to all company data and audit logs",
        }
        for role, perm in roles_data.items():
            st.markdown(f"**{role}** — {perm}")

    with col_right:
        st.markdown("### Secure Login")
        st.markdown("Sign in with your department credentials to access the AI assistant.")

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="e.g. alice")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("🔐 Login", use_container_width=True)

        if submitted:
            if not username or not password:
                st.warning("Please enter both username and password.")
            else:
                try:
                    resp = requests.post(
                        f"{API_BASE}/auth/login",
                        json={"username": username, "password": password},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state.token    = data["access_token"]
                        st.session_state.role     = data["role"]
                        st.session_state.username = data["username"]
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials. Please try again.")
                except requests.exceptions.ConnectionError:
                    st.error("⚠️ Cannot connect to the API server. Make sure uvicorn is running on port 8000.")

        st.divider()
        st.caption("**Demo Accounts**")
        demo = {
            "alice / alice123": "HR",
            "bob / bob123": "Finance",
            "charlie / charlie123": "Engineering",
            "diana / diana123": "Marketing",
            "admin / admin123": "Admin",
        }
        for cred, role in demo.items():
            st.caption(f"`{cred}` → {role}")

    st.stop()


# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR — shown after login
# ══════════════════════════════════════════════════════════════════════════
role = st.session_state.role
username = st.session_state.username
badge_class = ROLE_COLORS.get(role, "badge-admin")
cap = ROLE_CAPABILITIES.get(role, {})

with st.sidebar:
    # User info
    st.markdown(f"### {cap.get('icon','🏭')} {username}")
    st.markdown(
        f'<span class="role-badge {badge_class}">{role.upper()}</span>',
        unsafe_allow_html=True,
    )
    st.markdown(f"*{cap.get('desc','')}*")
    st.divider()

    # Sample queries
    if cap.get("sample_queries"):
        st.markdown("**💡 Sample Queries**")
        for q in cap["sample_queries"]:
            if st.button(q, key=f"sample_{q[:20]}", use_container_width=True):
                st.session_state["prefill_query"] = q
                st.rerun()

    st.divider()

    # ── Document Upload Panel ──────────────────────────────────────────
    st.markdown("### 📤 Upload Document")
    st.caption("Upload a PDF to make it searchable within the selected role's namespace.")

    # Role selector: admin can pick any role, others locked to their own
    if role == "admin":
        try:
            _roles_resp = requests.get(
                f"{API_BASE}/admin/roles",
                params={"token": st.session_state.token},
                timeout=10,
            )
            _all_roles = [r["role"] for r in _roles_resp.json()] if _roles_resp.status_code == 200 else []
        except Exception:
            _all_roles = []
        if not _all_roles:
            _all_roles = ["hr", "finance", "engineering", "marketing", "admin"]

        upload_role = st.selectbox(
            "Assign to role",
            options=_all_roles,
            index=_all_roles.index(role) if role in _all_roles else 0,
        )
    else:
        upload_role = role
        st.caption(f"Documents will be added to your role: **{role.upper()}**")

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Max 20MB. The document will be chunked and indexed automatically.",
    )

    if uploaded_file is not None:
        st.caption(f"📄 **{uploaded_file.name}** ({uploaded_file.size // 1024} KB)")

        if st.button("⚡ Ingest Document", use_container_width=True, type="primary"):
            with st.spinner(f"Ingesting into '{upload_role}' namespace..."):
                try:
                    resp = requests.post(
                        f"{API_BASE}/upload-document",
                        data={
                            "token": st.session_state.token,
                            "target_role": upload_role,
                        },
                        files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")},
                        timeout=60,
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        st.success(
                            f"✅ Ingested successfully!\n\n"
                            f"**Collection:** `{result['collection_name']}`\n\n"
                            f"**Chunks indexed:** {result['chunks_added']}\n\n"
                            f"**Role access:** `{result['role_granted'].upper()}`"
                        )
                    elif resp.status_code == 403:
                        st.error("🚫 Permission denied. You can only upload for your own role.")
                    elif resp.status_code == 400:
                        st.error(f"❌ {resp.json().get('detail', 'Invalid file.')}")
                    else:
                        st.error(f"Upload failed: {resp.text}")
                except requests.exceptions.ConnectionError:
                    st.error("⚠️ Cannot reach the API server.")

    st.divider()

    # Clear chat
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

    # Logout
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# MAIN CHAT AREA
# ══════════════════════════════════════════════════════════════════════════
# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🏭 Emerson Enterprise AI Assistant")
    st.caption(
        "Ask anything about Emerson's enterprise knowledge. "
        "Answers are grounded in documents you are authorised to access. "
        "Responses are generated by LLaMA 3.3 70B via Groq."
    )
with col2:
    st.markdown(
        f'<div style="text-align:right;padding-top:12px;">'
        f'<span class="role-badge {badge_class}">{role.upper()}</span>'
        f'<br><small style="color:#64748b;">@{username}</small></div>',
        unsafe_allow_html=True,
    )

st.divider()

# ── Chat history display ───────────────────────────────────────────────────
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("meta"):
            # Parse and display source tags nicely
            meta = msg["meta"]
            if "Sources:" in meta:
                parts = meta.split(" · ")
                for part in parts:
                    if part.startswith("Sources:"):
                        sources = part.replace("Sources:", "").strip().split(", ")
                        src_html = "".join(f'<span class="src-tag">📄 {s}</span>' for s in sources)
                        st.markdown(f"<small>{src_html}</small>", unsafe_allow_html=True)
                    else:
                        st.caption(part)
            else:
                st.caption(meta)

# ── Handle prefilled query from sidebar sample buttons ────────────────────
prefill = st.session_state.pop("prefill_query", None)

# ── Chat input ────────────────────────────────────────────────────────────
prompt = st.chat_input(
    "Ask anything about Emerson enterprise knowledge...",
    key="chat_input",
)

# Use prefill if sidebar button was clicked
if prefill and not prompt:
    prompt = prefill

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("🔍 Searching documents..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/query",
                    json={"query": prompt, "token": st.session_state.token},
                    timeout=45,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    answer    = data["answer"]
                    rtype     = data.get("response_type", "rag")
                    namespaces = data.get("namespaces_accessed", [])

                    st.markdown(answer)

                    # Build metadata display
                    rtype_emoji = {"rag": "📚", "sql": "🗄️", "blocked": "🚫", "upload": "📤"}.get(rtype, "💬")
                    meta_parts = [f"{rtype_emoji} `{rtype.upper()}`"]
                    if namespaces:
                        meta_parts.append(f"Sources: {', '.join(namespaces)}")
                    meta = " · ".join(meta_parts)

                    src_html = "".join(f'<span class="src-tag">📄 {s}</span>' for s in namespaces)
                    if src_html:
                        st.markdown(f"<small>{rtype_emoji} **{rtype.upper()}** &nbsp; {src_html}</small>", unsafe_allow_html=True)
                    else:
                        st.caption(meta)

                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": answer,
                        "meta": meta,
                    })

                elif resp.status_code == 401:
                    st.error("🔒 Session expired. Please log in again.")
                    st.session_state.clear()
                    st.rerun()
                else:
                    st.error(f"API error: {resp.text}")
            except requests.exceptions.ConnectionError:
                st.error("⚠️ Cannot reach the API server. Is uvicorn running?")


# ══════════════════════════════════════════════════════════════════════════
# ADMIN PANEL
# ══════════════════════════════════════════════════════════════════════════
if st.session_state.role == "admin":
    st.divider()
    st.markdown("### 🔐 Admin Panel")

    tab1, tab2, tab3 = st.tabs(["📋 Audit Logs", "📦 Document Collections", "🆕 Roles & Users"])

    with tab1:
        st.caption("All queries, uploads, and blocked attempts are logged here.")
        col_a, col_b = st.columns([1, 4])
        with col_a:
            limit = st.number_input("Rows", min_value=10, max_value=200, value=20, step=10)
        with col_b:
            refresh = st.button("🔄 Refresh Logs", use_container_width=False)

        if refresh:
            try:
                resp = requests.get(
                    f"{API_BASE}/admin/audit-logs",
                    params={"token": st.session_state.token, "limit": limit},
                    timeout=10,
                )
                if resp.status_code == 200:
                    import pandas as pd
                    logs = resp.json()
                    if logs:
                        df = pd.DataFrame(logs)
                        # Highlight blocked rows
                        def highlight_blocked(row):
                            if row.get("blocked"):
                                return ["background-color: #fee2e2"] * len(row)
                            return [""] * len(row)
                        st.dataframe(
                            df.style.apply(highlight_blocked, axis=1),
                            use_container_width=True,
                        )
                    else:
                        st.info("No audit logs yet.")
            except Exception as e:
                st.error(f"Failed to fetch logs: {e}")

    with tab2:
        st.caption("All document collections currently indexed in ChromaDB.")
        if st.button("🔄 Refresh Collections"):
            try:
                resp = requests.get(
                    f"{API_BASE}/collections",
                    params={"token": st.session_state.token},
                    timeout=10,
                )
                if resp.status_code == 200:
                    import pandas as pd
                    collections = resp.json()
                    if collections:
                        st.dataframe(
                            pd.DataFrame(collections),
                            use_container_width=True,
                        )
                        st.caption(f"Total collections: **{len(collections)}** | "
                                   f"Total chunks: **{sum(c['count'] for c in collections)}**")
                    else:
                        st.info("No collections found.")
            except Exception as e:
                st.error(f"Failed to fetch collections: {e}")

    with tab3:
        st.caption("Create new departments/roles and assign login credentials for them.")

        # Fetch current roles for display + dropdowns
        try:
            roles_resp = requests.get(
                f"{API_BASE}/admin/roles",
                params={"token": st.session_state.token},
                timeout=10,
            )
            existing_roles = roles_resp.json() if roles_resp.status_code == 200 else []
        except Exception:
            existing_roles = []

        col_role, col_user = st.columns(2, gap="large")

        # ── Create New Role ─────────────────────────────────────────────
        with col_role:
            st.markdown("#### Create New Role")
            with st.form("create_role_form", clear_on_submit=True):
                new_role_name = st.text_input("New Role Name", placeholder="e.g. Legal")
                add_role_submitted = st.form_submit_button("➕ Add Role", use_container_width=True)

            if add_role_submitted:
                if not new_role_name.strip():
                    st.warning("Please enter a role name.")
                else:
                    try:
                        resp = requests.post(
                            f"{API_BASE}/admin/roles",
                            json={
                                "token": st.session_state.token,
                                "role_name": new_role_name,
                                "namespaces": [],
                            },
                            timeout=10,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            st.success(f"✅ Role `{data['role_name']}` created.")
                            st.rerun()
                        else:
                            st.error(f"❌ {resp.json().get('detail', 'Failed to create role.')}")
                    except requests.exceptions.ConnectionError:
                        st.error("⚠️ Cannot reach the API server.")

            if existing_roles:
                st.markdown("**Existing Roles**")
                for r in existing_roles:
                    st.caption(f"`{r['role']}` — {len(r['namespaces'])} document namespace(s)")

        # ── Create New User (assign username/password to a role) ────────
        with col_user:
            st.markdown("#### Create New User")
            role_options = [r["role"] for r in existing_roles] or \
                ["hr", "finance", "engineering", "marketing", "admin"]

            with st.form("create_user_form", clear_on_submit=True):
                new_username = st.text_input("Username", placeholder="e.g. jordan")
                new_full_name = st.text_input("Full Name (optional)", placeholder="e.g. Jordan Lee")
                new_password = st.text_input("Password", type="password", placeholder="Min. 4 characters")
                new_user_role = st.selectbox("Assign Role", options=role_options)
                add_user_submitted = st.form_submit_button("➕ Add User", use_container_width=True)

            if add_user_submitted:
                if not new_username.strip() or not new_password:
                    st.warning("Please enter a username and password.")
                else:
                    try:
                        resp = requests.post(
                            f"{API_BASE}/admin/users",
                            json={
                                "token": st.session_state.token,
                                "username": new_username,
                                "password": new_password,
                                "role": new_user_role,
                                "full_name": new_full_name or None,
                            },
                            timeout=10,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            st.success(
                                f"✅ User `{data['username']}` created with role `{data['role'].upper()}`."
                            )
                            st.rerun()
                        else:
                            st.error(f"❌ {resp.json().get('detail', 'Failed to create user.')}")
                    except requests.exceptions.ConnectionError:
                        st.error("⚠️ Cannot reach the API server.")

            st.divider()
            st.markdown("**All Users**")
            try:
                users_resp = requests.get(
                    f"{API_BASE}/admin/users",
                    params={"token": st.session_state.token},
                    timeout=10,
                )
                if users_resp.status_code == 200:
                    for u in users_resp.json():
                        st.caption(f"`{u['username']}` ({u['full_name']}) → **{u['role'].upper()}**")
            except Exception:
                pass
