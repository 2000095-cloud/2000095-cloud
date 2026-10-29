# -*- coding: utf-8 -*-
"""
core.py — 特徵工程、模型預測、帕雷托前沿計算
============================================
與 v6.6 訓練端共用同一套特徵工程，確保線上線下一致。

模型載入策略（三層 fallback）：
  ① cement_analysis_v6.6.pkl 存在 → 用訓練好的模型（最準）
  ② 不存在 → 用內建的物理公式（σ_A·X^n，需模擬 DoH，僅供參考）
  ③ 兩者都不可用 → 只顯示帕雷托圖，不做預測
"""
import os
import numpy as np
import pandas as pd

# ── 路徑 ──
HERE = os.path.dirname(os.path.abspath(__file__))
SYNTH_PATH = os.path.join(HERE, 'synth_6000.parquet')
REAL_PATH = os.path.join(HERE, 'real_97.parquet')
# ── 模型檔自動搜尋 ──
# 訓練端會產生兩種檔名：
#   cement_v6.6_{資料指紋}_{時戳}.pkl   ← 每次訓練的版本檔（帶識別碼）
#   cement_analysis_v6.6.pkl           ← latest 副本
# 為了讓你「直接丟訓練產出的檔案」就能用，這裡自動搜尋：
#   ① 環境變數 CEMENT_MODEL_PATH（最高優先，測試/多版本切換用）
#   ② cement_*.pkl 中【檔名時戳最新】的一個
#   ③ 都沒有 → None（頁面仍可用帕雷托分析，只是不能預測）
MODEL_GLOB = 'cement_*.pkl'


def _find_model():
    """挑選要載入的模型檔。回傳路徑或 None。"""
    import glob
    import re as _re
    p = os.environ.get('CEMENT_MODEL_PATH')
    if p and os.path.exists(p):
        return p
    cands = sorted(glob.glob(os.path.join(HERE, MODEL_GLOB)))
    if not cands:
        return None

    def _key(fp):
        """排序鍵：優先用檔名裡的時戳，沒有就用檔案修改時間。"""
        name = os.path.basename(fp)
        m = _re.search(r'(\d{8})_(\d{4})', name)          # 20260812_2355
        if m:
            return (1, m.group(1) + m.group(2))
        return (0, str(int(os.path.getmtime(fp))))

    return max(cands, key=_key)


MODEL_PATH = _find_model() or os.path.join(HERE, 'cement_analysis_v6.6.pkl')

# ── 輸入欄位（上傳 Excel 需含這些） ──
XRD_COLS = ['C3S', 'C2S', 'C4AF', 'C3A_cubic', 'C3A_ortho', 'FreeLime',
            'Calcite', 'Gypsum', 'Bassanite', 'Anhydrite']
PHYS_COLS = ['比表面積', '#325篩餘']
REQUIRED = XRD_COLS + PHYS_COLS
OPTIONAL = ['年份', '3天', '7天', 'type', '來源']
# ★模擬強度欄位：來自 VCCTL 的 validation_report.csv
#   蘇澳II型 的 28 天模型【全部】需要它（因為該分段的模擬與實測組內相關
#   高達 0.807，v6.6 讓 sim_7天 取代實測 7天，可省下 7 天等待）。
#   其他三個分段不需要。
SIM_COLS = ['sim_3天', 'sim_7天', 'sim_28天']
# v6.6.1 起，模擬值是【選配】——`28天_XRD` 與 `28天_含七天實測`
# 都不使用模擬特徵，只有專屬任務 `28天_模擬特徵` 會用。
# 所以沒有模擬值時仍能完整預測三個齡期。
SEG_NEEDS_SIM = set()

# ── 帕雷托可選的特徵（含成本方向） ──
# direction: 'up' = 該值越高越省成本 / 'down' = 越高越費成本 / None = 中性
PARETO_FEATURES = {
    'Calcite':        ('石灰石', 'up',   '取代熟料，越高越省成本與 CO₂'),
    'C3S':            ('C3S', 'down',  '熟料主相，越高成本越高'),
    'C2S':            ('C2S', None,    '貝來石，燒成溫度較低'),
    'C4AF':           ('C4AF', None,   '鐵相'),
    'C3A_cubic':      ('C3A立方', None, '立方晶 C3A'),
    'C3A_ortho':      ('C3A斜方', None, '斜方晶 C3A'),
    'C3A_total':      ('C3A總量', None, '影響凝結與早期強度'),
    'FreeLime':       ('游離石灰', None, '未反應 CaO，過高有安定性風險'),
    'Sulfate':        ('總硫酸鹽', None, '石膏+半水+無水，調凝用'),
    'Gypsum':         ('二水石膏', None, ''),
    'Bassanite':      ('半水石膏', None, ''),
    'Anhydrite':      ('無水石膏', None, ''),
    '比表面積':        ('比表面積', 'down', '磨得越細能耗越高'),
    '#325篩餘':        ('#325篩餘', 'up',  '越高代表磨得越粗，越省能耗'),
    'Silicate':       ('矽酸鹽總量', None, 'C3S + C2S'),
    'Burning_degree': ('燒成度', None,  'C3S/(C3S+C2S)'),
}
AGE_COLS = ['3天', '7天', '28天']


def fillable_years():
    """讀取模型，回傳「年份」可填的民國年度清單（依序小到大）。

    ★年份是「必要輸入」：使用者無法預知選到的分段任務是否用到年份，
      統一要求填寫。且年份特徵無法外推——年度取自模型檔
      feature_stats 內各資料群（hp/sa）年份的 min~max 聯集；
      找不到再回退到實測資料的年份欄；兩者皆無給 [114, 115]。
    """
    m = load_model()
    yrs = set()
    if m:
        fs = m.get('feature_stats') or {}
        for grp in fs.values():
            if not isinstance(grp, dict):
                continue
            y = grp.get('年份')
            if isinstance(y, dict) and y.get('min') is not None \
                    and y.get('max') is not None:
                yrs.update(range(int(y['min']), int(y['max']) + 1))
    if not yrs:
        try:
            r = load_real()
            if '年份' in r.columns:
                yrs.update(int(v) for v in r['年份'].dropna().unique())
        except Exception:
            pass
    if not yrs:
        yrs = {114, 115}
    return sorted(yrs)


# ════════════════════════════════════════════════
#  特徵工程（與 v6.6 的 calculate_features 對齊）
# ════════════════════════════════════════════════
def add_features(df):
    """加入衍生特徵。缺欄時該衍生特徵設 NaN，不中斷。"""
    r = df.copy()
    g = lambda c: r[c].fillna(0) if c in r.columns else 0

    r['C3A_total'] = g('C3A_cubic') + g('C3A_ortho')
    r['Sulfate'] = g('Gypsum') + g('Bassanite') + g('Anhydrite')
    r['Silicate'] = g('C3S') + g('C2S')
    r['Silicate_total'] = r['Silicate']
    r['Sulfate_total'] = r['Sulfate']
    r['Burning_degree'] = g('C3S') / (g('C3S') + g('C2S') + 1e-3)
    r['C3S_C2S_ratio'] = g('C3S') / (g('C2S') + 1e-3)

    if '比表面積' in r.columns:
        b = r['比表面積'].fillna(0)
        r['SSA_C3S'] = b * g('C3S') / 1000
        r['SSA_C3A'] = b * r['C3A_total'] / 1000
        r['SSA_C2S'] = b * g('C2S') / 1000
        r['Reactivity_early'] = (g('C3S') + r['C3A_total'] * 2) * b / 10000
        r['Reactivity_late'] = g('C2S') * b / 10000

    r['Hydraulic_potential'] = (g('C3S') + g('C2S') * 0.2
                                + g('C3A_cubic') * 0.8 + g('C3A_ortho') * 0.4
                                + g('C4AF') * 0.15)
    r['Heat_est'] = (136 * g('C3S') + 62 * g('C2S')
                     + 200 * r['C3A_total'] + 30 * g('C4AF')) / 100

    # 氧化物反推
    r['Fe2O3_est'] = g('C4AF') / 3.043
    r['Al2O3_est'] = (r['C3A_total'] + 1.692 * r['Fe2O3_est']) / 2.650
    r['SiO2_est'] = g('C3S') * (60.1 / 228.3) + g('C2S') * (60.1 / 172.2)
    r['CaO_est'] = (g('C3S') * 0.737 + g('C2S') * 0.651
                    + r['C3A_total'] * 0.623 + g('C4AF') * 0.462
                    + g('FreeLime') + g('Calcite') * 0.56)
    r['LSF'] = ((r['CaO_est'] - 1.65 * r['Al2O3_est'] - 0.35 * r['Fe2O3_est'])
                / (2.80 * r['SiO2_est'] + 1e-3))
    r['IM'] = r['Al2O3_est'] / (r['Fe2O3_est'] + 1e-3)
    r['SM'] = r['SiO2_est'] / (r['Al2O3_est'] + r['Fe2O3_est'] + 1e-3)
    r['LSF_IM'] = r['LSF'] * r['IM']

    # C3A 品質與硫酸鹽平衡
    r['C3A_cubic_ratio'] = g('C3A_cubic') / (r['C3A_total'] + 1e-3)
    r['C3A_quality'] = g('C3A_cubic') / (g('C3A_cubic')
                                         + 1.5 * g('C3A_ortho') + 1e-3)
    r['SO3_C3A_ratio'] = r['Sulfate'] / (r['C3A_total'] + 1e-3)
    r['SO3_deficit'] = (0.8 * r['C3A_total'] - r['Sulfate']).clip(lower=0)
    r['Active_C3A_Sulf'] = ((g('C3A_cubic') + 0.5 * g('C3A_ortho'))
                            / (r['Sulfate'] + 1e-3))
    r['Active_CaO'] = r['Active_C3A_Sulf'] * r['CaO_est'] / 10
    r['Quality_CaO'] = r['C3A_quality'] * r['CaO_est'] / 10

    # 石灰石文獻特徵
    phases = [c for c in XRD_COLS if c in r.columns]
    if 'Calcite' in r.columns and len(phases) >= 6:
        tot = r[phases].fillna(0).sum(axis=1).replace(0, np.nan)
        f = (r['Calcite'].fillna(0) / tot).clip(0, 0.5)
        keep = (1 - f).clip(lower=0.3)
        r['f_limestone'] = f
        r['Dil_C3S'] = g('C3S') / keep
        r['Dil_C2S'] = g('C2S') / keep
        r['Dil_Hydraulic'] = r['Hydraulic_potential'] / keep
    if '3天' in r.columns and '7天' in r.columns:
        r['Strength_gain_3to7'] = r['7天'] - r['3天']
        r['Str7_C2S'] = r['7天'] * g('C2S') / 100
    return r


# ════════════════════════════════════════════════
#  資料載入
# ════════════════════════════════════════════════
_cache = {}


def load_synth():
    if 'synth' not in _cache:
        d = pd.read_parquet(SYNTH_PATH)
        _cache['synth'] = add_features(d)
    return _cache['synth']


def load_real():
    if 'real' not in _cache:
        d = pd.read_parquet(REAL_PATH)
        _cache['real'] = add_features(d)
    return _cache['real']


def load_model():
    """載入訓練好的模型。不存在回 None。"""
    if 'model' in _cache:
        return _cache['model']
    m = None
    path = _find_model()
    if path and os.path.exists(path):
        try:
            import joblib
            m = joblib.load(path)
            _cache['model_path'] = path
        except Exception as e:
            _cache['model_error'] = f'{type(e).__name__}: {e}'
            m = None
    _cache['model'] = m
    return m


def model_file_info():
    """回傳目前載入的模型檔資訊（供介面顯示）。

    含檔名、資料指紋、訓練時間（自動把 UTC 時戳轉台灣時間）。
    """
    import glob
    import re as _re
    from datetime import datetime, timezone, timedelta
    load_model()
    path = _cache.get('model_path')
    all_files = sorted(glob.glob(os.path.join(HERE, MODEL_GLOB)))
    info = {'path': path,
            'name': os.path.basename(path) if path else None,
            'n_found': len(all_files),
            'others': [os.path.basename(f) for f in all_files
                       if f != path],
            'error': _cache.get('model_error')}
    m = load_model()
    if m:
        info['version'] = m.get('version')
        info['data_hash'] = m.get('data_hash')
        info['synth_n'] = m.get('synth_n')
        # 訓練時間：優先用存檔內的台灣時間欄（v6.6.1 起有），
        # 沒有就從檔名時戳推（舊版是 UTC，加 8 小時）
        tw = m.get('run_timestamp_tw')
        if tw:
            info['trained'] = tw
        else:
            ts = m.get('run_timestamp') or ''
            mt = _re.search(r'(\d{8})_(\d{4})', ts or (info['name'] or ''))
            if mt:
                try:
                    dt = datetime.strptime(mt.group(1) + mt.group(2),
                                           '%Y%m%d%H%M')
                    dt = dt.replace(tzinfo=timezone.utc).astimezone(
                        timezone(timedelta(hours=8)))
                    info['trained'] = (dt.strftime('%Y-%m-%d %H:%M')
                                       + ' (UTC+8，由 UTC 時戳換算)')
                except Exception:
                    info['trained'] = ts
            else:
                info['trained'] = ts or '—'
    return info


# ════════════════════════════════════════════════
#  預測
# ════════════════════════════════════════════════
# 物理公式的凍結常數（無模型時的 fallback）
SIGMA_A = {'I型': 95.2, 'II型': 102.0, 'IL型': 84.4}
N_EXP = {'I型': 2.46, 'II型': 2.90, 'IL型': 2.46}
WC = 0.485
# 分段對映（與 v6.6.3 的細分機制一致）
# ★ v6.6.3: 蘇澳 I + IL 拆成兩段，因為合成資料已足夠支撐小樣本分段
SEG_OF = {('和平', 'I型'): '和平I型', ('和平', 'IL型'): '和平IL',
          ('蘇澳', 'I型'): '蘇澳I型', ('蘇澳', 'II型'): '蘇澳II型',
          ('蘇澳', 'IL型'): '蘇澳IL'}


def _pick_task(archive, seg, age, has_3d, has_7d, avail_cols=None):
    """依可用資訊挑任務（與 v6.6 的部署建議一致）。

    ★會檢查該任務的特徵是否【全部拿得到】——例如「28天_模擬早期」
      需要 sim_3天/sim_7天（來自 VCCTL 模擬），一般輸入沒有這些欄，
      若不檢查就會選中它然後預測失敗。
    """
    cands = []
    if age == '28天':
        if has_7d:
            cands.append('28天_含七天實測')     # 最準（Nested 0.66~0.76）
        cands += ['28天_XRD',                    # 純實測特徵，隨時可用
                  '28天_模擬特徵', '28天_模擬早期']  # 需 sim_* → 擺最後
                                                 # （後者是 v6.6 的舊名，相容）
    else:
        cands.append(f'{age}_XRD')
    for tk in cands:
        e = archive.get(tk, {}).get(seg)
        if not e or e.get('trained_model') is None:
            continue
        if avail_cols is not None:
            miss = [f for f in e['features'] if f not in avail_cols]
            if miss:
                continue          # 特徵拿不到就換下一個任務
        return tk, e
    return None, None


def _predict_saved_bundle(bundle, X):
    """預測訓練端存下的兩階段/三階段 bundle，不依賴訓練端模組。"""
    strategy = bundle.get('strategy')
    if strategy == 'mtl':
        idx = bundle['target_index']
        Xs = bundle['scaler'].transform(X)
        model = bundle['model']
        if isinstance(model, list):
            pred = np.column_stack([m.predict(Xs) for m in model])
        else:
            pred = model.predict(Xs)
        return (pred * bundle['y_scale'] + bundle['y_mean'])[:, idx]
    if strategy == 'ts_mtl':
        idx = bundle['target_index']
        if bundle.get('transfer_strategy') == 'weighted':
            model = bundle['model']
            if isinstance(model, list):
                return model[idx].predict(X)
            return model.predict(X)[:, idx]
        pretrained = bundle['pretrained']
        if isinstance(pretrained, list):
            base = np.column_stack([m.predict(X) for m in pretrained])
        else:
            base = pretrained.predict(X)
        correction = (bundle['corrector'].predict(
            bundle['scaler'].transform(X)) * bundle['residual_scale']
            + bundle['residual_mean'])
        return (base + correction)[:, idx]
    if strategy == 'weighted':
        return bundle['model'].predict(X)
    base = bundle['pretrained'].predict(X)
    return base + bundle['corrector'].predict(
        bundle['scaler'].transform(X))


def predict(df, plant=None, ctype=None):
    """預測 3/7/28 天強度。

    回傳 (結果 DataFrame, 說明字串)。
    結果含 pred_3天 / pred_7天 / pred_28天 與 method / segment / task 欄。
    """
    d = add_features(df.copy())
    model = load_model()
    n = len(d)
    out = d.copy()
    for a in AGE_COLS:
        out[f'pred_{a}'] = np.nan
    out['method'] = '—'
    out['segment'] = '—'
    out['task'] = '—'

    if model is None:
        return out, ('⚠ 找不到 `cement_analysis_v6.6.pkl`，無法用訓練模型預測。\n'
                     '請把 v6.6 跑完產生的 pkl 放進 app 目錄。')

    archive = model.get('model_archive', {})
    notes = []
    for i in range(n):
        row = d.iloc[[i]]
        pl = plant or (row['廠區'].iloc[0] if '廠區' in row.columns else None)
        ct = ctype or (row['type'].iloc[0] if 'type' in row.columns else None)
        seg = SEG_OF.get((pl, ct))
        if seg is None:
            notes.append(f'第 {i + 1} 筆：無法判定分段（廠區={pl}, 型別={ct}）')
            continue
        out.iat[i, out.columns.get_loc('segment')] = seg
        has3 = '3天' in row.columns and pd.notna(row['3天'].iloc[0])
        has7 = '7天' in row.columns and pd.notna(row['7天'].iloc[0])
        # 該筆實際「有值」的欄位（NaN 不算）
        avail = {c for c in row.columns if pd.notna(row[c].iloc[0])}
        for age in AGE_COLS:
            tk, entry = _pick_task(archive, seg, age, has3, has7, avail)
            if entry is None:
                # 診斷：是缺模擬值，還是真的沒模型？
                need_sim = False
                for _tk in (['28天_含七天實測', '28天_XRD', '28天_模擬特徵',
                             '28天_模擬早期'] if age == '28天'
                            else [f'{age}_XRD']):
                    _e = archive.get(_tk, {}).get(seg)
                    if _e and any(f.startswith('sim_') for f in _e['features']):
                        need_sim = True
                if need_sim:
                    notes.append(
                        f'第 {i + 1} 筆 {age}：目前載入的模型檔中，'
                        f'{seg} 的 {tk if tk else age + "_XRD"} 仍需要 '
                        f'VCCTL 模擬值（sim_*），因此無法只用晶相資料預測。'
                        f'這是舊模型檔的特徵設定；請用目前版本重新訓練並更新 '
                        f'cement_analysis_v6.6.pkl，新的 {age}_XRD 才能不依賴 '
                        f'7天實測或模擬值。')
                else:
                    notes.append(f'第 {i + 1} 筆 {age}：無可用任務'
                                 f'（特徵不足或該分段無模型）')
                continue
            feats = entry['features']
            try:
                trained = entry['trained_model']
                if isinstance(trained, dict):
                    p = _predict_saved_bundle(trained, row[feats].values)[0]
                else:
                    p = trained.predict(row[feats].values)[0]
                out.iat[i, out.columns.get_loc(f'pred_{age}')] = float(p)
                if age == '28天':
                    out.iat[i, out.columns.get_loc('task')] = tk
                    out.iat[i, out.columns.get_loc('method')] = \
                        entry.get('model_name', '?')
            except Exception as e:
                notes.append(f'第 {i + 1} 筆 {age}：{type(e).__name__}')
    msg = '\n'.join(notes[:8]) if notes else ''
    return out, msg


def model_info():
    """回傳模型摘要（供介面顯示可信度）。"""
    m = load_model()
    if m is None:
        return None
    rows = []
    for tk, segs in m.get('final_best', {}).items():
        for sg, b in segs.items():
            rows.append({'任務': tk, '分段': sg,
                         '等級': b.get('trust_grade', '?'),
                         '模型 R²': round(b.get('r2', 0), 3),
                         'Nested R²': round(b.get(
                             'nested_r2', b.get('official_r2', 0)), 3),
                         'RMSE': round(b.get('rmse', 0), 3),
                         '<2MPa%': round(b.get('within2', 0), 0),
                         '模型': b.get('model', '?')})
    return pd.DataFrame(rows)


def validation_series(task):
    """回傳任務的實測值與訓練時 LOO 預測，供可信度圖使用。

    ⚠ MTL 廠級模型（result 帶 mtl / mtl_plant 旗標）：
    訓練時 LOO 的 cohort 是【整廠】資料（和平 56 筆 / 蘇澳 41 筆），
    因此 loo_predictions 的長度 = 整廠筆數，不是本分段筆數
    （和平I型 35 / 蘇澳I型 13）。且序列依訓練檔的廠內分段順序排列，
    本分段排在 cohort 最前端；但 real_97.parquet 的廠內分段順序
    可能與訓練檔不同（蘇澳：訓練序 [一型, IL, 二型]，檔序
    [一型, 二型, IL]），故不能整段直接比對，須先截出前端
    len(subset) 筆＝本分段，再逐筆配對。
    """
    model = load_model()
    if model is None:
        return None
    target = task.split('_', 1)[0]
    task_results = model.get('final_best', {}).get(task, {})
    real = load_real()
    rows = []
    for segment, result in task_results.items():
        predictions = result.get('loo_predictions')
        features = result.get('features', [])
        if not predictions or target not in real.columns:
            continue
        sheets = SEG_SHEETS.get(segment, [])
        subset = real[real['來源'].isin(sheets)].dropna(
            subset=list(features) + [target]).reset_index(drop=True)
        predictions = list(predictions)
        if (result.get('mtl') or result.get('mtl_plant')) \
                and len(predictions) > len(subset):
            # 廠級 MTL：LOO 序列涵蓋整廠，本分段為其前端 len(subset) 筆
            predictions = predictions[:len(subset)]
        if len(subset) != len(predictions):
            continue
        for item_number, ((_, row), predicted) in enumerate(
                zip(subset.iterrows(), predictions), start=1):
            source = str(row.get('來源', segment))
            rows.append({
                '訓練資料項目': f'{source}-{item_number:02d}',
                '型別': str(row.get('type', '?')),
                '分段': segment,
                '實測值': float(row[target]),
                'LOO預測值': float(predicted),
                '誤差': float(predicted - row[target]),
            })
    return pd.DataFrame(rows) if rows else None


# ════════════════════════════════════════════════
#  帕雷托前沿
# ════════════════════════════════════════════════
def pareto_front(df, xcol, ycol, x_max=True, y_max=True):
    """回傳非支配解的索引（依 xcol 排序）。

    x_max/y_max：該目標是否越大越好。
    """
    d = df[[xcol, ycol]].dropna()
    if len(d) == 0:
        return d.index
    v = d.values.astype(float).copy()
    if not x_max:
        v[:, 0] = -v[:, 0]
    if not y_max:
        v[:, 1] = -v[:, 1]
    order = np.argsort(-v[:, 0], kind='stable')
    keep, best = [], -np.inf
    for i in order:
        if v[i, 1] > best:
            keep.append(d.index[i])
            best = v[i, 1]
    return pd.Index(keep)


def knee_point(front_df, xcol, ycol):
    """找拐點（前沿上曲率最大處）——性價比最高的折衷點。"""
    d = front_df[[xcol, ycol]].dropna().sort_values(xcol)
    if len(d) < 3:
        return None
    x = d[xcol].values.astype(float)
    y = d[ycol].values.astype(float)
    xr = (x - x.min()) / (np.ptp(x) + 1e-9)
    yr = (y - y.min()) / (np.ptp(y) + 1e-9)
    # 到兩端點連線的距離最大者
    x0, y0, x1, y1 = xr[0], yr[0], xr[-1], yr[-1]
    den = np.hypot(x1 - x0, y1 - y0) + 1e-9
    dist = np.abs((y1 - y0) * xr - (x1 - x0) * yr + x1 * y0 - y1 * x0) / den
    return d.index[int(np.argmax(dist))]

# ════════════════════════════════════════════════
#  訓練資料的時間涵蓋與各分段效能
# ════════════════════════════════════════════════
SEG_SHEETS = {'和平I型': ['和平一型'], '和平IL': ['和平IL'],
              '蘇澳I型': ['蘇澳一型'], '蘇澳II型': ['蘇澳二型'],
              '蘇澳IL': ['蘇澳IL']}

# Trust Grade 分數（愈大愈佳，A=3 … D=0）；缺值或未知（'?'）→ -1，最劣
GRADE_SCORE = {'A': 3, 'B': 2, 'C': 1, 'D': 0}


def _seg_task_key(b):
    """單一 task×seg entry 的「最佳方案」比較鍵：等級 → <2MPa% → Nested R² → 模型 R² → RMSE。

    - 等級 A(3)>B(2)>C(1)>D(0)；缺 trust_grade（'?'）→ -1，該維度最劣。
    - <2MPa% 用精確值（不分 2% 分桶）。
    - Nested R² 缺值回退 official R²，再缺視為 -9。
    - RMSE 愈低愈佳（鍵內取 -rmse）；缺值視為無窮大。
    鍵愈大代表方案愈佳，可直接用 max／sort(reverse=True)。
    """
    grade = GRADE_SCORE.get(str(b.get('trust_grade', '?')).upper(), -1)
    w = b.get('within2')
    within2 = float(w) if w is not None else 0.0
    nested = b.get('nested_r2')
    if nested is None:
        nested = b.get('official_r2', -9)
    nested = float(nested) if nested is not None else -9.0
    r2 = b.get('r2')
    r2 = float(r2) if r2 is not None else 0.0
    rmse = b.get('rmse')
    rmse = float(rmse) if rmse is not None else float('inf')
    return (grade, within2, nested, r2, -rmse)


def data_coverage():
    """各分段的訓練資料時間範圍與筆數。

    回傳 DataFrame，含起訖年月、涵蓋月份數、是否有斷檔。
    ★年月來自「項目」欄的尾碼（如 H-IL-3 = 3 月）與「年份」欄（民國年）。
    """
    r = load_real()
    rows = []
    for seg, shs in SEG_SHEETS.items():
        s = r[r['來源'].isin(shs)]
        if '月份' not in s.columns:
            rows.append({'分段': seg, '筆數': len(s), '時間範圍': '—',
                         '涵蓋月數': '—', '斷檔': '—'})
            continue
        d = s.dropna(subset=['月份', '年份'])
        if len(d) == 0:
            continue
        per = sorted({(int(a), int(b))
                      for a, b in zip(d['年份'], d['月份'])})
        lo, hi = per[0], per[-1]
        # 起訖之間應有幾個月
        span = (hi[0] - lo[0]) * 12 + (hi[1] - lo[1]) + 1
        gap = span - len(per)
        rows.append({
            '分段': seg, '筆數': len(s),
            '時間範圍': f'{lo[0]}/{lo[1]:02d} – {hi[0]}/{hi[1]:02d}',
            '涵蓋月數': f'{len(per)} / {span}',
            '斷檔': f'{gap} 個月' if gap > 0 else '無'})
    return pd.DataFrame(rows)


def missing_months():
    """全體資料的缺漏月份清單（供說明資料代表性）。"""
    r = load_real()
    if '月份' not in r.columns:
        return [], []
    d = r.dropna(subset=['月份', '年份'])
    per = sorted({(int(a), int(b)) for a, b in zip(d['年份'], d['月份'])})
    if not per:
        return [], []
    lo, hi = per[0], per[-1]
    full = []
    y, m = lo
    while (y, m) <= hi:
        full.append((y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    miss = [p for p in full if p not in per]
    return per, miss


def tasks_of_age(age):
    """回傳該齡期底下【模型檔實際有的】所有任務名。

    ★完全動態：任務改名（如 28天_模擬早期 → 28天_模擬特徵）或新增，
      不必改這支程式，重訓後頁面自動跟著更新。
    """
    m = load_model()
    if m is None:
        return []
    fb = m.get('final_best', {})
    out = []
    for tk in fb:
        # 任務名一律以齡期開頭（3天_XRD / 28天_含七天實測 / …）
        if tk.startswith(age + '_') or tk == age:
            out.append(tk)
    # 排序：純 XRD → 含實測 → 含模擬，讓表格順序穩定且合理
    def _rank(t):
        if '模擬' in t:
            return 2
        if '實測' in t or '含' in t:
            return 1
        return 0
    return sorted(out, key=lambda t: (_rank(t), t))


def task_performance(task):
    """單一任務在各分段的表現。找不到回 None。"""
    m = load_model()
    if m is None:
        return None
    segs = m.get('final_best', {}).get(task)
    if not segs:
        return None
    rows = []
    for sg, b in segs.items():
        feats = b.get('features', [])
        rows.append({
            '分段': sg,
            '等級': b.get('trust_grade', '?'),
            '<2MPa%': round(b.get('within2', 0)),
            'RMSE': round(b.get('rmse', 0), 3),
            '模型 R²': round(b.get('r2', 0), 3),
            'Nested R²': round(b.get(
                'nested_r2', b.get('official_r2', 0)), 3),
            '模型': str(b.get('model', '?'))[:22],
            '需模擬值': '是' if any(str(f).startswith('sim_')
                                    for f in feats) else '否',
            '特徵': ', '.join(map(str, feats)),
        })
    return pd.DataFrame(rows)


def seg_performance(age='28天'):
    """各分段在該齡期的【最佳】任務（依 等級 → <2MPa% → Nested R² → 模型 R² → RMSE）。"""
    m = load_model()
    if m is None:
        return None
    fb = m.get('final_best', {})
    tks = tasks_of_age(age)
    rows = []
    for seg in SEG_SHEETS:
        best = None          # (key, (tk, entry))
        for tk in tks:
            b = fb.get(tk, {}).get(seg)
            if not b:
                continue
            key = _seg_task_key(b)
            if best is None or key > best[0]:
                best = (key, (tk, b))
        if best:
            tk, b = best[1]
            rows.append((best[0], {'分段': seg, '採用任務': tk,
                                   '等級': b.get('trust_grade', '?'),
                                   '<2MPa%': round(b.get('within2', 0)),
                                   'RMSE': round(b.get('rmse', 0), 3),
                                   '模型 R²': round(b.get('r2', 0), 3),
                                   'Nested R²': round(b.get(
                                       'nested_r2', b.get('official_r2', 0)), 3),
                                   '模型': str(b.get('model', '?'))[:20]}))
    if not rows:
        return None
    # 排序同挑選鍵（等級 → <2MPa% → Nested R² → 模型 R² → RMSE），最佳在前
    rows.sort(key=lambda kv: kv[0], reverse=True)
    return pd.DataFrame([d for _, d in rows])


def weighted_hit(perf_df):
    """依各分段樣本數加權的 <2MPa%。perf_df 需含「分段」與「<2MPa%」。"""
    cov = data_coverage().set_index('分段')['筆數']
    d = perf_df[perf_df['分段'].isin(cov.index)]
    if len(d) == 0:
        return float('nan'), 0
    w = cov.loc[d['分段']].values
    return float((d['<2MPa%'].values * w).sum() / w.sum()), int(w.sum())
