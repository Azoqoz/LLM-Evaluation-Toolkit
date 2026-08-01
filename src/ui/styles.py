"""Portfolio-grade Streamlit styling."""

APP_CSS = """
<style>
    .stApp {
        background:
            radial-gradient(circle at 78% -12%, rgba(96, 165, 250, .055), transparent 32rem),
            radial-gradient(circle at 0% 38%, rgba(167, 139, 250, .04), transparent 28rem),
            #090d12;
        color: #f2f5f4;
        color-scheme: dark;
    }
    [data-testid="stHeader"] {
        background: rgba(11, 15, 21, .94);
    }
    [data-testid="stSidebar"] {
        background: rgba(14, 19, 26, .98);
        border-right: 1px solid #2e3642;
        color-scheme: dark;
    }
    .block-container {
        max-width: 1180px;
        padding-top: 4.25rem;
    }
    h1, h2, h3 {letter-spacing: -.035em;}
    h1 {font-size: clamp(2.25rem, 5vw, 4.2rem) !important; line-height: .98 !important;}
    .eyebrow {
        color: #54c7b5; font-size: .78rem; font-weight: 700;
        letter-spacing: .16em; text-transform: uppercase; margin-bottom: .7rem;
    }
    .hero-copy {color: #9aa7a3; font-size: 1.08rem; max-width: 760px; line-height: 1.7;}
    .runtime-badge {
        display: inline-flex; align-items: center; gap: .45rem;
        border: 1px solid rgba(31,157,139,.34); border-radius: 999px;
        background: rgba(31,157,139,.09); color: #8bdaca;
        padding: .42rem .72rem; font-size: .78rem; margin-top: .8rem;
    }
    .runtime-badge::before {content:""; width:.45rem; height:.45rem; border-radius:50%; background:#1f9d8b;}
    .runtime-badge.demo {
        border-color: rgba(124, 155, 200, .36);
        background: rgba(96, 132, 184, .10);
        color: #aebfd8;
    }
    .runtime-badge.demo::before {background:#7c9bc8;}
    .sidebar-brand {padding: .18rem 0 .1rem;}
    .sidebar-brand-title {
        color: #f2f5f4; font-size: 1.12rem; font-weight: 720;
        letter-spacing: -.02em; line-height: 1.25;
    }
    .sidebar-brand-title span {color:#54c7b5; margin-right:.28rem;}
    .sidebar-brand-subtitle {
        color: #9aa7a3; font-size: .78rem; line-height: 1.5; margin-top: .38rem;
    }
    .sidebar-section-label {
        color: #7f8b98; font-size: .68rem; font-weight: 700;
        letter-spacing: .13em; text-transform: uppercase; margin-bottom: .55rem;
    }
    .mode-badge {
        display: inline-flex; border-radius: 999px; padding: .28rem .55rem;
        font-size: .66rem; font-weight: 760; letter-spacing: .08em;
    }
    .mode-badge.local {
        color: #8bdaca; background: rgba(31,157,139,.10);
        border: 1px solid rgba(31,157,139,.34);
    }
    .mode-badge.demo {
        color: #aebfd8; background: rgba(96,132,184,.10);
        border: 1px solid rgba(124,155,200,.36);
    }
    .sidebar-mode-copy {
        color: #dce2e0; font-size: .79rem; line-height: 1.5; margin: .58rem 0 .35rem;
    }
    .sidebar-mode-note {
        color: #8f9aa6; font-size: .73rem; line-height: 1.48; margin: 0;
    }
    .sidebar-mode-points {
        color: #9aa7a3; font-size: .73rem; line-height: 1.55;
        margin: .25rem 0 0; padding-left: 1.1rem;
    }
    .sidebar-mode-points li {margin: .08rem 0;}
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] p,
    [data-testid="stMarkdownContainer"],
    label {
        color: #f2f5f4;
    }
    [data-baseweb="textarea"],
    [data-baseweb="textarea"] textarea,
    [data-baseweb="input"],
    [data-baseweb="input"] input,
    [data-baseweb="select"] > div {
        background-color: #252631 !important;
        border-color: #3a414e !important;
        color: #f2f5f4 !important;
        caret-color: #54c7b5;
    }
    textarea::placeholder,
    input::placeholder {
        color: #8f98a6 !important;
        opacity: 1;
    }
    [data-testid="stFileUploaderDropzone"] {
        background: #171c25 !important;
        border-color: #374150 !important;
        color: #dce2e0 !important;
    }
    [data-testid="stFileUploaderDropzone"] button {
        background: #222834 !important;
        border: 1px solid #414b59 !important;
        color: #f2f5f4 !important;
    }
    [data-testid="stFileUploaderDropzone"] small,
    [data-testid="stFileUploaderDropzoneInstructions"] {
        color: #9aa7a3 !important;
    }
    [data-testid="stMetric"] {
        background: #10151d; border: 1px solid #2e3642;
        padding: 1rem 1.1rem; border-radius: 14px;
    }
    [data-testid="stMetricValue"] {color: #f2f5f4;}
    .st-key-batch_summary_passed [data-testid="stMetric"] {
        border-color: rgba(31, 157, 139, .52);
        background: linear-gradient(145deg, rgba(22, 57, 51, .72), #10151d 72%);
    }
    .st-key-batch_summary_passed [data-testid="stMetricValue"] {
        color: #8bdaca;
    }
    .st-key-batch_summary_failed [data-testid="stMetric"] {
        border-color: rgba(176, 83, 92, .50);
        background: linear-gradient(145deg, rgba(67, 34, 39, .72), #10151d 72%);
    }
    .st-key-batch_summary_failed [data-testid="stMetricValue"] {
        color: #efb1b7;
    }
    .result-status-badge {
        display: inline-flex; align-items: center; justify-content: center;
        min-width: 4.2rem; padding: .3rem .62rem; border-radius: 999px;
        font-size: .72rem; font-weight: 780; letter-spacing: .07em;
        margin-bottom: .65rem;
    }
    .result-status-badge.pass {
        color: #92e0d1; background: #153b35;
        border: 1px solid rgba(70, 183, 163, .48);
    }
    .result-status-badge.fail {
        color: #efb1b7; background: #452529;
        border: 1px solid rgba(190, 94, 104, .48);
    }
    div[data-testid="stForm"], div[data-testid="stExpander"] {
        border-color: #2e3642; background: rgba(16, 21, 29, .84);
        border-radius: 16px;
    }
    div[data-testid="stExpander"] details,
    div[data-testid="stExpander"] summary {
        background: transparent !important;
        color: #f2f5f4 !important;
    }
    [data-testid="stDataFrame"],
    [data-testid="stTable"],
    [data-testid="stVegaLiteChart"] {
        background: #10151d !important;
        border-color: #2e3642 !important;
        color: #f2f5f4 !important;
        color-scheme: dark;
    }
    [data-testid="stDataFrame"] canvas {
        color-scheme: dark;
    }
    [data-testid="stRadio"] label,
    [data-testid="stSlider"] label,
    [data-testid="stFileUploader"] label {
        color: #f2f5f4 !important;
    }
    .score-card {
        border: 1px solid #2e3642; background: #10151d;
        border-radius: 14px; padding: 1rem;
    }
    .muted {color:#9aa7a3; font-size:.9rem;}
    .stButton > button, .stDownloadButton > button {
        border-radius: 10px; font-weight: 650;
    }
    .st-key-single_action_group [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
        justify-content: center;
    }
    .st-key-single_run_evaluation button {
        background: #1f9d8b !important;
        border: 1px solid #39aa99 !important;
        color: #f7fffc !important;
        box-shadow: 0 6px 18px rgba(10, 88, 72, .22);
        transition: background-color .18s ease, border-color .18s ease,
                    box-shadow .18s ease, transform .18s ease;
    }
    .st-key-single_run_evaluation button:hover {
        background: #268f82 !important;
        border-color: #55b7a8 !important;
        box-shadow: 0 8px 22px rgba(10, 88, 72, .30);
        transform: translateY(-1px);
    }
    .st-key-single_run_evaluation button:focus-visible {
        outline: 2px solid rgba(84, 199, 181, .76);
        outline-offset: 2px;
    }
    .st-key-single_clear_fields button {
        background: #11161d !important;
        border: 1px solid #37404c !important;
        color: #dce2e0 !important;
    }
    .st-key-single_clear_fields button:hover {
        background: #1a202a !important;
        border-color: #566171 !important;
        color: #f2f5f4 !important;
    }
    @media (max-width: 640px) {
        .st-key-single_action_group [data-testid="stHorizontalBlock"] {
            align-items: stretch;
            flex-direction: column;
        }
        .st-key-single_action_group button {
            width: 100% !important;
        }
        [data-testid="stDataFrame"] {
            max-width: 100%;
            overflow: auto;
        }
    }
    footer {visibility:hidden;}
</style>
"""
