'''
Function:based on baidu-asr-api ,archieving online speech recognition
Author: ken-zoukun(github)
Requirements:
+ pyaudio - `pip install pyaudio`
+ py-webrtcvad - `pip install webrtcvad`
+ baiduaip  -'pip install baiduaip'
'''



import time
import uuid
import wave
import pyaudio
import webrtcvad
import signal
import collections
import sys
from aip import AipSpeech
from struct import pack
from array import array


# 用Pyaudio库录制音频
def audio_record1(out_file, rec_time):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    # RECORD_SECONDS = 5
    # WAVE_OUTPUT_FILENAME = "output.wav"

    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("Start Recording...")

    frames = []
    # 录制音频数据
    for i in range(0, int(RATE / CHUNK * rec_time) + 1):
        data = stream.read(CHUNK)
        frames.append(data)
    stream.stop_stream()
    stream.close()
    p.terminate()

    print("Recording Done...")

    # 保存音频文件
    recorded_data = b''.join(frames)
    wf = wave.open(out_file, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(recorded_data)
    wf.close()
    return recorded_data


# 用Pyaudio库录制音频,归一化音量最大值到int16位
def audio_record2(out_file, rec_time):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    # RECORD_SECONDS = 5
    # WAVE_OUTPUT_FILENAME = "output.wav"

    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("Start Recording...")
    raw_data = array('h')

    # frames = []
    # 录制音频数据
    for i in range(0, int(RATE / CHUNK * rec_time) + 1):
        data = stream.read(CHUNK)
        raw_data.extend(array('h', data))

        # frames.append(data)
    stream.stop_stream()
    stream.close()
    p.terminate()
    print("Recording Done...")

    def normalize(snd_data):
        "Average the volume out"
        MAXIMUM = 32767  # 16384
        times = float(MAXIMUM) / max(abs(i) for i in snd_data)
        r = array('h')
        for i in snd_data:
            r.append(int(i * times))
        return r

    def record_to_file(path, data, sample_width, RATE):
        """Records from the microphone and outputs the resulting data to 'path'"""
        # sample_width, data = record()
        data = pack('<' + ('h' * len(data)), *data)
        wf = wave.open(path, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(sample_width)
        wf.setframerate(RATE)
        wf.writeframes(data)
        wf.close()

    raw_data = normalize(raw_data)
    record_to_file(out_file, raw_data, 2, RATE)


# 用webrtcvad进行语音端点检测,用Pyaudio库录制音频,并归一化音量最大值到int16位
def audio_record3(recording_path, recording_time):  # 20,160
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK_DURATION_MS = 30  # supports 10, 20 and 30 (ms)
    PADDING_DURATION_MS = 1500  # 1 sec jugement
    CHUNK_SIZE = int(RATE * CHUNK_DURATION_MS / 1000)  # chunk to read
    CHUNK_BYTES = CHUNK_SIZE * 2  # 16bit = 2 bytes, PCM
    NUM_PADDING_CHUNKS = int(PADDING_DURATION_MS / CHUNK_DURATION_MS)

    # NUM_WINDOW_CHUNKS = int(240 / CHUNK_DURATION_MS)
    NUM_WINDOW_CHUNKS = int(400 / CHUNK_DURATION_MS)  # 400/ 30ms  ge
    NUM_WINDOW_CHUNKS_END = int(NUM_WINDOW_CHUNKS * 2)

    # START_OFFSET = int(NUM_WINDOW_CHUNKS * CHUNK_DURATION_MS * 0.5 * RATE)

    vad = webrtcvad.Vad(1)

    pa = pyaudio.PyAudio()
    stream = pa.open(format=FORMAT,
                     channels=CHANNELS,
                     rate=RATE,
                     input=True,
                     start=False,
                     # input_device_index=2,
                     frames_per_buffer=CHUNK_SIZE)

    got_a_sentence = False
    leave = False

    def handle_int(sig, chunk):
        global leave, got_a_sentence
        leave = True
        got_a_sentence = True

    def record_to_file(path, data, sample_width):
        "Records from the microphone and outputs the resulting data to 'path'"
        # sample_width, data = record()
        data = pack('<' + ('h' * len(data)), *data)
        wf = wave.open(path, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(sample_width)
        wf.setframerate(RATE)
        wf.writeframes(data)
        wf.close()

    def normalize(snd_data):
        "Average the volume out"
        MAXIMUM = 32767  # 16384
        times = float(MAXIMUM) / max(abs(i) for i in snd_data)
        r = array('h')
        for i in snd_data:
            r.append(int(i * times))
        return r

    signal.signal(signal.SIGINT, handle_int)

    while not leave:
        ring_buffer = collections.deque(maxlen=NUM_PADDING_CHUNKS)
        triggered = False
        voiced_frames = []
        ring_buffer_flags = [0] * NUM_WINDOW_CHUNKS
        ring_buffer_index = 0

        ring_buffer_flags_end = [0] * NUM_WINDOW_CHUNKS_END
        ring_buffer_index_end = 0
        buffer_in = ''
        # WangS
        raw_data = array('h')
        index = 0
        start_point = 0
        StartTime = time.time()
        print("* recording: ")
        stream.start_stream()

        while not got_a_sentence and not leave:
            chunk = stream.read(CHUNK_SIZE)
            # add WangS
            raw_data.extend(array('h', chunk))
            index += CHUNK_SIZE
            TimeUse = time.time() - StartTime

            active = vad.is_speech(chunk, RATE)

            sys.stdout.write('1' if active else '_')
            ring_buffer_flags[ring_buffer_index] = 1 if active else 0
            ring_buffer_index += 1
            ring_buffer_index %= NUM_WINDOW_CHUNKS

            ring_buffer_flags_end[ring_buffer_index_end] = 1 if active else 0
            ring_buffer_index_end += 1
            ring_buffer_index_end %= NUM_WINDOW_CHUNKS_END

            # start point detection
            if not triggered:
                ring_buffer.append(chunk)
                num_voiced = sum(ring_buffer_flags)
                if num_voiced > 0.8 * NUM_WINDOW_CHUNKS:
                    sys.stdout.write(' Open ')
                    triggered = True
                    start_point = index - CHUNK_SIZE * 20  # start point
                    # voiced_frames.extend(ring_buffer)
                    ring_buffer.clear()
            # elif TimeUse > 3:
            #     leave = True
            #     sys.stdout.flush()
            #     break
            # end point detection
            else:
                # voiced_frames.append(chunk)
                ring_buffer.append(chunk)
                num_unvoiced = NUM_WINDOW_CHUNKS_END - sum(ring_buffer_flags_end)
                if num_unvoiced > 0.90 * NUM_WINDOW_CHUNKS_END or TimeUse > recording_time:
                    sys.stdout.write(' Close ')
                    triggered = False
                    got_a_sentence = True

            sys.stdout.flush()

        sys.stdout.write('\n')
        # data = b''.join(voiced_frames)

        stream.stop_stream()
        # if leave:
        #     break
        print("* done recording")

        got_a_sentence = False

        # write to file
        raw_data.reverse()
        for index in range(start_point):
            raw_data.pop()
        raw_data.reverse()
        raw_data = normalize(raw_data)
        record_to_file(recording_path, raw_data, 2)
        leave = True

    stream.close()


def main():
    # 获取本机MAC
    def get_mac_address():
        mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
        return ":".join([mac[e:e + 2] for e in range(0, 11, 2)])

    # 读取音频文件
    def get_file_content(filePath):
        with open(filePath, 'rb') as fp:
            return fp.read()

    # 获取Access Token
    # 应用名称       |AppID      |API Key                    |Secret Key                         |包名
    # Python语音识别 |16972159   |fsatvWpiIfwuoSQ4uNnoSxsF   |ksPzxc18ZfUU7Zo89Kt6trkvkU8EIg1f   |百度语音
    APPID = "16972159"
    API_KEY = "xxxxxxxxxxx"   # 个人百度语音应用API_KEY
    SECRET_KEY = "xxxxxxxx"   # 个人百度语音应用SECRET_KEY
    CUID = get_mac_address()        # 获取本机MAC
    DEV_PID = "1536"  # 1536,普通话(支持简单的英文识别),搜索模型,无标点,支持自定义词库

    AUDIO_FORMAT = "WAV"
    AUDIO_OUTPUT = "./Audio_recording.wav"       # 录音文件名
    AUDIO_SAVEFILE = "./Audio_synthesis.wav"     # 合成语音文件名

    # 本地语音识别
    def aip_get_asrresult(client, afile, afmt):
        # 识别结果已经被SDK由JSON字符串转为dict
        result = client.asr(get_file_content(afile), afmt, 16000, {"cuid": CUID, "dev_pid": DEV_PID})
        # print(result)
        if result["err_msg"] == "success.":
            # print(result["result"])
            return result["result"]
        else:
            # print(result["err_msg"])
            return ""

    # asr_result =  aip_get_asrresult(client, AUDIO_FILE, AUDIO_FORMAT)
    # print(asr_result)

    # 汉字语音合成
    def aip_get_synthesis(client, zh_str, fsave):
        # spd   String  语速，取值0-9，默认为5中语速
        # vol   String  音量，取值0-15，默认为5中音量
        # per   String  发音人选择, 0为女声，1为男声，3为情感合成-度逍遥，4为情感合成-度丫丫，默认为普通女
        result = client.synthesis(zh_str, "zh", 1, {"cuid": CUID, "spd": 5, "vol": 1, "per": 4})

        # 识别正确返回语音二进制 错误则返回dict
        if not isinstance(result, dict):
            with open(fsave, 'wb') as fs:
                fs.write(result)
            print("success")
            return 0
        else:
            print(result["err_msg"])
            return -1

    # synthesis_result = aip_get_synthesis(client, asr_result, AUDIO_SAVEFILE)

    # 新建AipSpeech
    client = AipSpeech(APPID, API_KEY, SECRET_KEY)
    while True:
        # 请说出你想识别的内容
        print("\n\n==================================================")
        print("Please tell me the command(limit within 3 seconds):")
        # print("Please tell me what you want to identify(limit within 10 seconds):")
        audio_record2(AUDIO_OUTPUT, 3)
        print("Identify On Network...")
        asr_result = aip_get_asrresult(client, AUDIO_OUTPUT, AUDIO_FORMAT)
        synthesis_result = aip_get_synthesis(client, asr_result, AUDIO_SAVEFILE)

        if len(asr_result) != 0:
            print("Identify Result:", asr_result[0])
            if asr_result[0].find("退出") != -1:
                break
            time.sleep(1.5)
        # os.system('pause')


if __name__ == '__main__':
    main()
