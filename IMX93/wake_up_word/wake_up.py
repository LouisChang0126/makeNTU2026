import os
import time
from edge_impulse_linux.audio import AudioImpulseRunner
import speech_recognition as sr

# 內部變數，紀錄自上次 getter 呼叫後的最高狀態值
_current_max_status = 0

# 喚醒詞清單
wordlist = ["沒事", "取消", "救命", "啊", "unknown"]

# 1. 載入模型路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
model_file = os.path.join(current_dir, "model.eim")

# --- 修改後的 Getter 函數 ---
def getter():
    """
    回傳自上次呼叫此函數以來偵測到的最大數值：
    - 若期間偵測到 '沒事' 或 '取消'，回傳 2 (最高優先級)
    - 若期間僅偵測到 '救命' 或 '啊'，回傳 1
    - 若期間只有 'unknown' 或無偵測，回傳 0
    呼叫後會重置為 0。
    """
    global _current_max_status
    ret = _current_max_status
    _current_max_status = 0  # 重置紀錄
    return ret

# 2. 定義語音轉文字函數 (STT) - 保留結構
def perform_stt():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print(">>> 偵測到喚醒詞！請說出您的指令...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        audio_data = recognizer.listen(source, timeout=5, phrase_time_limit=5)
    
    try:
        text = recognizer.recognize_google(audio_data, language="zh-TW")
        print(f">>> 您說的是: {text}")
    except Exception as e:
        print(f">>> 辨識失敗: {e}")

# 3. 主循環：喚醒詞偵測 (Edge Impulse)
def main():
    global _current_max_status
    
    with AudioImpulseRunner(model_file) as runner:
        model_info = runner.init()
        print(f"模型已啟動，正在監聽喚醒詞...")

        for res, audio in runner.classifier():
            classifications = res['result']['classification']
            best_score = 0.0
            best_word = None
            
            for word in wordlist:
                if word in classifications:
                    score = classifications[word]
                    if score > 0.8: # 信心值門檻
                        if best_score < score:
                            best_score = score
                            best_word = word
            
            # 判斷本次偵測的分數
            this_run_status = 0
            if best_word in ["救命", "啊"]:
                this_run_status = 1
            elif best_word in ["沒事", "取消"]:
                this_run_status = 2
            
            # 更新累計的最大值 (確保 2 > 1 > 0)
            if this_run_status > _current_max_status:
                _current_max_status = this_run_status
            
            # 輔助偵錯訊息
            if best_word:
                print(f"🎤 偵測到: [{best_word}] (狀態: {this_run_status}), 目前累計最大值: {_current_max_status}")
            else:
                print(f".", end="", flush=True) # 未偵測到時印點表示運行中

if __name__ == "__main__":
    # 提醒：若要在其他地方呼叫 get_last_detection_status()，
    # 建議使用多線程 (threading) 執行 main()
    main()