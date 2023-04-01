import os
import glob
import time
import subprocess
import shlex
import webrtcvad
import numpy as np
from deepspeech import Model, version
from libs import wavsplit

def run_model_live():
	model_path = os.path.expanduser("./models")
	o_graph, scorer = resolve_models(model_path)
	model = load_model(o_graph, scorer)

	model_stream = model[0].createStream()
	recording_process = subprocess.Popen(shlex.split('rec -q -V0 -e signed -L -c 1 -b 16 -r 16k -t raw - gain -2'), stdout=subprocess.PIPE, bufsize=0)

	try:
		rolling_count = 0
		print("Recording has start, you can now start talking:")
		while True:
			data = recording_process.stdout.read(512)
			model_stream.feedAudioContent(np.frombuffer(data, np.int16))

			rolling_count += 1

			if rolling_count == 75:
				print('Transcription: ', model_stream.finishStream())
				model_stream = model[0].createStream()
				rolling_count = 0


	except KeyboardInterrupt:
		recording_process.terminate()
		recording_process.wait()

def run_model_on_file(wav_path):
	model_path = os.path.expanduser("./models")
	o_graph, scorer = resolve_models(model_path)
	model = load_model(o_graph, scorer)

	segments, sample_rate, audio_length = segment_generator(wav_path)

	inference_time = 0
	transcript = ""
	for i, segment in enumerate(segments):
		# Run deepspeech on the chunk that just completed VAD
		print(f"Processing chunk {i}")
		audio = np.frombuffer(segment, dtype=np.int16)
		inference_start = time.time()
		transcript += model[0].stt(audio) + " "
		inference_end = time.time() - inference_start
		inference_time += inference_end
		print(f"Inference took {inference_end}s for {audio_length}s audio file.")

	print(f'Finished inference in {inference_time}s.')
	print(f"Transcript:\n{transcript}")


def segment_generator(wavFile):
    audio, sample_rate, audio_length = wavsplit.read_wave(wavFile)
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

run_model_on_file("./test_wavs/gridspace-stanford-harper-valley/data/audio/agent/de6e39536c314488_16k.wav")