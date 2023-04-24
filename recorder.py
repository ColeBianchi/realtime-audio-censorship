import sounddevice as sd
from scipy.io.wavfile import write
import threading
import os
import numpy as np

class AudioRecorder(threading.Thread):
    def __init__(self, duration):
        super(AudioRecorder, self).__init__()
        self.duration = duration
        self.frames = None

    def run(self):
        # def callback(indata, frames, time, status):
        #     if status:
        #         print(status)
        #     self.frames.append(indata.copy())

        # with sd.InputStream(callback=callback, channels=1, samplerate=16000):
        #     sd.sleep(int(self.duration * 1000))
        channels = 1
        sample_rate = 16000
        self.frames = sd.rec(int(self.duration * sample_rate), samplerate=sample_rate, channels=channels)
        sd.wait()

    def get_frames(self):
        return self.frames

    def save(self, filename):
        if not os.path.exists('recordings'):
            os.makedirs('recordings')
        write(f'recordings/{filename}.wav', 16000, self.frames)
