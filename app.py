# -*- coding: utf-8 -*-
"""
app.py — 水泥強度預測與帕雷托分析（Hugging Face Spaces / Streamlit）
====================================================================
四個頁籤：
  ① 強度預測 — 上傳 Excel 或手動輸入 → 3/7/28 天預測
  ② 帕雷托分析 — 6000 筆模擬 vs 模型預測值，16 個特徵可切換
    ③ 模型可信度 — 各分段的 Trust Grade / 模型 R² / Nested R² / <2MPa%
  ④ 使用說明
"""
import io
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

import core
from ui import charts, components, theme

st.set_page_config(page_title='水泥強度決策儀表板', page_icon='C', layout='wide')
theme.apply_theme()
components.render_header()

TAB1, TAB2, TAB3, TAB5, TAB4 = st.tabs(
    ['預測', '帕雷托', '可信度', '資料與可靠性', '說明'])


# ══════════════════════════════════════════════
#  ① 強度預測
# ══════════════════════════════════════════════
with TAB1:
    left, right = st.columns([1, 1.4])

    with left:
        components.section_heading('輸入資料', icon='tray-arrow-up')
        mode = st.radio('輸入方式', ['上傳 Excel', '手動輸入'],
                        horizontal=True, label_visibility='collapsed',
                        key='t1_mode')

        c1, c2 = st.columns(2)
        plant = c1.selectbox('廠區', ['和平', '蘇澳'], key='t1_plant')
        ctype = c2.selectbox('型別', ['I型', 'II型', 'IL型'], key='t1_type')
        seg = core.SEG_OF.get((plant, ctype))
        if seg:
            st.caption(f'→ 對應分段：**{seg}**')
        else:
            st.warning(f'{plant} 沒有 {ctype} 的模型')

        df_in = None
        if mode == '上傳 Excel':
            up = st.file_uploader('選擇 Excel 或 CSV',
                                  type=['xlsx', 'xls', 'csv'],
                                  key='t1_upload')
            if up:
                try:
                    df_in = (pd.read_csv(up) if up.name.endswith('.csv')
                             else pd.read_excel(up))
                    df_in = df_in[df_in[core.XRD_COLS[0]].notna()] \
                        if core.XRD_COLS[0] in df_in.columns else df_in
                    st.success(f'讀入 {len(df_in)} 筆')
                    if '年份' not in df_in.columns:
                        st.warning('⚠ 檔案缺少**「年份」欄**（必要，民國年）'
                                   '。年份是部分任務的模型特徵，'
                                   '未填時無法使用對應的任務。')
                    else:
                        yrs = core.fillable_years()
                        num = pd.to_numeric(df_in['年份'], errors='coerce')
                        bad = sorted({int(v) for v in num.dropna().unique()
                                      if float(v) not in [float(y)
                                                          for y in yrs]})
                        na_n = int(num.isna().sum())
                        msgs = []
                        if na_n:
                            msgs.append(f'{na_n} 筆「年份」為空白或非數值')
                        if bad:
                            msgs.append('年份超出模型涵蓋：'
                                        + '、'.join(map(str, bad)))
                        if msgs:
                            st.warning('⚠ ' + '；'.join(msgs)
                                       + f'。模型年份只涵蓋 '
                                         f'**{yrs[0]}–{yrs[-1]}**（民國年），'
                                         '無法外推到其他年度。')
                except Exception as e:
                    st.error(f'讀取失敗：{e}')
            with st.expander('需要哪些欄位'):
                years = core.fillable_years()
                st.write('**必要**：' + '、'.join(core.REQUIRED + ['年份']))
                st.write('**可選**：7天'
                         + '（有 7天 實測可大幅提升 28 天準確度）')
                st.caption('「年份」請填**民國年**——它是部分任務的模型特徵、'
                           '無法外推，只能填下列模型涵蓋的年度：')
                yy = st.selectbox('年份（民國年）', years,
                                  index=len(years) - 1, key='t1_yr_hint',
                                  help='Excel 的「年份」欄請填下拉清單內的年度之一')
                tmpl_cols = list(core.REQUIRED) + ['年份', '7天']
                tmpl = pd.DataFrame([{c: (yy if c == '年份' else '')
                                      for c in tmpl_cols}])
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as w:
                    tmpl.to_excel(w, index=False, sheet_name='輸入範本')
                st.caption(f'空白範本的「年份」欄已帶入 **{yy}**（可自行改其他年度）。')
                st.download_button('下載空白範本', buf.getvalue(),
                                   '輸入範本.xlsx', width='stretch',
                                   key='t1_tmpl')
        else:
            real = core.load_real()
            ref = real[(real.get('廠區') == plant) & (real.get('type') == ctype)]
            d = ref.median(numeric_only=True) if len(ref) else None
            vals = {}
            st.markdown('**XRD 晶相 (%)**')
            cols = st.columns(3)
            for i, c in enumerate(core.XRD_COLS):
                dv = float(d[c]) if d is not None and c in d else 0.0
                vals[c] = cols[i % 3].number_input(c, value=round(dv, 2),
                                                   step=0.1, format='%.2f',
                                                   key=f't1_xrd_{c}')
            st.markdown('**物性**')
            cols = st.columns(2)
            for i, c in enumerate(core.PHYS_COLS):
                dv = float(d[c]) if d is not None and c in d else 0.0
                vals[c] = cols[i].number_input(c, value=round(dv, 2),
                                               step=1.0 if i == 0 else 0.1,
                                               format='%.2f', key=f't1_phys_{c}')
            st.markdown('**年份（民國）— 必要**')
            years = core.fillable_years()
            yr = st.selectbox(
                '年份', years, index=len(years) - 1, key='t1_year',
                format_func=lambda y: f'民國 {y} 年',
                help='年份是部分任務的模型特徵、無法外推，'
                     '只能選模型涵蓋的年度。')
            vals['年份'] = yr

            st.markdown('**選填**（有 7 天實測可大幅提升 28 天準確度）')
            s7 = st.number_input('7天實測', value=0.0, step=0.1,
                                 help='0 = 未量測', key='t1_s7')
            if s7 > 0:
                vals['7天'] = s7

            # 手動輸入也要建立單筆資料，否則預測按鈕會因 df_in=None 停用。
            df_in = pd.DataFrame([vals])

        go_btn = st.button('開始預測', type='primary', key='t1_go',
                           width='stretch', disabled=df_in is None)

    with right:
        components.section_heading('預測結果', icon='chart-bar')
        if df_in is not None and go_btn:
            miss = [c for c in core.REQUIRED + ['年份']
                    if c not in df_in.columns]
            if miss:
                st.error(f'缺少必要欄位：{miss}')
            else:
                with st.spinner('預測中…'):
                    res, msg = core.predict(df_in, plant, ctype)
                if msg:
                    st.warning(msg)

                if len(res) == 1:
                    r = res.iloc[0]
                    m1, m2, m3 = st.columns(3)
                    for m, a in zip([m1, m2, m3], core.AGE_COLS):
                        v = r.get(f'pred_{a}')
                        act = r.get(a)
                        if pd.notna(v):
                            delta = (f'{v - act:+.2f} vs 實測'
                                     if pd.notna(act) and act > 0 else None)
                            m.metric(f'{a} 預測', f'{v:.2f} MPa', delta)
                        else:
                            m.metric(f'{a} 預測', '—')
                    st.caption(f"分段 **{r['segment']}** ｜ "
                               f"模型 **{r['method']}** ｜ 任務 **{r['task']}**")
                    # 用模擬與實測分布定位本次預測，不解讀為強度高低排名。
                    real = core.load_real()
                    synth = core.load_synth()
                    ref = real[(real.get('廠區') == plant)
                               & (real.get('type') == ctype)]
                    sim = synth[synth.get('type') == ctype]
                    p28 = r.get('pred_28天')
                    if (len(ref) or len(sim)) and pd.notna(p28):
                        fig = go.Figure()
                        if len(sim) and '28天' in sim.columns:
                            fig.add_histogram(
                                x=sim['28天'].dropna(), nbinsx=24,
                                histnorm='probability density',
                                marker_color=theme.COLORS['slate'], opacity=.48,
                                name='同型別模擬分布')
                        if len(ref) and '28天' in ref.columns:
                            fig.add_histogram(
                                x=ref['28天'].dropna(), nbinsx=12,
                                histnorm='probability density',
                                marker_color=theme.COLORS['amber'], opacity=.62,
                                name='同型別實測分布')
                        fig.add_vline(x=float(p28), line_color=theme.COLORS['blue'],
                                      line_width=3,
                                      annotation_text=f'本次預測 {p28:.1f}')
                        fig.update_layout(
                            height=260, margin=dict(l=10, r=10, t=36, b=10),
                            title=f'{ctype}：模擬與實測的 28 天強度分布',
                            xaxis_title='28 天強度 (MPa)',
                            yaxis_title='機率密度', barmode='overlay',
                            showlegend=True)
                        st.plotly_chart(theme.style_figure(fig, 280),
                                        width='stretch')
                else:
                    show = [c for c in ['segment', 'task', 'method']
                            + [f'pred_{a}' for a in core.AGE_COLS]
                            + core.AGE_COLS if c in res.columns]
                    components.render_table(res[show].round(2))
                    ok = res['pred_28天'].notna().sum()
                    st.caption(f'成功預測 {ok}/{len(res)} 筆')

                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as w:
                    res.to_excel(w, index=False, sheet_name='預測結果')
                st.download_button('下載結果 (Excel)', buf.getvalue(),
                                   '強度預測結果.xlsx', type='primary',
                                   key='t1_dl')
        elif df_in is None:
            st.info('請先在左側輸入資料')


# ══════════════════════════════════════════════
#  ② 帕雷托分析
# ══════════════════════════════════════════════
with TAB2:
    components.section_heading('帕雷托最佳前沿', icon='chart-scatter')
    st.warning('模擬強度用於組成趨勢與候選配方探索；未經分段遷移校正時，不可直接視為實測強度。')
    st.markdown("""<div class="note">
    <b>怎麼讀</b>：帕雷托前沿是「互不相讓的最佳解集合」——線上的每一點，
    都找不到另一個配方能<u>同時</u>在兩個目標上都更好。<b>選擇應落在這條線上</b>，
    線內的點都被支配（存在更好的替代）。<br>
    <b>拐點</b>是曲率最大處，通常是性價比最高的折衷點。
    </div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1.4, 1, 1, 1])
    feat_opts = {f'{v[0]}（{k}）': k for k, v in core.PARETO_FEATURES.items()}
    fsel = c1.selectbox('X 軸特徵', list(feat_opts), index=0, key='t2_feat')
    xcol = feat_opts[fsel]
    age = c2.selectbox('Y 軸齡期', core.AGE_COLS, index=2, key='t2_age')
    tsel = c3.selectbox('型別', ['I型', 'II型', 'IL型'], index=2,
                        key='t2_type')
    src = c4.selectbox('資料來源', ['6000 筆模擬', '97 筆實測', '兩者疊圖'],
                       index=2, key='t2_src')

    name, direction, desc = core.PARETO_FEATURES[xcol]
    x_max = st.radio(
        f'{name} 的方向', ['越高越好（省成本／省能耗）', '越低越好'],
        index=0 if direction == 'up' else 1, horizontal=True,
        help=desc or '中性特徵，請依你的實際成本結構選擇',
        key=f't2_dir_{xcol}')
    x_is_max = x_max.startswith('越高')

    synth = core.load_synth()
    real = core.load_real()
    S = synth[synth['type'] == tsel]
    R = real[real['type'] == tsel]

    if xcol not in S.columns or len(S) == 0:
        st.warning(f'{tsel} 沒有 {name} 的資料')
    else:
        fig = go.Figure()
        summary = []

        def _add(df, label, cbg, cfr, marker, size_bg=6, size_fr=10,
                 width_fr=3.0, op_bg=0.55):
            if len(df) == 0 or xcol not in df.columns:
                return
            d = df.dropna(subset=[xcol, age])
            if len(d) == 0:
                return
            idx = core.pareto_front(d, xcol, age, x_is_max, True)
            fr = d.loc[idx].sort_values(xcol)
            plot = d if len(d) <= 1200 else d.sample(1200, random_state=0)
            fig.add_scatter(x=plot[xcol], y=plot[age], mode='markers',
                            name=f'{label}（被支配）',
                            marker=dict(color=cbg, size=size_bg, opacity=op_bg),
                            hovertemplate=f'{name}: %{{x:.2f}}<br>'
                                          f'{age}: %{{y:.2f}} MPa<extra></extra>')
            fig.add_scatter(x=fr[xcol], y=fr[age], mode='lines+markers',
                            name=f'{label} 前沿（{len(fr)}）',
                            line=dict(color=cfr, width=width_fr),
                            marker=dict(color=cfr, size=size_fr, symbol=marker),
                            hovertemplate=f'前沿<br>{name}: %{{x:.2f}}<br>'
                                          f'{age}: %{{y:.2f}} MPa<extra></extra>')
            k = core.knee_point(fr, xcol, age)
            if k is not None:
                fig.add_scatter(x=[fr.loc[k, xcol]], y=[fr.loc[k, age]],
                                mode='markers', name=f'{label} 拐點',
                                marker=dict(color=theme.COLORS['teal'], size=20,
                                            symbol='star',
                                            line=dict(color=theme.COLORS['panel'], width=1.5)),
                                hovertemplate=f'拐點（性價比最佳）<br>'
                                              f'{name}: %{{x:.2f}}<br>'
                                              f'{age}: %{{y:.2f}} MPa<extra></extra>')
            summary.append({'資料來源': label, '樣本數': len(d),
                            '前沿點數': len(fr),
                            f'{name}範圍': f'{d[xcol].min():.2f}~{d[xcol].max():.2f}',
                            f'{age}範圍':
                                f'{d[age].min():.1f}~{d[age].max():.1f}',
                            '拐點':
                                (f'{fr.loc[k, xcol]:.2f} → '
                                 f'{fr.loc[k, age]:.1f} MPa') if k is not None
                                else '—'})

        if src in ('6000 筆模擬', '兩者疊圖'):
            _add(S, '模擬', theme.COLORS['vivid_blue'], theme.COLORS['deep_blue'],
                 'square', size_bg=5, op_bg=0.5, size_fr=10, width_fr=3.0)
        if src in ('97 筆實測', '兩者疊圖'):
            _add(R, '實測', theme.COLORS['vivid_red'], theme.COLORS['deep_red'],
                 'diamond', size_bg=9, op_bg=0.85, size_fr=13, width_fr=4.0)

        arrow = '→ 越高越好' if x_is_max else '← 越低越好'
        fig.update_layout(
            title=f'{tsel}：{name} vs {age}強度',
            xaxis_title=f'{name}　{arrow}',
            yaxis_title=f'{age}抗壓強度 (MPa)　→ 越高越好',
            hovermode='closest')
        # 字級倍率集中在 theme.PARETO_*_SCALE（刻度 24／軸標題 21／圖例 18／標題 51）
        st.plotly_chart(
            theme.style_figure(
                fig, 700,
                tick_font=theme.PARETO_TICK_FONT,
                axis_title_font=theme.PARETO_AXIS_TITLE_FONT,
                legend_font=theme.PARETO_LEGEND_FONT,
                title_font=theme.PARETO_TITLE_FONT,
                margin=dict(l=110, r=40, t=110, b=200),
                legend_y=-0.20),
            width='stretch')

        if summary:
            components.summary_cards(
                summary, fields=['樣本數', '前沿點數', f'{name}範圍', f'{age}範圍', '拐點'])
            # 匯出前沿點
            exp = []
            for df, lab in [(S, '模擬'), (R, '實測')]:
                d = df.dropna(subset=[xcol, age])
                if len(d) == 0:
                    continue
                fr = d.loc[core.pareto_front(d, xcol, age, x_is_max, True)]
                fr = fr.copy()
                fr.insert(0, '資料來源', lab)
                exp.append(fr)
            if exp:
                out = pd.concat(exp, ignore_index=True)
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as w:
                    out.to_excel(w, index=False, sheet_name='帕雷托前沿')
                st.download_button('下載前沿配方 (Excel)', buf.getvalue(),
                                   f'帕雷托前沿_{tsel}_{name}_{age}.xlsx',
                                   key='t2_dl')

        if src == '兩者疊圖':
            st.markdown("""<div class="note">
            <b>模擬 vs 實測的差距怎麼看</b>：模擬涵蓋範圍較寬（含刻意生成的
            極端組成），實測集中在實際生產區間。<b>兩者前沿的落差 = 模擬的
            系統偏差</b>；若實測前沿明顯低於模擬前沿，代表該型別的模擬偏樂觀。
            </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  ③ 模型可信度
# ══════════════════════════════════════════════
with TAB3:
    components.section_heading('模型可信度', icon='seal-check')
    info = core.model_info()
    if info is None:
        st.warning('尚未載入模型檔（`cement_analysis_v6.6.pkl`）。'
                   '請把 v6.6 跑完產生的 pkl 放進 app 目錄。')
    else:
        st.markdown("""<div class="note">
        <b>Trust Grade</b>：A 可部署／B 可使用（需複核）／C 實驗性／D 不可靠。<br>
        <b>模型 R²</b> 是最終模型的標準 LOO R²；<b>Nested R²</b> 是
        連選特徵都不能看測試樣本的無偏估計，主要用於 Trust Grade 與過擬合檢查。
        <b><2MPa%</b> 是主要業務指標。
        </div>""", unsafe_allow_html=True)
        tasks = sorted(info['任務'].unique())
        selected_task = st.selectbox('校準驗證任務', tasks, key='t3_task')
        validation = core.validation_series(selected_task)
        if validation is None:
            st.info('此模型檔未保存 LOO 預測序列；重新訓練後可顯示實測校準驗證圖。')
        else:
            types = sorted(validation['型別'].dropna().unique())
            selected_types = st.multiselect('型別', types, default=types,
                                            key='t3_type')
            validation = validation[validation['型別'].isin(selected_types)]
            if validation.empty:
                st.info('請至少選擇一個型別以顯示校準驗證圖。')
            else:
                calibration, comparison = charts.validation_figures(
                    validation, selected_task)
                st.plotly_chart(theme.style_figure(calibration, 330),
                                width='stretch')
                st.plotly_chart(theme.style_figure(comparison, 430),
                                width='stretch')
        task_hits = []
        for task in tasks:
            performance = core.task_performance(task)
            if performance is None:
                continue
            weighted_hit, sample_n = core.weighted_hit(performance)
            task_hits.append((task, weighted_hit, sample_n))
        if task_hits:
            components.section_heading('各任務整體命中率',
                                       '依各分段訓練樣本數加權計算',
                                       icon='target')
            columns = st.columns(len(task_hits))
            for column, (task, weighted_hit, sample_n) in zip(columns, task_hits):
                column.metric(task, f'{weighted_hit:.1f}%',
                              f'加權 <2MPa% (n={sample_n})', delta_color='off')

        # ── 各分段的預測命中率（<2MPa%）──
        # 原「資料與可靠性」頁的區塊移入；與上方卡片共用模型檔 final_best。
        components.section_heading('各分段的預測命中率（<2MPa%）', icon='target')
        st.markdown("""<div class="note">
        <b><2MPa%</b> = 預測值與實測值相差 <b>2 MPa 以內</b>的批次比例，
        是本系統的<b>主要業務指標</b>——品管在乎的是「這批預測 45 MPa，
        實際會不會落在 43–47」，而不是統計上的解釋力。<br>
        下表<b>直接讀取模型檔</b>，重新訓練後會自動更新（含任務改名或新增）。
        </div>""", unsafe_allow_html=True)

        if core.load_model() is None:
            st.warning('尚未載入模型檔')
        else:
            tabs = st.tabs(['28 天', '7 天', '3 天'])

            for tb, age in zip(tabs, ['28天', '7天', '3天']):
                with tb:
                    tks = core.tasks_of_age(age)
                    if not tks:
                        st.warning(f'模型檔內沒有 {age} 的任務')
                        continue

                    # ── 摘要：各分段的最佳方案（等級 → <2MPa% → Nested R²
                    #     → 模型 R² → RMSE，見 core.seg_performance）──
                    best = core.seg_performance(age)
                    if best is not None:
                        w, n = core.weighted_hit(best)
                        st.markdown(f'**各分段的最佳方案**　'
                                    f'加權 <2MPa% = **{w:.1f}%**（n={n}）')
                        cs = st.columns(len(best))
                        for c, (_, row) in zip(cs, best.iterrows()):
                            c.metric(row['分段'], f"{row['<2MPa%']:.0f}%",
                                     f"{row['採用任務']}", delta_color='off')
                        components.render_table(best)

                    # ── 逐任務明細（28 天有多個任務時最有用）──
                    if len(tks) > 1:
                        st.markdown('---')
                        st.markdown(f'**逐任務比較**（{age} 共 {len(tks)} 個任務）')
                        rows = []
                        for tk in tks:
                            d = core.task_performance(tk)
                            if d is None:
                                continue
                            w, _ = core.weighted_hit(d)
                            need = (d['需模擬值'] == '是').sum()
                            rows.append({'任務': tk, '加權<2MPa%': round(w, 1),
                                         '需模擬值的分段': f'{need}/{len(d)}'})
                        if rows:
                            cmp_df = pd.DataFrame(rows).sort_values(
                                '加權<2MPa%', ascending=False)
                            components.render_table(
                                cmp_df, center_cols=['需模擬值的分段'])

                        for tk in tks:
                            d = core.task_performance(tk)
                            if d is None:
                                continue
                            w, _ = core.weighted_hit(d)
                            need = (d['需模擬值'] == '是').sum()
                            tag = (f'　{need} 個分段需 VCCTL 模擬值'
                                   if need else '　純實測特徵，隨時可用')
                            with st.expander(
                                    f'{tk}　加權 <2MPa% = {w:.1f}%{tag}'):
                                components.render_table(
                                    d, center_cols=['需模擬值'])

                        st.caption('模型 R² = 標準 LOO 表現；Nested R² = 特徵/模型選擇隔離後的評估，'
                                   '主要用於 Trust Grade　｜　'
                                   '等級：A 可部署／B 可使用／C 實驗性／D 不可靠　｜　'
                                   '「需模擬值」= 該分段的模型用到 sim_* 特徵，'
                                   '沒有 VCCTL 模擬結果時無法預測')

        st.markdown("""<div class="note">
        <b>怎麼解讀等級與命中率的落差</b>：有些分段 <2MPa% 很高（甚至 100%）
        但等級是 C 或 D——這不矛盾。<b><2MPa%</b> 衡量「多數批次夠準」，
        <b>等級</b>則綜合了 Nested R² 與 Bootstrap 信賴區間，
        反映「這個估計本身有多穩」。<b>樣本少時信賴區間必然很寬</b>，
        等級就會偏保守。兩者一起看才完整；Nested R² 不等於模型 R²。
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  ⑤ 資料來源與可靠性
# ══════════════════════════════════════════════
with TAB5:
    components.section_heading('訓練資料來源與可靠性基準', icon='database')

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
### 模擬資料（5,998 筆）

**來源**：NIST **VCCTL / CEMHYD3D** 水泥水化模擬
（引擎 10.0.0 @ commit f2c3a04af7e6）

```
XRD 晶相 + 粒徑分佈(PSD)
      ↓ 3D 微結構模擬
   水化程度 DoH
      ↓ σ_A · X^n
     強度預測
```

**產生方式**：以 97 筆實測的組成分布為基礎，用 GMM 取樣生成
（每型別 2,000 筆 = 正常區 70% + 高強尾端 15% + 低強尾端 15%）。

**校準**：強度公式 σ = σ_A·X^n 的常數由實測反解，
並經 **LOO 交叉驗證**把關——只有交叉驗證不輸凍結值才採用新值。

| 型別 | σ_A | n | 依據 |
|---|---|---|---|
| I型 | 95.2 | 2.46 | 48 筆實測校準 |
| II型 | 102.0 | 2.90 | 17 筆（樣本不足，沿用凍結） |
| IL型 | 84.4 | 2.46 | 32 筆實測校準 |

**物理校準**（合成標籤的系統偏差修正）：

| 型別×齡期 | 變數 | 係數 | 文獻依據 |
|---|---|---|---|
| IL型 3/7天 | Calcite | 0.011 | 石灰石稀釋 |
| IL型 28天 | Calcite | 0.012 | 10%取代→−13% |
| II型 28天 | Sulfate | 0.018 | 過硫酸鹽化 |

#### 28 天模擬與實測的差異

VCCTL/CEMHYD3D 是水化與微結構模型，不提供可套用到所有水泥的固定「28 天偏高」比例。
NIST 的使用說明明確指出，模型在特定材料與養護情境未必具有預測力，結果必須以實測驗證。

本案對 IL 型採用型別內相對校正：每增加 1% 石灰石，28 天合成標籤乘以
`1 − 0.012 × Calcite%`。因此 10% 石灰石約對應 **12% 相對修正**；其用途是修正
石灰石稀釋造成的斜率偏差，且校正後會重新對齊 IL 型合成平均值，**不是 VCCTL 一律高估 12%**。

I 型沒有通過交叉驗證的系統性修正；II 型只對 28 天的總硫酸鹽偏差做型別內校正。
前端的模擬/實測分布圖應用於判讀差異，不能把單一模擬值當作未校準的實測強度。

**文獻依據**：D. P. Bentz, *CEMHYD3D: A Three-Dimensional Cement Hydration and
Microstructure Development Modeling Package, Version 3.0*, NISTIR 7232 (2005),
https://doi.org/10.6028/NIST.IR.7232；CEMHYD3D v3 已納入 limestone/inert filler
對水化的影響。石灰石水泥的水化與稀釋機制可參考 De Weerdt et al.,
*Cement and Concrete Research* 41 (2011), https://doi.org/10.1016/j.cemconres.2010.11.014。
""")
    with c2:
        st.markdown("""
### 實測資料（97 筆）

**來源**：台泥和平廠、蘇澳廠的例行品管紀錄

| 分段 | 筆數 | 期間（民國） |
|---|---|---|
| 和平I型 | 35 | 114/03 – 115/05 |
| 和平IL | 21 | 114/03 – 115/05 |
| 蘇澳I型 | 13 | 114/03 – 115/05 |
| 蘇澳II型 | 17 | 114/03 – 115/05 |
| 蘇澳IL | 11 | 114/03 – 115/05 |

> 年月來自「項目」欄尾碼（如 `H-IL-3` = 3 月）與「年份」欄。
> **114/06–09 缺漏**，詳見下方時間涵蓋分析。

> v6.6.3 起，蘇澳 I + IL 已拆成兩段；前端與訓練端都按細分機制顯示，
> 以反映實際水化機制差異與合成資料補足的樣本量。

**量測方法**：
- **XRD 晶相**：Rietveld 定量（10 相）
- **比表面積**：Blaine 透氣法
- **#325 篩餘**：45 µm 篩分
- **抗壓強度**：**CNS 1010** 水硬性水泥墁料抗壓強度檢驗法
  （50mm 立方試體，水泥 500g + 標準砂 1375g + 水 242.5g，w/c = 0.485）

**全部由同一位試驗人員操作**——試驗方式、手法、穩定性一致，
排除了操作員間變異這個常見的誤差來源。
""")

    st.divider()
    components.section_heading('訓練資料的時間涵蓋', icon='calendar-dots')

    cov = core.data_coverage()
    per, miss = core.missing_months()
    k1, k2, k3, k4 = st.columns(4)
    if per:
        k1.metric('資料期間',
                  f'{per[0][0]}/{per[0][1]:02d} – {per[-1][0]}/{per[-1][1]:02d}',
                  '民國年/月')
        k2.metric('涵蓋月份', f'{len(per)} 個月')
        k3.metric('缺漏月份', f'{len(miss)} 個',
                  delta='—' if not miss else '見下方',
                  delta_color='off')
    k4.metric('總樣本', f'{cov["筆數"].sum()} 筆')

    components.render_table(cov)

    st.markdown(f"""<div class="note">
    <b>年度涵蓋限制</b>：訓練資料只涵蓋 <b>民國 114–115 兩個年度</b>。
    模型以「年份」特徵補償年度間的差異，但<b>該特徵無法外推</b>
    ——跨到 116 年會失效。<br>
    <b>使用時「年份」欄只能輸入涵蓋年度（114 或 115）</b>；
    116 年之後的樣本需以新資料重新訓練模型。
    </div>""", unsafe_allow_html=True)

    st.divider()
    components.section_heading('實測資料的可靠性驗證', icon='shield-check')
    st.markdown("""<div class="note">
    <b>為什麼要驗這個</b>：模型的準確度上限，受限於<b>目標變數本身的量測誤差</b>。
    若實測強度有人為修飾（例如湊整、壓低、抄前一批），模型學到的就是假訊號。
    以下四項檢驗全部用<b>統計方法</b>，不依賴主觀判斷。
    </div>""", unsafe_allow_html=True)

    v1, v2 = st.columns(2)
    with v1:
        st.markdown("""
#### ① 末位數字分布（χ² 檢定）

若有人工湊整，小數第一位會集中在 0 和 5。

| 齡期 | χ² | p 值 | 末位0或5 | 判定 |
|---|---|---|---|---|
| 3天 | 5.2 | 0.820 | 21.6% | 通過：接近均勻 |
| 7天 | 8.1 | 0.529 | 22.7% | 通過：接近均勻 |
| 28天 | 11.8 | 0.227 | 18.6% | 通過：接近均勻 |

> 無修飾時末位 0 或 5 應約 20%，實測 18.6~22.7%
> ——**沒有湊整痕跡**。

#### ③ 殘差常態性（Shapiro-Wilk）

人為調整會讓殘差偏離常態。

| 分段 | W | p 值 | 判定 |
|---|---|---|---|
| 和平I型 | 0.981 | 0.777 | 通過：常態 |
| 和平IL | 0.860 | 0.006 | 需注意：非常態 |
| 蘇澳II型 | 0.916 | 0.126 | 通過：常態 |
| 蘇澳I型 | — | — | 依模型檔與實際資料更新 |
| 蘇澳IL | — | — | 依模型檔與實際資料更新 |
""")
    with v2:
        st.markdown("""
#### ② 齡期間一致性：最有力的證據

若 28 天有大量獨立量測噪音，它與 7 天的相關必然被稀釋。

| 分段 | r(3,7) | r(7,28) | **噪音上限** |
|---|---|---|---|
| 和平I型 | 0.879 | 0.767 | 41.2% |
| 和平IL | 0.887 | 0.758 | 42.5% |
| 蘇澳II型 | 0.949 | 0.714 | 49.1% |
| 蘇澳I型 | — | — | 依模型檔更新 |
| 蘇澳IL | — | — | 依模型檔更新 |

> r(3,7) 高達 0.88~0.95 — **三個齡期高度一致**，
> 這是量測穩定的直接證據。噪音上限已扣除
> 「7天無法解釋的真實變異」，實際噪音**必定更低**。

#### ④ 噪音上界（恆等式）

```
RMSE² = σ²模型誤差 + σ²噪音 ≥ σ²噪音
⇒ CoV ≤ RMSE / 平均強度
```

數值由目前載入模型檔的各分段/齡期 RMSE 推算；不是實驗室重複試驗
直接量測的 CoV。
""")

    cov_info = (core.load_model() or {}).get('cov_analysis', {})
    cov_rows = cov_info.get('rows', [])
    cov_min = None
    if cov_rows:
        cov_df = pd.DataFrame(cov_rows).rename(columns={
            'segment': '分段', 'age': '齡期', 'n': '樣本數',
            'mean_strength': '平均強度', 'rmse': 'RMSE',
            'cov_upper_bound': 'CoV上界(%)', 'model': '模型'})
        cov_df['平均強度'] = cov_df['平均強度'].round(2)
        cov_df['RMSE'] = cov_df['RMSE'].round(3)
        cov_df['CoV上界(%)'] = cov_df['CoV上界(%)'].round(2)
        cov_min = cov_df.loc[cov_df['CoV上界(%)'].idxmin()]
        components.render_table(cov_df, center_cols=['齡期'])
        st.info(
            f"最嚴格單一組合：{cov_min['分段']} {cov_min['齡期']}，"
            f"CoV上界 ≤ {cov_min['CoV上界(%)']:.2f}%。這不是所有分段的共同代表值。")
        st.caption(
            f"各組合上界範圍：{cov_df['CoV上界(%)'].min():.2f}% ~ "
            f"{cov_df['CoV上界(%)'].max():.2f}%；"
            f"中位數：{cov_df['CoV上界(%)'].median():.2f}%。")
    else:
        st.warning('目前模型檔沒有 CoV 上界明細；請重新訓練模型後更新模型檔。')

    components.section_heading('和平IL 殘差非常態的追查', icon='warning',
                               caption='異常樣本的統計追查結果')
    st.markdown("""<div class="note">
    唯一未通過常態檢定的分段。<b>追查結果：不是「虛低」，是三筆特別高的樣本。</b><br><br>
    <b>殘差最高的三筆全部是 114 年</b>：+5.24 / +5.00 / +3.45 MPa
    （實測 51.14 / 49.64 / 49.45，模型預測 45.89 / 44.64 / 46.00）。<br>
    移除最高 2 筆後 Shapiro p 由 0.006 升到 <b>0.238（恢復常態）</b>。<br><br>
    <b>關鍵判別</b>：若是人為虛低，應看到<u>多筆被壓低</u> → <b>左偏（負偏度）</b>；
    實際是<b>右偏 +1.20</b> = 少數樣本特別好，其餘正常。
    <b>這不是虛低的特徵。</b><br><br>
    這也呼應了另一個發現：<b>114→115 年五個分段的 28 天強度全面下降 2.8~4.1 MPa</b>，
    而組成幾乎沒變。那三筆高值正是 114 年的樣本。
    </div>""", unsafe_allow_html=True)

    st.divider()
    components.section_heading('綜合結論', icon='chart-donut')
    r1, r2, r3, r4 = st.columns(4)
    r1.metric('末位數字檢定', '3/3 通過', '無湊整痕跡')
    r2.metric('齡期一致性', 'r(3,7)=0.88~0.95', '量測穩定')
    r3.metric('殘差常態性', '3/4 通過', '第4個已追查')
    if cov_min is not None:
        r4.metric('模型誤差比例上界',
                  f"最低 {cov_min['CoV上界(%)']:.2f}%",
                  '單一分段/齡期')
    else:
        r4.metric('模型誤差比例上界', '無資料', '需重新訓練')

    st.markdown("""
**四項檢驗的結論：實測資料沒有「人為誤差虛低」的跡象。**

1. 末位數字接近均勻分布 → 無湊整
2. 三齡期高度一致（r=0.88~0.95）→ 量測穩定
3. 殘差常態（唯一例外已追查，是右偏非左偏）
4. CoV 上界由模型 RMSE 推導，需查看各分段/齡期明細，不能直接當作實驗室重複性。

> **這些是不需額外試驗的統計推論，不是重複試驗的直接量測結果**。
> 要得到精確的重複性數字，需在資料中記錄
> **每批 3 個試體的個別值**（目前只有平均）——
> 那三個數字試驗室本來就有量，是零成本的改進。
""")

    st.divider()
    components.section_heading('目前載入的模型', icon='cpu')
    fi = core.model_file_info()
    if not fi.get('name'):
        st.error('找不到模型檔。請把訓練產出的 `cement_*.pkl` 放進 app 目錄。')
        if fi.get('error'):
            st.caption(f"載入錯誤：{fi['error']}")
    else:
        i1, i2, i3, i4 = st.columns(4)
        i1.metric('版本', fi.get('version', '?'))
        i2.metric('資料指紋', fi.get('data_hash', '?'))
        i3.metric('合成資料', f"{fi.get('synth_n', 0):,} 筆")
        i4.metric('模型檔數', fi['n_found'])
        st.caption(f"**檔案**：`{fi['name']}`　｜　"
                   f"**訓練時間**：{fi.get('trained', '—')}")
        if fi['others']:
            with st.expander(f"目錄裡還有 {len(fi['others'])} 個模型檔"
                             f"（未載入）"):
                for o in fi['others']:
                    st.write(f'　• `{o}`')
                st.caption('系統自動載入**檔名時戳最新**的一個。'
                           '若要指定其他版本，設環境變數 '
                           '`CEMENT_MODEL_PATH=/路徑/檔名.pkl`。')
        st.markdown("""<div class="note">
        <b>更換模型</b>：直接把訓練產出的
        <code>cement_v6.6_{指紋}_{時戳}.pkl</code> 丟進 app 目錄即可，
        <b>不需要改名</b>。系統會自動挑檔名時戳最新的載入，
        頁面上的所有數字（任務清單、各分段命中率、可信度）
        都會跟著更新。<br><br>
        <b>資料指紋</b>用於確認「模型是用哪一版資料訓練的」——
        實測資料更新後指紋會變，可據此判斷模型是否需要重訓。
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  ④ 使用說明
# ══════════════════════════════════════════════
with TAB4:
    components.section_heading('使用說明', icon='question')
    st.markdown('''
### 1. 強度預測

在上方選擇廠區與型別，再選擇輸入方式：

- **上傳 Excel 或 CSV**：填入必要的 XRD 晶相與物性欄位，以及「年份」（民國年）。
- **手動輸入**：以表單輸入配方資料；年份為必要（下拉選單），7 天實測可選填。

送出後系統會依可用資料，自動選擇適合的模型，預測 3、7、28 天抗壓強度。

### 2. 必要欄位

必要欄位包含 10 個 XRD 晶相欄位，以及 `比表面積`、`#325篩餘`、`年份`（民國年）。
年份是部分任務的模型特徵、無法外推，只能填模型涵蓋的年度（可從下拉選單得知）。
可選欄位為 `7天`。廠區與型別請使用頁面上方選單選擇。

### 3. 帕雷托分析

選擇 X 軸特徵、Y 軸齡期、資料來源與型別後，圖表會顯示模擬或實測資料的
帕雷托前沿。前沿上的點代表沒有其他配方能同時在兩個目標上更好；拐點可作為
成本與強度的折衷參考。

### 4. 模型可信度

- **模型 R²**：最終模型的標準 LOO 實際表現。
- **Nested R²**：特徵與模型選擇隔離後的無偏評估，主要用於 Trust Grade。
- **Trust Grade**：A 可部署、B 可使用但需複核、C 實驗性、D 不可靠。
- **<2MPa%**：預測誤差小於 2 MPa 的比例，是主要業務指標。

頁面下半部以 28／7／3 天分頁呈現「各分段的預測命中率」：
每個分段的最佳方案依 **等級（A>B>C>D）→ <2MPa% → Nested R² → 模型 R² → RMSE** 挑選，
並列出逐任務的加權 <2MPa% 與分段明細。

### 5. 資料與可靠性頁面

此頁說明訓練資料的來源與品質：模擬資料的產生與校準基準、實測資料的
時間涵蓋，以及四項「實測資料可靠性驗證」（末位數字分布、齡期一致性、
殘差常態性、CoV 上界）。頁面中的 CoV 上界是由模型 RMSE 推導的誤差比例，
不是重複試驗直接量測的實驗室 CoV。各分段與齡期的預測命中率明細
已移至「模型可信度」頁。
''')
