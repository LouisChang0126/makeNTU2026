# 隱私守護的長者居家 Edge AI 防護網

makeNTU 2026 — 恩智浦 X 安富利 題目二「面向萬物互聯的下一哩路」。
完整提案見 [專案計畫/提案2.md](專案計畫/提案2.md)。

## 架構

兩節點透過共享 `STREAM_SIGNING_KEY` 簽 / 驗 JWT 互通。無狀態，雙方不需要直接通訊。

```
┌──────────────┐                                ┌──────────────────┐
│ IMX93 (sensor)│  ① POST /event {fall|help}    │ linebot/         │
│ + ESP32 nodes │ ─────────────────────────────► │ Cloud Function   │
│ + camera      │                                │ - LINE webhook   │
└──────────────┘                                │ - sign JWT       │
                                                │ - push LINE msg  │
                                                └────────┬─────────┘
                                                         │ ② push
                                                         ▼
                                                ┌──────────────────┐
                                                │ family LINE app  │
                                                └────────┬─────────┘
                                                         │ ③ tap stream URL
                                                         ▼
┌────────────────────────────────────────────────────────────────────┐
│ streaming_web/  (runs on IMX93, exposed via ngrok)                 │
│ - verify JWT (HS256)                                               │
│ - GET /stream?token=...    MJPEG live view                         │
│ - GET /snapshot?token=...  single JPEG (used in LINE ImageMessage) │
└────────────────────────────────────────────────────────────────────┘
```

對應提案 §3「邊緣閉環決策」、§5「平時你看不到、出事才看得到」。

## 目錄

| 目錄 | 用途 |
|---|---|
| [linebot/](linebot/) | LINE bot — Cloud Function 端。收 IMX93 事件、簽 JWT、push LINE。 |
| [streaming_web/](streaming_web/) | Streaming server — 跑在 IMX93。驗 JWT、串 MJPEG。 |
| [專案計畫/](專案計畫/) | 提案文件 |
| [spec/](spec/) | 競賽資料 |

## 快速開始（本機兩節點）

### 0. 環境

```powershell
conda create -n makentu python=3.11
conda activate makentu
```

### 1. 產生共享簽章金鑰

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

把輸出貼到 **兩邊**的 `.env`（`linebot/.env` 與 `streaming_web/.env`）的 `STREAM_SIGNING_KEY`，務必一致。

### 2. 設 LINE channel

1. 到 [LINE Developers Console](https://developers.line.biz/) 建一個 Messaging API channel
2. 拿到 `Channel secret` 與 `Channel access token`
3. 貼進 `linebot/.env`

### 3. 跑 streaming_web

```powershell
cd streaming_web
copy .env.example .env
# 編輯 .env 填 STREAM_SIGNING_KEY
pip install -r requirements.txt
python local_host.py
```

另開 terminal：

```powershell
ngrok http 5001
```

把 ngrok 的 https URL 記下來。

### 4. 跑 linebot

```powershell
cd linebot
copy .env.example .env
# 編輯 .env 填 LINE 三個欄位 + STREAM_SIGNING_KEY + STREAM_PUBLIC_BASE_URL（步驟 3 的 ngrok URL）
pip install -r requirements.txt
python local_host.py
```

### 5. 拿到 LINE userId

加 bot 為好友 → 隨便傳訊息 → bot 回你 userId（需要 LINE webhook 設好；若還沒部署 Cloud Function，可暫時對 linebot 也跑一個 ngrok 設 webhook）。把 userId 貼到 `linebot/.env` 的 `LINE_USER_ID` 後重啟 linebot。

### 6. 觸發測試

```powershell
curl.exe -X POST http://localhost:5000/event -H "Content-Type: application/json" -d "{\"event_type\":\"fall\"}"
```

或從另一份 Python 檔案 import：

```python
import sys; sys.path.insert(0, 'linebot')
from notifier import trigger_event
trigger_event("fall")
```

預期：
- 手機收到 LINE 文字 + webcam 截圖
- 點訊息中的連結 → 看到即時 MJPEG
- 等 `STREAM_TTL_SECONDS` 過期後再點 → 410 Gone

## 部署到 Cloud Function（linebot 端）

```powershell
cd linebot
gcloud functions deploy linebot `
  --gen2 --runtime=python311 --region=asia-east1 `
  --source=. --entry-point=linebot `
  --trigger-http --allow-unauthenticated `
  --env-vars-file=.env.yaml
```

`.env.yaml` 需自行從 `.env` 轉換（YAML 格式），**不要 commit**。
部署完成後把 Cloud Function URL + `/webhook` 設到 LINE Developers Console。

## 環境變數

### linebot/.env

| 變數 | 說明 |
|---|---|
| `LINE_CHANNEL_SECRET` | LINE channel secret |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE channel access token |
| `LINE_USER_ID` | 收推播的家屬 userId |
| `STREAM_SIGNING_KEY` | JWT 簽章金鑰（與 streaming_web 一致） |
| `STREAM_PUBLIC_BASE_URL` | streaming_web 對外 URL（不含結尾斜線） |
| `STREAM_TTL_SECONDS` | token 有效秒數，預設 7200 |
| `PORT` | 本機 port，預設 5000 |

### streaming_web/.env

| 變數 | 說明 |
|---|---|
| `STREAM_SIGNING_KEY` | JWT 簽章金鑰（與 linebot 一致） |
| `CAMERA_INDEX` | OpenCV `VideoCapture` 索引，預設 0 |
| `PORT` | 本機 port，預設 5001 |

## 安全模型

- **平時無串流**：streaming_web 的 `/stream` 沒有有效 JWT 一律 410；webcam 不會啟動。
- **token 隨機且短期**：HS256 簽 JWT，預設 2 小時過期；無法偽造，過期後即失效。
- **無共享狀態**：兩節點不共用資料庫；linebot 簽 → streaming_web 驗，毋須通訊。
- **影像不離家**：除了事件觸發後的限時窗口，影像始終留在 streaming_web 本地。

對應提案 §5 的安全宣告：「**平時你看不到，出事才看得到**」。

## 不在當前 prototype 範圍內

- 家屬「查看 / 取消」LINE 指令回覆 — v2
- 多家屬註冊（目前單一 userId） — v2
- IMX93 跌倒偵測模型本身 — 由其他組員處理，透過 `POST /event` 串接
- ESP32-CAM 邊緣節點 ↔ IMX93 通訊 — 提案 §2.1
- 智慧家庭整合（開燈、解鎖、關瓦斯） — 提案 §7.2
