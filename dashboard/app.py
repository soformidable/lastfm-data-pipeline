import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path
from datetime import timedelta
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.genre_analysis import get_artist_genres, get_genre_trends_by_period, parse_genres_json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.database import get_engine

# ─────────────────────────────────────────────
#  Page config — must be first Streamlit call
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Scrobble.space",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  Global CSS — dark vinyl aesthetic
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

:root {
    --bg:        #0c0c0f;
    --surface:   #13131a;
    --surface2:  #1c1c28;
    --border:    #2a2a3a;
    --accent:    #e8365d;
    --accent2:   #ff8c42;
    --accent3:   #7c6af7;
    --text:      #e8e6f0;
    --muted:     #7a788a;
    --serif:     'DM Serif Display', serif;
    --mono:      'DM Mono', monospace;
    --sans:      'DM Sans', sans-serif;
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--sans) !important;
}

[data-testid="stSidebar"] {
    background-color: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* Date input — fix white background / white text in dark theme */
[data-testid="stSidebar"] [data-baseweb="input"],
[data-testid="stSidebar"] [data-baseweb="base-input"],
[data-testid="stSidebar"] input[type="text"] {
    background-color: var(--surface2) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}
[data-testid="stSidebar"] [data-baseweb="input"]:focus-within,
[data-testid="stSidebar"] [data-baseweb="base-input"]:focus-within {
    border-color: var(--accent) !important;
}
/* Calendar popover */
[data-baseweb="calendar"],
[data-baseweb="popover"] [data-baseweb="calendar"] {
    background-color: var(--surface2) !important;
    border: 1px solid var(--border) !important;
}
[data-baseweb="calendar"] button,
[data-baseweb="calendar"] [role="option"] {
    background-color: transparent !important;
    color: var(--text) !important;
}
[data-baseweb="calendar"] button:hover,
[data-baseweb="calendar"] [role="option"]:hover {
    background-color: var(--border) !important;
}
[data-baseweb="calendar"] [aria-selected="true"] {
    background-color: var(--accent) !important;
    color: #fff !important;
}

/* Hide default header */
header[data-testid="stHeader"] { display: none; }

h1, h2, h3 { font-family: var(--serif) !important; }

/* Metric cards */
[data-testid="metric-container"] {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1.2rem 1.4rem !important;
}
[data-testid="metric-container"] label {
    color: var(--muted) !important;
    font-family: var(--mono) !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--text) !important;
    font-family: var(--serif) !important;
    font-size: 1.9rem !important;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-family: var(--mono) !important;
    font-size: 0.78rem !important;
}

/* Section headers */
.section-label {
    font-family: var(--mono);
    font-size: 0.7rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 0.3rem;
}
.section-title {
    font-family: var(--serif);
    font-size: 1.8rem;
    color: var(--text);
    margin-bottom: 1.2rem;
    line-height: 1.1;
}

/* Divider */
.divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 2.5rem 0;
}

/* Hero banner */
.hero {
    background: linear-gradient(135deg, #13131a 0%, #1a0d1f 50%, #0d0d1a 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 2.4rem 2.8rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '◉';
    position: absolute;
    right: 2rem;
    top: 50%;
    transform: translateY(-50%);
    font-size: 7rem;
    color: var(--border);
    line-height: 1;
    pointer-events: none;
}
.hero-title {
    font-family: var(--serif);
    font-size: 2.6rem;
    color: var(--text);
    margin: 0 0 0.3rem 0;
    line-height: 1.05;
}
.hero-sub {
    font-family: var(--mono);
    font-size: 0.78rem;
    color: var(--muted);
    letter-spacing: 0.1em;
}
.hero-accent { color: var(--accent); }

/* Rank table */
.rank-table { width: 100%; border-collapse: collapse; }
.rank-table tr { border-bottom: 1px solid var(--border); }
.rank-table tr:last-child { border-bottom: none; }
.rank-table td {
    padding: 0.65rem 0.5rem;
    font-family: var(--sans);
    font-size: 0.9rem;
    color: var(--text);
}
.rank-num {
    font-family: var(--mono);
    color: var(--muted);
    font-size: 0.78rem;
    width: 28px;
    text-align: right;
    padding-right: 0.8rem !important;
}
.rank-count {
    font-family: var(--mono);
    color: var(--accent);
    font-size: 0.85rem;
    text-align: right;
    white-space: nowrap;
}
.rank-bar-cell { width: 80px; padding-left: 0.8rem !important; }
.rank-bar-bg {
    background: var(--border);
    border-radius: 99px;
    height: 4px;
    width: 100%;
}
.rank-bar-fill {
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    border-radius: 99px;
    height: 4px;
}

/* Card wrapper */
.card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    height: 100%;
}
.card-label {
    font-family: var(--mono);
    font-size: 0.68rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.6rem;
}
.card-value {
    font-family: var(--serif);
    font-size: 1.5rem;
    color: var(--text);
    margin-bottom: 0.2rem;
    line-height: 1.2;
}
.card-sub {
    font-family: var(--sans);
    font-size: 0.8rem;
    color: var(--muted);
}

/* Scrollable leaderboard container */
.leaderboard-scroll {
    max-height: 340px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
}

/* Plotly chart background */
.js-plotly-plot { border-radius: 12px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────
def _time_to_str(t):
    if hasattr(t, "strftime"):
        return t.strftime("%H:%M:%S")
    s = str(t)
    return s.split(" days ")[-1] if " days " in s else s


PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="#e8e6f0", size=12),
    margin=dict(l=16, r=16, t=40, b=16),
    colorway=["#e8365d", "#ff8c42", "#7c6af7", "#4ecdc4", "#ffe66d", "#a8edea"],
    xaxis=dict(gridcolor="#2a2a3a", linecolor="#2a2a3a", tickfont=dict(size=11)),
    yaxis=dict(gridcolor="#2a2a3a", linecolor="#2a2a3a", tickfont=dict(size=11)),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#2a2a3a"),
)

def apply_layout(fig, **kwargs):
    layout = {**PLOT_LAYOUT, **kwargs}
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────
#  Data loading
# ─────────────────────────────────────────────
@st.cache_data(ttl=600)
def load_scrobbles() -> pd.DataFrame:
    engine = get_engine()
    df = pd.read_sql("SELECT * FROM lastfm_scrobbles", engine)
    if df.empty:
        return df
    df["Played_At"] = pd.to_datetime(
        df["Date_played"].astype(str) + " " + df["Time_played"].apply(_time_to_str)
    )
    df["Month"]     = df["Played_At"].dt.to_period("M").astype(str)
    df["DayOfWeek"] = df["Played_At"].dt.dayofweek
    df["Hour"]      = df["Played_At"].dt.hour
    df["Week"]      = df["Played_At"].dt.to_period("W").apply(lambda p: str(p.start_time.date()))
    df["Year"]      = df["Played_At"].dt.year
    return df


# ─────────────────────────────────────────────
#  Load + gate
# ─────────────────────────────────────────────
df_full = load_scrobbles()
if df_full.empty:
    st.warning("No scrobbles found. Run the fetch script first.")
    st.stop()

# ─────────────────────────────────────────────
#  Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='font-family:var(--serif);font-size:1.4rem;margin-bottom:1.2rem;'>
        🎵 scrobble.space
    </div>
    """, unsafe_allow_html=True)

    min_date = df_full["Played_At"].min().date()
    max_date = df_full["Played_At"].max().date()

    date_range = st.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    st.markdown("---")

    top_n = st.slider("Top N for leaderboards", min_value=5, max_value=25, value=10, step=5)

    st.markdown("---")
    view_mode = st.radio("Trend granularity", ["Monthly", "Weekly"], index=0)

    st.markdown("---")
    st.markdown(f"<span style='font-family:var(--mono);font-size:0.72rem;color:var(--muted);'>TOTAL IN DB</span>", unsafe_allow_html=True)
    st.markdown(f"<span style='font-family:var(--serif);font-size:1.5rem;'>{len(df_full):,}</span> scrobbles", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Filter by date
# ─────────────────────────────────────────────
if len(date_range) == 2:
    start_date, end_date = date_range
    df = df_full[
        (df_full["Played_At"].dt.date >= start_date) &
        (df_full["Played_At"].dt.date <= end_date)
    ].copy()
else:
    df = df_full.copy()

if df.empty:
    st.warning("No scrobbles in selected date range.")
    st.stop()

# ─────────────────────────────────────────────
#  Derived stats
# ─────────────────────────────────────────────
total_scrobbles   = len(df)
unique_artists    = df["Artist"].nunique()
unique_tracks     = df["Track"].nunique()
unique_albums     = df["Album"].nunique()

days_span         = max((df["Played_At"].max() - df["Played_At"].min()).days, 1)
avg_per_day       = round(total_scrobbles / days_span, 1)

top_artist_name   = df["Artist"].value_counts().idxmax()
top_artist_plays  = df["Artist"].value_counts().max()

top_track_name    = df["Track"].value_counts().idxmax()
top_track_plays   = df["Track"].value_counts().max()

latest_row        = df.loc[df["Played_At"].idxmax()]
latest_str        = latest_row["Played_At"].strftime("%d %b %Y, %H:%M")

# Discovery: tracks heard only once
one_hit           = (df["Track"].value_counts() == 1).sum()

# Most active hour
top_hour          = df["Hour"].value_counts().idxmax()
top_hour_str      = f"{top_hour:02d}:00 – {top_hour+1:02d}:00"

# Average listening session length (gap > 30 min = new session)
df_sorted         = df.sort_values("Played_At")
gaps              = df_sorted["Played_At"].diff()
session_starts    = (gaps > timedelta(minutes=30)) | gaps.isna()
df_sorted["SessionID"] = session_starts.cumsum()
session_lengths   = df_sorted.groupby("SessionID")["Played_At"].agg(lambda x: (x.max() - x.min()).total_seconds() / 60)
avg_session_min   = round(session_lengths.mean(), 0)
total_sessions    = df_sorted["SessionID"].nunique()

# 30-day vs prior 30-day comparison
now               = df["Played_At"].max()
last30            = df[df["Played_At"] >= now - timedelta(days=30)]
prev30            = df[(df["Played_At"] >= now - timedelta(days=60)) & (df["Played_At"] < now - timedelta(days=30))]
delta_pct         = round(((len(last30) - len(prev30)) / max(len(prev30), 1)) * 100, 1)

# ─────────────────────────────────────────────
#  HERO
# ─────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
    <div class="hero-title">Your listening, <span class="hero-accent">visualised.</span></div>
    <div class="hero-sub">
        {start_date.strftime("%d %b %Y")} → {end_date.strftime("%d %b %Y")} &nbsp;·&nbsp;
        {total_scrobbles:,} scrobbles &nbsp;·&nbsp;
        Last played: {latest_str}
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  KPI row
# ─────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Scrobbles",    f"{total_scrobbles:,}",     f"{delta_pct:+.1f}% vs prev 30d")
c2.metric("Unique Artists",     f"{unique_artists:,}")
c3.metric("Unique Tracks",      f"{unique_tracks:,}")
c4.metric("Avg / Day",          f"{avg_per_day}")
c5.metric("Listening Sessions", f"{total_sessions:,}",      f"~{int(avg_session_min)} min avg")
c6.metric("Peak Hour",          top_hour_str)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  Trend chart
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">over time</div>', unsafe_allow_html=True)
st.markdown(f'<div class="section-title">Scrobble Trend</div>', unsafe_allow_html=True)

period_col = "Month" if view_mode == "Monthly" else "Week"
trend = df.groupby(period_col).size().reset_index(name="Count").sort_values(period_col)
trend["Rolling"] = trend["Count"].rolling(3, min_periods=1).mean().round(1)

fig_trend = go.Figure()
fig_trend.add_trace(go.Bar(
    x=trend[period_col], y=trend["Count"],
    name="Scrobbles", marker_color="#e8365d", opacity=0.55,
))
fig_trend.add_trace(go.Scatter(
    x=trend[period_col], y=trend["Rolling"],
    name="3-period avg", line=dict(color="#ff8c42", width=2.5),
    mode="lines",
))
apply_layout(fig_trend, title=None, xaxis_tickangle=-45,
             legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig_trend, use_container_width=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  Leaderboards
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">leaderboards</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Top Artists & Tracks</div>', unsafe_allow_html=True)

col_a, col_t = st.columns(2)

def render_leaderboard(counts: pd.Series, label: str):
    top = counts.head(top_n)
    max_count = top.max()
    rows = ""
    for i, (name, count) in enumerate(top.items(), 1):
        pct = int(count / max_count * 100)
        rows += f"""
        <tr>
            <td class="rank-num">{i}</td>
            <td>{name}</td>
            <td class="rank-count">{count:,}</td>
            <td class="rank-bar-cell">
                <div class="rank-bar-bg">
                    <div class="rank-bar-fill" style="width:{pct}%"></div>
                </div>
            </td>
        </tr>"""
    st.markdown(f"""
    <div class="card">
        <div class="card-label">{label}</div>
        <div class="leaderboard-scroll">
            <table class="rank-table">{rows}</table>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_a:
    render_leaderboard(df["Artist"].value_counts(), f"Top {top_n} Artists")

with col_t:
    render_leaderboard(df["Track"].value_counts(), f"Top {top_n} Tracks")

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  Top artist by month + discovery rate
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">month by month</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Artist Dominance & Discovery</div>', unsafe_allow_html=True)

col_l, col_r = st.columns([3, 2])

with col_l:
    artist_month = (
        df.groupby(["Month", "Artist"])
        .size()
        .reset_index(name="Count")
        .sort_values(["Month", "Count"], ascending=[True, False])
    )
    top_per_month = artist_month.groupby("Month").head(1).reset_index(drop=True)

    fig_dom = px.bar(
        top_per_month, x="Month", y="Count", color="Artist", text="Artist",
        color_discrete_sequence=["#e8365d","#ff8c42","#7c6af7","#4ecdc4","#ffe66d","#a8edea",
                                  "#f72585","#4cc9f0","#f9c74f","#90be6d","#43aa8b","#577590"],
    )
    fig_dom.update_traces(textposition="outside", textfont_size=9)
    apply_layout(fig_dom, title="Most played artist per month", showlegend=False, xaxis_tickangle=-45)
    st.plotly_chart(fig_dom, use_container_width=True)

with col_r:
    # New artists discovered each month (first appearance)
    first_seen = df.groupby("Artist")["Month"].min().reset_index()
    first_seen.columns = ["Artist", "Month"]
    discovery = first_seen.groupby("Month").size().reset_index(name="New Artists")
    discovery = discovery.sort_values("Month")

    fig_disc = px.area(
        discovery, x="Month", y="New Artists",
        color_discrete_sequence=["#7c6af7"],
    )
    fig_disc.update_traces(fill="tozeroy", fillcolor="rgba(124,106,247,0.18)", line_color="#7c6af7")
    apply_layout(fig_disc, title="New artists discovered per month", xaxis_tickangle=-45)
    st.plotly_chart(fig_disc, use_container_width=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  Heatmap
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">listening patterns</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">When Do You Listen?</div>', unsafe_allow_html=True)

day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
heat_data = (
    df.groupby(["DayOfWeek", "Hour"])
    .size()
    .unstack(fill_value=0)
    .reindex(range(7), fill_value=0)
    .reindex(columns=range(24), fill_value=0)
)

fig_heat = go.Figure(go.Heatmap(
    z=heat_data.values,
    x=[f"{h:02d}:00" for h in range(24)],
    y=day_labels,
    colorscale=[[0, "#13131a"], [0.3, "#3d1a2e"], [0.6, "#a0194a"], [1, "#e8365d"]],
    hovertemplate="<b>%{y} %{x}</b><br>%{z} scrobbles<extra></extra>",
    showscale=True,
))
apply_layout(fig_heat,
    title=None,
    xaxis=dict(tickfont=dict(size=10), gridcolor="rgba(0,0,0,0)"),
    yaxis=dict(tickfont=dict(size=11), gridcolor="rgba(0,0,0,0)"),
    height=300,
    margin=dict(l=16, r=16, t=16, b=16),
)
st.plotly_chart(fig_heat, use_container_width=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  Deep dive: Artist explorer
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">deep dive</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Artist Explorer</div>', unsafe_allow_html=True)

all_artists = sorted(df["Artist"].dropna().unique())
default_ix  = all_artists.index(top_artist_name) if top_artist_name in all_artists else 0
selected    = st.selectbox("Pick an artist", all_artists, index=default_ix)

adf = df[df["Artist"] == selected].copy()

ea1, ea2, ea3, ea4 = st.columns(4)
ea1.metric("Total Plays",     f"{len(adf):,}")
ea2.metric("Unique Tracks",   f"{adf['Track'].nunique():,}")
ea3.metric("Unique Albums",   f"{adf['Album'].nunique():,}")
first_heard = adf["Played_At"].min().strftime("%d %b %Y")
ea4.metric("First Scrobbled", first_heard)

col_1, col_2 = st.columns(2)

with col_1:
    a_monthly = adf.groupby("Month").size().reset_index(name="Plays").sort_values("Month")
    fig_a = px.line(a_monthly, x="Month", y="Plays", markers=True,
                    color_discrete_sequence=["#e8365d"])
    fig_a.update_traces(line_width=2.5, marker_size=5)
    apply_layout(fig_a, title=f"{selected} — plays over time", xaxis_tickangle=-45)
    st.plotly_chart(fig_a, use_container_width=True)

with col_2:
    top_tracks = adf["Track"].value_counts().head(10).reset_index()
    top_tracks.columns = ["Track", "Plays"]
    fig_tt = px.bar(top_tracks, x="Plays", y="Track", orientation="h",
                    color_discrete_sequence=["#ff8c42"])
    fig_tt.update_layout(yaxis=dict(autorange="reversed"))
    apply_layout(fig_tt, title=f"Top tracks — {selected}")
    st.plotly_chart(fig_tt, use_container_width=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# Then add this section to your dashboard after the "Artist Explorer" section:

# ─────────────────────────────────────────────
#  Genre Analysis
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">genre analysis</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Genres by Artist</div>', unsafe_allow_html=True)

# Parse genres from the filtered dataframe
df["Genres_parsed"] = df["Genres"].apply(parse_genres_json)

# Get all genres from filtered data
all_genres_filtered = []
for genres_list in df["Genres_parsed"]:
    all_genres_filtered.extend(genres_list)

# Top genres overall (filtered by date range)
genre_counter = pd.Series(all_genres_filtered).value_counts()
top_genres_df = genre_counter.head(15).reset_index()
top_genres_df.columns = ["Genre", "Plays"]

col_tg, col_ga = st.columns([2, 3])

with col_tg:
    fig_genres = px.bar(
        top_genres_df, x="Plays", y="Genre", orientation="h",
        color_discrete_sequence=["#7c6af7"]
    )
    fig_genres.update_layout(yaxis=dict(autorange="reversed"))
    apply_layout(fig_genres, title="Top 15 Genres (by play count)")
    st.plotly_chart(fig_genres, use_container_width=True)

with col_ga:
    # Artist -> Genre mapping
    artist_genre_map = {}
    for _, row in df.iterrows():
        artist = row["Artist"]
        genres = row["Genres_parsed"]
        
        if artist not in artist_genre_map:
            artist_genre_map[artist] = []
        artist_genre_map[artist].extend(genres)
    
    # Show top artist and their genres
    if top_artist_name in artist_genre_map:
        top_artist_genres = artist_genre_map[top_artist_name]
        if top_artist_genres:
            genre_dist = pd.Series(top_artist_genres).value_counts().head(5)
            st.markdown(f"""
            <div class="card">
                <div class="card-label">Top Artist's Genres</div>
                <div class="card-value">{top_artist_name}</div>
                <div class="card-sub">Primary genres in your listening</div>
            """, unsafe_allow_html=True)
            
            for genre, count in genre_dist.items():
                st.markdown(f"<p style='margin:0.3rem 0;'><strong>{genre}</strong> ({count} scrobbles)</p>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  Genre Evolution
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">genre trends</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Genre Popularity Over Time</div>', unsafe_allow_html=True)

# Get top 6 genres and track them over time
top_6_genres = genre_counter.head(6).index.tolist()

genre_trend_data = []
for _, row in df.iterrows():
    period = row[period_col]  # Uses the view_mode period from earlier
    for genre in row["Genres_parsed"]:
        if genre in top_6_genres:
            genre_trend_data.append({"Period": period, "Genre": genre})

if genre_trend_data:
    genre_trend_df = pd.DataFrame(genre_trend_data)
    genre_trend_agg = genre_trend_df.groupby(["Period", "Genre"]).size().reset_index(name="Count")
    
    fig_gen_trend = px.line(
        genre_trend_agg, x="Period", y="Count", color="Genre",
        color_discrete_sequence=["#e8365d", "#ff8c42", "#7c6af7", "#4ecdc4", "#ffe66d", "#a8edea"]
    )
    apply_layout(fig_gen_trend, title=None, xaxis_tickangle=-45)
    st.plotly_chart(fig_gen_trend, use_container_width=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Curiosities row
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">curiosities</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Listening Fingerprint</div>', unsafe_allow_html=True)

# Repeat ratio: how often do you re-listen vs discover?
repeat_plays   = total_scrobbles - unique_tracks
repeat_ratio   = round(repeat_plays / total_scrobbles * 100, 1)

# Top album
top_album_name  = df["Album"].dropna().value_counts().idxmax()
top_album_plays = df["Album"].dropna().value_counts().max()

# Longest streak (consecutive days with at least 1 scrobble)
active_days     = df["Played_At"].dt.date.unique()
active_days     = sorted(active_days)
best_streak, cur_streak = 1, 1
for i in range(1, len(active_days)):
    if (active_days[i] - active_days[i-1]).days == 1:
        cur_streak += 1
        best_streak = max(best_streak, cur_streak)
    else:
        cur_streak = 1

# Most common listening gap (mode of gaps in minutes, rounded to 5)
gaps_min = gaps.dt.total_seconds().dropna() / 60
gaps_min = gaps_min[(gaps_min > 1) & (gaps_min < 120)]
gap_mode = int(round(gaps_min.median() / 5) * 5) if not gaps_min.empty else "—"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Repeat Play Ratio",   f"{repeat_ratio}%",       "of plays are re-listens")
c2.metric("Top Album",           top_album_name[:28] + ("…" if len(top_album_name) > 28 else ""),
                                  f"{top_album_plays:,} plays")
c3.metric("Longest Streak",      f"{best_streak} days",    "of consecutive listening")
c4.metric("Typical Track Gap",   f"~{gap_mode} min",       "median gap between plays")

st.markdown("<br>", unsafe_allow_html=True)

# Genre-like scatter: artist play count vs unique track ratio (breadth vs depth)
artist_stats = df.groupby("Artist").agg(
    plays=("Track", "count"),
    unique_tracks=("Track", "nunique"),
).reset_index()
artist_stats["breadth"] = (artist_stats["unique_tracks"] / artist_stats["plays"]).round(3)
artist_stats = artist_stats[artist_stats["plays"] >= 5]  # filter noise

fig_scatter = px.scatter(
    artist_stats,
    x="plays", y="breadth",
    size="plays", size_max=40,
    hover_name="Artist",
    hover_data={"plays": True, "unique_tracks": True, "breadth": ":.2f"},
    color="breadth",
    color_continuous_scale=[[0,"#e8365d"],[0.5,"#ff8c42"],[1,"#7c6af7"]],
    labels={"plays": "Total Plays", "breadth": "Track Breadth (unique / total)"},
)
apply_layout(fig_scatter,
    title="Artist depth vs breadth  —  low breadth = you stick to the same songs; high = wide exploration",
    coloraxis_showscale=False,
    height=420,
)
st.plotly_chart(fig_scatter, use_container_width=True)

# ─────────────────────────────────────────────
#  Footer
# ─────────────────────────────────────────────
st.markdown("""
<hr class='divider'>
<div style='font-family:var(--mono);font-size:0.7rem;color:var(--muted);text-align:center;padding-bottom:1rem;'>
    scrobble.space &nbsp;·&nbsp; data: lastfm_scrobbles &nbsp;·&nbsp; built with Streamlit + Plotly
</div>
""", unsafe_allow_html=True)
