import os
import queue
import threading
import time
import recorder

from whisper_transcribe import Transcriber

recording_queue = queue.Queue()
playback_queue = queue.Queue()

recording_time = 4
rate = 16000

def record_audio():	
	while True:
		start = time.time()

		# Record 5 seconds of audio
		rec = recorder.AudioRecorder(duration=recording_time)
		rec.set_rate(rate)
		recording_thread = threading.Thread(target=rec.run)
		recording_thread.daemon = True
		recording_thread.start()

		time.sleep(recording_time)

		frames = rec.get_frames()

		recording_queue.put(frames)
		rec.save('test')
		print(f'Obtained audio segment in {time.time() - start} seconds')

def process_audio():
	t = Transcriber()

	while True:
		if not recording_queue.empty():
			audio = recording_queue.get()
			t.run_model_on_pcm(audio, rate, recording_time)
		else:
			time.sleep(0.1) #sleep for 100ms if no audio found

#Start processing thread
processing_thread = threading.Thread(target=process_audio)
processing_thread.daemon = True
processing_thread.start()

#Start recording thread
record_audio()


#Wait for threads to exit
recording_queue.join()
playback_queue.join()