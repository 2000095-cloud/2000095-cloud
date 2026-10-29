---
title: 水泥強度決策儀表板
emoji: 🏗
colorFrom: gray
colorTo: blue
sdk: streamlit
sdk_version: 1.57.0
app_file: app.py
pinned: false
---

<!-- 上方 YAML 是 Hugging Face Spaces 專用；
     在 Streamlit Cloud / Cloud Run / Render 上無害但無效，可留著。 -->

# 水泥強度決策儀表板

用出廠當天的 XRD 晶相 + 比表面積 + 篩餘，預測 3／7／28 天抗壓強度，
並以帕雷托前沿呈現「成本 vs 品質」的取捨空間。

本前端遵循當前 v6.6 處理機制：
- 以 5 個細分段為主（和平I型 / 和平IL / 蘇澳I型 / 蘇澳II型 / 蘇澳IL）
- 28 天任務優先使用實測 7 天特徵與 XRD 特徵
- 兩階段模型、MTL、Optuna 調參結果會進入模型庫與可信度頁
- SHAP / Permutation 輸出是最後採用模型的解釋結果，不再只在單一模型勝出時才產生

## 文件

- `README_前端維護.md`：本機啟動、模型與資料更新、可信度頁資料規則及維護驗證
- `README_部署方案評估.md`：Streamlit Cloud、Cloud Run、Render 與 Koyeb 的部署比較

## 功能

- **強度預測**：上傳 Excel 批次預測，或手動輸入單筆試算；**年份為必要輸入**（民國年，由模型檔自動給出可填年度下拉，無法外推），7 天實測為選填
- **帕雷托分析**：16 個特徵可切換，6000 筆模擬 vs 97 筆實測疊圖；XY 軸刻度數值放大 2 倍、軸標題與圖例放大 1.5 倍，模擬（亮藍）／實測（亮紅）以醒目色區分前沿與被支配點
- **模型可信度**：任務及型別篩選、Trust Grade / Nested R² / <2MPa%，實測與 LOO 預測的校準散點圖、訓練資料項目疊圖，以及 28／7／3 天分頁的「各分段最佳方案」與逐任務命中率明細（後者原在「資料與可靠性」頁，已移入）
- **任務切換**：按 3 天、7 天、28 天及不同部署任務自動選擇最合適的模型

## 部署所需檔案

```
app.py                             主程式
core.py                            特徵工程 + 預測 + 帕雷托計算 + 可信度 LOO 組裝
ui/theme.py                        共用色票、擬物化樣式與 Plotly 主題
ui/components.py                   儀表板頁首與 HTML 響應式資料表（render_table）
ui/charts.py                       可信度圖表工廠
synth_6000.parquet                 6000 筆模擬資料（294 KB）
real_97.parquet                    97 筆實測資料（19 KB）
cement_v6.6_{指紋}_{時戳}.pkl        ★訓練好的模型
requirements.txt
```

## 更換模型

直接把訓練產出的 pkl 丟進目錄即可，**不需要改名**：

```
cement_v6.6_c2bef2b1bcef_20260812_2355.pkl
```

系統會自動搜尋 `cement_*.pkl`，挑**檔名時戳最新**的載入。
多個版本並存時，未載入的會列在「資料來源與可靠性」頁籤供確認。

指定特定版本：設環境變數 `CEMENT_MODEL_PATH=/路徑/檔名.pkl`。

> 目前前端會依模型歸檔裡的 `final_best` / `model_archive` 自動選擇最適任務，
> 不再假設固定只有一個部署模型。若更新到新的處理機制（兩階段 / Optuna / MTL），
> 介面會自動反映這些任務與分段表現。

> 沒有 pkl 時仍可使用帕雷托分析，只是無法做預測。

## 部署平台

實測：部署包 0.4 MB、記憶體峰值 **246 MB**（閒置 76 MB）。

| 平台 | 需要 Dockerfile | 隱私 | 說明 |
|---|---|---|---|
| **Streamlit Community Cloud** | ✗ | ★ 1 個免費私有 app | **推薦**，5 分鐘上線 |
| Google Cloud Run | ✓（已附） | IAM 控管 | 若要一步到位進 GCP |
| Render / Koyeb | ✓（已附） | 僅公開 | 備案 |
| Hugging Face Spaces | ✗ | 可設私有 | 額度足夠時 |

完整比較與操作步驟見 **`部署方案評估.md`**。

## 技術

VCCTL（NIST CEMHYD3D）物理模擬 + 分段機器學習，
以 Nested LOO 做無偏效能估計，主要指標為 `<2MPa%` 命中率。

## 介面與響應式設計

- 桌機使用橫向報表導覽、寬表格及可懸停的多維 Plotly 圖表。
- 手機在 720px 以下切換為固定底部導覽；摘要表改顯示欄位/數值資料卡，避免將寬表格硬塞進窄螢幕。
- 展示層集中在 `ui/`；資料載入、特徵工程和模型推論仍由 `core.py` 管理。
- 藍色表示主要預測與操作、綠藍色表示穩定或成功、紅色表示實測或警示、橘色表示需注意的資料。
- 視覺層次參考 Figma Community 的 Glass SaaS Dashboard 設計系統；小圖示統一使用 Phosphor Icons regular 筆畫，完整來源與使用規則見 `README_前端維護.md`。

## ⚠ Streamlit Community Cloud 部署注意

### Python 版本要在 UI 設定，不是 runtime.txt

Streamlit Cloud **不讀 `runtime.txt`**（那是 Heroku / Render 的慣例）。

```
部署時：Advanced settings → Python version → 3.11
部署後：App settings → Python version → 改完 Reboot app
```

不設的話平台會給最新版（實測給了 **3.14**），
部分套件在 3.14 上沒有預編譯 wheel，要從原始碼編譯 → 很慢。

> 本專案的 `requirements.txt` 已放寬版本範圍，3.11~3.14 都能解出組合，
> 但 **3.11 最快也最穩**。
> `runtime.txt` 留著給 Render / Koyeb 用（那兩個平台會讀）。

### 所有 Streamlit 元件都要有 `key`

新版 Streamlit 對重複元件 ID 更嚴格。若兩個 widget 的
**標籤與選項完全相同**（例如兩個頁籤各有一個 `selectbox('型別', [...])`），
會拋 `StreamlitDuplicateElementId`。

本專案所有互動元件都已加上唯一 `key`，前綴標明所屬頁籤
（`t1_` 強度預測、`t2_` 帕雷托、`t3_` 可信度）。

**新增元件時請沿用這個慣例。**

## 當前處理機制對前端的影響

- `SEG_OF` 現在使用細分段：`和平I型 / 和平IL / 蘇澳I型 / 蘇澳II型 / 蘇澳IL`
- 28 天預測優先在前端依模型歸檔自動決定任務：
  - `28天_含七天實測`
  - `28天_XRD`
  - `28天_模擬特徵`（若有模擬值）
- 若訓練端產出 `final_best` 並附帶 `two_stage` / `optuna_adopted` / `mtl` 等資訊，
  前端的可信度頁和任務展示會自動反映最新策略
- **各分段最佳方案的顯示規則**（`core.seg_performance()`）為 **等級（A>B>C>D，缺值最後）
  → <2MPa% → Nested R² → 模型 R² → RMSE**；實際預測 `core._pick_task()` 仍以特徵可用性
  優先，顯示的「最佳方案」與部署預測選用的任務可能不同，屬預期行為
- **廠級 MTL 分段**（I 型分段常被採納為整廠 MTL）：該分段的 `loo_predictions` 涵蓋整廠 cohort
  （和平 56 / 蘇澳 41 筆），可信度頁會取前端該分段筆數切片後再畫圖，因此
  校準圖／疊圖仍看得到 I 型（和平I型、蘇澳I型）的點
- SHAP 輸出不再依賴單一勝出模型；所有最終採用模型都會產出 SHAP 與 Permutation 資訊
