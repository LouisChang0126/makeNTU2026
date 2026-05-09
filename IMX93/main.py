# IMX93/main.py
import time
import threading
from wake_up_word.wake_up import getter as wake_getter, main as wake_up_main
from double_check import confirm

POLL_INTERVAL_S = 0.1
WARNING_COOLDOWN_TIME = 20.0  # 設定冷卻時間為 20 秒

def main() -> None:
    # 啟動背景語音偵測線程
    detection_thread = threading.Thread(target=wake_up_main, daemon=True)
    detection_thread.start()
    
    last_alert_time = -WARNING_COOLDOWN_TIME  # 初始值確保程式啟動後能立即反應
    
    print(f">>> 系統已啟動，冷卻時間設定為 {WARNING_COOLDOWN_TIME} 秒")

    while True:
        # 持續呼叫 getter 以清除舊的狀態紀錄
        # 根據 wake_up.py 邏輯，getter() 會重置偵測值
        status = wake_getter() 
        current_time = time.monotonic()

        if status == 1:
            # 檢查是否已過冷卻時間
            if current_time - last_alert_time > WARNING_COOLDOWN_TIME:
                print(">>> 偵測到危險訊號，啟動確認流程...")
                # 只有當 confirm 正式發出通知（回傳 True）時，才更新冷卻計時器
                if confirm(event_type="help"):
                    last_alert_time = time.monotonic()
                    print(f">>> 通知已發送，進入 {WARNING_COOLDOWN_TIME} 秒冷卻期。")
            else:
                remaining = WARNING_COOLDOWN_TIME - (current_time - last_alert_time)
                print(f">>> [忽略] 偵測到求救，但處於冷卻期（還剩 {remaining:.1f} 秒）")

        time.sleep(POLL_INTERVAL_S)

if __name__ == "__main__":
    main()
