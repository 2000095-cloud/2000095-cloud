# -*- coding: utf-8 -*-
"""Reusable dashboard components shared by the Streamlit report pages."""
import pandas as pd
import streamlit as st


def render_header():
    st.markdown("""
        <div class="dashboard-header">
            <div class="dashboard-mark"><i class="ph ph-cube-focus"></i></div>
            <div>
                <div class="dashboard-kicker">CEMENT INTELLIGENCE PLATFORM</div>
                <div class="dashboard-title">水泥強度決策儀表板</div>
                <div class="dashboard-subtitle">XRD 晶相、物性資料與分段模型的品質分析工作台</div>
            </div>
        </div>
        <div class="dashboard-meta">
            <span><i class="ph ph-chart-line-up"></i>品質預測</span>
            <span><i class="ph ph-flask"></i>VCCTL 模擬</span>
            <span><i class="ph ph-shield-check"></i>Nested LOO 驗證</span>
        </div>
    """, unsafe_allow_html=True)


def section_heading(title, caption=None, icon=None):
    """Render a section heading with an optional Phosphor icon."""
    icon_html = f'<i class="ph ph-{icon}"></i>' if icon else ''
    st.markdown(
        f'<div class="section-heading">{icon_html}<span>{title}</span></div>',
        unsafe_allow_html=True)
    if caption:
        st.markdown(f'<div class="section-caption">{caption}</div>', unsafe_allow_html=True)


def summary_cards(rows, fields):
    """Render source-level summaries as cards on every viewport."""
    columns = st.columns(len(rows))
    for column, row in zip(columns, rows):
        with column:
            title = row.get('資料來源', '摘要')
            details = ''.join(
                f'<div><span>{field}</span><strong>{row.get(field, "-")}</strong></div>'
                for field in fields if field in row)
            st.markdown(
                f'<div class="summary-card"><div class="summary-card-title">{title}'
                f'</div>{details}</div>', unsafe_allow_html=True)


def fmt_cell(v):
    """把單一 cell 值轉成顯示字串：整數不加小數，浮點最多 3 位、去尾零。"""
    if v is None:
        return '—'
    if isinstance(v, float):
        if pd.isna(v):
            return '—'
        if v.is_integer():
            return str(int(v))
        return f'{v:.3f}'.rstrip('0').rstrip('.')
    if isinstance(v, bool):
        return '是' if v else '否'
    return str(v)


def render_table(df: pd.DataFrame, center_cols=None, left_cols=None,
                 caption=None):
    """以自訂 HTML 表格渲染清單，置中與小數位完全可控、跨版本穩定。

    對齊規則（可由 center_cols / left_cols 覆寫）：
    - 表頭（th）全部置中
    - 第一欄置中（任務／分段等短標籤）
    - 「等級」欄（A/B/C/D）與數值欄置中
    - 其餘長文字欄（模型／特徵…）靠左
    數值一律經 fmt_cell：整數無小數、浮點最多 3 位且去尾零。
    """
    if df is None or len(df) == 0:
        if caption:
            st.caption(caption)
        return
    cols = list(df.columns)
    center = {cols[0]} if cols else set()
    for c in cols:
        if c == '等級' or pd.api.types.is_numeric_dtype(df[c]):
            center.add(c)
    if center_cols:
        center |= set(center_cols)
    if left_cols:
        center -= set(left_cols)

    head = ''.join(f'<th>{html_escape(str(c))}</th>' for c in cols)
    body = []
    for _, row in df.iterrows():
        tds = []
        for c in cols:
            cls = ' class="c"' if c in center else ''
            tds.append(f'<td{cls}>{html_escape(fmt_cell(row[c]))}</td>')
        body.append(f'<tr>{"".join(tds)}</tr>')

    st.markdown(
        f'<div class="table-scroll"><table class="report-table">'
        f'<thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody>'
        f'</table></div>', unsafe_allow_html=True)
    if caption:
        st.caption(caption)


def html_escape(v):
    """Escape 使用者資料中的 HTML 特殊字元。"""
    import html
    return html.escape(str(v), quote=False)


def responsive_dataframe(frame: pd.DataFrame, fields=None, height=360):
    """桌面以 HTML 表格呈現；行動版改為精簡 field/value 卡片。"""
    render_table(frame)
    fields = fields or list(frame.columns[:4])
    st.markdown('<div class="mobile-only">', unsafe_allow_html=True)
    for _, row in frame.iterrows():
        values = ''.join(
            f'<div><span>{field}</span><strong>{html_escape(fmt_cell(row.get(field)))}</strong></div>'
            for field in fields if field in row.index)
        st.markdown(f'<div class="data-card">{values}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
