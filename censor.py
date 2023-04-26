import queue
import threading
import time
import recorder
import os
import string
import sounddevice as sd

from whisper_transcribe import Transcriber
from speechremover import bleep_audio_segments

recording_queue = queue.Queue()
playback_queue = queue.Queue()

RECORDING_INTERVAL = 4
SAMPLE_RATE = 16000
SAVE_FRAMES = False
BANNING_PROBABILITY = 0.5

def record_audio():
	'''
	Starts a new thread to record audio live and output it as PCM data frames
	Arugments:
		None
	Returns:
		Live output to recorded audio queue in the form of PCM data frames
	'''
	frame_count = 0
	while True:

		# Record audio and split into N second long frames for processing
		rec = recorder.AudioRecorder(duration=RECORDING_INTERVAL)
		rec.set_rate(SAMPLE_RATE)
		recording_thread = threading.Thread(target=rec.run)
		recording_thread.daemon = True
		recording_thread.start()

		time.sleep(RECORDING_INTERVAL)

		# Grab frames from recorder. This will be an ndarray of samples from
		# sounddevice.
		frames = rec.get_frames()
		print(f"Shape of recorded frames: {frames.shape}")
		# Format audio such that it's always one-dimensional.
		frames = frames.squeeze()
		print(f"Squeezed frame shape: {frames.shape}")

		# Add audio frames to shared recording queue
		frames_package = (frame_count, frames)
		recording_queue.put(frames_package)
		print(f"Placed audio segment {frame_count} in recording queue.")
		frame_count += 1

		# Save frames for debugging review
		if SAVE_FRAMES:
			rec.save(f'frame_{frame_count}')

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
		# Check if there is any audio in the recording queue. If so, read it,
		# transcribe it, and process it.
		if not recording_queue.empty():

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

		else:
			print(f"No audio found in recording queue.")
			time.sleep(0.1) # sleep for 100ms if no audio found
			# This may not be necessary, as, if there's nothing in the queue, the
			# thread may just end up waiting on a condition variable internally
			# provided by the threadsafe python queue.

def playback_audio():
	'''
	Scans to see if audio track violates word list and if not plays the track back over the device's speakers
	Arguments:
		None
	Returns:
		None
	'''
	
	while True:
		if not playback_queue.empty():

			# Get audio track and transcription from playback queue
			track_id, censored_audio = playback_queue.get()

			# Take audio and play it with sounddevice.
			print(f"Playing censored track {track_id}.")
			sd.play(censored_audio, samplerate=SAMPLE_RATE)

		else:
			time.sleep(0.1) # sleep for 100ms if no audio found
	


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