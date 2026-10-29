# 免費部署方案評估（HF Spaces 額度用盡後）

> **實測基準**：部署包 0.4 MB、記憶體峰值 **246 MB**（閒置 76 MB，含三個 booster）。
> 這個數字很輕，讓幾乎所有免費方案都可行——**選擇的關鍵不是資源，是隱私與休眠**。

---

## 一、結論先看

| 情境 | 選這個 |
|---|---|
| **想最快上線、且能接受 GitHub** | **Streamlit Community Cloud**（有 1 個免費私有 app） |
| **反正之後要進 GCP，想一步到位** | **Google Cloud Run 免費額度** |
| 不想用 GitHub，也不碰 GCP | Render 免費（但只能公開） |

---

## 二、平台對照

| 平台 | RAM | 隱私 | 休眠 | 部署方式 | 適配 |
|---|---|---|---|---|---|
| **Streamlit Community Cloud** | 1 GB | ★ **1 個私有 app** | 12h 無流量 | GitHub 連結，1 鍵 | ★★★★★ |
| **Google Cloud Run** | 512MB~ | 私有（IAM） | 縮至零，冷啟 10–20s | 需 Dockerfile | ★★★★☆ |
| Render 免費 | 512 MB | 僅公開 | 15min，750h/月 | Dockerfile 或自動偵測 | ★★★☆☆ |
| Koyeb 免費 | 512 MB | 僅公開 | 縮至零 | 需 Dockerfile | ★★★☆☆ |
| Railway | — | — | **已無永久免費**（僅 $5 試用） | — | ✗ |
| Vercel / Netlify / CF Pages | — | — | **不支援長連線 WebSocket** | — | ✗ **不適用** |

> **為何 Vercel 那類不能用**：Streamlit 是**長駐的 WebSocket 伺服器**，
> 每個瀏覽器分頁維持一條連線、伺服器端保有 session state。
> serverless function 每次請求都是新行程，撐不住這個模型。

---

## 三、方案 A：Streamlit Community Cloud（推薦）

### 為何適合你

- **免費額度含 1 個私有 app** —— 正好符合「公司品管資料 + 主管看報表」
- 1 GB RAM，你只用 210 MB
- Streamlit 原生平台，**不需要 Dockerfile**
- 推 GitHub 就自動重新部署（換模型 pkl 也是）

### 限制

| 限制 | 影響 |
|---|---|
| 需要 GitHub 帳號與 repo | 模型與資料會放在 private repo |
| 12 小時無流量休眠 | 主管早上開啟需等 ~30 秒喚醒 |
| 只有 1 個私有 app | 夠用（測試版可先開公開的） |
| 無自訂網域 | 網址是 `xxx.streamlit.app` |

### 步驟

```
1. GitHub 建 private repo，把解壓後的檔案全部推上去
   （0.4 MB，不需要 Git LFS）

2. share.streamlit.io → Sign in with GitHub → New app
   Repository: 你的 repo
   Branch: main
   Main file path: app.py

3. Deploy（約 3–5 分鐘）

4. Settings → Sharing → 改為 Private
   加入允許的 email（主管、品管人員）
```

### 換模型

```bash
git add cement_v6.6_{新指紋}_{新時戳}.pkl
git commit -m "update model"
git push
```
推上去自動重新部署，**舊 pkl 可以留著**（系統只載最新的）。

---

## 四、方案 B：Google Cloud Run（若要一步到位）

### 為何值得考慮

你本來就規劃要進 GCP——**直接用 Cloud Run 可以省掉之後的遷移**。

| 項目 | 說明 |
|---|---|
| 免費額度 | 每月 200 萬次請求、36 萬 GB-秒記憶體（長期免費） |
| 隱私 | 用 IAM 控制，比 email allow-list 更嚴謹 |
| 休眠 | `min-instances=0` 時縮至零，冷啟 10–20 秒 |
| 成本 | 你這種用量**幾乎確定落在免費額度內** |

### 需要的檔案（已附）

```
Dockerfile              ← 已建好，用 $PORT 相容 Cloud Run/Render
.dockerignore
.streamlit/config.toml  ← 關閉 CORS/XSRF（反向代理後方必要）
```

### 部署（PowerShell）

```powershell
# 前置：安裝 gcloud CLI 並登入
gcloud auth login
gcloud config set project 你的專案ID

# 一行部署（會自動建置映像）
gcloud run deploy cement-app `
  --source . `
  --region asia-east1 `
  --memory 512Mi `
  --cpu 1 `
  --min-instances 0 `
  --max-instances 3 `
  --timeout 3600 `
  --session-affinity `
  --no-allow-unauthenticated
```

**幾個參數的用意**：

| 參數 | 為何這樣設 |
|---|---|
| `--region asia-east1` | 台灣，延遲最低 |
| `--memory 512Mi` | 實測 210 MB，512 有餘裕 |
| `--min-instances 0` | 沒人用時不計費（代價是冷啟動） |
| `--max-instances 3` | **防呆**：避免異常流量燒掉額度 |
| `--timeout 3600` | Streamlit 是長連線，預設 300 秒會斷 |
| `--session-affinity` | **必要**：同一使用者固定連到同一實例 |
| `--no-allow-unauthenticated` | 私有，需 IAM 授權才能存取 |

### 授權特定使用者

```powershell
gcloud run services add-iam-policy-binding cement-app `
  --region asia-east1 `
  --member="user:主管@公司.com" `
  --role="roles/run.invoker"
```

### 若想公開（不建議，公司資料）

把 `--no-allow-unauthenticated` 改成 `--allow-unauthenticated`。

---

## 五、方案 C：Render（備案）

**只有在你不想用 GitHub 也不想碰 GCP 時才選**——因為免費方案**只能公開**。

```
1. render.com → New → Web Service
2. 連 GitHub repo，或選 "Deploy from Docker"
3. Environment: Docker（會自動抓 Dockerfile）
4. Instance Type: Free
```

| 限制 | 影響 |
|---|---|
| **僅公開** | ⚠ 公司資料外流風險 |
| 15 分鐘休眠 | 比 Streamlit Cloud 的 12 小時嚴格得多 |
| 750 小時/月 | 單一服務約 31 天，剛好夠 |

> 若要用 Render 又要隱私，可在 app 加一層密碼
> （見下方「加簡易密碼保護」）。

---

## 六、加簡易密碼保護（選配）

若選了只能公開的平台，可在 `app.py` 最前面加：

```python
import streamlit as st

def check_password():
    """簡易密碼閘。密碼存在 secrets，不寫在程式碼裡。"""
    if st.session_state.get('auth_ok'):
        return True
    st.title('🏗 水泥強度預測系統')
    pw = st.text_input('請輸入存取密碼', type='password')
    if pw:
        if pw == st.secrets.get('APP_PASSWORD', ''):
            st.session_state['auth_ok'] = True
            st.rerun()
        else:
            st.error('密碼錯誤')
    st.stop()

check_password()
```

設定密碼：
- **Streamlit Cloud**：Settings → Secrets → `APP_PASSWORD = "你的密碼"`
- **Cloud Run / Render**：環境變數 `APP_PASSWORD`（需改成 `os.environ.get`）

> ⚠ 這只擋隨機訪客，**不是真正的驗證**。
> 真要控管請用 Cloud Run + IAM。

---

## 七、我的建議

**先用 Streamlit Community Cloud**，理由：

1. 免費私有 app 正好符合需求
2. 不必寫 Dockerfile，5 分鐘上線
3. 換模型只要 `git push`
4. 1 GB RAM 對 210 MB 綽綽有餘

**等實際用起來、確認使用模式後**（多少人用、要不要常駐不休眠、
要不要接公司 SSO），再決定要不要搬到 Cloud Run。

Dockerfile 我已經先準備好——**要搬的時候直接用，不用再回頭改**。

---

## 附：三個平台的檔案需求對照

| 檔案 | Streamlit Cloud | Cloud Run | Render |
|---|---|---|---|
| `app.py` / `core.py` | ✓ | ✓ | ✓ |
| `*.parquet` / `*.pkl` | ✓ | ✓ | ✓ |
| `requirements.txt` | ✓ | ✓ | ✓ |
| `.streamlit/config.toml` | 選配 | ✓ **必要** | ✓ **必要** |
| `Dockerfile` | ✗ 不需要 | ✓ | ✓ |
| `README.md` 的 YAML header | ✗（那是 HF 專用） | ✗ | ✗ |

> HF Spaces 的 `README.md` front matter（`sdk: streamlit` 那段）
> 在其他平台**無害但無效**，可以留著。

---

## 八、Streamlit Cloud 部署常見錯誤（實際踩過）

### 錯誤 1：`No solution found when resolving dependencies`

```
Because catboost==1.2.7 depends on numpy>=1.16.0,<2.0 and you require
numpy==2.1.3, we can conclude that your requirements are unsatisfiable.
```

**原因**：`requirements.txt` 用 `==` 鎖死版本，兩個套件的需求互斥。

**解法**：
- 改用**範圍**（`>=x,<y`），讓解析器自行找相容組合
- `catboost>=1.2.8` 才支援 numpy 2.x（1.2.7 以下需 numpy<2.0）

### 錯誤 2：安裝卡在 `pandas-2.2.3.tar.gz` 編譯

```
Using Python 3.14.7 environment at /home/adminuser/venv
Downloading pandas-2.2.3.tar.gz (4.4 MB)
  Installing build dependencies: started      ← 卡在這裡
```

**原因**：**沒指定 Python 版本，平台給了最新的 3.14**。
pandas / numpy / catboost 在 3.14 上都還沒有預編譯 wheel
→ 退而從原始碼編譯 → 極慢且多半失敗。

**解法**：加 `runtime.txt`（一行）：

```
python-3.11
```

> **3.11 是目前 wheel 覆蓋最完整的版本。**
> 3.12 多數套件也有，但 3.13 / 3.14 仍有明顯缺口。

### 錯誤 3：`StreamlitDuplicateElementId`

```
streamlit.errors.StreamlitDuplicateElementId
  File "app.py", line 217, in <module>
    tsel = c3.selectbox('型別', ['I型', 'II型', 'IL型'])
```

**原因**：Streamlit 用「元件類型 + 標籤 + 選項」自動產生 ID。
兩個 widget 若這些**完全相同**就會撞 ID：

```python
# TAB1 強度預測
ctype = c2.selectbox('型別', ['I型', 'II型', 'IL型'])   # L53
# TAB2 帕雷托分析
tsel  = c3.selectbox('型別', ['I型', 'II型', 'IL型'])   # L217  ← 撞了
```

舊版 Streamlit 容忍這種情況，**新版（1.5x+）改為直接報錯**。

**解法**：**每個互動元件都給唯一 `key`**。

```python
ctype = c2.selectbox('型別', [...], key='t1_type')
tsel  = c3.selectbox('型別', [...], key='t2_type')
```

本專案的 key 命名慣例——**前綴標明所屬頁籤**：

| 前綴 | 頁籤 |
|---|---|
| `t1_` | 強度預測 |
| `t2_` | 帕雷托分析 |
| `t3_` | 模型可信度 |

迴圈內產生的元件用 f-string 帶入變數，確保執行期唯一：

```python
key=f't1_xrd_{c}'      # 每個 XRD 欄位一個
key=f't2_dir_{xcol}'   # 每個特徵的方向選擇一個
```

**檢查有沒有漏掉**：

```bash
grep -nE "\.(selectbox|radio|number_input|multiselect|file_uploader|button)\(" app.py \
  | grep -v "key=" 
```

有輸出就是還有元件沒加 key。

### 錯誤 4：`runtime.txt` 沒生效

log 顯示 `python3.14` 但你明明寫了 `python-3.11`。

**原因**：**Streamlit Community Cloud 不讀 `runtime.txt`**
（那是 Heroku / Render 的慣例）。

**解法**：在 UI 設定——

```
部署時：Advanced settings → Python version → 3.11
部署後：App settings → Python version → 改完 Reboot app
```

> `runtime.txt` 可以留著，**Render / Koyeb 會讀它**。

| 平台 | Python 版本怎麼指定 |
|---|---|
| **Streamlit Cloud** | **UI（Advanced settings）** |
| Render / Koyeb | `runtime.txt` 或 Dockerfile |
| Cloud Run | Dockerfile 的 `FROM python:3.11-slim` |

### 推上去之前先驗依賴能不能解

```bash
pip install --dry-run --python-version 3.11 --only-binary=:all: \
  -r requirements.txt --target /tmp/dryrun
```

`--only-binary=:all:` **強制只用 wheel**——若有套件需要編譯就直接報錯，
正好模擬雲端的限制。無輸出即代表通過。

### 本專案驗證過的組合（Python 3.11）

| 套件 | 解析版本 |
|---|---|
| streamlit | 1.62.0 |
| pandas | 2.3.3 |
| numpy | 2.4.6 |
| scikit-learn | 1.9.0 |
| catboost | 1.2.10 |
| xgboost | 3.2.0 |

共 56 個套件（含間接依賴），全部有 wheel。實測預測結果正確。

### 三個 booster 全部納入（不依當前模型檔精簡）

`requirements.txt` 同時裝 **catboost + lightgbm + xgboost**，
即使當前模型檔沒用到 lightgbm 也照裝。

**理由**：v6.6 有多個機制都可能選中它們，**重訓後組合會變**：

| 機制 | 可能產生的模型 |
|---|---|
| `MODEL_ZOO` | `CatB*` → catboost、`LGBM*` → lightgbm、`XGB*` → xgboost |
| [5] 兩階段 | catboost / lightgbm / xgboost **三選一**（逐分段裁決） |
| [6] MTL 後端 | ridge / lightgbm / catboost（取 `<2MPa%` 最佳） |
| `Stack_MAE` | 內含 catboost + xgboost + svr + gb |

**少裝任何一個的後果很嚴重**：不是預測時才失敗，而是**載入 pkl 時整個
app 就掛掉**（`ModuleNotFoundError`），因為 pickle 反序列化需要原始類別。

**成本很低**（實測）：

| 項目 | 現況 |
|---|---|
| 記憶體 | 239 MB → **243 MB**（+4 MB） |
| 安裝體積 | +約 180 MB |
| 部署時間 | +約 1 分鐘 |

> lightgbm 只多 4 MB，因為**模組 import 本身很輕**，
> 真正吃記憶體的是模型物件——而那本來就要載。

**用這點成本換「換模型不必改 requirements」是划算的。**

### 當前模型檔實際用到的（供參考）

```
sklearn.Ridge                 × 14
catboost.CatBoostRegressor    ×  4
sklearn.RandomForestRegressor ×  1
xgboost.XGBRegressor          ×  1
```

想確認新模型用了什麼：

```python
import joblib, collections
m = joblib.load('cement_v6.6_xxx.pkl')
c = collections.Counter()
for tk, segs in m['model_archive'].items():
    for sg, e in segs.items():
        mdl = e.get('trained_model')
        if mdl is not None:
            c[type(mdl).__module__.split('.')[0]] += 1
print(c)
```

> 這只是**診斷用**——因為三個 booster 都已納入，
> 不論結果如何都不必改 requirements。
