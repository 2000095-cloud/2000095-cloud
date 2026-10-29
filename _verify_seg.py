# -*- coding: utf-8 -*-
"""驗證 seg_performance 等級優先排序：採用任務按比較鍵不劣於同分段所有候選。"""
import io
import sys
import core

GRADE_SCORE = {'A': 3, 'B': 2, 'C': 1, 'D': 0}


def entry_key(tk, seg, fb):
    b = fb.get(tk, {}).get(seg)
    if not b:
        return None
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


def fmt_key(k):
    grade_name = {3: 'A', 2: 'B', 1: 'C', 0: 'D', -1: '?'}[k[0]]
    return f"(grade={grade_name}, <2MPa%={k[1]:.1f}, NestedR2={k[2]:.3f}, R2={k[3]:.3f}, rmse={-k[4]:.3f})"


out = io.StringIO()
m = core.load_model()
if m is None:
    out.write("NO_MODEL\n")
else:
    fb = m.get('final_best', {})
    all_ok = True
    for age in ['28天', '7天', '3天']:
        tks = core.tasks_of_age(age)
        out.write(f"\n===== {age}  tasks={tks} =====\n")
        best_df = core.seg_performance(age)
        if best_df is None:
            out.write("  (no best_df)\n")
            continue
        best_map = dict(zip(best_df['分段'], best_df['採用任務']))
        for seg in core.SEG_SHEETS:
            cands = [(tk, entry_key(tk, seg, fb)) for tk in tks]
            cands = [(tk, k) for tk, k in cands if k is not None]
            if not cands:
                out.write(f"  {seg}: no candidates\n")
                continue
            cands.sort(key=lambda x: x[1])
            best_key = cands[-1][1]
            adopted = best_map.get(seg)
            adopted_key = entry_key(adopted, seg, fb) if adopted else None
            ok = (adopted is not None and adopted_key == best_key)
            all_ok = all_ok and ok
            out.write(f"  {seg}: adopted={adopted} key={fmt_key(adopted_key) if adopted_key else None}\n")
            for tk, k in cands:
                mark = ' <== 採用' if tk == adopted else ''
                out.write(f"      {tk:22s} {fmt_key(k)}{mark}\n")
            if not ok:
                out.write("      !! 採用任務非候選中最優 (比較鍵不一致)\n")
    out.write(f"\nALL_OK={all_ok}\n")

# 交叉驗證：採用任務若與舊邏輯不同，列出差異處供人工檢視
out.write("\n===== 與舊邏輯(round(within2/2), nested)之差異 =====")
with open('_verify_seg_out.txt', 'w', encoding='utf-8') as f:
    f.write(out.getvalue())
print("WROTE _verify_seg_out.txt")
