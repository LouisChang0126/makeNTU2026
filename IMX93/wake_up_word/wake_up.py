import collections
import json
import os
import platform
import socket
import struct
import subprocess
import tempfile
import time

# 內部變數，紀錄自上次 getter 呼叫後的最高狀態值
_current_max_status = 0

# 喚醒詞清單
wordlist = ["沒事", "取消", "救命", "啊", "unknown"]

# 1. 載入模型路徑：x86_64 (Ubuntu PC) 用 x86_model.eim，aarch64 (IMX93) 用 model.eim。
# WAKE_MODEL 環境變數可覆寫（檔名或絕對路徑皆可）。
current_dir = os.path.dirname(os.path.abspath(__file__))
_arch = platform.machine().lower()
_default_model = (
    "x86_model.eim" if _arch in ("x86_64", "amd64", "i386", "i686") else "model.eim"
)
_model_override = os.environ.get("WAKE_MODEL", _default_model)
model_file = (
    _model_override
    if os.path.isabs(_model_override)
    else os.path.join(current_dir, _model_override)
)


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


class EimRunner:
    """以 Unix socket + newline-delimited JSON 與 .eim 模型直接溝通，
    取代 edge_impulse_linux 套件 (避免其 pyaudio 依賴)。"""

    def __init__(self, model_path: str):
        self._model_path = model_path
        self._proc = None
        self._sock = None
        self._tempdir = None
        self._socket_path = None
        self._ix = 0
        self._recv_buf = b""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()

    def init(self) -> dict:
        if not os.path.exists(self._model_path):
            raise FileNotFoundError(f"Model file does not exist: {self._model_path}")

        os.chmod(self._model_path, 0o755)
        self._tempdir = tempfile.mkdtemp(prefix="eim-")
        self._socket_path = os.path.join(self._tempdir, "runner.sock")

        # Inherit stdout/stderr so the eim binary's own diagnostics surface
        # (the runner's "error code was -22" comes via the JSON channel; the
        # underlying cause — DSP/NPU/TFLite failure — is logged to stderr).
        self._proc = subprocess.Popen(
            [self._model_path, self._socket_path],
        )

        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                raise RuntimeError(
                    f"eim runner exited (code={self._proc.returncode}) before socket was ready"
                )
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.connect(self._socket_path)
                self._sock = s
                break
            except (FileNotFoundError, ConnectionRefusedError):
                time.sleep(0.05)
        if self._sock is None:
            raise RuntimeError(f"timed out waiting for eim socket: {self._socket_path}")

        return self._send({"hello": 1})

    def classify(self, features) -> dict:
        return self._send({"classify": list(features)})

    def classify_continuous(self, features) -> dict:
        return self._send({"classify_continuous": list(features)})

    def _send(self, msg: dict) -> dict:
        msg = dict(msg)
        msg["id"] = self._ix
        self._ix += 1
        # eim runner protocol: raw JSON request, response framed by trailing \x00
        self._sock.sendall(json.dumps(msg).encode("utf-8"))
        return self._recv()

    def _recv(self) -> dict:
        # Accumulate until we see the null-byte terminator (some chunks may
        # carry multiple/partial messages, so search the whole buffer).
        while b"\x00" not in self._recv_buf:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise IOError("eim socket closed")
            self._recv_buf += chunk
        msg_bytes, _, rest = self._recv_buf.partition(b"\x00")
        self._recv_buf = rest
        text = msg_bytes.decode("utf-8", errors="replace")
        # Extract the first balanced {...} object (string-aware brace counting)
        depth = 0
        start = None
        in_str = False
        escape = False
        for i, ch in enumerate(text):
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                if start is None:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    return json.loads(text[start : i + 1])
        raise IOError(f"no complete JSON object in eim response: {text!r}")

    def stop(self):
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None
        if self._proc is not None:
            try:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            finally:
                self._proc = None
        if self._socket_path and os.path.exists(self._socket_path):
            try:
                os.remove(self._socket_path)
            except OSError:
                pass
        if self._tempdir and os.path.exists(self._tempdir):
            try:
                os.rmdir(self._tempdir)
            except OSError:
                pass


# 主循環：喚醒詞偵測 (eim runner + arecord)
def main():
    global _current_max_status

    with EimRunner(model_file) as runner:
        model_info = runner.init()
        params = model_info["model_parameters"]
        sample_rate = int(params["frequency"])
        window_size = int(params["input_features_count"])
        # AudioImpulseRunner derives the slice from slices_per_model_window;
        # using window/4 instead can produce EINVAL (-22) from the runner.
        slices_per_window = int(params.get("slices_per_model_window") or 4)
        slice_size = max(1, window_size // slices_per_window)
        bytes_per_slice = slice_size * 2  # int16 = 2 bytes
        unpack_fmt = f"<{slice_size}h"

        print(
            f"模型已啟動，正在監聽喚醒詞 "
            f"(sr={sample_rate}, window={window_size}, "
            f"slices/window={slices_per_window}, slice={slice_size})..."
        )

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
            # Rolling buffer of the last `window_size` int16 samples. We feed
            # arecord output in slice-sized chunks and call classify() with a
            # full window each time, matching upstream AudioImpulseRunner —
            # this .eim image does not implement classify_continuous.
            buf = collections.deque(maxlen=window_size)

            while True:
                raw = proc.stdout.read(bytes_per_slice)
                if not raw or len(raw) < bytes_per_slice:
                    break

                buf.extend(struct.unpack(unpack_fmt, raw))
                if len(buf) < window_size:
                    continue  # still filling the first window

                res = runner.classify(list(buf))

                if not res.get("success", True):
                    print(f"\n[eim] error: {res.get('error', res)}", flush=True)
                    continue

                result = res.get("result")
                if not isinstance(result, dict):
                    continue
                classifications = result.get("classification")
                if not isinstance(classifications, dict):
                    continue

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
