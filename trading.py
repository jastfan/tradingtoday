"""
Trading Platform - Full TradingView-style chart
Run: python app.py
Open: http://localhost:8050
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context, no_update
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf
import pandas_ta as ta
import json
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Trading Platform"

# ─── Watchlist symbols ────────────────────────────────────────────────────────
WATCHLIST = [
    {"symbol": "^NSEI",      "label": "NIFTY",    "name": "Nifty 50 Index",    "exchange": "NSE"},
    {"symbol": "^NSEBANK",   "label": "BANKNIFTY","name": "Bank Nifty",         "exchange": "NSE"},
    {"symbol": "RELIANCE.NS","label": "RELIANCE", "name": "Reliance Industries","exchange": "NSE"},
    {"symbol": "TCS.NS",     "label": "TCS",       "name": "Tata Consultancy",  "exchange": "NSE"},
    {"symbol": "INFY.NS",    "label": "INFOSYS",  "name": "Infosys Limited",    "exchange": "NSE"},
    {"symbol": "HDFCBANK.NS","label": "HDFC BANK","name": "HDFC Bank",          "exchange": "NSE"},
    {"symbol": "AAPL",       "label": "AAPL",     "name": "Apple Inc",          "exchange": "NASDAQ"},
    {"symbol": "TSLA",       "label": "TSLA",     "name": "Tesla Inc",          "exchange": "NASDAQ"},
    {"symbol": "BTC-USD",    "label": "BTC/USD",  "name": "Bitcoin USD",        "exchange": "CRYPTO"},
    {"symbol": "ETH-USD",    "label": "ETH/USD",  "name": "Ethereum USD",       "exchange": "CRYPTO"},
]

TIMEFRAMES = [
    {"label": "1D",  "value": "1d",  "period": "6mo",  "interval": "1d"},
    {"label": "5D",  "value": "5d",  "period": "60d",  "interval": "1h"},
    {"label": "1M",  "value": "1mo", "period": "3mo",  "interval": "1d"},
    {"label": "3M",  "value": "3mo", "period": "6mo",  "interval": "1d"},
    {"label": "6M",  "value": "6mo", "period": "1y",   "interval": "1d"},
    {"label": "1Y",  "value": "1y",  "period": "2y",   "interval": "1wk"},
    {"label": "5Y",  "value": "5y",  "period": "10y",  "interval": "1mo"},
    {"label": "ALL", "value": "all", "period": "max",  "interval": "1mo"},
]

INDICATORS_LIST = [
    "Moving Average (MA)",
    "Exponential MA (EMA)",
    "Bollinger Bands",
    "MACD",
    "RSI",
    "Stochastic",
    "ATR",
    "Volume",
    "VWAP",
    "Supertrend",
    "Ichimoku Cloud",
    "ADX",
    "CCI",
    "Williams %R",
    "OBV",
    "Parabolic SAR",
    "Aroon",
    "Chaikin Money Flow",
]

# ─── Color theme ──────────────────────────────────────────────────────────────
THEME = {
    "bg_main":    "#131722",
    "bg_panel":   "#1e222d",
    "bg_card":    "#2a2e39",
    "bg_hover":   "#363a45",
    "border":     "#363a45",
    "text_main":  "#d1d4dc",
    "text_dim":   "#787b86",
    "text_bright":"#ffffff",
    "green":      "#26a69a",
    "red":        "#ef5350",
    "blue":       "#2196f3",
    "orange":     "#ff9800",
    "purple":     "#9c27b0",
    "yellow":     "#ffeb3b",
    "accent":     "#2962ff",
}

# ─── Layout ───────────────────────────────────────────────────────────────────
app.layout = html.Div([

    # Hidden stores
    dcc.Store(id="store-symbol",    data="^NSEI"),
    dcc.Store(id="store-tf",        data="1d"),
    dcc.Store(id="store-indicators",data=[]),
    dcc.Store(id="store-charttype", data="candle"),

    # ── TOP BAR ──────────────────────────────────────────────────────────────
    html.Div([
        # Left: symbol selector
        html.Div([
            html.Div("F", style={
                "width":"28px","height":"28px","borderRadius":"6px",
                "background":THEME["accent"],"display":"flex","alignItems":"center",
                "justifyContent":"center","fontWeight":"700","fontSize":"14px",
                "color":"#fff","marginRight":"10px","flexShrink":"0"
            }),
            dcc.Dropdown(
                id="dd-symbol",
                options=[{"label": f"{w['label']}  ·  {w['exchange']}", "value": w["symbol"]} for w in WATCHLIST],
                value="^NSEI",
                clearable=False,
                style={
                    "width":"200px","background":"transparent",
                    "border":"none","color":THEME["text_main"]
                },
            ),
        ], style={"display":"flex","alignItems":"center","flexShrink":"0"}),

        # Timeframe buttons
        html.Div([
            html.Button(tf["label"], id=f"btn-tf-{tf['value']}", n_clicks=0,
                className="tf-btn", **{"data-tf": tf["value"]})
            for tf in TIMEFRAMES
        ], id="tf-buttons", style={"display":"flex","gap":"2px","margin":"0 16px"}),

        # Chart type buttons
        html.Div([
            html.Button("🕯 Candles", id="btn-type-candle", n_clicks=0, className="tf-btn active-btn"),
            html.Button("📊 Bars",    id="btn-type-ohlc",   n_clicks=0, className="tf-btn"),
            html.Button("〰 Line",    id="btn-type-line",   n_clicks=0, className="tf-btn"),
            html.Button("📈 Area",    id="btn-type-area",   n_clicks=0, className="tf-btn"),
        ], style={"display":"flex","gap":"2px","marginRight":"16px"}),

        # Indicators button
        html.Button([
            html.Span("⚡ ", style={"fontSize":"14px"}),
            "Indicators"
        ], id="btn-indicators", n_clicks=0, style={
            "background":THEME["bg_card"],"color":THEME["text_main"],
            "border":f"1px solid {THEME['border']}","borderRadius":"6px",
            "padding":"6px 14px","cursor":"pointer","fontSize":"13px",
            "marginRight":"auto"
        }),

        # Price display
        html.Div(id="top-price-display", style={"marginLeft":"auto","marginRight":"16px"}),

    ], style={
        "display":"flex","alignItems":"center","padding":"8px 12px",
        "background":THEME["bg_panel"],"borderBottom":f"1px solid {THEME['border']}",
        "height":"52px","flexWrap":"nowrap","overflow":"hidden"
    }),

    # ── OHLCV INFO BAR ────────────────────────────────────────────────────────
    html.Div(id="ohlcv-bar", style={
        "display":"flex","alignItems":"center","gap":"20px",
        "padding":"4px 16px","background":THEME["bg_main"],
        "fontSize":"13px","borderBottom":f"1px solid {THEME['border']}",
        "minHeight":"28px"
    }),

    # ── MAIN AREA ─────────────────────────────────────────────────────────────
    html.Div([

        # Left toolbar (drawing tools)
        html.Div([
            html.Div("✚", title="Crosshair",    className="toolbar-btn active-tool"),
            html.Div("╲", title="Trendline",    className="toolbar-btn"),
            html.Div("⬜", title="Rectangle",   className="toolbar-btn"),
            html.Div("⭕", title="Circle",      className="toolbar-btn"),
            html.Div("✏", title="Pencil",       className="toolbar-btn"),
            html.Div("T",  title="Text",         className="toolbar-btn"),
            html.Div("📐", title="Fibonacci",   className="toolbar-btn"),
            html.Div("—", title="H-Line",        className="toolbar-btn"),
            html.Div("│",  title="V-Line",       className="toolbar-btn"),
            html.Div("🔔", title="Alert",        className="toolbar-btn"),
            html.Hr(style={"border":f"1px solid {THEME['border']}","margin":"8px 0","width":"80%"}),
            html.Div("🔍", title="Zoom In",      className="toolbar-btn"),
            html.Div("🔎", title="Zoom Out",     className="toolbar-btn"),
            html.Div("↩", title="Undo",           className="toolbar-btn"),
            html.Div("🗑", title="Clear All",     className="toolbar-btn"),
        ], style={
            "width":"44px","background":THEME["bg_panel"],
            "borderRight":f"1px solid {THEME['border']}",
            "display":"flex","flexDirection":"column","alignItems":"center",
            "padding":"8px 0","gap":"2px","flexShrink":"0",
            "overflowY":"auto"
        }),

        # Chart area
        html.Div([
            dcc.Graph(
                id="main-chart",
                config={
                    "displayModeBar": True,
                    "displaylogo": False,
                    "modeBarButtonsToRemove": ["select2d","lasso2d","autoScale2d"],
                    "scrollZoom": True,
                    "toImageButtonOptions": {"format":"png","filename":"chart","scale":2}
                },
                style={"height":"100%","width":"100%"},
            ),
        ], style={"flex":"1","background":THEME["bg_main"],"position":"relative","overflow":"hidden"}),

        # Right panel - watchlist
        html.Div([
            # Watchlist header
            html.Div([
                html.Span("Watchlist", style={"fontSize":"13px","fontWeight":"600","color":THEME["text_main"]}),
                html.Div([
                    html.Span("➕", style={"cursor":"pointer","marginRight":"8px","fontSize":"16px"}),
                    html.Span("⚙", style={"cursor":"pointer","fontSize":"16px"}),
                ], style={"display":"flex","alignItems":"center"})
            ], style={
                "display":"flex","justifyContent":"space-between","alignItems":"center",
                "padding":"10px 12px","borderBottom":f"1px solid {THEME['border']}"
            }),

            # Column headers
            html.Div([
                html.Span("Symbol", style={"flex":"1","fontSize":"11px","color":THEME["text_dim"]}),
                html.Span("Last",   style={"width":"80px","textAlign":"right","fontSize":"11px","color":THEME["text_dim"]}),
                html.Span("Chg%",   style={"width":"70px","textAlign":"right","fontSize":"11px","color":THEME["text_dim"]}),
            ], style={
                "display":"flex","padding":"6px 12px","borderBottom":f"1px solid {THEME['border']}"
            }),

            # Watchlist items
            html.Div(id="watchlist-items", style={"overflowY":"auto","flex":"1"}),

            # Symbol detail panel
            html.Div([
                html.Hr(style={"border":f"1px solid {THEME['border']}","margin":"0"}),
                html.Div(id="symbol-detail", style={"padding":"12px"}),
            ]),

        ], style={
            "width":"240px","background":THEME["bg_panel"],
            "borderLeft":f"1px solid {THEME['border']}",
            "display":"flex","flexDirection":"column","flexShrink":"0"
        }),

    ], style={"display":"flex","flex":"1","overflow":"hidden"}),

    # ── BOTTOM TIMEFRAME BAR ─────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Button(tf["label"], className="tf-btn-bottom")
            for tf in TIMEFRAMES
        ], style={"display":"flex","gap":"2px"}),
        html.Div(id="bottom-time", style={"marginLeft":"auto","fontSize":"12px","color":THEME["text_dim"]}),
    ], style={
        "display":"flex","alignItems":"center","padding":"4px 12px",
        "background":THEME["bg_panel"],"borderTop":f"1px solid {THEME['border']}",
        "height":"36px"
    }),

    # ── INDICATORS MODAL ─────────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Div([
                html.H3("Indicators, metrics, and strategies", style={
                    "color":THEME["text_bright"],"margin":"0","fontSize":"18px","fontWeight":"600"
                }),
                html.Button("✕", id="close-indicators", n_clicks=0, style={
                    "background":"none","border":"none","color":THEME["text_dim"],
                    "fontSize":"20px","cursor":"pointer","padding":"4px 8px"
                }),
            ], style={"display":"flex","justifyContent":"space-between","alignItems":"center","marginBottom":"16px"}),

            # Tabs
            html.Div([
                html.Button("Indicators",  id="ind-tab-indicators",  n_clicks=0, className="ind-tab-active"),
                html.Button("Strategies",  id="ind-tab-strategies",  n_clicks=0, className="ind-tab"),
                html.Button("Profiles",    id="ind-tab-profiles",    n_clicks=0, className="ind-tab"),
                html.Button("Patterns",    id="ind-tab-patterns",    n_clicks=0, className="ind-tab"),
            ], style={"display":"flex","gap":"4px","marginBottom":"16px"}),

            html.Div([
                # Left sidebar
                html.Div([
                    dcc.Input(placeholder="Search indicators...", id="indicator-search",
                        style={
                            "width":"100%","background":THEME["bg_card"],
                            "border":f"1px solid {THEME['border']}","borderRadius":"6px",
                            "padding":"8px 12px","color":THEME["text_main"],
                            "fontSize":"13px","marginBottom":"12px","boxSizing":"border-box"
                        }),
                    html.Div("PERSONAL", style={"fontSize":"11px","color":THEME["text_dim"],"padding":"4px 0","letterSpacing":"1px"}),
                    html.Div("My scripts",    className="ind-sidebar-item"),
                    html.Div("Purchased",     className="ind-sidebar-item"),
                    html.Div("BUILT-IN",      style={"fontSize":"11px","color":THEME["text_dim"],"padding":"8px 0 4px","letterSpacing":"1px"}),
                    html.Div("Technicals",    className="ind-sidebar-item ind-sidebar-active", id="sidebar-technicals"),
                    html.Div("Fundamentals", className="ind-sidebar-item"),
                    html.Div("COMMUNITY",     style={"fontSize":"11px","color":THEME["text_dim"],"padding":"8px 0 4px","letterSpacing":"1px"}),
                    html.Div("Editors' picks",className="ind-sidebar-item"),
                    html.Div("Top",           className="ind-sidebar-item"),
                    html.Div("Trending",      className="ind-sidebar-item"),
                    html.Div("Store",         className="ind-sidebar-item"),
                ], style={
                    "width":"200px","flexShrink":"0","paddingRight":"16px",
                    "borderRight":f"1px solid {THEME['border']}"
                }),

                # Right: indicator list
                html.Div([
                    html.Div("SCRIPT NAME", style={
                        "fontSize":"11px","color":THEME["text_dim"],
                        "letterSpacing":"1px","padding":"4px 8px","marginBottom":"4px"
                    }),
                    html.Div(id="indicator-list-items",
                        style={"overflowY":"auto","maxHeight":"380px"}),
                ], style={"flex":"1","paddingLeft":"16px"}),

            ], style={"display":"flex","flex":"1","overflow":"hidden"}),

            # Active indicators
            html.Div([
                html.Div("Active on chart:", style={
                    "fontSize":"12px","color":THEME["text_dim"],"marginBottom":"8px","marginTop":"12px"
                }),
                html.Div(id="active-indicators-display"),
            ]),

        ], style={
            "background":THEME["bg_panel"],"borderRadius":"12px",
            "padding":"24px","width":"800px","maxHeight":"600px",
            "display":"flex","flexDirection":"column",
            "border":f"1px solid {THEME['border']}"
        }),
    ], id="indicators-modal", style={
        "display":"none","position":"fixed","top":"0","left":"0",
        "width":"100%","height":"100%","background":"rgba(0,0,0,0.7)",
        "zIndex":"9999","justifyContent":"center","alignItems":"center"
    }),

    # Auto-refresh
    dcc.Interval(id="interval-refresh", interval=60000, n_intervals=0),

], style={
    "display":"flex","flexDirection":"column","height":"100vh",
    "background":THEME["bg_main"],"color":THEME["text_main"],
    "fontFamily":"'Trebuchet MS', system-ui, sans-serif","overflow":"hidden"
})


# ─── CSS ──────────────────────────────────────────────────────────────────────
app.index_string = '''
<!DOCTYPE html>
<html>
<head>
{%metas%}
<title>{%title%}</title>
{%favicon%}
{%css%}
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #131722; overflow: hidden; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #1e222d; }
::-webkit-scrollbar-thumb { background: #363a45; border-radius: 3px; }

.tf-btn {
    background: transparent; color: #787b86; border: none;
    padding: 5px 10px; border-radius: 4px; cursor: pointer;
    font-size: 13px; font-family: inherit; transition: all 0.15s;
}
.tf-btn:hover { background: #2a2e39; color: #d1d4dc; }
.active-btn { background: #2962ff !important; color: #fff !important; }

.tf-btn-bottom {
    background: transparent; color: #787b86; border: none;
    padding: 3px 10px; border-radius: 4px; cursor: pointer;
    font-size: 12px; font-family: inherit;
}
.tf-btn-bottom:hover { background: #2a2e39; color: #d1d4dc; }

.toolbar-btn {
    width: 32px; height: 32px; display: flex; align-items: center;
    justify-content: center; border-radius: 4px; cursor: pointer;
    color: #787b86; font-size: 14px; transition: all 0.15s;
    user-select: none;
}
.toolbar-btn:hover { background: #2a2e39; color: #d1d4dc; }
.active-tool { background: #2a2e39; color: #2196f3; }

.watchlist-row {
    display: flex; align-items: center; padding: 8px 12px;
    cursor: pointer; border-bottom: 1px solid #1e222d;
    transition: background 0.1s;
}
.watchlist-row:hover { background: #2a2e39; }
.watchlist-active { background: #2a2e39; border-left: 2px solid #2962ff; }

.ind-tab-active {
    background: #2a2e39; color: #d1d4dc; border: none;
    padding: 8px 16px; border-radius: 6px; cursor: pointer;
    font-size: 13px; font-family: inherit; font-weight: 600;
}
.ind-tab {
    background: transparent; color: #787b86; border: none;
    padding: 8px 16px; border-radius: 6px; cursor: pointer;
    font-size: 13px; font-family: inherit;
}
.ind-tab:hover { background: #2a2e39; color: #d1d4dc; }

.ind-sidebar-item {
    padding: 8px 10px; border-radius: 4px; cursor: pointer;
    font-size: 13px; color: #787b86; transition: all 0.1s;
}
.ind-sidebar-item:hover { background: #2a2e39; color: #d1d4dc; }
.ind-sidebar-active { background: #2a2e39; color: #d1d4dc; }

.ind-list-item {
    padding: 10px 8px; cursor: pointer; border-radius: 4px;
    font-size: 14px; color: #d1d4dc; display: flex;
    justify-content: space-between; align-items: center;
    transition: background 0.1s;
}
.ind-list-item:hover { background: #2a2e39; }

.ind-active-tag {
    display: inline-flex; align-items: center; gap: 4px;
    background: #2a2e39; border: 1px solid #363a45;
    border-radius: 4px; padding: 3px 8px; font-size: 12px;
    color: #d1d4dc; margin: 2px;
}

/* Dropdown styling */
.Select-control { background: #1e222d !important; border: 1px solid #363a45 !important; }
.Select-menu-outer { background: #1e222d !important; border: 1px solid #363a45 !important; }
.Select-option { color: #d1d4dc !important; }
.Select-option:hover, .Select-option.is-focused { background: #2a2e39 !important; }
.Select-value-label { color: #d1d4dc !important; }
.Select-arrow { border-color: #787b86 transparent transparent !important; }
</style>
</head>
<body>
{%app_entry%}
<footer>
{%config%}
{%scripts%}
{%renderer%}
</footer>
</body>
</html>
'''


# ─── DATA FETCH ───────────────────────────────────────────────────────────────
def fetch_data(symbol, period="6mo", interval="1d"):
    try:
        df = yf.download(symbol, period=period, interval=interval,
                         progress=False, auto_adjust=True)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()
        return df
    except Exception as e:
        print(f"Data fetch error: {e}")
        return None


def compute_indicators(df, active_indicators):
    """Compute all requested indicators and return traces + subplot count."""
    close = df["Close"].squeeze()
    high  = df["High"].squeeze()
    low   = df["Low"].squeeze()
    volume= df["Volume"].squeeze()

    overlay_traces  = []  # drawn on price chart
    subplot_traces  = []  # each gets own subplot
    subplot_labels  = []

    # ── Overlay indicators ────────────────────────────────────────────────────
    if "Moving Average (MA)" in active_indicators:
        ma20 = ta.sma(close, length=20)
        ma50 = ta.sma(close, length=50)
        overlay_traces.append(go.Scatter(x=df.index, y=ma20,
            line=dict(color="#ff9800", width=1.5), name="MA 20", hovertemplate="MA20: %{y:.2f}<extra></extra>"))
        overlay_traces.append(go.Scatter(x=df.index, y=ma50,
            line=dict(color="#e91e63", width=1.5), name="MA 50", hovertemplate="MA50: %{y:.2f}<extra></extra>"))

    if "Exponential MA (EMA)" in active_indicators:
        ema20 = ta.ema(close, length=20)
        ema50 = ta.ema(close, length=50)
        ema200= ta.ema(close, length=200)
        overlay_traces.append(go.Scatter(x=df.index, y=ema20,
            line=dict(color="#ff9800", width=1.5, dash="dot"), name="EMA 20"))
        overlay_traces.append(go.Scatter(x=df.index, y=ema50,
            line=dict(color="#2196f3", width=1.5, dash="dot"), name="EMA 50"))
        overlay_traces.append(go.Scatter(x=df.index, y=ema200,
            line=dict(color="#9c27b0", width=1.5, dash="dot"), name="EMA 200"))

    if "Bollinger Bands" in active_indicators:
        bb = ta.bbands(close, length=20)
        if bb is not None:
            upper = bb.iloc[:, 2]
            mid   = bb.iloc[:, 1]
            lower = bb.iloc[:, 0]
            overlay_traces.append(go.Scatter(x=df.index, y=upper,
                line=dict(color="#e91e63", width=1, dash="dash"), name="BB Upper"))
            overlay_traces.append(go.Scatter(x=df.index, y=mid,
                line=dict(color="#ff9800", width=1), name="BB Mid"))
            overlay_traces.append(go.Scatter(x=df.index, y=lower,
                line=dict(color="#e91e63", width=1, dash="dash"), name="BB Lower",
                fill="tonexty", fillcolor="rgba(233,30,99,0.06)"))

    if "VWAP" in active_indicators:
        try:
            vwap = ta.vwap(high, low, close, volume)
            overlay_traces.append(go.Scatter(x=df.index, y=vwap,
                line=dict(color="#00bcd4", width=1.5, dash="dot"), name="VWAP"))
        except: pass

    if "Supertrend" in active_indicators:
        try:
            st = ta.supertrend(high, low, close, length=10, multiplier=3)
            if st is not None:
                sup_col = [c for c in st.columns if "SUPERT_" in c and "d" not in c.lower() and "l" not in c.lower() and "s" not in c.lower()]
                if sup_col:
                    overlay_traces.append(go.Scatter(x=df.index, y=st[sup_col[0]],
                        line=dict(color="#00e676", width=2), name="Supertrend"))
        except: pass

    if "Parabolic SAR" in active_indicators:
        try:
            psar = ta.psar(high, low, close)
            if psar is not None:
                psar_col = [c for c in psar.columns if "PSARl" in c or "PSARs" in c]
                if psar_col:
                    overlay_traces.append(go.Scatter(x=df.index, y=psar[psar_col[0]],
                        mode="markers", marker=dict(color="#ff5722", size=3, symbol="circle"),
                        name="Parabolic SAR"))
        except: pass

    if "Ichimoku Cloud" in active_indicators:
        try:
            ich = ta.ichimoku(high, low, close)
            if ich is not None and len(ich) >= 2:
                overlay_traces.append(go.Scatter(x=df.index, y=ich[0].iloc[:, 0],
                    line=dict(color="#26a69a", width=1), name="Tenkan"))
                overlay_traces.append(go.Scatter(x=df.index, y=ich[0].iloc[:, 1],
                    line=dict(color="#ef5350", width=1), name="Kijun"))
        except: pass

    # ── Subplot indicators ────────────────────────────────────────────────────
    if "MACD" in active_indicators:
        try:
            macd_df = ta.macd(close)
            if macd_df is not None:
                macd_line   = macd_df.iloc[:, 0]
                macd_signal = macd_df.iloc[:, 2]
                macd_hist   = macd_df.iloc[:, 1]
                hist_colors = ["#26a69a" if v >= 0 else "#ef5350"
                               for v in macd_hist.fillna(0)]
                subplot_traces.append([
                    go.Bar(x=df.index, y=macd_hist, marker_color=hist_colors,
                           name="MACD Hist", showlegend=False),
                    go.Scatter(x=df.index, y=macd_line,
                        line=dict(color="#2196f3", width=1.5), name="MACD"),
                    go.Scatter(x=df.index, y=macd_signal,
                        line=dict(color="#ff9800", width=1.5), name="Signal"),
                ])
                subplot_labels.append("MACD")
        except: pass

    if "RSI" in active_indicators:
        try:
            rsi = ta.rsi(close, length=14)
            subplot_traces.append([
                go.Scatter(x=df.index, y=rsi,
                    line=dict(color="#9c27b0", width=1.5), name="RSI"),
            ])
            subplot_labels.append("RSI")
        except: pass

    if "Stochastic" in active_indicators:
        try:
            stoch = ta.stoch(high, low, close)
            if stoch is not None:
                subplot_traces.append([
                    go.Scatter(x=df.index, y=stoch.iloc[:, 0],
                        line=dict(color="#2196f3", width=1.5), name="%K"),
                    go.Scatter(x=df.index, y=stoch.iloc[:, 1],
                        line=dict(color="#ff9800", width=1.5), name="%D"),
                ])
                subplot_labels.append("Stochastic")
        except: pass

    if "ATR" in active_indicators:
        try:
            atr = ta.atr(high, low, close, length=14)
            subplot_traces.append([
                go.Scatter(x=df.index, y=atr,
                    line=dict(color="#ff9800", width=1.5), name="ATR"),
            ])
            subplot_labels.append("ATR")
        except: pass

    if "ADX" in active_indicators:
        try:
            adx = ta.adx(high, low, close, length=14)
            if adx is not None:
                subplot_traces.append([
                    go.Scatter(x=df.index, y=adx.iloc[:, 0],
                        line=dict(color="#ffeb3b", width=1.5), name="ADX"),
                ])
                subplot_labels.append("ADX")
        except: pass

    if "CCI" in active_indicators:
        try:
            cci = ta.cci(high, low, close, length=20)
            subplot_traces.append([
                go.Scatter(x=df.index, y=cci,
                    line=dict(color="#00bcd4", width=1.5), name="CCI"),
            ])
            subplot_labels.append("CCI")
        except: pass

    if "Williams %R" in active_indicators:
        try:
            willr = ta.willr(high, low, close, length=14)
            subplot_traces.append([
                go.Scatter(x=df.index, y=willr,
                    line=dict(color="#e91e63", width=1.5), name="Williams %R"),
            ])
            subplot_labels.append("Williams %R")
        except: pass

    if "OBV" in active_indicators:
        try:
            obv = ta.obv(close, volume)
            subplot_traces.append([
                go.Scatter(x=df.index, y=obv,
                    line=dict(color="#26a69a", width=1.5), name="OBV"),
            ])
            subplot_labels.append("OBV")
        except: pass

    if "Aroon" in active_indicators:
        try:
            aroon = ta.aroon(high, low, length=14)
            if aroon is not None:
                subplot_traces.append([
                    go.Scatter(x=df.index, y=aroon.iloc[:, 0],
                        line=dict(color="#26a69a", width=1.5), name="Aroon Up"),
                    go.Scatter(x=df.index, y=aroon.iloc[:, 1],
                        line=dict(color="#ef5350", width=1.5), name="Aroon Down"),
                ])
                subplot_labels.append("Aroon")
        except: pass

    if "Chaikin Money Flow" in active_indicators:
        try:
            cmf = ta.cmf(high, low, close, volume, length=20)
            subplot_traces.append([
                go.Scatter(x=df.index, y=cmf,
                    line=dict(color="#00e5ff", width=1.5), name="CMF"),
            ])
            subplot_labels.append("CMF")
        except: pass

    return overlay_traces, subplot_traces, subplot_labels


def build_figure(df, symbol_info, chart_type, active_indicators):
    """Build the full Plotly figure."""
    overlay, subplots, sub_labels = compute_indicators(df, active_indicators)

    has_volume = "Volume" in active_indicators
    n_sub = len(subplots) + (1 if has_volume else 0)
    total_rows = 1 + n_sub

    # Row heights
    if n_sub == 0:
        heights = [1.0]
    else:
        price_h = 0.60
        sub_h = (1.0 - price_h) / n_sub
        heights = [price_h] + [sub_h] * n_sub

    # Build subplot specs
    specs = [[{"type":"xy"}]] * total_rows

    fig = make_subplots(
        rows=total_rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.01,
        row_heights=heights,
        specs=specs,
    )

    close = df["Close"].squeeze()
    colors_vol = ["#26a69a" if c >= o else "#ef5350"
                  for c, o in zip(df["Close"].squeeze(), df["Open"].squeeze())]

    # ── Main price chart ──────────────────────────────────────────────────────
    if chart_type == "candle":
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"].squeeze(), high=df["High"].squeeze(),
            low=df["Low"].squeeze(),   close=df["Close"].squeeze(),
            increasing=dict(line=dict(color="#26a69a", width=1), fillcolor="#26a69a"),
            decreasing=dict(line=dict(color="#ef5350", width=1), fillcolor="#ef5350"),
            name=symbol_info["label"],
            hovertext=[f"O: {o:.2f} H: {h:.2f} L: {l:.2f} C: {c:.2f}"
                       for o,h,l,c in zip(
                           df["Open"].squeeze(), df["High"].squeeze(),
                           df["Low"].squeeze(), df["Close"].squeeze())],
            hoverinfo="x+text",
        ), row=1, col=1)

    elif chart_type == "ohlc":
        fig.add_trace(go.Ohlc(
            x=df.index,
            open=df["Open"].squeeze(), high=df["High"].squeeze(),
            low=df["Low"].squeeze(),   close=df["Close"].squeeze(),
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
            name=symbol_info["label"],
        ), row=1, col=1)

    elif chart_type == "line":
        fig.add_trace(go.Scatter(
            x=df.index, y=close,
            line=dict(color="#2196f3", width=2),
            name=symbol_info["label"],
        ), row=1, col=1)

    elif chart_type == "area":
        fig.add_trace(go.Scatter(
            x=df.index, y=close,
            line=dict(color="#2196f3", width=2),
            fill="tozeroy", fillcolor="rgba(33,150,243,0.1)",
            name=symbol_info["label"],
        ), row=1, col=1)

    # Overlay indicators on price chart
    for trace in overlay:
        fig.add_trace(trace, row=1, col=1)

    # ── Volume bar ────────────────────────────────────────────────────────────
    current_row = 2
    if has_volume:
        fig.add_trace(go.Bar(
            x=df.index, y=df["Volume"].squeeze(),
            marker_color=colors_vol, name="Volume", showlegend=False,
            hovertemplate="Vol: %{y:,.0f}<extra></extra>",
        ), row=current_row, col=1)
        fig.update_yaxes(title_text="Vol", row=current_row, col=1,
            title_font=dict(size=10, color="#787b86"),
            tickfont=dict(size=9, color="#787b86"))
        current_row += 1

    # ── Subplot indicators ────────────────────────────────────────────────────
    for i, (traces, label) in enumerate(zip(subplots, sub_labels)):
        for trace in traces:
            fig.add_trace(trace, row=current_row, col=1)
        # Reference lines
        if label == "RSI":
            fig.add_hline(y=70, line_dash="dash", line_color="#ef5350",
                          line_width=1, row=current_row, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#26a69a",
                          line_width=1, row=current_row, col=1)
            fig.add_hline(y=50, line_dash="dot", line_color="#787b86",
                          line_width=1, row=current_row, col=1)
        elif label == "Stochastic":
            fig.add_hline(y=80, line_dash="dash", line_color="#ef5350",
                          line_width=1, row=current_row, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color="#26a69a",
                          line_width=1, row=current_row, col=1)
        elif label == "CCI":
            fig.add_hline(y=100,  line_dash="dash", line_color="#ef5350",
                          line_width=1, row=current_row, col=1)
            fig.add_hline(y=-100, line_dash="dash", line_color="#26a69a",
                          line_width=1, row=current_row, col=1)

        fig.update_yaxes(title_text=label, row=current_row, col=1,
            title_font=dict(size=10, color="#787b86"),
            tickfont=dict(size=9, color="#787b86"))
        current_row += 1

    # ── Global layout ─────────────────────────────────────────────────────────
    fig.update_layout(
        paper_bgcolor=THEME["bg_main"],
        plot_bgcolor=THEME["bg_main"],
        font=dict(family="'Trebuchet MS', sans-serif", color=THEME["text_main"]),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=THEME["bg_card"], bordercolor=THEME["border"],
            font=dict(color=THEME["text_main"], size=12)
        ),
        margin=dict(l=8, r=8, t=8, b=8),
        legend=dict(
            bgcolor="rgba(0,0,0,0)", bordercolor=THEME["border"],
            borderwidth=0, font=dict(size=12),
            x=0.01, y=0.99, xanchor="left", yanchor="top"
        ),
        xaxis_rangeslider_visible=False,
        showlegend=True,
        dragmode="pan",
    )

    # Style all axes
    for i in range(1, total_rows + 1):
        fig.update_xaxes(
            showgrid=True, gridcolor="#1e2130", gridwidth=0.5,
            showline=False, zeroline=False,
            tickfont=dict(size=11, color=THEME["text_dim"]),
            showspikes=True, spikethickness=1, spikecolor=THEME["text_dim"],
            spikedash="solid", spikemode="across",
            row=i, col=1,
        )
        fig.update_yaxes(
            showgrid=True, gridcolor="#1e2130", gridwidth=0.5,
            showline=False, zeroline=False,
            tickfont=dict(size=11, color=THEME["text_dim"]),
            side="right",
            showspikes=True, spikethickness=1, spikecolor=THEME["text_dim"],
            row=i, col=1,
        )

    return fig


# ─── CALLBACKS ────────────────────────────────────────────────────────────────

# Open/close indicators modal
@app.callback(
    Output("indicators-modal", "style"),
    Input("btn-indicators", "n_clicks"),
    Input("close-indicators", "n_clicks"),
    State("indicators-modal", "style"),
    prevent_initial_call=True,
)
def toggle_modal(open_clicks, close_clicks, current_style):
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    trigger = ctx.triggered[0]["prop_id"]
    base_style = {
        "position":"fixed","top":"0","left":"0","width":"100%","height":"100%",
        "background":"rgba(0,0,0,0.7)","zIndex":"9999",
        "justifyContent":"center","alignItems":"center"
    }
    if "btn-indicators" in trigger:
        return {**base_style, "display":"flex"}
    return {**base_style, "display":"none"}


# Indicator list (with search filter)
@app.callback(
    Output("indicator-list-items", "children"),
    Input("indicator-search", "value"),
    Input("store-indicators", "data"),
)
def update_indicator_list(search, active):
    active = active or []
    items = INDICATORS_LIST
    if search:
        items = [i for i in items if search.lower() in i.lower()]
    children = []
    for ind in items:
        is_active = ind in active
        children.append(html.Div([
            html.Span(ind),
            html.Span("✓ Added" if is_active else "+ Add",
                style={"fontSize":"12px",
                       "color": THEME["green"] if is_active else THEME["text_dim"]}),
        ], className="ind-list-item",
           id={"type":"ind-toggle", "index": ind},
           n_clicks=0,
        ))
    return children


# Toggle indicator on/off when clicked in list
@app.callback(
    Output("store-indicators", "data"),
    Input({"type":"ind-toggle", "index": dash.ALL}, "n_clicks"),
    State("store-indicators", "data"),
    prevent_initial_call=True,
)
def toggle_indicator(n_clicks_list, active):
    active = active or []
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    trigger_id = ctx.triggered[0]["prop_id"]
    try:
        ind_name = json.loads(trigger_id.split(".")[0])["index"]
    except:
        return active
    if ind_name in active:
        active = [a for a in active if a != ind_name]
    else:
        active = active + [ind_name]
    return active


# Show active indicators in modal
@app.callback(
    Output("active-indicators-display", "children"),
    Input("store-indicators", "data"),
)
def show_active(active):
    active = active or []
    if not active:
        return html.Span("None", style={"color":THEME["text_dim"],"fontSize":"13px"})
    return html.Div([
        html.Span([
            ind,
            html.Span(" ✕", style={"cursor":"pointer","marginLeft":"4px",
                                    "color":THEME["text_dim"]}),
        ], className="ind-active-tag")
        for ind in active
    ], style={"display":"flex","flexWrap":"wrap"})


# Chart type store
@app.callback(
    Output("store-charttype", "data"),
    Input("btn-type-candle", "n_clicks"),
    Input("btn-type-ohlc",   "n_clicks"),
    Input("btn-type-line",   "n_clicks"),
    Input("btn-type-area",   "n_clicks"),
    prevent_initial_call=True,
)
def set_chart_type(c1, c2, c3, c4):
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    trigger = ctx.triggered[0]["prop_id"]
    if "candle" in trigger: return "candle"
    if "ohlc"   in trigger: return "ohlc"
    if "line"   in trigger: return "line"
    if "area"   in trigger: return "area"
    return "candle"


# Symbol from watchlist click
@app.callback(
    Output("store-symbol", "data"),
    Input({"type":"wl-row", "index": dash.ALL}, "n_clicks"),
    State("store-symbol", "data"),
    prevent_initial_call=True,
)
def set_symbol_from_watchlist(n_clicks_list, current):
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    trigger_id = ctx.triggered[0]["prop_id"]
    try:
        sym = json.loads(trigger_id.split(".")[0])["index"]
        return sym
    except:
        return current


# Also update symbol from dropdown
@app.callback(
    Output("store-symbol", "data", allow_duplicate=True),
    Input("dd-symbol", "value"),
    prevent_initial_call=True,
)
def set_symbol_from_dropdown(value):
    return value or no_update


# Timeframe store
@app.callback(
    Output("store-tf", "data"),
    [Input(f"btn-tf-{tf['value']}", "n_clicks") for tf in TIMEFRAMES],
    prevent_initial_call=True,
)
def set_timeframe(*args):
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    trigger = ctx.triggered[0]["prop_id"]
    for tf in TIMEFRAMES:
        if f"btn-tf-{tf['value']}" in trigger:
            return tf["value"]
    return "1d"


# Main chart render
@app.callback(
    Output("main-chart", "figure"),
    Output("ohlcv-bar", "children"),
    Output("top-price-display", "children"),
    Input("store-symbol", "data"),
    Input("store-tf", "data"),
    Input("store-charttype", "data"),
    Input("store-indicators", "data"),
    Input("interval-refresh", "n_intervals"),
)
def update_chart(symbol, tf, chart_type, active_indicators, _):
    # Find timeframe config
    tf_cfg = next((t for t in TIMEFRAMES if t["value"] == tf), TIMEFRAMES[0])
    symbol_info = next((w for w in WATCHLIST if w["symbol"] == symbol),
                       {"symbol": symbol, "label": symbol, "exchange": ""})

    df = fetch_data(symbol, period=tf_cfg["period"], interval=tf_cfg["interval"])

    if df is None or df.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            paper_bgcolor=THEME["bg_main"], plot_bgcolor=THEME["bg_main"],
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False),
            annotations=[dict(text="No data available", x=0.5, y=0.5,
                xref="paper", yref="paper", showarrow=False,
                font=dict(color=THEME["text_dim"], size=16))]
        )
        return empty_fig, "No data", ""

    close = df["Close"].squeeze()
    last_close = float(close.iloc[-1])
    prev_close = float(close.iloc[-2]) if len(close) > 1 else last_close
    change     = last_close - prev_close
    change_pct = (change / prev_close * 100) if prev_close != 0 else 0
    color      = THEME["green"] if change >= 0 else THEME["red"]
    sign       = "+" if change >= 0 else ""

    last_row   = df.iloc[-1]
    o = float(last_row["Open"].squeeze())  if hasattr(last_row["Open"],  "squeeze") else float(last_row["Open"])
    h = float(last_row["High"].squeeze())  if hasattr(last_row["High"],  "squeeze") else float(last_row["High"])
    l = float(last_row["Low"].squeeze())   if hasattr(last_row["Low"],   "squeeze") else float(last_row["Low"])
    c = float(last_row["Close"].squeeze()) if hasattr(last_row["Close"], "squeeze") else float(last_row["Close"])
    v = float(last_row["Volume"].squeeze())if hasattr(last_row["Volume"],"squeeze") else float(last_row["Volume"])

    # OHLCV bar
    def ohlcv_item(label, value, color=THEME["text_main"]):
        return html.Span([
            html.Span(label + " ", style={"color":THEME["text_dim"],"fontSize":"12px"}),
            html.Span(f"{value:,.2f}", style={"color":color,"fontSize":"13px","fontWeight":"500"}),
        ], style={"marginRight":"8px"})

    ohlcv_bar = [
        html.Span(f"{symbol_info['name']}  {tf_cfg['label']} · {symbol_info['exchange']}",
            style={"color":THEME["text_dim"],"fontSize":"12px","marginRight":"16px"}),
        ohlcv_item("O", o),
        ohlcv_item("H", h, THEME["green"]),
        ohlcv_item("L", l, THEME["red"]),
        ohlcv_item("C", c, color),
        html.Span([
            html.Span(f"{sign}{change:.2f} ({sign}{change_pct:.2f}%)",
                style={"color":color,"fontSize":"13px","fontWeight":"500"}),
        ]),
        html.Span(f"  Vol: {v:,.0f}", style={"color":THEME["text_dim"],"fontSize":"12px","marginLeft":"8px"}),
    ]

    # Top price display
    top_price = html.Div([
        html.Span(f"{last_close:,.2f}", style={
            "color":color,"fontSize":"15px","fontWeight":"700","marginRight":"8px"
        }),
        html.Span(f"{sign}{change_pct:.2f}%", style={
            "color":color,"fontSize":"13px"
        }),
    ], style={"display":"flex","alignItems":"center"})

    # Build figure
    active = active_indicators or []
    fig = build_figure(df, symbol_info, chart_type or "candle", active)
    return fig, ohlcv_bar, top_price


# Watchlist render
@app.callback(
    Output("watchlist-items", "children"),
    Output("symbol-detail", "children"),
    Input("interval-refresh", "n_intervals"),
    Input("store-symbol", "data"),
)
def update_watchlist(_, active_symbol):
    items = []
    detail = html.Div("Loading...", style={"color":THEME["text_dim"],"fontSize":"12px"})

    for w in WATCHLIST:
        try:
            tkr = yf.Ticker(w["symbol"])
            info = tkr.fast_info
            last  = float(info.last_price) if info.last_price else 0
            prev  = float(info.previous_close) if info.previous_close else last
            chg   = last - prev
            pct   = (chg / prev * 100) if prev else 0
            color = THEME["green"] if chg >= 0 else THEME["red"]
            sign  = "+" if chg >= 0 else ""
            is_active = w["symbol"] == active_symbol

            items.append(html.Div([
                html.Div([
                    html.Div(w["label"], style={
                        "fontSize":"13px","fontWeight":"600","color":THEME["text_bright"]
                    }),
                    html.Div(w["exchange"], style={
                        "fontSize":"10px","color":THEME["text_dim"]
                    }),
                ], style={"flex":"1"}),
                html.Div(f"{last:,.2f}", style={
                    "width":"80px","textAlign":"right","fontSize":"13px",
                    "color":THEME["text_main"],"fontWeight":"500"
                }),
                html.Div(f"{sign}{pct:.2f}%", style={
                    "width":"70px","textAlign":"right","fontSize":"12px","color":color
                }),
            ], className=f"watchlist-row {'watchlist-active' if is_active else ''}",
               id={"type":"wl-row","index":w["symbol"]},
               n_clicks=0,
            ))

            # Detail for active symbol
            if w["symbol"] == active_symbol:
                chg_color = THEME["green"] if chg >= 0 else THEME["red"]
                detail = html.Div([
                    html.Div(w["label"], style={
                        "fontSize":"18px","fontWeight":"700",
                        "color":THEME["text_bright"],"marginBottom":"2px"
                    }),
                    html.Div(w["name"], style={
                        "fontSize":"11px","color":THEME["text_dim"],"marginBottom":"8px"
                    }),
                    html.Div(f"{last:,.2f}", style={
                        "fontSize":"22px","fontWeight":"700",
                        "color":THEME["text_bright"],"marginBottom":"2px"
                    }),
                    html.Div(f"{sign}{chg:.2f}  {sign}{pct:.2f}%", style={
                        "fontSize":"13px","color":chg_color,"marginBottom":"8px"
                    }),
                    html.Div("Market " + ("open" if datetime.now().hour < 16 else "closed"), style={
                        "fontSize":"11px","color":THEME["text_dim"]
                    }),
                ])
        except Exception as e:
            items.append(html.Div(w["label"], className="watchlist-row",
                id={"type":"wl-row","index":w["symbol"]}, n_clicks=0))

    return items, detail


# Bottom time display
@app.callback(
    Output("bottom-time", "children"),
    Input("interval-refresh", "n_intervals"),
)
def update_time(_):
    now = datetime.now()
    return now.strftime("%H:%M:%S UTC+5:30")


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  Trading Platform starting...")
    print("  Open in browser: http://localhost:8050")
    print("  Press Ctrl+C to stop")
    print("="*55 + "\n")
    app.run(debug=False, port=8050)