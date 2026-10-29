# -*- coding: utf-8 -*-
"""Shared visual tokens and responsive Streamlit styling."""
import plotly.graph_objects as go
import streamlit as st

COLORS = {
    'ink': '#20313b',
    'muted': '#667681',
    'canvas': '#e7ecef',
    'surface': '#f4f7f8',
    'panel': '#ffffff',
    'blue': '#2475a7',
    'teal': '#168177',
    'red': '#c65252',
    'amber': '#d18d32',
    'slate': '#718796',
    'grid': '#d9e1e5',
    # ★帕雷托頁專用醒目色：模擬＝亮藍、實測＝亮紅（深色為前沿線）
    'vivid_blue': '#1e7bff',
    'deep_blue': '#0b3f9e',
    'vivid_red': '#ff2d55',
    'deep_red': '#a8002a',
}
CHART_COLORS = [
    COLORS['blue'], COLORS['teal'], COLORS['amber'], COLORS['red'],
    '#715f9d', '#317b78', '#9a6b43', COLORS['slate'],
  ]

# ── 帕雷托頁字級（各自獨立倍率，以 Plotly 預設值為基準）──
# Plotly 預設刻度約 12px、軸標題約 14px、圖例約 12px、圖表標題約 17px。
# 要放大／縮小只改對應倍率，不要在 app.py 寫死數字。
#
# 演進：v1 全部 ×3；v2 依需求調整為
#   XY 軸刻度 → 原本的 2/3（36 → 24）
#   XY 軸標題、圖例 → 原本的 1/2（42 → 21、36 → 18）
#   圖表標題未指定，維持 ×3（51）
PARETO_TICK_SCALE = 2.0        # 12 → 24（= 原 3.0 的 2/3）
PARETO_AXIS_TITLE_SCALE = 1.5  # 14 → 21（= 原 3.0 的 1/2）
PARETO_LEGEND_SCALE = 1.5      # 12 → 18（= 原 3.0 的 1/2）
PARETO_TITLE_SCALE = 3.0       # 17 → 51（不變）

PARETO_TICK_FONT = int(12 * PARETO_TICK_SCALE)              # XY 軸刻度數值
PARETO_AXIS_TITLE_FONT = int(14 * PARETO_AXIS_TITLE_SCALE)  # XY 軸標題文字
PARETO_LEGEND_FONT = int(12 * PARETO_LEGEND_SCALE)          # 圖例文字
PARETO_TITLE_FONT = int(17 * PARETO_TITLE_SCALE)            # 圖表標題


def apply_theme():
    """Install the shared soft-skeuomorphic dashboard style."""
    st.markdown(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
      @import url('https://unpkg.com/@phosphor-icons/web@2.1.1/src/regular/style.css');
      :root {{
        --ink: {COLORS['ink']}; --muted: {COLORS['muted']};
        --canvas: {COLORS['canvas']}; --panel: {COLORS['panel']};
        --blue: {COLORS['blue']}; --teal: {COLORS['teal']};
        --shadow-raised: 10px 10px 22px #c8d0d4, -10px -10px 22px #ffffff;
        --shadow-inset: inset 3px 3px 7px #d0d7da, inset -3px -3px 7px #ffffff;
      }}
      .stApp {{ background: var(--canvas); color: var(--ink); }}
      .main .block-container {{ max-width: 1440px; padding: 1.4rem 2rem 3.6rem; }}
      html, body, [class*="css"], [data-testid="stMarkdownContainer"] {{
        font-family: 'Noto Sans TC', sans-serif;
      }}
      h1, h2, h3 {{ color: var(--ink); letter-spacing: 0; }}
      h1, .dashboard-title {{ font-family: 'Space Grotesk', 'Noto Sans TC', sans-serif; }}
      .ph {{ display: inline-flex; align-items: center; line-height: 1; }}
      .dashboard-header {{ display: flex; align-items: flex-start; gap: .9rem; margin-bottom: .35rem; }}
      .dashboard-mark {{ display: grid; place-items: center; flex: 0 0 auto; width: 2.8rem; height: 2.8rem;
        color: var(--blue); background: var(--panel); border-radius: 8px;
        box-shadow: 6px 6px 14px #cbd3d7, -6px -6px 14px #fff; font-size: 1.45rem; }}
      .dashboard-mark .ph {{ font-size: 1.45rem; }}
      .dashboard-meta {{ display: flex; flex-wrap: wrap; gap: .8rem; color: var(--muted); margin: -.1rem 0 1.2rem 3.7rem; font-size: .78rem; }}
      .dashboard-meta span {{ display: inline-flex; align-items: center; gap: .3rem; }}
      [data-testid="stMetric"] {{
        background: var(--panel); border: 0; border-radius: 8px; box-shadow: var(--shadow-raised);
        padding: 1rem 1.1rem; min-height: 104px;
      }}
      [data-testid="stMetricLabel"] {{ color: var(--muted); font-size: .8rem; }}
      [data-testid="stMetricValue"] {{ color: var(--ink); font-family: 'Space Grotesk', 'Noto Sans TC', sans-serif; font-size: 1.65rem; text-align: right; }}
      [data-testid="stMetricDelta"] {{ justify-content: flex-end; }}
      [data-testid="stVerticalBlockBorderWrapper"], .stExpander {{
        background: var(--panel); border: 0 !important; border-radius: 8px;
        box-shadow: 7px 7px 16px #cbd3d7, -7px -7px 16px #ffffff;
      }}
      .stExpander {{ padding: .1rem .35rem; }}
      .stButton > button, [data-testid="stDownloadButton"] > button {{
        border: 0; border-radius: 7px; background: var(--panel); color: var(--ink);
        box-shadow: 5px 5px 11px #cbd3d7, -5px -5px 11px #ffffff;
        font-weight: 600;
      }}
      .stButton > button[kind="primary"], [data-testid="stDownloadButton"] > button[kind="primary"] {{
        background: var(--blue); color: #fff; box-shadow: 5px 5px 11px #b6c1c7, -4px -4px 10px #fff;
      }}
      .stButton > button:active, [data-testid="stDownloadButton"] > button:active {{ box-shadow: var(--shadow-inset); transform: translateY(1px); }}
      [data-baseweb="select"] > div, [data-testid="stNumberInput"] input {{
        background: #f8fafb !important; border: 0 !important; border-radius: 6px !important;
        box-shadow: var(--shadow-inset) !important;
      }}
      [data-testid="stDataFrame"] {{ border-radius: 8px; overflow: hidden; box-shadow: var(--shadow-raised); }}
      [data-testid="stDataFrame"] [role="columnheader"] {{ background: #edf2f4; color: var(--muted); font-weight: 700; }}
      .table-scroll {{ overflow-x: auto; background: var(--panel); border-radius: 8px;
        box-shadow: var(--shadow-raised); margin: .5rem 0 .9rem; }}
      .report-table {{ width: 100%; border-collapse: collapse; font-size: .86rem; min-width: 560px; }}
      .report-table th {{ background: #edf2f4; color: var(--muted); font-weight: 700;
        text-align: center; padding: .6rem .8rem; white-space: nowrap;
        border-bottom: 2px solid var(--grid); }}
      .report-table td {{ padding: .5rem .8rem; border-top: 1px solid var(--grid);
        color: var(--ink); vertical-align: middle; word-break: break-word; }}
      .report-table td.c {{ text-align: center; white-space: nowrap; font-variant-numeric: tabular-nums; }}
      .report-table tbody tr:nth-child(even) td {{ background: #f7fafb; }}
      .report-table tbody tr:hover td {{ background: #edf4f8; }}
      [data-baseweb="tab-list"] {{ gap: .45rem; padding: .4rem; margin: 0 0 1.6rem; background: #edf2f4; border-radius: 8px; box-shadow: var(--shadow-inset); }}
      [data-baseweb="tab"] {{ height: 42px; background: transparent; border-radius: 6px; color: var(--muted); font-weight: 600; padding: 0 .9rem; }}
      [data-baseweb="tab"][aria-selected="true"] {{ background: var(--panel); color: var(--blue); box-shadow: 3px 3px 8px #cbd3d7, -3px -3px 8px #fff; }}
      [data-baseweb="tab-border"] {{ display: none; }}
      .dashboard-kicker {{ color: var(--teal); font-size: .78rem; font-weight: 700; letter-spacing: .08rem; margin-bottom: .25rem; }}
      .dashboard-title {{ margin: 0; font-size: 2rem; font-weight: 700; }}
      .dashboard-subtitle {{ color: var(--muted); margin: .35rem 0 1.1rem; font-size: .93rem; }}
      .section-heading {{ display: flex; align-items: center; gap: .45rem; margin: .6rem 0 .25rem; font-size: 1.35rem; font-weight: 700; }}
      .section-heading .ph {{ color: var(--blue); font-size: 1.2em; }}
      .section-caption {{ color: var(--muted); margin: 0 0 1rem; font-size: .88rem; }}
      .note {{ background: #f5f8f9; border-left: 4px solid var(--teal); padding: .75rem 1rem;
        font-size: .88rem; color: var(--ink); border-radius: 0 6px 6px 0; margin: .7rem 0 1rem;
        box-shadow: 4px 4px 10px #d1d9dd, -4px -4px 10px #fff; }}
      .summary-card {{ background: var(--panel); border-radius: 8px; box-shadow: var(--shadow-raised);
        min-height: 126px; padding: 1rem 1.1rem; margin: .35rem 0 1rem; }}
      .summary-card-title {{ color: var(--blue); font-weight: 700; margin-bottom: .65rem; }}
      .summary-card > div:not(.summary-card-title) {{ display: flex; justify-content: space-between;
        align-items: baseline; gap: .7rem; padding: .18rem 0; font-size: .82rem; }}
      .summary-card span {{ color: var(--muted); text-align: left; }}
      .summary-card strong {{ color: var(--ink); text-align: right; font-family: 'Space Grotesk', 'Noto Sans TC', sans-serif; }}
      .mobile-only {{ display: none; }}
      @media (max-width: 720px) {{
        .main .block-container {{ padding: 1rem 1rem 7rem; }}
        .dashboard-title {{ font-size: 1.5rem; }}
        .dashboard-subtitle {{ font-size: .78rem; }}
        .dashboard-mark {{ width: 2.35rem; height: 2.35rem; font-size: 1.2rem; }}
        .dashboard-mark .ph {{ font-size: 1.2rem; }}
        .dashboard-meta {{ margin-left: 3.25rem; gap: .55rem; font-size: .7rem; }}
        [data-testid="stMetric"] {{ min-height: 84px; padding: .7rem; }}
        [data-testid="stMetricValue"] {{ font-size: 1.3rem; }}
        [data-baseweb="tab-list"] {{
          position: fixed; bottom: 0; left: 0; right: 0; z-index: 1000; margin: 0;
          padding: .35rem .2rem calc(.35rem + env(safe-area-inset-bottom)); border-radius: 0;
          background: rgba(244, 247, 248, .97); box-shadow: 0 -5px 18px rgba(68, 87, 96, .16);
          justify-content: space-around;
        }}
        [data-baseweb="tab"] {{ flex: 1 1 20%; min-width: 0; height: 48px; padding: 0 .1rem; font-size: .68rem; white-space: normal; line-height: 1.05; }}
        [data-testid="stDataFrame"] {{ display: none; }}
        .desktop-only {{ display: none; }}
        .mobile-only {{ display: block; }}
        .data-card {{ background: var(--panel); border-radius: 8px; box-shadow: 5px 5px 12px #cbd3d7, -5px -5px 12px #fff; margin: .65rem 0; padding: .75rem .85rem; }}
        .data-card > div {{ display: flex; justify-content: space-between; gap: .8rem; padding: .2rem 0; font-size: .82rem; }}
        .data-card span {{ color: var(--muted); text-align: left; }}
        .data-card strong {{ color: var(--ink); text-align: right; font-weight: 700; }}
        .summary-card {{ min-height: 0; padding: .75rem; }}
        .summary-card-title {{ margin-bottom: .35rem; }}
        .stButton:has(button[kind="primary"]) {{ position: sticky; bottom: 4.75rem; z-index: 20; }}
      }}
    </style>
    """, unsafe_allow_html=True)


def style_figure(fig: go.Figure, height: int = 420, *, tick_font=None,
                 axis_title_font=None, legend_font=None, title_font=None,
                 margin=None, legend_y=None) -> go.Figure:
    """Apply the dashboard chart treatment consistently.

    字級與留白參數預設 None＝沿用既有主題（其他頁面不受影響）。
    帕雷托頁會傳入放大後的參數（見 PARETO_*_FONT）。
    """
    m = dict(l=20, r=20, t=52, b=36)
    if margin:
        m.update(margin)
    fig.update_layout(
        height=height,
        paper_bgcolor=COLORS['panel'],
        plot_bgcolor=COLORS['panel'],
        font=dict(family='Noto Sans TC, sans-serif', color=COLORS['ink']),
        colorway=CHART_COLORS,
        hoverlabel=dict(bgcolor=COLORS['ink'], font=dict(color='#ffffff')),
        margin=m,
        legend=dict(orientation='h', y=-0.2 if legend_y is None else legend_y),
    )
    fig.update_xaxes(gridcolor=COLORS['grid'], zerolinecolor=COLORS['grid'])
    fig.update_yaxes(gridcolor=COLORS['grid'], zerolinecolor=COLORS['grid'])
    if tick_font:
        fig.update_xaxes(tickfont=dict(size=tick_font))
        fig.update_yaxes(tickfont=dict(size=tick_font))
    if axis_title_font:
        fig.update_xaxes(title=dict(font=dict(size=axis_title_font)))
        fig.update_yaxes(title=dict(font=dict(size=axis_title_font)))
    if legend_font:
        fig.update_layout(legend=dict(font=dict(size=legend_font)))
    if title_font:
        fig.update_layout(title=dict(font=dict(size=title_font)))
    return fig
