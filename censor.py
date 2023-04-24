import os
import queue
import threading
import transcriber
import time
import recorder

recording_queue = queue.Queue()
playback_queue = queue.Queue()

def record_audio():	
	while True:
		start = time.time()

		# Record 5 seconds of audio
		rec = recorder.AudioRecorder(duration=5)
		recording_thread = threading.Thread(target=rec.run)
		recording_thread.daemon = True
		recording_thread.start()

		time.sleep(5)

		frames = rec.get_frames()

		recording_queue.put(frames)
		print(frames)
		rec.save('test')
		print(f'Obtained audio segment in {time.time() - start} seconds')

def process_audio():
	model_path = os.path.expanduser("./models")
	o_graph, scorer = transcriber.resolve_models(model_path)
	model = transcriber.load_model(o_graph, scorer)

	while True:
		if not recording_queue.empty():
			audio = recording_queue.get()
			transcriber.run_model_on_pcm(audio, 16000, 5, model)
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