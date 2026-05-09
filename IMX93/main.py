# IMX93/main.py
import sys
import time
import threading
from pathlib import Path

from wake_up_word.wake_up import getter as wake_getter, main as wake_up_main

# fall_getter 在開發板上位於 repo 外的 ../root/fall_detection/imx93_version/
_FALL_GETTER_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "root" / "fall_detection" / "imx93_version"
)
sys.path.insert(0, str(_FALL_GETTER_DIR))
from fall_getter import get_fall_status

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
        wake_status = wake_getter()
        fall_status = get_fall_status()
        current_time = time.monotonic()

        if wake_status == 1:
            triggered_event, label = "help", "求救"
        elif fall_status == 1:
            triggered_event, label = "fall", "跌倒"
        else:
            triggered_event = None

        if triggered_event is not None:
            # 檢查是否已過冷卻時間
            if current_time - last_alert_time > WARNING_COOLDOWN_TIME:
                print(f">>> 偵測到危險訊號 ({label})，啟動確認流程...")
                # 只有當 confirm 正式發出通知（回傳 True）時，才更新冷卻計時器
                if confirm(event_type=triggered_event):
                    last_alert_time = time.monotonic()
                    print(f">>> 通知已發送，進入 {WARNING_COOLDOWN_TIME} 秒冷卻期。")
            else:
                remaining = WARNING_COOLDOWN_TIME - (current_time - last_alert_time)
                print(f">>> [忽略] 偵測到{label}，但處於冷卻期（還剩 {remaining:.1f} 秒）")

        time.sleep(POLL_INTERVAL_S)

if __name__ == "__main__":
    main()
