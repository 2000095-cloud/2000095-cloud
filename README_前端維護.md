# 前端維護手冊

本文件說明 Streamlit 前端的日常啟動、模型與資料更新、驗證，以及模型可信度頁的資料規則。

## 檔案職責

| 檔案 | 職責 |
|---|---|
| `app.py` | Streamlit 工作流、頁面編排與互動元件 |
| `core.py` | 資料載入、特徵工程、模型選擇與預測、可信度 LOO 序列組裝 |
| `ui/theme.py` | 語意化色票、軟性擬物化樣式與 Plotly 共用主題 |
| `ui/components.py` | 儀表板頁首、區段標題與 HTML 響應式資料表（`render_table`） |
| `ui/charts.py` | 模型可信度頁的校準與 LOO 疊圖圖表工廠 |
| `real_97.parquet` | 97 筆實測訓練資料，供可信度與帕雷托頁使用 |
| `synth_6000.parquet` | VCCTL 合成資料，供帕雷托頁使用 |
| `cement_*.pkl` | 訓練模型及各任務的 LOO 驗證預測 |
| `requirements.txt` | 前端執行與模型反序列化所需套件 |

## 本機啟動

在 `cement_XRD_Predictor` 目錄執行：

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

建議使用 Python 3.11。模型檔可能使用 CatBoost、LightGBM 或 XGBoost，三者都必須依 `requirements.txt` 安裝，否則載入 pickle 時會失敗。

## UI 架構與響應式規則

展示層放在 `ui/`，資料、模型和預測行為維持在 `core.py`。新增樣式、共用元件或圖表時，優先在對應 UI 模組修改，避免將展示細節散落到 `app.py`。

| 使用情境 | 行為 |
|---|---|
| 桌機（寬度大於 720px） | 頂部報表導覽、寬表格、多維 Plotly 圖表與 hover 詳情 |
| 手機（寬度不大於 720px） | 固定底部報表導覽、縮小 KPI、表格改為欄位/數值資料卡、圖表保留點擊與觸控互動 |

色彩只使用 `ui.theme.COLORS` 定義的語意色：藍色為模型預測或主要操作、綠藍色為穩定或成功狀態、紅色為實測或警示、橘色為需注意資料。新增圖表應先呼叫 `theme.style_figure()`，維持背景、網格、字型、留白與圖例位置一致。

### 帕雷托頁圖表樣式（放大字級與醒目配色）

帕雷托頁（TAB2）的字級**各自獨立倍率**（以 Plotly 預設值為基準），由 `ui/theme.py` 常數集中控制：

| 倍率常數 | 值 | 基準 | 產出字級常數 | 實際 px | 用途 |
|---|---|---|---|---|---|
| `PARETO_TICK_SCALE` | `2.0` | 12 | `PARETO_TICK_FONT` | **24** | XY 軸刻度數值 |
| `PARETO_AXIS_TITLE_SCALE` | `1.5` | 14 | `PARETO_AXIS_TITLE_FONT` | **21** | XY 軸標題文字 |
| `PARETO_LEGEND_SCALE` | `1.5` | 12 | `PARETO_LEGEND_FONT` | **18** | 圖例文字 |
| `PARETO_TITLE_SCALE` | `3.0` | 17 | `PARETO_TITLE_FONT` | **51** | 圖表標題 |

> 演進紀錄：最初四項一律 ×3（36/42/36/51）。需求調整為「XY 軸刻度變 2/3、軸標題與圖例減半」後
> 改為獨立倍率，圖表標題維持 ×3。要再調整只改對應的 `*_SCALE`，不要在 `app.py` 寫死數字。

- `theme.style_figure()` 的 `tick_font` / `axis_title_font` / `legend_font` / `title_font` / `margin` / `legend_y` 均為**選用參數**（預設 `None` ＝ 沿用原主題），只有帕雷托頁傳入放大值，其他頁面不受影響。
- 帕雷托頁圖高 700、`margin=l110/r40/t110/b200`、`legend_y=-0.20`：大字級需要更大留白，改字級時務必同步確認圖例不被裁切。
- 醒目配色（帕雷托頁專用，定義於 `ui.theme.COLORS`）：
  - 模擬＝`vivid_blue #1e7bff`、模擬前沿＝`deep_blue #0b3f9e`
  - 實測＝`vivid_red #ff2d55`、實測前沿＝`deep_red #a8002a`
  - **不要再退回 `slate` / `amber`**：被支配點會灰掉、與面板背景太近，不利辨識。
- 實測點大於模擬點（9 vs 5）、不透明度也較高（0.85 vs 0.5）——實測僅 97 筆必須突出，模擬 6000 筆需保留重疊密度感。

### 表格渲染標準（render_table）

清單／摘要表格一律用 `ui/components.py` 的 `render_table(df, center_cols=None, left_cols=None, caption=None)`，以 `st.markdown(unsafe_allow_html=True)` 輸出 HTML 表格。

- **不要用 `st.dataframe` + pandas Styler 做文字置中或數值格式**：目前 Streamlit 版本以 canvas 繪製 dataframe，CSS `text-align` 不生效；Styler 顯示也隨 pandas 版本不穩。故表格置中與去尾零都在 HTML／`fmt_cell` 端處理。
- 對齊規則：表頭（th）全置中；第一欄、等級與數值欄置中（`class="c"`）；其餘長文字靠左。CSS 定義在 `ui/theme.py`（`.table-scroll` / `.report-table`）。
- 數值格式統一走 `ui/components.py` 的 `fmt_cell`：整數不帶小數、float 最多 3 位去尾零、None/NaN 顯示 `—`。app 端不要再自行 `round` 顯示，避免 3 位小數噪音。
- 數值欄若要置中，呼叫時傳 `center_cols=['該欄']`。

## 視覺與圖示來源

介面採用 Figma Community 的 [Glass SaaS Dashboard UI Kit & Design System](https://www.figma.com/community/file/1633077830104049751/glass-saas-dashboard-free-figma-ui-kit-design-system) 作為淺色半透明層次、緊湊報表導覽與狀態卡的參考方向；實作時只採用設計原則，不複製其畫面或素材。

頁面內的小圖示統一使用 [Phosphor Icons](https://phosphoricons.com/) 的 regular 筆畫。它以網頁字型方式在 `ui/theme.py` 載入，並集中於 `ui/components.py` 的頁首元件。若在 Figma 內製作設計稿，可使用 [Phosphor Figma library](https://www.figma.com/community/file/903830135544202908/Phosphor-Icons)；[Tabler Icons](https://tabler.io/icons) 與其 [Figma plugin](https://www.figma.com/community/plugin/1169807996149376642/Tabler-Icons) 可作為替代來源，但單一畫面不可混用兩套圖示筆畫。

## 更新模型與資料

1. 從訓練端取得 `cement_v6.6_{資料指紋}_{時戳}.pkl`、`real_97.parquet` 與 `synth_6000.parquet`。
2. 將檔案放入本目錄，覆蓋同名 parquet；模型版本可與舊版並存。
3. 重新啟動 Streamlit。系統會從 `cement_*.pkl` 選取檔名時戳最新的版本。
4. 到「資料來源與可靠性」確認目前載入的模型檔、資料指紋與訓練時間。

如需固定測試某個模型版本，可設定 `CEMENT_MODEL_PATH` 為完整檔案路徑。模型、實測資料與合成資料須來自同一次訓練輸出；資料指紋不同時，可信度結果不應視為目前資料的驗證結果。

## 強度預測輸入規則

- **年份是必要輸入**（上傳與手動都要），因為部分任務把「年份」當特徵、且該特徵無法外推。
- 可填年度由 `core.fillable_years()` 讀模型 `feature_stats` 各群年份 min~max 聯集（現行為民國 114–115），找不到再回退實測資料年份欄。**不要 hardcode 年份清單**。
- 上傳模式：欄位說明與空白範本在「需要哪些欄位」expander 內，範本年份帶入 `t1_yr_hint` 選的年；上傳檔缺「年份」欄或年份超出模型涵蓋 → `st.warning`。
- 手動模式：年份用 `selectbox`（key `t1_year`，`format_func` 顯示「民國 {y} 年」），不再自由輸入。
- **「3天實測」與「VCCTL 模擬強度」輸入已全數移除**——目前 40 個 task×seg 的 `feature_stats` 沒有任何任務用到 3天 / sim_* 特徵；7天 實測（`t1_s7`）仍保留為選填。`core.REQUIRED` = XRD 10 欄 + `比表面積`、`#325篩餘`；`OPTIONAL` 含 3天/sim_* 僅為相容保留，不要在 app 端再生出 3天/VCCTL 輸入框。

## 模型可信度頁

可信度頁從模型檔的 `final_best` 讀取任務與分段表現，並使用訓練階段保存的 `loo_predictions` 顯示驗證結果。

- 「校準驗證任務」決定要查看的 3 天、7 天或 28 天任務。
- 「型別」為多選篩選，預設選取該任務所有可用型別；它會同時套用到兩張驗證圖。
- 校準散點圖的 X 軸是實測強度，Y 軸是 LOO 預測強度；虛線是理想校準線。
- 訓練資料項目疊圖以項目為 X 軸、強度為 Y 軸，紅線是實測值，藍線是 LOO 預測值。

LOO 預測是每一筆樣本未參與該次模型擬合時得到的預測，不是訓練內擬合值，因此可用於觀察實際泛化誤差。

### 廠級 MTL 分段的 LOO 序列（重要）

若某分段的最佳模型是**廠級 MTL**（`final_best` entry 帶 `mtl` / `mtl_plant` 旗標，如和平I型、蘇澳I型在 `3天_XRD`、`28天_含七天實測`、`7天_XRD` 任務中被採納），訓練時 LOO 的 cohort 是**整廠**資料（和平 56 筆 / 蘇澳 41 筆），不是該分段自己（和平I型 35 / 蘇澳I型 13）。因此 entry 的 `loo_predictions` 長度 = 整廠筆數，遠大於分段實測筆數。

`core.validation_series()` 對這類 entry 會取**前 `len(分段實測)` 筆**對齊（訓練檔的廠內分段順序中，本分段排在 cohort 最前端），再逐筆配對成資料列——**不要把長度不符的整段跳過**，否則 I 型分段會從可信度頁消失。也不要整段直接比對：`real_97.parquet` 的廠內分段順序可能與訓練檔不同（蘇澳廠：訓練序為 [一型, IL, 二型]，parquet 檔序為 [一型, 二型, IL]），只有分段前端切片是可靠的。

另外，這類 entry 的 `rmse` / `r2` / `within2` 是**整廠 cohort** 算出的指標，而 entry 的 `n` 仍是分段筆數，兩者不對應同一群樣本，引用時勿混用。

### 訓練資料項目標籤

目前 `real_97.parquet` 未保存 Excel 原始資料的 `項目` 欄。前端會在 `core.validation_series()` 依每筆樣本在分段中的訓練順序產生唯一標籤：`來源-序號`，例如 `和平一型-01`。

若後續要顯示原始項目名稱，訓練端匯出 `real_97.parquet` 時必須保留 `項目` 欄，並將 `core.validation_series()` 的 `訓練資料項目` 改為優先使用該欄位。不要用不同訓練批次的排序覆寫現有 parquet，否則標籤和 LOO 預測的對應會失真。

### 各分段的預測命中率區塊與最佳方案排序

「各分段的預測命中率（<2MPa%）」區塊位於模型可信度頁下半部（原在「資料與可靠性」頁，2026-09-04 移入），以 28／7／3 天分頁呈現：

- 每個齡期先列出「各分段的最佳方案」（由 `core.seg_performance(age)` 產出），任務數 >1 時再展開逐任務比較與各任務的分段明細（expander）。
- 摘要與明細**直接讀取模型檔 `final_best`**，重訓後自動更新（含任務改名或新增）；加權 <2MPa% 由 `core.weighted_hit()` 依分段樣本數計算。
- 「最佳方案」的挑選與結果排序鍵（`core._seg_task_key()`）為：
  **Trust Grade（A>B>C>D；缺值/未知 `'?'` 視為最差）→ <2MPa%（精確值）→ Nested R²（缺值回退 official R²）→ 模型 R² → RMSE（低者佳）**。
  等級反映「這個估計有多穩」（Nested R² + Bootstrap 信賴區間），<2MPa% 反映「多數批次夠不夠準」，兩者可能衝突（<2MPa% 高但 C/D 級），故**等級優先**。

> ⚠ 此排序只影響「各分段的最佳方案」的**顯示與建議**；實際預測時 `core._pick_task()` 仍以特徵可用性＋固定偏好（含七天實測 → XRD → 模擬）選任務。兩者可能不一致（例如 28天_XRD 等級較高，但有 7 天實測時部署預測仍走 28天_含七天實測）——屬預期行為：一個是「建議採用的最佳方案」，一個是「該筆輸入實際拿得到特徵的可用任務」。

## 新增或修改互動元件

每個 Streamlit widget 都要有唯一 `key`。依頁籤使用既有前綴：

| 頁籤 | `key` 前綴 |
|---|---|
| 強度預測 | `t1_` |
| 帕雷托分析 | `t2_` |
| 模型可信度 | `t3_` |

新增可信度圖時，應先由 `core.validation_series()` 提供資料，並將 Plotly 組裝放在 `ui/charts.py`；不要在 `app.py` 重新計算預測，否則會把部署模型預測與訓練期 LOO 預測混在一起。

## 維護驗證

程式修改後，先在本目錄執行：

```powershell
python -m py_compile app.py core.py
```

若修改可信度資料流，可用下列檢查確認每個任務都有訓練項目、型別、實測值與 LOO 預測值：

```powershell
python -c "import core; tasks = core.model_info().iloc[:, 0].drop_duplicates(); [print(task, len(core.validation_series(task))) for task in tasks]"
```

每個任務都應回傳 97 筆、且型別同時包含 I 型／II 型／IL 型（用 `core.validation_series(task)['型別'].unique()` 檢查）。若某任務少了 I 型，通常是廠級 MTL 分段（和平I型／蘇澳I型）的 `loo_predictions` 長度與分段實測筆數不符而整段被跳過——參考「廠級 MTL 分段的 LOO 序列」一節。

若修改「最佳方案」排序規則，可列出各齡期採用結果快速檢查（採用任務應按 等級 → <2MPa% → Nested R² → 模型 R² → RMSE 不劣於同分段其他候選）：

```powershell
python -c "import core; [print(age, '\\n', core.seg_performance(age)[['分段','採用任務','等級','<2MPa%']].to_string(index=False)) for age in ['28天','7天','3天']]"
```

最後以 `streamlit run app.py` 開啟頁面，逐一切換任務與型別，確認兩張驗證圖都會同步更新。

### 頁面測試

每次調整 `ui/` 或 `app.py` 後，至少在桌機與手機寬度各檢查一次：

1. 首頁可顯示「水泥強度決策儀表板」及五個報表入口。
2. 桌機的頂部報表導覽可切換預測、帕雷托、可信度、資料與可靠性、說明。
3. 手機寬度下，報表導覽固定於底部，文字不截斷且不遮住主要內容。
4. 帕雷托與可信度頁的 Plotly 圖表可渲染；切換型別或任務後，圖表會更新。
5. 可信度與帕雷托摘要資料在手機版應顯示為資料卡，而非寬表格。