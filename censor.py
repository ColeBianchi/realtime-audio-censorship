import queue
import threading
import time
import recorder
import os
import string
import sounddevice as sd
import numpy as np

from whisper_transcribe import Transcriber
from speechremover import bleep_audio_segments

recording_queue = queue.Queue()
playback_queue = queue.Queue()

RECORDING_INTERVAL = 30
SAMPLE_RATE = 16000
CHANNELS = 1
SAVE_FRAMES = False
BANNING_PROBABILITY = 0.2
BLOCKSIZE = RECORDING_INTERVAL*SAMPLE_RATE

def record_audio():
	'''
	Creates a sounddevice InputStream and records audio to a queue. This function
	then takes that and pushes it to the shared recording_queue.
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

	mic_callback_queue = queue.Queue()

	def mic_callback(indata: np.ndarray, frames: int, time, status) -> None:
		assert len(indata) == frames
		# Use special slice to make sure we're pushing a COPY of the indata
		# values to our queue.
		mic_callback_queue.put(indata[:])

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

	mic_stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=mic_callback, blocksize=BLOCKSIZE)

	# How do I start the stream? Well, the __enter__ functionality
	# (executed when we use it with "with") calls "self.start" -- and that's what
	# they do in all th examples--so I'll follow that.
	with mic_stream:

		print('#' * 80)
		print('press Ctrl+C to stop the recording')
		print('#' * 80)

		# Once the stream is running, I basically just want to continuously take
		# data out of that "mic_callback_queue" and put it into our shared
		# recording_queue as soon as new data is available.
		block_count = 0
		while True:
			block = mic_callback_queue.get()
			block = block.squeeze() # Makes audio format match that of everything else internally.
			block_package = (block_count, block)
			recording_queue.put(block_package)
			block_count += 1
			print(f"Placed audio segment {block_count} of length {len(block_package[-1])} in recording queue.")

		# https://python-sounddevice.readthedocs.io/en/0.4.6/examples.html#recording-with-arbitrary-duration
		# The above example mimics this most closely--we're we want to wake up
		# this thread to wait on the queue's condition until woken up by the
		# PortAudio (Stream) thread that is going to put more data in the
		# mic_callback_queue via the callback function.

def process_audio():
	'''
	Creates transcription from audio and "bleeps out" portions of the audio stream
	that correspond with blacklisted words found in the transcription.
	
	Arguments:
		None
	Returns:
		Modified audio segments with ID's pushed into shared processed audio queue.
	'''
	# Create transcriber instance.
	transcriber = Transcriber()

	# Load banned words list to scan later.
	banned_words = ["andre", "test", "nate", "phone"]
	with open('banned_words.txt', 'r') as f:
		for line in f:
			banned_words.append(line.strip())
		f.close()

	# Translator used to clean detected words for list queries
	translator = str.maketrans('', '', string.punctuation)

	while True:
		# # Check if there is any audio in the recording queue. If so, read it,
		# # transcribe it, and process it.
		# if not recording_queue.empty():

		# Get audio track from shared recording queue.
		# Blocks by default until there is something to get from the queue.
		track_id, audio = recording_queue.get()
		print(f"Transcriber picked up audio track {track_id} -- transcribing now!")

		# Transcribe audio track
		transcription_start = time.time()
		segments = transcriber.run_model_on_pcm(audio)
		transcription_end = time.time()
		print(f"Successfully transcribed audio segment {track_id} in {transcription_end-transcription_start}s.")
		
		print(f"Beginning censoring words in audio segment {track_id} now.")
		censoring_start = time.time()
		# Parse the start/end times of all banned word instances found in the
		# transcript.
		banned_word_segment_times = []
		for segment in segments:
			for word_dict in segment["words"]:
				word = word_dict["word"].translate(translator).lower().strip()
				if word in banned_words:
					if word_dict['probability'] > BANNING_PROBABILITY:
						banned_word_segment_times.append((word_dict['start'], word_dict['end']))
						print(f"\tFound banned word \"{word}\" in audio at {word_dict['start']}-->{word_dict['end']}!")
					else:
						print(f"\tFound banned word \"{word}\" in audio at {word_dict['start']}-->{word_dict['end']}, but ignoring as confidence below threshold ({word_dict['probability']} < {BANNING_PROBABILITY}).")

		# "Bleep out" banned portions of audio using speeechremover.
		censored_audio = bleep_audio_segments(audio_ndarray=audio, audio_samplerate=SAMPLE_RATE, segment_times=banned_word_segment_times)
		censoring_end = time.time()
		print(f"Completed censoring of {len(banned_word_segment_times)} banned words in audio segment {track_id} in {censoring_end-censoring_start}s.")

		# Add censored audio to the playback/output queue.
		output_package = (track_id, censored_audio)
		playback_queue.put(output_package)
		print(f"Placed censored audio segment {track_id} into playback queue.")

def playback_audio():
	'''
	Scans to see if audio track violates word list and if not plays the track back over the device's speakers
	Arguments:
		None
	Returns:
		None
	'''
	
	# For now, to avoid dealing with the output_callback_queue being empty for a
	# while, maybe I'll just put a sleep here. In fact, if this works--that actually
	# kinda makes sense. Why? Because, if we gaurantee to the user that it takes our
	# system end-to-end 1 minute to process their audio, then they'd expect to have
	# it start coming out 60s later. Therefore, if we just wait that long to start
	# the output stream, that's probably how it should be anyways! Extra 2 seconds
	# for setup???
	time.sleep(RECORDING_INTERVAL*2 - 2)
	
	# Just like in record_audio, I think the best route here is to follow the same
	# kind of scheme: Create a sounddevice OutputStream and a callback that will take
	# our desired output data and write it to the address provided as a callback
	# argument.

	# Here I create a queue that we will update externally with the playback queue,
	# but that will have results immediately for the callback to pull from (so no
	# risk of waiting on synchronization).
	output_callback_queue = queue.Queue()
	
	# Here's the callback as specified in the sounddevice docs. All we do here is
	# write the most recent value from our internal output_callback_queue to the
	# array at the outdata address.
	def output_callback(outdata: np.ndarray, frames: int, time, status) -> None:
		try:
			output_frames = output_callback_queue.get_nowait()
		except queue.Empty as e:
			print(f"output_callback_queue is empty (no censored audio to playback)")
			# Raising callback abort will terminate the stream before letting its
			# buffers "drain."

			# Could also consider just pushing out zeros here, rather than aborting.
			# Maybe experiment with this--no data for us doesn't mean we're done,
			# necessarily (it might have meant that for this example though).
			raise sd.CallbackAbort from e
		
		assert(len(output_frames) == frames)
		outdata[:] = output_frames

	# Then, define the output stream that will actually take care of playing the
	# audio.
	# Note that the SAMPLE_RATE*0.5 is an arbitrary small number choice--smaller ==
	# more granular, but I don't know how small it's supposed to be.
	output_stream = sd.OutputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=output_callback, blocksize=10)
	# To resolve the issue where it overwrites a massive block of frames when it
	# becomes slightly out of sync, we should be READING (outputting) frame by frame.
	# Therefore, what if I set the blocksize for the output to the default optimal
	# size, and split up the incoming (larger) blocks into chunks of this size. Then
	# the output_callback and properly use the output_callback_queue and get only as
	# many smaller frames as it needs at a time!

	# Open up the stream and infinitely push values from the shared playback queue to
	# the non-shared output_callback_queue.
	try:
		# Preload output_callback_queue.
		track_id, censored_audio = playback_queue.get()
		print(f"Pick up block {track_id} from playback queue.")
		split_audio = np.split(censored_audio, BLOCKSIZE/10, axis=0)
		for small_block in split_audio:
			small_block = np.expand_dims(small_block, axis=1) # Output wants array in form (#samples, 1) rather than squeezed (#sampes,) form.
			output_callback_queue.put(small_block)
		print(f"Playing censored track {track_id}.")

		with output_stream:
			while True:
				track_id, censored_audio = playback_queue.get()
				print(f"Pick up block {track_id} from playback queue.")
				split_audio = np.split(censored_audio, BLOCKSIZE/10, axis=0)
				for small_block in split_audio:
					small_block = np.expand_dims(small_block, axis=1) # Output wants array in form (#samples, 1) rather than squeezed (#sampes,) form.
					output_callback_queue.put(small_block)
				print(f"Playing censored track {track_id}.")
	except Exception as ex:
		print(ex)
	
if __name__ == "__main__":

	try:
		
		#Start threads
		processing_thread = threading.Thread(target=process_audio)
		processing_thread.daemon = True
		processing_thread.start()

		playback_thread = threading.Thread(target=playback_audio)
		playback_thread.daemon = True
		playback_thread.start()

		#Start recording thread
		record_audio()

		#Wait for threads to exit
		recording_queue.join()
		playback_queue.join()

	except KeyboardInterrupt:
		print('\nRecording finished: ')
	except Exception as e:
		print(e)