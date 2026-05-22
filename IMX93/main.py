# IMX93/main.py
import sys
import time
from pathlib import Path

from double_check import confirm, wake_getter

# fall_getter 在開發板上位於 repo 外的 /root/fall_detection/imx93_version/
_FALL_GETTER_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "fall_detection" / "imx93_version"
)
sys.path.insert(0, str(_FALL_GETTER_DIR))
from fall_getter import get_fall_status

POLL_INTERVAL_S = 0.1
WARNING_COOLDOWN_TIME = 20.0  # 設定冷卻時間為 20 秒


def main() -> None:
    last_alert_time = -WARNING_COOLDOWN_TIME  # 初始值確保程式啟動後能立即反應

    print(f">>> 系統已啟動，冷卻時間設定為 {WARNING_COOLDOWN_TIME} 秒")

    while True:
        fall_status = get_fall_status()
        wake_status = wake_getter()  # 喊「救命/啊」回 1，喊「沒事/取消」回 2
        current_time = time.monotonic()

        # 跌倒優先；沒跌倒但聽到求救也走 confirm 流程。
        # wake_status==2 在這層忽略，那只在 confirm 的取消視窗裡才有意義。
        if fall_status == 1:
            triggered_event, label = "fall", "跌倒"
        elif wake_status == 1:
            triggered_event, label = "help", "求救"
        else:
            triggered_event = None

        if triggered_event is not None:
            if current_time - last_alert_time > WARNING_COOLDOWN_TIME:
                print(f">>> 偵測到危險訊號 ({label})，啟動 10 秒取消視窗...")
                # confirm() 會播 prompt、輪詢遠端喚醒詞 server，沒取消才送 LINE 通知
                if confirm(event_type=triggered_event):
                    last_alert_time = time.monotonic()
                    print(f">>> 通知已發送，進入 {WARNING_COOLDOWN_TIME} 秒冷卻期。")
                else:
                    print(">>> 已取消或發送失敗，不進入冷卻期。")
            else:
                remaining = WARNING_COOLDOWN_TIME - (current_time - last_alert_time)
                print(f">>> [忽略] 偵測到{label}，但處於冷卻期（還剩 {remaining:.1f} 秒）")

        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
