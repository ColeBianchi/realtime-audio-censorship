import sounddevice as sd
from scipy.io.wavfile import write
import threading
import os
import numpy as np

class AudioRecorder(threading.Thread):
	'''
	Asynchronous audio recording class, uses default device microphone
	'''
	def __init__(self, duration):
		'''
		Constructor for audio recorder
		Arguments:
			duration -- length of audio segments to ouput
		'''
		super(AudioRecorder, self).__init__()
		self.duration = duration
		self.frames = None
		self.rate = 16000

	def set_rate(self, hz):
		'''
		Set rate in hz of audio recording
		Arguments:
			hz -- Rate of recording in hz
		Returns:
			None
		'''
		self.rate = hz

	def run(self):
		'''
		Starts recording audio for defined duration of seconds
		Arguments:
			None
		Returns:
			None
		'''
		channels = 1
		sample_rate = self.rate
		self.frames = sd.rec(int(self.duration * sample_rate), samplerate=sample_rate, channels=channels)
		sd.wait()

	def get_frames(self):
		'''
		Retrieves the recorded audio frames from previous run command
		Arguments:
			None
		Returns:
			None
		'''
		return self.frames

	def save(self, filename):
		'''
		Saves the current frame to a .wav file in the ./recordings directory
		Arguments:
			filename -- Name of file to save
		Returns:
			Saved file at ./recordings/FILENAME.wav
		'''
		if not os.path.exists('recordings'):
			os.makedirs('recordings')
		write(f'recordings/{filename}.wav', self.rate, self.frames)
