import queue
import threading
import time
import recorder

from whisper_transcribe import Transcriber

recording_queue = queue.Queue()
playback_queue = queue.Queue()

recording_time = 4
rate = 16000
save_frames = False

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
		start = time.time()

		# Record audio and split into N second long frames for processing
		rec = recorder.AudioRecorder(duration=recording_time)
		rec.set_rate(rate)
		recording_thread = threading.Thread(target=rec.run)
		recording_thread.daemon = True
		recording_thread.start()

		time.sleep(recording_time)

		frames = rec.get_frames()

		# Add audio frames to shared recording queue
		frames_package = (frame_count, frames)
		recording_queue.put(frames_package)

		frame_count =+ 1

		# Save frames for debugging review
		if save_frames:
			rec.save(f'frame_{frame_count}')

		print(f'Obtained audio segment in {time.time() - start} seconds')

def process_audio():
	'''
	Creates a transciber model thread that converts PCM data frames from the shared queue into transcribed text
	Arguments:
		None
	Returns:
		Transcribed audio segments with ID's pushed into shared processed queue
	'''
	t = Transcriber()

	while True:
		if not recording_queue.empty():

			# Get audio track from shared recording queue
			track_id, audio = recording_queue.get()

			# Transcribe audio track
			segments = t.run_model_on_pcm(audio)

			# Add transcription to playback_queue
			segments_package = (track_id, segments, audio)
			playback_queue.put(segments_package)
		else:
			time.sleep(0.1) # sleep for 100ms if no audio found

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
			track_id, segments, audio = playback_queue.get()

			# Display transcription details for audio track
			for segment in segments:
				print(f"ID: {segment['id']}\nStart: {segment['start']}, End: {segment['end']}\nText: {segment['text']}\nNoSpeechProb: {segment['no_speech_prob']}\n")
				formatted_words = [f"\t{segment['words'][i]['word']}: Start: {segment['words'][i]['start']}, End: {segment['words'][i]['end']}" for i in range(len(segment["words"]))]
				for word in formatted_words:
					print(word)

			# Scan transcription for banned words

			# Playback clean audio segments

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