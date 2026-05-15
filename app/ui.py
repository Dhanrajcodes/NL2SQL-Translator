import json
from html import escape

import requests
import streamlit as st


API_BASE_URL = "http://localhost:5000"
GENERATION_DIALECTS = ["SQLite", "PostgreSQL", "MySQL", "SQL Server", "Oracle"]
THEMES = {
    "Night blue": {
        "page": "#07111d",
        "page_alt": "#0c2133",
        "sidebar": "#07101c",
        "panel": "#111d2f",
        "panel_2": "#0d2237",
        "field": "#0a1727",
        "field_hover": "#10243a",
        "text": "#f4f8fc",
        "muted": "#9fb3ca",
        "placeholder": "#7890ad",
        "border": "#263d5c",
        "accent": "#45b7e8",
        "accent_2": "#2f8bd3",
        "success": "#34d399",
        "tooltip": "#16263b",
        "tooltip_text": "#edf6ff",
        "shadow": "rgba(0, 0, 0, 0.32)",
    },
    "Sky blue": {
        "page": "#d8e8f3",
        "page_alt": "#c8dfec",
        "sidebar": "#e9f2f8",
        "panel": "#f4f8fb",
        "panel_2": "#e4f0f7",
        "field": "#f8fbfd",
        "field_hover": "#eef6fa",
        "text": "#142235",
        "muted": "#53697f",
        "placeholder": "#788aa0",
        "border": "#9fbcd2",
        "accent": "#2f80b9",
        "accent_2": "#246aa3",
        "success": "#24715e",
        "tooltip": "#edf5fa",
        "tooltip_text": "#172638",
        "shadow": "rgba(42, 92, 122, 0.12)",
    },
}


st.set_page_config(
    page_title="NL2SQL Studio",
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_styles(theme_name: str) -> None:
    theme = THEMES[theme_name]
    st.markdown(
        """
        <style>
        @import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;450;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap");

        :root {
            --page: __PAGE__;
            --page-alt: __PAGE_ALT__;
            --sidebar: __SIDEBAR__;
            --panel: __PANEL__;
            --panel-2: __PANEL_2__;
            --field: __FIELD__;
            --field-hover: __FIELD_HOVER__;
            --text: __TEXT__;
            --muted: __MUTED__;
            --placeholder: __PLACEHOLDER__;
            --border: __BORDER__;
            --accent: __ACCENT__;
            --accent-2: __ACCENT_2__;
            --success: __SUCCESS__;
            --tooltip: __TOOLTIP__;
            --tooltip-text: __TOOLTIP_TEXT__;
            --shadow: __SHADOW__;
            --font-sans: "IBM Plex Sans", "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
            --font-mono: "JetBrains Mono", "SFMono-Regular", Consolas, "Liberation Mono", monospace;
        }

        #MainMenu,
        footer,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"] {
            display: none;
        }

        [data-testid="stHeader"] {
            display: none !important;
        }

        html, body, .stApp {
            overflow-x: hidden;
        }

        .stApp {
            background:
                radial-gradient(circle at 82% -10%, color-mix(in srgb, var(--accent) 14%, transparent), transparent 34rem),
                linear-gradient(180deg, var(--page-alt) 0%, var(--page) 42%),
                var(--page);
            color: var(--text);
            font-family: var(--font-sans);
            font-optical-sizing: auto;
        }

        .stApp * {
            font-family: var(--font-sans);
            letter-spacing: 0;
        }

        .stApp [data-testid="stIconMaterial"],
        .stApp [class*="material-icons"],
        .stApp [class*="MaterialIcons"],
        .stApp [translate="no"],
        .stApp i {
            font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
            font-weight: normal !important;
            font-style: normal !important;
            letter-spacing: normal !important;
            text-transform: none !important;
            white-space: nowrap !important;
            word-wrap: normal !important;
            direction: ltr !important;
            -webkit-font-feature-settings: "liga";
            -webkit-font-smoothing: antialiased;
        }

        .block-container {
            max-width: 1240px;
            padding: 0.55rem 1.35rem 1.9rem;
        }

        [data-testid="stSidebar"] {
            background: var(--sidebar);
            border-right: 1px solid var(--border);
        }

        /* Keep sidebar permanently visible and remove collapse controls */
        [data-testid="stSidebarCollapseButton"],
        [data-testid="collapsedControl"],
        button[aria-label="Close sidebar"],
        button[aria-label="Open sidebar"] {
            display: none !important;
            visibility: hidden !important;
            pointer-events: none !important;
        }

        [data-testid="stSidebar"][aria-expanded="false"] {
            min-width: 20rem !important;
            max-width: 20rem !important;
            transform: translateX(0) !important;
            margin-left: 0 !important;
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span {
            color: var(--text);
        }

        h1, h2, h3, h4, h5, h6, p, label, span {
            color: var(--text);
        }

        .stCaptionContainer,
        [data-testid="stCaptionContainer"],
        [data-testid="stSidebar"] .stCaptionContainer,
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            color: var(--muted) !important;
        }

        hr {
            border-color: var(--border);
            margin: 0.75rem 0;
        }

        .app-header {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 18px;
            align-items: center;
            background: color-mix(in srgb, var(--panel) 94%, transparent);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 18px 20px;
            box-shadow: 0 18px 44px var(--shadow);
            margin-bottom: 14px;
        }

        .app-title {
            font-size: 30px;
            line-height: 1.1;
            font-weight: 700;
            margin: 0 0 6px 0;
            color: var(--text);
            letter-spacing: 0;
        }

        .app-subtitle {
            max-width: 850px;
            margin: 0;
            color: var(--muted);
            font-size: 14.5px;
            line-height: 1.48;
        }

        .status-stack {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 8px;
        }

        .chip {
            border: 1px solid var(--border);
            background: var(--panel-2);
            color: var(--text);
            border-radius: 999px;
            padding: 7px 10px;
            font-size: 12px;
            font-weight: 700;
            white-space: nowrap;
        }

        .feature-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 10px;
            margin: 12px 0 10px;
        }

        .feature-card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px 13px;
            box-shadow: 0 10px 28px var(--shadow);
        }

        .feature-card span {
            color: var(--muted);
            font-size: 12px;
        }

        .feature-card strong {
            display: block;
            color: var(--text);
            font-size: 17px;
            font-weight: 700;
            margin-top: 4px;
        }

        .section-title {
            font-size: 16px;
            font-weight: 700;
            color: var(--text);
            margin: 5px 0 7px;
        }

        .helper {
            color: var(--muted);
            font-size: 14px;
            line-height: 1.5;
        }

        .status-ok {
            color: var(--accent-2);
            font-weight: 800;
        }

        div[data-testid="stTabs"] button {
            color: var(--muted) !important;
            font-weight: 700;
            padding: 10px 14px;
        }

        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--accent) !important;
        }

        div[data-testid="stTabs"] div[data-baseweb="tab-highlight"] {
            background-color: var(--accent) !important;
        }

        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div,
        .stNumberInput input {
            background: var(--field) !important;
            border: 1px solid var(--border) !important;
            color: var(--text) !important;
            border-radius: 9px !important;
            box-shadow: inset 0 1px 0 color-mix(in srgb, white 5%, transparent);
            font-size: 14px !important;
            font-weight: 450 !important;
        }

        .stSelectbox div[data-baseweb="select"] > div,
        .stSelectbox div[data-baseweb="select"] input,
        .stSelectbox div[data-baseweb="select"] span,
        .stSelectbox div[data-baseweb="select"] div {
            color: var(--text) !important;
            opacity: 1 !important;
        }

        .stSelectbox div[data-baseweb="select"] input::placeholder,
        .stSelectbox div[data-baseweb="select"] [data-placeholder="true"] {
            color: var(--placeholder) !important;
            opacity: 1 !important;
        }

        .stTextInput input:focus,
        .stTextArea textarea:focus,
        .stNumberInput input:focus,
        .stSelectbox div[data-baseweb="select"] > div:focus-within {
            border-color: color-mix(in srgb, var(--accent) 72%, var(--border)) !important;
            box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 18%, transparent) !important;
        }

        .stTextArea textarea::placeholder,
        .stTextInput input::placeholder {
            color: var(--placeholder) !important;
            opacity: 1 !important;
            font-weight: 450 !important;
        }

        .stTextInput [data-testid="stTextInputRootElement"] {
            background: var(--field) !important;
            border: 1px solid var(--border) !important;
            border-radius: 9px !important;
            box-shadow: inset 0 1px 0 color-mix(in srgb, white 5%, transparent);
            overflow: hidden !important;
        }

        .stTextInput [data-baseweb="base-input"] {
            background: transparent !important;
        }

        .stTextInput [data-testid="stTextInputRootElement"] input {
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            min-height: 40px !important;
            color: var(--text) !important;
        }

        .stSelectbox [data-baseweb="popover"] ul,
        div[data-baseweb="popover"] ul,
        div[data-baseweb="menu"] {
            background: var(--panel) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            box-shadow: 0 18px 42px var(--shadow) !important;
        }

        .stSelectbox [data-baseweb="popover"] *,
        div[data-baseweb="popover"] *,
        div[data-baseweb="menu"] * {
            color: var(--text) !important;
        }

        div[role="listbox"],
        div[role="option"] {
            background: var(--panel) !important;
            color: var(--text) !important;
            opacity: 1 !important;
        }

        div[role="option"]:hover,
        div[role="option"][aria-selected="true"] {
            background: var(--field-hover) !important;
            color: var(--text) !important;
        }

        [data-testid="stExpander"] {
            background: var(--panel) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            overflow: hidden !important;
        }

        [data-testid="stExpander"] details {
            background: var(--panel) !important;
            color: var(--text) !important;
        }

        [data-testid="stExpander"] details summary {
            background: var(--panel-2) !important;
            color: var(--text) !important;
            border-radius: 9px 9px 0 0 !important;
        }

        [data-testid="stExpander"] details:not([open]) summary {
            border-radius: 9px !important;
        }

        [data-testid="stExpander"] details summary:hover {
            background: var(--field-hover) !important;
        }

        [data-testid="stExpander"] details summary * {
            color: var(--text) !important;
        }

        [data-testid="stExpander"] details summary p {
            font-weight: 750;
        }

        .stMarkdown code {
            background: var(--panel-2);
            color: var(--success);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 2px 6px;
            font-family: var(--font-mono);
            font-size: 0.86em;
        }

        .stButton > button {
            background: var(--panel-2);
            color: var(--text);
            border-radius: 9px;
            min-height: 43px;
            font-weight: 700;
            border: 1px solid var(--border);
        }

        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, var(--accent-2), var(--accent));
            color: white;
            border: 0;
        }

        .stButton > button:hover {
            border-color: var(--accent);
        }

        div[data-testid="stAlert"] {
            border-radius: 10px;
            background: var(--panel-2);
            color: var(--text);
            border-color: var(--border);
        }

        div[data-testid="stAlert"] * {
            color: var(--text) !important;
        }

        [data-testid="stCodeBlock"],
        .stCodeBlock {
            background: var(--field) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            overflow: hidden !important;
        }

        [data-testid="stCodeBlock"] pre,
        .stCodeBlock pre {
            border: 0 !important;
            border-radius: 10px;
            background: var(--field) !important;
            color: var(--text) !important;
        }

        [data-testid="stCodeBlock"] pre,
        [data-testid="stCodeBlock"] pre code,
        [data-testid="stCodeBlock"] span,
        .stCodeBlock pre,
        .stCodeBlock pre code,
        .stCodeBlock span {
            font-family: var(--font-mono) !important;
            background: transparent !important;
            color: var(--text) !important;
        }

        [data-testid="stCodeBlock"] button,
        .stCodeBlock button {
            background: var(--panel-2) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
        }

        [data-testid="stSpinner"] *,
        .stSpinner * {
            color: var(--text) !important;
        }

        .sql-result {
            background: var(--field);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 14px 16px;
            color: var(--text);
            box-shadow: inset 0 1px 0 color-mix(in srgb, white 5%, transparent);
            overflow-x: auto;
            margin: 2px 0 12px;
        }

        .sql-result code {
            background: transparent !important;
            border: 0 !important;
            color: var(--text) !important;
            font-family: var(--font-mono) !important;
            font-size: 13.5px;
            line-height: 1.65;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .stDataFrame {
            border: 1px solid var(--border);
            border-radius: 10px;
            overflow: hidden;
        }

        div[data-testid="stFileUploader"] section {
            background: var(--field);
            border: 1px dashed var(--border);
            border-radius: 10px;
        }

        div[data-testid="stFileUploader"] section * {
            color: var(--text) !important;
        }

        div[data-testid="stFileUploader"] button {
            background: var(--panel-2) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
        }

        button[aria-label="Show password text"],
        button[aria-label="Hide password text"] {
            background: transparent !important;
            color: var(--muted) !important;
            border: none !important;
            border-left: 1px solid var(--border) !important;
            border-radius: 0 !important;
            min-height: 38px !important;
            min-width: 38px !important;
            width: 38px !important;
            padding: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            flex-shrink: 0 !important;
            transition: color 0.15s ease, background 0.15s ease !important;
        }

        button[aria-label="Show password text"]:hover,
        button[aria-label="Hide password text"]:hover {
            background: color-mix(in srgb, var(--accent) 10%, transparent) !important;
            color: var(--accent) !important;
        }

        button[aria-label="Show password text"] svg,
        button[aria-label="Hide password text"] svg {
            width: 16px !important;
            height: 16px !important;
            opacity: 0.75;
        }

        .stTextInput:has(button[aria-label="Show password text"]) input,
        .stTextInput:has(button[aria-label="Hide password text"]) input {
            border-radius: 0 !important;
        }

        div[data-baseweb="tooltip"],
        div[data-baseweb="popover"] div[role="tooltip"],
        [data-testid="stTooltipContent"] {
            background: var(--tooltip) !important;
            color: var(--tooltip-text) !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            box-shadow: 0 14px 32px var(--shadow) !important;
            font-size: 12.5px !important;
            line-height: 1.45 !important;
        }

        div[data-baseweb="tooltip"] *,
        div[data-baseweb="popover"] div[role="tooltip"] *,
        [data-testid="stTooltipContent"] * {
            color: var(--tooltip-text) !important;
        }

        div[data-testid="stVerticalBlock"] > div:has(> div.element-container .section-title) {
            margin-top: 0;
        }

        @media (max-width: 900px) {
            .block-container {
                padding: 1rem;
            }
            .app-header {
                grid-template-columns: 1fr;
            }
            .status-stack {
                justify-content: flex-start;
            }
            .app-title {
                font-size: 30px;
            }
            .feature-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """
        .replace("__PAGE__", theme["page"])
        .replace("__PAGE_ALT__", theme["page_alt"])
        .replace("__SIDEBAR__", theme["sidebar"])
        .replace("__PANEL__", theme["panel"])
        .replace("__PANEL_2__", theme["panel_2"])
        .replace("__FIELD__", theme["field"])
        .replace("__FIELD_HOVER__", theme["field_hover"])
        .replace("__TEXT__", theme["text"])
        .replace("__MUTED__", theme["muted"])
        .replace("__PLACEHOLDER__", theme["placeholder"])
        .replace("__BORDER__", theme["border"])
        .replace("__ACCENT__", theme["accent"])
        .replace("__ACCENT_2__", theme["accent_2"])
        .replace("__SUCCESS__", theme["success"])
        .replace("__TOOLTIP__", theme["tooltip"])
        .replace("__TOOLTIP_TEXT__", theme["tooltip_text"])
        .replace("__SHADOW__", theme["shadow"]),
        unsafe_allow_html=True,
    )


def uploaded_file_payload(uploaded_file):
    return (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "application/octet-stream")


def post_with_db(endpoint: str, uploaded_file, form_data: dict, timeout: int = 120):
    return requests.post(
        f"{API_BASE_URL}{endpoint}",
        data=form_data,
        files={"db_file": uploaded_file_payload(uploaded_file)},
        headers={"Accept": "application/json"},
        timeout=timeout,
    )


def post_json(endpoint: str, payload: dict, timeout: int = 120):
    return requests.post(
        f"{API_BASE_URL}{endpoint}",
        json=payload,
        headers={"Accept": "application/json"},
        timeout=timeout,
    )


def schema_metrics(schema: dict) -> tuple[int, int, int]:
    tables = schema.get("tables", {})
    table_count = len(tables)
    column_count = sum(len(table.get("columns", [])) for table in tables.values())
    relationship_count = len(schema.get("relationships", []))
    return table_count, column_count, relationship_count


def render_schema(schema: dict) -> None:
    tables = schema.get("tables", {})
    if not tables:
        st.info("No tables found in this database.")
        return

    for table_name, table_info in tables.items():
        columns = table_info.get("columns", [])
        with st.expander(f"{table_name} - {len(columns)} columns", expanded=False):
            st.dataframe(
                [
                    {
                        "column": column["name"],
                        "type": column["type"],
                        "primary_key": column["primary_key"],
                        "nullable": column["nullable"],
                    }
                    for column in columns
                ],
                width="stretch",
                hide_index=True,
            )

    relationships = schema.get("relationships", [])
    if relationships:
        st.markdown('<div class="section-title">Relationships</div>', unsafe_allow_html=True)
        st.dataframe(relationships, width="stretch", hide_index=True)


def show_error_response(response) -> None:
    try:
        st.error(response.json().get("error", response.text))
    except ValueError:
        st.error(response.text)


def render_sql_result(sql: str) -> None:
    st.markdown(
        f'<div class="sql-result"><code>{escape(sql)}</code></div>',
        unsafe_allow_html=True,
    )


if "schema" not in st.session_state:
    st.session_state.schema = None
if "translation_result" not in st.session_state:
    st.session_state.translation_result = None
if "live_result" not in st.session_state:
    st.session_state.live_result = None
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Night blue"

interface_theme = st.sidebar.radio(
    "Interface theme",
    options=["Night blue", "Sky blue"],
    horizontal=True,
    key="theme_mode",
)

apply_styles(interface_theme)

with st.sidebar:
    st.markdown("## NL2SQL Studio")
    st.caption("Enterprise-style NL to SQL workbench")

    selected_model = st.selectbox(
        "Model",
        options=["gemma3:1b", "gemma3-nl2sql:latest"],
        index=0,
    )
    selected_dialect = st.selectbox(
        "SQL output dialect",
        options=GENERATION_DIALECTS,
        index=0,
        help="Generation can target these dialects. Live execution supports SQLite files and supported external database URLs.",
    )

    st.markdown("### Database")
    db_mode = st.radio(
        "Execution source",
        options=["SQLite file", "External connection"],
        horizontal=False,
    )
    uploaded_db = st.file_uploader(
        "SQLite database for schema/live results",
        type=["db", "sqlite", "sqlite3"],
        disabled=db_mode != "SQLite file",
    )
    connection_url = st.text_input(
        "External DB connection URL",
        type="password",
        placeholder="postgresql+psycopg://user:pass@host/db",
        disabled=db_mode != "External connection",
        help="Use a SQLAlchemy URL for PostgreSQL, MySQL/MariaDB, SQL Server, or Oracle.",
    )

    row_limit = st.slider("Live result row limit", min_value=10, max_value=500, value=100, step=10)

    if st.button("Inspect database", width="stretch"):
        if db_mode == "SQLite file" and uploaded_db is None:
            st.error("Upload a SQLite database first.")
        elif db_mode == "External connection" and not connection_url.strip():
            st.error("Enter a database connection URL first.")
        else:
            with st.spinner("Extracting schema..."):
                try:
                    if db_mode == "SQLite file":
                        response = post_with_db("/schema", uploaded_db, {})
                    else:
                        response = post_json("/connection_schema", {"connection_url": connection_url})
                    if response.status_code == 200:
                        st.session_state.schema = response.json()["schema"]
                        st.success("Schema loaded")
                    else:
                        show_error_response(response)
                except requests.exceptions.ConnectionError:
                    st.error("Backend is not running.")
                except Exception as exc:
                    st.error(f"Schema inspection failed: {exc}")

    st.divider()
    if st.button("Check backend", width="stretch"):
        try:
            health = requests.get(f"{API_BASE_URL}/health", timeout=10)
            if health.status_code == 200:
                st.success("Backend is running")
            else:
                st.error("Backend returned an error")
        except requests.exceptions.ConnectionError:
            st.error("Backend is not running")

st.markdown(
    """
    <div class="app-header">
        <div>
            <div class="app-title">Natural language to SQL translator</div>
            <p class="app-subtitle">Translate English questions into SQL, inspect database schemas, and run safe read-only queries on SQLite files or external SQL databases.</p>
        </div>
        <div class="status-stack">
            <div class="chip">Local Ollama</div>
            <div class="chip">5 dialects</div>
            <div class="chip">Read-only execution</div>
        </div>
    </div>
    <div class="feature-grid">
        <div class="feature-card"><span>Default workflow</span><strong>NL to SQL</strong></div>
        <div class="feature-card"><span>Live execution</span><strong>5 DB families</strong></div>
        <div class="feature-card"><span>Generation dialects</span><strong>5 options</strong></div>
        <div class="feature-card"><span>Query safety</span><strong>Read-only SELECT</strong></div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.schema:
    tables, columns, relationships = schema_metrics(st.session_state.schema)
    st.caption(f"Loaded schema: {tables} tables, {columns} columns, {relationships} relationships")


tab_translate, tab_live, tab_schema, tab_about = st.tabs(
    ["NL to SQL", "Live DB output", "Database schema", "Project features"]
)

with tab_translate:
    left, right = st.columns([0.95, 1.05], gap="large")

    with left:
        st.markdown('<div class="section-title">Translate English into SQL</div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="helper">This is the main project feature. A database upload is optional here, but using schema gives better table and column names.</p>',
            unsafe_allow_html=True,
        )
        question = st.text_area(
            "Natural language question",
            height=155,
            placeholder="Example: Show all employees with salary above 70000",
        )

        use_uploaded_schema = st.checkbox(
            "Use uploaded database schema if available",
            value=True,
        )

        with st.expander("Manual schema JSON", expanded=False):
            manual_schema = st.text_area(
                "Optional manual schema JSON",
                height=150,
                placeholder='{"tables": {"employees": {"columns": [{"name": "id", "type": "INTEGER"}], "foreign_keys": [], "primary_key": ["id"]}}, "relationships": []}',
            )

        if st.button("Generate SQL", type="primary", width="stretch"):
            if not question.strip():
                st.error("Enter a natural language question.")
            else:
                payload = {
                    "question": question.strip(),
                    "model": selected_model,
                    "dialect": selected_dialect,
                }

                if manual_schema.strip():
                    try:
                        payload["schema"] = json.loads(manual_schema)
                    except json.JSONDecodeError:
                        st.error("Manual schema must be valid JSON.")
                        st.stop()

                try:
                    with st.spinner("Preparing model and generating SQL..."):
                        if uploaded_db is not None and use_uploaded_schema and "schema" not in payload:
                            response = post_with_db(
                                "/translate",
                                uploaded_db,
                                {
                                    "question": question.strip(),
                                    "model": selected_model,
                                    "dialect": selected_dialect,
                                },
                            )
                        else:
                            response = requests.post(
                                f"{API_BASE_URL}/translate",
                                json=payload,
                                headers={"Accept": "application/json"},
                                timeout=120,
                            )

                    if response.status_code == 200:
                        st.session_state.translation_result = response.json()
                    else:
                        show_error_response(response)
                except requests.exceptions.ConnectionError:
                    st.error("Backend is not running. Start it with `python run_project.py`.")
                except requests.exceptions.Timeout:
                    st.error("The request timed out. Check whether Ollama is running.")
                except Exception as exc:
                    st.error(f"Translation failed: {exc}")

    with right:
        st.markdown('<div class="section-title">Generated SQL</div>', unsafe_allow_html=True)
        result = st.session_state.translation_result
        if result:
            render_sql_result(result["sql"])
            st.caption(f"Dialect: {result.get('dialect', selected_dialect)}")
            if result.get("schema_used"):
                st.success("Schema-aware generation was used.")
            else:
                st.info("Generated without database schema.")
            st.caption(f"Question: {result['question']}")
        else:
            st.info("Ask a question to generate SQL.")

        st.markdown('<div class="section-title">Supported SQL information</div>', unsafe_allow_html=True)
        st.markdown(
            """
            - SQL generation can be prompted for 5 dialects: SQLite, PostgreSQL, MySQL, SQL Server, and Oracle.
            - Live execution supports SQLite files and external URLs for PostgreSQL, MySQL/MariaDB, SQL Server, and Oracle when the matching driver is installed.
            - The execution layer blocks write operations such as `INSERT`, `UPDATE`, `DELETE`, and `DROP`.
            """
        )

with tab_live:
    left, right = st.columns([0.95, 1.05], gap="large")

    with left:
        st.markdown('<div class="section-title">Generate SQL and run it on a database</div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="helper">Use this for demos where the professor can see real rows coming from a database.</p>',
            unsafe_allow_html=True,
        )
        live_question = st.text_area(
            "Question for live database",
            height=155,
            placeholder="Example: Show all employees with salary above 70000",
        )

        if st.button("Generate and show live output", type="primary", width="stretch"):
            if db_mode == "SQLite file" and uploaded_db is None:
                st.error("Upload a SQLite database first.")
            elif db_mode == "External connection" and not connection_url.strip():
                st.error("Enter a database connection URL first.")
            elif not live_question.strip():
                st.error("Enter a question first.")
            else:
                form_data = {
                    "question": live_question.strip(),
                    "model": selected_model,
                    "row_limit": str(row_limit),
                }
                with st.spinner("Generating SQL and running read-only query..."):
                    try:
                        if db_mode == "SQLite file":
                            response = post_with_db("/query", uploaded_db, form_data)
                        else:
                            response = post_json(
                                "/query_connection",
                                {
                                    "question": live_question.strip(),
                                    "model": selected_model,
                                    "dialect": selected_dialect,
                                    "connection_url": connection_url,
                                    "row_limit": str(row_limit),
                                },
                            )
                        if response.status_code == 200:
                            st.session_state.live_result = response.json()
                            st.session_state.schema = st.session_state.live_result.get("schema")
                        else:
                            show_error_response(response)
                    except requests.exceptions.ConnectionError:
                        st.error("Backend is not running. Start it with `python run_project.py`.")
                    except requests.exceptions.Timeout:
                        st.error("The request timed out. Check whether Ollama is running.")
                    except Exception as exc:
                        st.error(f"Live query failed: {exc}")

    with right:
        st.markdown('<div class="section-title">Live database result</div>', unsafe_allow_html=True)
        live = st.session_state.live_result
        if live:
            render_sql_result(live["sql"])
            execution = live.get("execution", {})
            st.markdown(
                f'<p class="status-ok">Returned {execution.get("row_count", 0)} rows from {live.get("dialect", "database")}.</p>',
                unsafe_allow_html=True,
            )
            rows = execution.get("rows", [])
            if rows:
                st.dataframe(rows, width="stretch", hide_index=True)
            else:
                st.info("The query ran successfully but returned no rows.")
        else:
            st.info("Choose a database source and run a live question.")

    st.divider()
    st.markdown('<div class="section-title">Edit and run SQL manually</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="helper">Use this after generation if you want to correct table names or test a custom SQLite SELECT query.</p>',
        unsafe_allow_html=True,
    )
    default_sql = ""
    if st.session_state.live_result:
        default_sql = st.session_state.live_result.get("sql", "")
    elif st.session_state.translation_result:
        default_sql = st.session_state.translation_result.get("sql", "")

    manual_sql = st.text_area(
        "SQLite SELECT query",
        value=default_sql,
        height=120,
        placeholder="SELECT * FROM employees LIMIT 10;",
    )

    if st.button("Run edited SQL", width="stretch"):
        if db_mode == "SQLite file" and uploaded_db is None:
            st.error("Upload a SQLite database first.")
        elif db_mode == "External connection" and not connection_url.strip():
            st.error("Enter a database connection URL first.")
        elif not manual_sql.strip():
            st.error("Enter a SELECT query first.")
        else:
            with st.spinner("Running read-only SQL..."):
                try:
                    if db_mode == "SQLite file":
                        response = post_with_db(
                            "/execute_sql",
                            uploaded_db,
                            {"sql": manual_sql.strip(), "row_limit": str(row_limit)},
                        )
                    else:
                        response = post_json(
                            "/execute_connection_sql",
                            {
                                "connection_url": connection_url,
                                "sql": manual_sql.strip(),
                                "row_limit": str(row_limit),
                            },
                        )
                    if response.status_code == 200:
                        st.session_state.live_result = response.json()
                        execution = st.session_state.live_result.get("execution", {})
                        st.success(f"Returned {execution.get('row_count', 0)} rows.")
                        rows = execution.get("rows", [])
                        if rows:
                            st.dataframe(rows, width="stretch", hide_index=True)
                    else:
                        show_error_response(response)
                except requests.exceptions.ConnectionError:
                    st.error("Backend is not running. Start it with `python run_project.py`.")
                except Exception as exc:
                    st.error(f"Manual execution failed: {exc}")

with tab_schema:
    st.markdown('<div class="section-title">Database schema viewer</div>', unsafe_allow_html=True)
    if st.session_state.schema:
        render_schema(st.session_state.schema)
    elif db_mode == "SQLite file" and uploaded_db is None:
        st.info("Upload a SQLite database from the sidebar.")
    elif db_mode == "External connection" and not connection_url.strip():
        st.info("Enter an external database connection URL from the sidebar.")
    else:
        st.info("Click `Inspect database` in the sidebar to load schema details.")

with tab_about:
    st.markdown("### Project feature summary")
    st.markdown(
        """
        This project is built for **Natural Language to SQL translation** using a local Ollama model.

        Current strong features:
        - NL question to SQL generation
        - Dialect-prompted output for SQLite, PostgreSQL, MySQL, SQL Server, and Oracle
        - Schema-aware prompting from uploaded SQLite databases
        - Live read-only execution for SQLite, PostgreSQL, MySQL/MariaDB, SQL Server, and Oracle
        - Manual edit-and-run SQL execution for read-only SELECT queries
        - Basic schema viewer for tables, columns, primary keys, and relationships
        - Fine-tuning preparation scripts for Spider/WikiSQL style datasets

        Suggested future improvements:
        - Add query history and CSV export for result tables
        - Add SQL error repair when the first generated query fails
        - Add execution accuracy evaluation, not only text match
        - Add saved connection profiles without exposing passwords in the UI
        - Add a short demo video and screenshots in the README
        """
    )
