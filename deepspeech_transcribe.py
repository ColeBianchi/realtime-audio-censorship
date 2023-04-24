import os
import glob
import time
import subprocess
import shlex
import webrtcvad
import numpy as np
from deepspeech import Model, version
from libs import wavsplit

class Transcriber():
	def __init__():
		model_path = os.path.expanduser("./models")
		o_graph, scorer = transcriber.resolve_models(model_path)
		self.model = transcriber.load_model(o_graph, scorer)

	def run_model_on_pcm(audio, sample_rate, audio_length):
		segments, sample_rate, audio_length = segment_generator(audio, sample_rate, audio_length)

		inference_time = 0
		transcript = ""
		for i, segment in enumerate(segments):
			# Run deepspeech on the chunk that just completed VAD
			print(f"Processing chunk {i}")
			audio = np.frombuffer(segment, dtype=np.int16)
			inference_start = time.time()
			transcript += self.model[0].stt(audio) + " "
			inference_end = time.time() - inference_start
			inference_time += inference_end
			print(f"Inference took {inference_end}s for {audio_length}s audio file.")

		print(f'Finished inference in {inference_time}s.')
		print(f"Transcript:\n{transcript}")


	def segment_generator(audio, sample_rate, audio_length):
		assert sample_rate == 16000, f"Only 16000Hz input WAV files are supported!, Input file is {sample_rate}Hz"
		vad = webrtcvad.Vad(0) #Change this value (0-3) to be the amount to filter out non speech
		frames = wavsplit.frame_generator(30, audio, sample_rate)
		frames = list(frames)
		segments = wavsplit.vad_collector(sample_rate, 30, 300, vad, frames)

		return segments, sample_rate, audio_length 

	def resolve_models(dirName):
		pb = glob.glob(dirName + "/*.pbmm")[0]
		print(f"Found Model: {pb}")

		scorer = glob.glob(dirName + "/*.scorer")[0]
		print(f"Found scorer: {scorer}")

		return pb, scorer

	def load_model(models, scorer):
		model_load_start = time.time()
		ds = Model(models)
		model_load_end = time.time() - model_load_start
		print(f"Loaded model in {model_load_end}s.")

		scorer_load_start = time.time()
		ds.enableExternalScorer(scorer)
		scorer_load_end = time.time() - scorer_load_start
		print(f"Loaded external scorer in {scorer_load_end}s.")

		return [ds, model_load_end, scorer_load_end]