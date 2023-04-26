import whisper
import time
import numpy as np

class Transcriber():
	'''
	Transcription class that runs OpenAI Whisper model and converts raw PCM data to labeled text segments
	'''
	def __init__(self):
		self.model = whisper.load_model("tiny.en")

	def _format_pcm(self, pcm):
		'''
		Accepts raw PCM data and formats it correctly for the Whisper model, max length of 30 seconds
		Arguments:
			pcm -- Raw PCM data frame
		Returns:
			np data array of trimmed audio for whisper model
		'''
		audio = np.squeeze(pcm)
		audio = whisper.pad_or_trim(audio)

		return audio

	def run_model_on_pcm(self, pcm):
		'''
		Runs whisper model on raw PCM data and returns labeled words within audio segment
		Arguments:
			pcm -- Raw PCM data frame
		Returns:
			Array of segments of labeled words
		'''
		audio = self._format_pcm(pcm)

		transcribe_start = time.time()
		results = self.model.transcribe(audio, word_timestamps=True)
		transcribe_end = time.time()

		return results["segments"]