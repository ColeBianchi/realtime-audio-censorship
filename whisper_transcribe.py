import whisper
import time
import numpy as np

class Transcriber():
	def __init__(self):
		self.model = whisper.load_model("tiny.en")

	def _format_pcm(self, pcm, hz, seconds):
		audio = np.squeeze(pcm)
		audio = whisper.pad_or_trim(audio)

		return audio

	def run_model_on_pcm(self, pcm, hz=16000, seconds=5):

		audio = self._format_pcm(pcm, hz, seconds)

		transcribe_start = time.time()
		results = self.model.transcribe(audio, word_timestamps=True)
		transcribe_end = time.time()
		print(f"It took {transcribe_end - transcribe_start} to transcribe the size {len(audio)} audio.")

		segments = results["segments"]
		for segment in segments:
			print(f"ID: {segment['id']}\nStart: {segment['start']}, End: {segment['end']}\nText: {segment['text']}\nNoSpeechProb: {segment['no_speech_prob']}\n")
			formatted_words = [f"\t{segment['words'][i]['word']}: Start: {segment['words'][i]['start']}, End: {segment['words'][i]['end']}" for i in range(len(segment["words"]))]
			for word in formatted_words:
				print(word)