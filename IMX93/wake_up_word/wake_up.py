import os
import subprocess

import numpy as np
from edge_impulse_linux.runner import ImpulseRunner

# 內部變數，紀錄自上次 getter 呼叫後的最高狀態值
_current_max_status = 0

# 喚醒詞清單
wordlist = ["沒事", "取消", "救命", "啊", "unknown"]

# 1. 載入模型路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
model_file = os.path.join(current_dir, "model.eim")


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


# 主循環：喚醒詞偵測 (Edge Impulse + arecord)
def main():
    global _current_max_status

    with ImpulseRunner(model_file) as runner:
        model_info = runner.init()
        params = model_info["model_parameters"]
        sample_rate = int(params["frequency"])
        window_size = int(params["input_features_count"])
        # 與 AudioImpulseRunner.classifier() 行為一致：每次以 1/4 視窗滑動
        slice_size = max(1, window_size // 4)
        bytes_per_slice = slice_size * 2  # int16 = 2 bytes

        print(f"模型已啟動，正在監聽喚醒詞 (sr={sample_rate}, window={window_size})...")

        # 以 arecord 直接擷取原始 PCM (S16_LE, mono) 串流
        cmd = [
            "arecord",
            "-q",
            "-f", "S16_LE",
            "-c", "1",
            "-r", str(sample_rate),
            "-t", "raw",
        ]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        try:
            while True:
                raw = proc.stdout.read(bytes_per_slice)
                if not raw or len(raw) < bytes_per_slice:
                    break

                samples = np.frombuffer(raw, dtype=np.int16).tolist()
                res = runner.classify_continuous(samples)

                classifications = res["result"]["classification"]
                best_score = 0.0
                best_word = None

                for word in wordlist:
                    if word in classifications:
                        score = classifications[word]
                        if score > 0.8:  # 信心值門檻
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
                    print(
                        f"🎤 偵測到: [{best_word}] (狀態: {this_run_status}), "
                        f"目前累計最大值: {_current_max_status}"
                    )
                else:
                    print(".", end="", flush=True)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
