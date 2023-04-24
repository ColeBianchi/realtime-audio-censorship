import sounddevice as sd
from scipy.io.wavfile import write
import os
import queue
import threading
import transcriber
import time

fs = 16000  # Sample rate (16kHz)
seconds = 5  # Duration of recording (5 sec)
file_count = 0
save_recordings = True

recording_queue = queue.Queue()
playback_queue = queue.Queue()

def record_audio():
	try:
		while True:
			audio = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
			sd.wait()  # Wait until recording is finished

			if save_recordings:
				if not os.path.exists('recordings'):
					os.makedirs('recordings')
				write('recordings/output.wav', fs, myrecording)

			recording_queue.put(audio)
	except KeyboardInterrupt:
		print('Exiting recording thread')

def process_audio():
	try:
		model_path = os.path.expanduser("./models")
		o_graph, scorer = transcriber.resolve_models(model_path)
		model = transcriber.load_model(o_graph, scorer)

		while True:
			if recording_queue.not_empty():
				audio = recording_queue.get()
				transcriber.run_model_on_pcm(audio, 16000, 5, model)
			else:
				time.sleep(0.1) #sleep for 100ms if no audio found
	except KeyboardInterrupt:
		print('Exiting transcription thread')

#Start Threads
recording_thread = threading.Thread(target=record_audio)
processing_thread = threading.Thread(target=process_audio)

recording_thread.daemon = True
processing_thread.daemon = True

recording_thread.start()
processing_thread.start()

#Wait for threads to exit
recording_queue.join()
playback_queue.join()