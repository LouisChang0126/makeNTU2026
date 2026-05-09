# 喚醒詞
要跑喚醒詞，在linux環境下執行以下程式(含CONDA ENV配置)
```
# 路徑
cd 喚醒詞 # 或對應資料夾名

# 環境
conda create -n makentu python=3.11 -y

sudo apt update
sudo apt install libasound2-dev portaudio19-dev flac -y

conda activate makentu

python -m pip install --upgrade pip

python -m pip install numpy
python -m pip install pyaudio
python -m pip install speechrecognition
python -m pip install edge-impulse-linux

# 檢查 PyAudio 是否能正常 import
python -c "import pyaudio; print('✅ PyAudio 成功'); import speech_recognition as sr; print('✅ SpeechRecognition 成功')"

python -m pip install six
python -m pip install "opencv-python>=4.5.1.48,<5"

# 賦予模型權限
chmod +x x86_model.eim
chmod +x model.eim

# 執行程式
python wake_up.py
```
getter叫getter