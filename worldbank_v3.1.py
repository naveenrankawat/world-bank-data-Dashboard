# -*- coding: utf-8 -*-
"""
Created on Mon Apr 20 20:34:38 2026

@author: navee
"""

"""
🌍 World Bank Pro Dashboard v3 — FIXED
======================================
STEP 1: pip install dash dash-bootstrap-components plotly pandas numpy
STEP 2: python worldbank_v3.py
STEP 3: Open http://127.0.0.1:8050
"""

import io, base64, os, warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import dcc, html, dash_table, Input, Output, State
import dash_bootstrap_components as dbc

# ─────────────────────────────────────────────────────────────────────
#  AUTO-FIND CSV  (searches common locations automatically)
# ─────────────────────────────────────────────────────────────────────
def find_csv():
    candidates = [
        "WorldBank.csv",
        os.path.join(os.path.expanduser("~"), "Downloads", "WorldBank.csv"),
        os.path.join(os.path.expanduser("~"), "Desktop",   "WorldBank.csv"),
        # Removed __file__ reference here to prevent crashes in Spyder
    ]
    for p in candidates:
        if os.path.exists(p):
            print(f"✅ Found CSV at: {p}")
            return p
    print("⚠️  WorldBank.csv not found — use the upload button in the dashboard")
    return None

CSV_PATH = find_csv()

# ─────────────────────────────────────────────────────────────────────
#  COLOURS
# ─────────────────────────────────────────────────────────────────────
BG      = "#0D1117"
CARD    = "#161B22"
CARD2   = "#1C2333"
BORDER  = "#30363D"
BLUE    = "#58A6FF"
TEAL    = "#39D0D8"
PURPLE  = "#BC8CFF"
GREEN   = "#3FB950"
YELLOW  = "#D29922"
RED     = "#F85149"
TEXT    = "#E6EDF3"
MUTED   = "#8B949E"
PAL     = [BLUE, TEAL, PURPLE, GREEN, YELLOW, RED, "#FFA657", "#79C0FF"]

def dark_layout(title="", h=370):
    return dict(
        template="plotly_dark",
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        font=dict(color=TEXT, size=12),
        title=dict(text=title, font=dict(size=13, color=BLUE), x=0.02),
        margin=dict(l=48, r=16, t=46, b=42),
        height=h,
        legend=dict(bgcolor=CARD2, bordercolor=BORDER, borderwidth=1),
        xaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=MUTED)),
        yaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=MUTED)),
    )

# ─────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────
def load_df(path):
    try:
        # Added na_values to handle potential missing data dots '..'
        df = pd.read_csv(path, na_values=['..', 'NA', 'N/A', ''])
        print(f"✅ Loaded {len(df):,} rows, columns: {list(df.columns)}")
        return df
    except Exception as e:
        print(f"❌ Load error: {e}")
        return pd.DataFrame()

def get_num_cols(df):
    skip = {"Year"}
    return [c for c in df.select_dtypes(include=[np.number]).columns if c not in skip]

def safe_unique(df, col):
    return sorted(df[col].dropna().unique().tolist()) if col in df.columns else []

def short(s, n=36):
    return s if len(s) <= n else s[:n-1] + "…"

def fmt(v):
    if pd.isna(v): return "N/A"
    av = abs(v)
    if av >= 1e12: return f"{v/1e12:.2f} T"
    if av >= 1e9:  return f"{v/1e9:.2f} B"
    if av >= 1e6:  return f"{v/1e6:.2f} M"
    if av >= 1e3:  return f"{v/1e3:.2f} K"
    return f"{v:.2f}"

def get_kpis(df, col):
    if not col or col not in df.columns:
        return "—","—","—","—"
    s = df[col].dropna()
    return (fmt(s.sum()), fmt(s.mean()), fmt(s.max()), fmt(s.min())) if not s.empty else ("—","—","—","—")

def get_insight(df, col):
    try:
        if "Year" not in df.columns or not col or col not in df.columns:
            return "Select a metric to see an auto-insight."
        t = df.groupby("Year")[col].mean().dropna()
        if len(t) < 2: return "Not enough data points."
        pct = (t.iloc[-1]-t.iloc[0]) / abs(t.iloc[0]) * 100
        arrow = "📈 increased" if pct > 0 else "📉 decreased"
        return f"'{short(col,30)}' {arrow} by {abs(pct):.1f}% from {t.index[0]} to {t.index[-1]}, avg {t.mean():,.1f}."
    except:
        return "Could not generate insight."

def apply_filters(df, store, years, regions, incomes):
    try:
        if store:
            df = pd.read_json(io.StringIO(store), orient="split")
        else:
            df = df.copy()
        if df.empty: return df
        if "Year" in df.columns and years:
            df = df[(df["Year"] >= years[0]) & (df["Year"] <= years[1])]
        if "Region" in df.columns and regions:
            df = df[df["Region"].isin(regions)]
        if "IncomeGroup" in df.columns and incomes:
            df = df[df["IncomeGroup"].isin(incomes)]
        return df
    except:
        return pd.DataFrame()

# ─────────────────────────────────────────────────────────────────────
#  LOAD DATA AT STARTUP
# ─────────────────────────────────────────────────────────────────────
df_base = load_df(CSV_PATH) if CSV_PATH else pd.DataFrame()

num_cols_list = get_num_cols(df_base)
all_regions   = safe_unique(df_base, "Region")
all_incomes   = safe_unique(df_base, "IncomeGroup")

print(f"📊 Numeric columns found: {num_cols_list}")

# Pre-select sensible defaults
def pick(lst, keyword):
    for c in lst:
        if keyword.lower() in c.lower():
            return c
    return lst[0] if lst else None

default_m1 = pick(num_cols_list, "GDP per capita")
default_m2 = pick(num_cols_list, "Life expectancy")

metric_options = [{"label": short(c), "value": c} for c in num_cols_list]

# ─────────────────────────────────────────────────────────────────────
#  UI COMPONENTS
# ─────────────────────────────────────────────────────────────────────
def kpi_card(title, value, icon, color):
    return dbc.Col(html.Div([
        html.Span(icon, style={"fontSize":"28px"}),
        html.P(title, style={"color":MUTED,"fontSize":"10px","margin":"6px 0 0",
                              "textTransform":"uppercase","letterSpacing":"1.2px"}),
        html.H3(value, style={"color":color,"fontSize":"22px","fontWeight":"700","margin":"8px 0 0"}),
    ], style={
        "background":CARD, "border":f"1px solid {color}33",
        "borderTop":f"3px solid {color}", "borderRadius":"10px",
        "padding":"18px 14px", "textAlign":"center",
    }), md=3, sm=6, style={"marginBottom":"14px"})

def wrap(children, title=None):
    hdr = [html.P(title, style={"color":BLUE,"fontSize":"10px","fontWeight":"700",
                                 "textTransform":"uppercase","letterSpacing":"1.2px",
                                 "marginBottom":"12px"})] if title else []
    items = children if isinstance(children, list) else [children]
    return html.Div(hdr + items,
                    style={"background":CARD,"border":f"1px solid {BORDER}",
                           "borderRadius":"12px","padding":"18px","marginBottom":"16px"})

def lbl(text):
    return html.P(text, style={"color":MUTED,"fontSize":"10px","margin":"12px 0 5px",
                                "textTransform":"uppercase","letterSpacing":"1px"})

def ddrop(id_, opts, val):
    return dbc.Select(id=id_, options=opts, value=val,
                      style={"background":CARD2,"color":TEXT,
                             "border":f"1px solid {BORDER}","borderRadius":"8px","fontSize":"12px"})

# ─────────────────────────────────────────────────────────────────────
#  APP LAYOUT
# ─────────────────────────────────────────────────────────────────────
app = dash.Dash(__name__,
    external_stylesheets=[dbc.themes.CYBORG,
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&display=swap"],
    suppress_callback_exceptions=True,
    title="🌍 World Bank Dashboard")

app.layout = html.Div([
    dcc.Store(id="store"),

    # HEADER
    html.Div([
        html.Div([
            html.Span("🌍", style={"fontSize":"34px","marginRight":"12px"}),
            html.Div([
                html.H1("World Bank Pro Dashboard",
                        style={"margin":0,"fontSize":"22px","fontWeight":"700","color":TEXT}),
                html.P(f"211 Countries · 1960–2018 · {len(num_cols_list)} Indicators",
                       style={"margin":0,"color":MUTED,"fontSize":"11px"}),
            ]),
        ], style={"display":"flex","alignItems":"center"}),
        html.Div([
            dcc.Upload(id="upload",
                children=html.Div(["📂 Drop CSV or ", html.B("click to upload")]),
                style={"padding":"9px 18px","border":f"2px dashed {BLUE}55",
                       "borderRadius":"8px","color":BLUE,"cursor":"pointer",
                       "fontSize":"12px","background":CARD2},
                accept=".csv"),
            html.Div(id="upload-msg",
                     children=f"✓ WorldBank.csv ({len(df_base):,} rows)" if not df_base.empty else "",
                     style={"color":GREEN,"fontSize":"11px","marginTop":"4px","textAlign":"right"}),
        ]),
    ], style={"background":f"linear-gradient(135deg,{CARD},{CARD2})",
              "borderBottom":f"1px solid {BORDER}","padding":"18px 28px",
              "display":"flex","justifyContent":"space-between",
              "alignItems":"center","flexWrap":"wrap","gap":"12px"}),

    # BODY
    html.Div([

        # SIDEBAR
        html.Div([
            wrap([
                lbl("🎯 Primary Metric"),
                ddrop("m1", metric_options, default_m1),
                lbl("📊 Compare With"),
                ddrop("m2", metric_options, default_m2),
                lbl("🗓 Year Range"),
                dcc.RangeSlider(id="years", min=1960, max=2018, step=1, value=[2000,2018],
                    marks={y:{"label":str(y),"style":{"color":MUTED,"fontSize":"9px"}}
                           for y in [1960,1975,1990,2005,2018]},
                    tooltip={"placement":"bottom","always_visible":False}),
                lbl("🌐 Region"),
                dcc.Checklist(id="regions",
                    options=[{"label":html.Span(r,style={"color":TEXT,"fontSize":"11px"}),"value":r}
                             for r in all_regions],
                    value=all_regions,
                    style={"display":"flex","flexDirection":"column","gap":"6px"},
                    inputStyle={"accentColor":BLUE,"marginRight":"7px"}),
                lbl("💰 Income Group"),
                dcc.Checklist(id="incomes",
                    options=[{"label":html.Span(g,style={"color":TEXT,"fontSize":"11px"}),"value":g}
                             for g in all_incomes],
                    value=all_incomes,
                    style={"display":"flex","flexDirection":"column","gap":"6px"},
                    inputStyle={"accentColor":PURPLE,"marginRight":"7px"}),
                html.Div(style={"height":"16px"}),
                html.Button("⬇ Export CSV", id="btn-export", n_clicks=0,
                    style={"width":"100%","padding":"10px","background":f"{BLUE}18",
                           "border":f"1px solid {BLUE}55","borderRadius":"8px",
                           "color":BLUE,"cursor":"pointer","fontSize":"12px","fontWeight":"600"}),
                dcc.Download(id="dl"),
            ], title="⚙ Controls"),
        ], style={"width":"255px","flexShrink":"0"}),

        # CHARTS
        html.Div([
            html.Div(id="kpis", style={"marginBottom":"6px"}),
            html.Div(id="insight-box"),
            dbc.Row([
                dbc.Col(wrap(dcc.Graph(id="g-line",   config={"displayModeBar":False}), "📈 Trend Over Time"), md=7),
                dbc.Col(wrap(dcc.Graph(id="g-bar",    config={"displayModeBar":False}), "🏆 Top 15 Countries"), md=5),
            ]),
            dbc.Row([
                dbc.Col(wrap(dcc.Graph(id="g-scatter",config={"displayModeBar":False}), "🔵 Scatter Plot"), md=7),
                dbc.Col(wrap(dcc.Graph(id="g-pie",    config={"displayModeBar":False}), "🥧 By Region"), md=5),
            ]),
            dbc.Row([
                dbc.Col(wrap(dcc.Graph(id="g-hist",   config={"displayModeBar":False}), "📊 Distribution"), md=5),
                dbc.Col(wrap(dcc.Graph(id="g-map",    config={"displayModeBar":False}), "🗺 World Map"), md=7),
            ]),
            wrap([
                html.Div([
                    html.P("📋 Data Table", style={"color":BLUE,"fontSize":"10px","fontWeight":"700",
                                                    "textTransform":"uppercase","letterSpacing":"1.2px","margin":0}),
                    html.Span(id="tbl-label", style={"color":MUTED,"fontSize":"11px"}),
                ], style={"display":"flex","justifyContent":"space-between",
                          "alignItems":"center","marginBottom":"12px"}),
                html.Div(id="tbl"),
            ]),
        ], style={"flex":"1","minWidth":"0"}),

    ], style={"display":"flex","gap":"18px","padding":"18px 22px","alignItems":"flex-start"}),

], style={"backgroundColor":BG,"minHeight":"100vh",
           "fontFamily":"'IBM Plex Mono', monospace","color":TEXT})


# ─────────────────────────────────────────────────────────────────────
#  CALLBACKS
# ─────────────────────────────────────────────────────────────────────

@app.callback(Output("store","data"), Output("upload-msg","children"),
              Input("upload","contents"), State("upload","filename"),
              prevent_initial_call=True)
def on_upload(contents, name):
    if not contents: return dash.no_update, ""
    try:
        _, data = contents.split(",")
        df = pd.read_csv(io.StringIO(base64.b64decode(data).decode("utf-8")), na_values=['..', 'NA', 'N/A', ''])
        return df.to_json(orient="split"), f"✓ {name} ({len(df):,} rows)"
    except Exception as e:
        return dash.no_update, f"❌ {e}"

def get_df(store):
    if store:
        try: return pd.read_json(io.StringIO(store), orient="split")
        except: pass
    return df_base.copy()

def filtered(store, years, regions, incomes):
    df = get_df(store)
    if df.empty: return df
    if "Year" in df.columns and years:
        df = df[(df["Year"]>=years[0])&(df["Year"]<=years[1])]
    if "Region" in df.columns and regions:
        df = df[df["Region"].isin(regions)]
    if "IncomeGroup" in df.columns and incomes:
        df = df[df["IncomeGroup"].isin(incomes)]
    return df

# KPIs
@app.callback(Output("kpis","children"),
              Input("store","data"),Input("m1","value"),
              Input("years","value"),Input("regions","value"),Input("incomes","value"))
def cb_kpi(store,m1,years,regions,incomes):
    df = filtered(store,years,regions,incomes)
    t,avg,mx,mn = get_kpis(df,m1)
    lbl_ = short(m1,18) if m1 else "Metric"
    return dbc.Row([
        kpi_card("Total · "+lbl_, t,   "∑", BLUE),
        kpi_card("Average",        avg, "μ", TEAL),
        kpi_card("Maximum",        mx,  "↑", GREEN),
        kpi_card("Minimum",        mn,  "↓", YELLOW),
    ], className="g-3")

# Insight
@app.callback(Output("insight-box","children"),
              Input("store","data"),Input("m1","value"),
              Input("years","value"),Input("regions","value"),Input("incomes","value"))
def cb_insight(store,m1,years,regions,incomes):
    df = filtered(store,years,regions,incomes)
    txt = get_insight(df,m1)
    return html.Div([
        html.Span("💡 Auto-Insight  ",style={"color":TEAL,"fontWeight":"700","fontSize":"12px"}),
        html.Span(txt,style={"color":TEXT,"fontSize":"12px"}),
    ],style={"background":f"{TEAL}0F","border":f"1px solid {TEAL}33",
             "borderLeft":f"4px solid {TEAL}","borderRadius":"8px",
             "padding":"11px 16px","marginBottom":"16px"})

# Line
@app.callback(Output("g-line","figure"),
              Input("store","data"),Input("m1","value"),
              Input("years","value"),Input("regions","value"),Input("incomes","value"))
def cb_line(store,m1,years,regions,incomes):
    df = filtered(store,years,regions,incomes)
    if df.empty or not m1 or m1 not in df.columns or "Year" not in df.columns:
        fig=go.Figure(); fig.update_layout(**dark_layout("No data")); return fig
    gc = "Region" if "Region" in df.columns else None
    if gc:
        t = df.groupby(["Year",gc])[m1].mean().reset_index()
        fig = px.line(t,x="Year",y=m1,color=gc,color_discrete_sequence=PAL,line_shape="spline")
    else:
        t = df.groupby("Year")[m1].mean().reset_index()
        fig = px.line(t,x="Year",y=m1,line_shape="spline",color_discrete_sequence=[BLUE])
    fig.update_traces(line_width=2.5)
    fig.update_layout(**dark_layout(short(m1)+" over time"))
    return fig

# Bar
@app.callback(Output("g-bar","figure"),
              Input("store","data"),Input("m1","value"),
              Input("years","value"),Input("regions","value"),Input("incomes","value"))
def cb_bar(store,m1,years,regions,incomes):
    df = filtered(store,years,regions,incomes)
    cc = "Country Name" if "Country Name" in df.columns else (df.columns[0] if not df.empty else None)
    if df.empty or not m1 or m1 not in df.columns or not cc:
        fig=go.Figure(); fig.update_layout(**dark_layout("No data")); return fig
    top = df.groupby(cc)[m1].mean().dropna().sort_values(ascending=False).head(15).reset_index()
    fig = px.bar(top,x=m1,y=cc,orientation="h",color=m1,
                 color_continuous_scale=["#1C2333",BLUE,TEAL])
    fig.update_layout(**dark_layout("Top 15"))
    fig.update_layout(yaxis=dict(autorange="reversed",gridcolor=BORDER,tickfont=dict(size=10,color=MUTED)),
                      coloraxis_showscale=False)
    return fig

# Scatter
@app.callback(Output("g-scatter","figure"),
              Input("store","data"),Input("m1","value"),Input("m2","value"),
              Input("years","value"),Input("regions","value"),Input("incomes","value"))
def cb_scatter(store,m1,m2,years,regions,incomes):
    df = filtered(store,years,regions,incomes)
    cc = "Country Name" if "Country Name" in df.columns else None
    rc = "Region" if "Region" in df.columns else None
    if df.empty or not m1 or not m2 or m1 not in df.columns or m2 not in df.columns:
        fig=go.Figure(); fig.update_layout(**dark_layout("Select two metrics")); return fig
    cols=[c for c in [m1,m2,rc,cc] if c]
    sub = df[cols].dropna()
    if sub.empty:
        fig=go.Figure(); fig.update_layout(**dark_layout("No overlapping data")); return fig
    
    # REMOVED trendline="lowess" here to fix the crash
    fig = px.scatter(sub,x=m1,y=m2,color=rc,hover_name=cc,
                     color_discrete_sequence=PAL,opacity=0.72)
    
    fig.update_traces(marker=dict(size=5))
    fig.update_layout(**dark_layout(f"{short(m1,20)} vs {short(m2,20)}"))
    return fig

# Pie
@app.callback(Output("g-pie","figure"),
              Input("store","data"),Input("m1","value"),
              Input("years","value"),Input("regions","value"),Input("incomes","value"))
def cb_pie(store,m1,years,regions,incomes):
    df = filtered(store,years,regions,incomes)
    gc = "Region" if "Region" in df.columns else ("IncomeGroup" if "IncomeGroup" in df.columns else None)
    if df.empty or not m1 or m1 not in df.columns or not gc:
        fig=go.Figure(); fig.update_layout(**dark_layout("No data")); return fig
    pie = df.groupby(gc)[m1].mean().dropna().reset_index()
    fig = px.pie(pie,names=gc,values=m1,color_discrete_sequence=PAL,hole=0.44)
    fig.update_traces(marker=dict(line=dict(color=CARD,width=2)),textfont_color=TEXT)
    fig.update_layout(**dark_layout("Share by "+gc))
    return fig

# Histogram
@app.callback(Output("g-hist","figure"),
              Input("store","data"),Input("m1","value"),
              Input("years","value"),Input("regions","value"),Input("incomes","value"))
def cb_hist(store,m1,years,regions,incomes):
    df = filtered(store,years,regions,incomes)
    if df.empty or not m1 or m1 not in df.columns:
        fig=go.Figure(); fig.update_layout(**dark_layout("No data")); return fig
    fig = px.histogram(df.dropna(subset=[m1]),x=m1,nbins=40,
                       color_discrete_sequence=[PURPLE],marginal="box",opacity=0.85)
    fig.update_layout(**dark_layout("Distribution"))
    return fig

# Map
@app.callback(Output("g-map","figure"),
              Input("store","data"),Input("m1","value"),
              Input("years","value"),Input("regions","value"),Input("incomes","value"))
def cb_map(store,m1,years,regions,incomes):
    df = filtered(store,years,regions,incomes)
    code = "Country Code" if "Country Code" in df.columns else None
    name = "Country Name" if "Country Name" in df.columns else None
    if df.empty or not m1 or m1 not in df.columns or not code:
        fig=go.Figure(); fig.update_layout(**dark_layout("No country code column")); return fig
    cols=[c for c in [code,name,m1] if c]
    mp = df[cols].groupby(code)[m1].mean().dropna().reset_index()
    if name:
        mp = mp.merge(df[[code,name]].drop_duplicates(),on=code,how="left")
    fig = px.choropleth(mp,locations=code,color=m1,hover_name=name or code,
                        color_continuous_scale=["#0D1117",BLUE,TEAL],
                        labels={m1:short(m1,20)})
    fig.update_layout(**dark_layout("World Map · "+short(m1,25)),
                      geo=dict(bgcolor=CARD,showframe=False,showcoastlines=True,
                               coastlinecolor=BORDER,showland=True,landcolor=CARD2,
                               showocean=True,oceancolor=BG,
                               showcountries=True,countrycolor=BORDER))
    return fig

# Table
@app.callback(Output("tbl","children"),Output("tbl-label","children"),
              Input("store","data"),Input("m1","value"),
              Input("years","value"),Input("regions","value"),Input("incomes","value"))
def cb_table(store,m1,years,regions,incomes):
    df = filtered(store,years,regions,incomes)
    if df.empty: return html.P("No data.",style={"color":MUTED}),""
    priority=["Country Name","Country Code","Region","IncomeGroup","Year"]
    show=[c for c in priority if c in df.columns]
    if m1 and m1 in df.columns and m1 not in show: show.append(m1)
    sample=df[show].head(200)
    tbl=dash_table.DataTable(
        data=sample.to_dict("records"),
        columns=[{"name":short(c,28),"id":c} for c in show],
        page_size=12,sort_action="native",filter_action="native",
        style_table={"overflowX":"auto","borderRadius":"8px"},
        style_header={"backgroundColor":CARD2,"color":BLUE,"fontWeight":"600",
                      "border":f"1px solid {BORDER}","fontSize":"11px"},
        style_cell={"backgroundColor":CARD,"color":TEXT,"border":f"1px solid {BORDER}",
                    "fontSize":"12px","padding":"8px 12px"},
        style_data_conditional=[{"if":{"row_index":"odd"},"backgroundColor":CARD2}],
    )
    return tbl, f"Showing top 200 of {len(df):,} rows"

# Export
@app.callback(Output("dl","data"),Input("btn-export","n_clicks"),
              State("store","data"),State("m1","value"),
              State("years","value"),State("regions","value"),State("incomes","value"),
              prevent_initial_call=True)
def cb_export(n,store,m1,years,regions,incomes):
    df=filtered(store,years,regions,incomes)
    if df.empty: return dash.no_update
    return dcc.send_data_frame(df.to_csv,"worldbank_filtered.csv",index=False)

# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n"+"═"*52)
    print("  🌍 World Bank Pro Dashboard v3")
    print("  Open → http://127.0.0.1:8050")
    print("═"*52+"\n")
    app.run(debug=False, port=8050)