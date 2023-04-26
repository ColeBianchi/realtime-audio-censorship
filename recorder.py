import time
import sounddevice as sd
from scipy.io.wavfile import write
import threading
import os
import numpy as np
import queue

class AudioRecorder(threading.Thread):
	'''
	Asynchronous audio recording class, uses default device microphone
	'''
	def __init__(self, duration, sample_rate, recording_queue: queue.Queue, channels: int = 1):
		'''
		Constructor for audio recorder
		Arguments:
			duration -- length of audio segments to ouput
		'''
		super(AudioRecorder, self).__init__()
		self.duration = duration
		self.frames = None
		self.rate = sample_rate
		self.recording_queue = recording_queue
		self.channels = channels

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
		# self.frames = sd.rec(int(self.duration * sample_rate),
		# samplerate=sample_rate, channels=channels)

		# Okay, to avoid the stopping issues, I'm going to try and use the raw
		# InputStream provided by sounddevice for recording.
		# https://python-sounddevice.readthedocs.io/en/0.4.6/api/streams.html#sounddevice.InputStream
		# A more practical example (which I based this on) is
		# https://python-sounddevice.readthedocs.io/en/0.4.6/examples.html#plot-microphone-signal-s-in-real-time 

		# First, define the callback that PortAudio will call while the stream is
		# running. PortAudio will call this and provide as many frames as we specify,
		# and it's the job of this callback to take those frames and put them
		# somewhere.
		# Callback signature as provided in docs.

		# "The PortAudio stream callback runs at very high or real-time priority. It
		# is required to consistently meet its time deadlines. Do not allocate
		# memory, access the file system, call library functions or call other
		# functions from the stream callback that may block or take an unpredictable
		# amount of time to complete."

		# THE ABOVE is important, because it means: we want to push the data that
		# PortAudio passes to this callback to a data structure that we don't have to
		# wait to use--like a queue shared by multiple threads. Obtaining the lock
		# could lead to unpredictable wait times--which screws up PortAudio.

		# Instead, we create a separate queue for "callback use only," which we'll
		# then grab items from and push to our shared array. So sure--it's another
		# intermediary data structure, but necessary.

		self.mic_callback_queue = queue.Queue()

		def mic_callback(indata: np.ndarray, frames: int, time, status) -> None:
			assert len(indata) == frames
			# Use special slice to make sure we're pushing a COPY of the indata
			# values to our queue.
			self.mic_callback_queue.put(indata[:])

		# Next, we actually need to define the stream that we're going to "connect"
		# or point at the default input device. Starting a stream basically means
		# firing up a thread where PortAudio (a C/C++ Audio I/O library) runs and
		# takes data from inputs / writes data to outputs. The stream we define is a
		# convenient framework for telling PortAudio what to do!

		# In this case, we'll define a special case of the normal Stream called
		# InputStream. This is just a normal stream, but we can only read from it, as
		# it is just telling PortAudio to grab the data provided by our microphone
		# and hand it off to us (normal streams can connect to multiple input and/or
		# output devices--we don't need/want that for our input!).

		mic_stream = sd.InputStream(samplerate=self.rate, channels=self.channels, callback=mic_callback)

		# How do I start the stream? Well, the __enter__ functionality
		# (executed when we use it with "with") calls "self.start" -- and that's what
		# they do in all th examples--so I'll follow that.
		with mic_stream:
			# Once the stream is running, I basically just want to continuously take
			# data out of that "mic_callback_queue" and put it into our shared
			# recording_queue as soon as new data is available.
			frame_count = 0
			while True:
				frame_package = (frame_count, self.mic_callback_queue.get())
				self.recording_queue.put(frame_package)
				frame_count += 1

			# https://python-sounddevice.readthedocs.io/en/0.4.6/examples.html#recording-with-arbitrary-duration
			# The above example mimics this most closely--we're we want to wake up
			# this thread to wait on the queue's condition until woken up by the
			# PortAudio (Stream) thread that is going to put more data in the
			# mic_callback_queue via the callback function.

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
