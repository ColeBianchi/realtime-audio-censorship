import string
import numpy as np
from typing import Tuple
import whisper
import wavio
import time

def _convert_timestamp(timestamp: float):
    """Function that converts a floating point timestamp to a tuple, where the first
    vialue is seconds and the second value is milliseconds. """
    return (int(timestamp), int((timestamp*1000)%1000))

def _timestamp_to_index(audio_samplerate: int, timestamp: float) -> int:
    """Function that takes a timestamp from a provided audio array and returns the
    index of the sample that timestamp corresponds to. 
    
    Parameters
    ----------
    audio_samplerate: int
        The sample rate of the audio array provided above. This is necessary to
        understand how time maps to the provided audio data.
    
    timestamp: float
        The timestamp from the audio that you want the corresponding sample of. Note:
        this should be provided in format "s.ms" s = # seconds and  = #
        milliseconds.

    Returns
    -------
    An integer index from the provided audio_ndarray that most closely corresponds
    with the provided timestamp."""

    # Convert the string timestamp to milliseconds.
    seconds, millis = _convert_timestamp(timestamp=timestamp)

    # Compute the offset from the beginning of the audio_ndarray, which is more
    # accurately called a "sample array," where each entry in the numpy array is a
    # sample.
    offset = int(seconds*audio_samplerate + (millis/1000)*audio_samplerate)

    return offset

def _get_num_samples_from_timestamps(audio_samplerate: int, start_timestamp: float, end_timestamp: float) -> int:
    """Function that returns the number of samples covered by a word, provided its
    timestamps as strs.

    Parameters
    ----------
    start_timestamp: float
        The starting timestamp from the audio that you want the corresponding sample
        of. This should be provided in formation: "s.ms"

    end_timestamp: float
        The ending timestamp from the audio that you want the corresponding sample
        of. This should be provided in formation: "s.ms"

    Returns
    -------
    The integer number of audio sample values that correspond with this word.
    """
    return _timestamp_to_index(audio_samplerate, end_timestamp) - _timestamp_to_index(audio_samplerate, start_timestamp)

def _generate_1000hz_bleep(num_samples: int, sample_rate: int) -> np.ndarray:
    """Function that generates a 1000 Hz sine wave that spans the number of samples
    you provide. 1000 Hz chosen, as this is the most commonly used frequency for
    profanity censoring sounds. Note that the audio generated has only a 16-bit
    sample depth.

    Parameters
    ----------
    num_samples: str
        The number of samples this sine wave will span / be comprised of.
    sample_rate: int
        The number of samples per second.
    
    Returns
    ----------
    An ndarray of length num_samples whose values create a 1000 Hz sine wave.
    """
    
    duration_s = num_samples/sample_rate
    t = np.linspace(0, duration_s, num_samples, False)
    note = np.sin(1000 * t * 2 * np.pi)
    # Ensure that highest value is in 16-bit range
    audio:np.ndarray = note * (2**15 - 1) / np.max(np.abs(note))
    # Convert to 16-bit data
    audio = audio.astype(np.int16)
    return audio

def _generate_silence(num_samples: int) -> np.ndarray:
    """Returns blank filler audio."""
    return np.zeros(num_samples).astype(np.int16)

def replace_audio_segment(audio_ndarray: np.ndarray, audio_samplerate: int, start_timestamp: float, end_timestamp: float, replacement_audio: np.ndarray) -> np.ndarray:
    """Takes in a numpy array of audio samples and replaces all values between the
    start and end with the provided replacement_audio."""

    start_index = _timestamp_to_index(audio_samplerate, start_timestamp)
    end_index = _timestamp_to_index(audio_samplerate, end_timestamp)
    replace_indices = np.arange(start=start_index, stop=end_index, step=1)
    try:
        audio_ndarray[replace_indices] = replacement_audio
    except Exception as e:
        print(f"Audio shape: {audio_ndarray.shape} vs sinewave shape: {replacement_audio.shape}")
        print(f"Replacement indices size? Maybe those were too big? {replace_indices.shape}")
        print(e)

    return audio_ndarray

def bleep_audio_segment(audio_ndarray: np.ndarray, audio_samplerate: int, start_timestamp: float, end_timestamp: float) -> np.ndarray:
    """Shortcut function to call without having to generate your own replacement
    signal."""
    
    num_samples = _get_num_samples_from_timestamps(audio_samplerate=audio_samplerate, start_timestamp=start_timestamp, end_timestamp=end_timestamp)
    if num_samples == 0:
        return audio_ndarray
    bleep = _generate_1000hz_bleep(num_samples, sample_rate=audio_samplerate)
    return replace_audio_segment(audio_ndarray=audio_ndarray, audio_samplerate=audio_samplerate, start_timestamp=start_timestamp, end_timestamp=end_timestamp, replacement_audio=bleep)

def replace_audio_segments(audio_ndarray: np.ndarray, audio_samplerate:int, segment_times: list, replacement_tones: list) -> np.ndarray:
    """Basically calls the above replace audio functions but multiple times across an
    array of start and stop times. Implemented this way such that the ndarray is
    being operated on all at once so that it doesn't have to be moved in and out of
    cache constantly."""

    for i, start_timestamp, end_timestamp in enumerate(segment_times):
        audio_ndarray = replace_audio_segment(audio_ndarray, audio_samplerate, start_timestamp, end_timestamp, replacement_tones[i])
    return audio_ndarray

def bleep_audio_segments(audio_ndarray: np.ndarray, audio_samplerate: int, segment_times: list) -> np.ndarray:
    """Function that takes in a list of segment times and replaces the audio in those
    segments with a 1000Hz bleep tone."""

    for start_timestamp, end_timestamp in segment_times:
        print(f"\tCensoring word starting at {start_timestamp} and ending at {end_timestamp}")
        audio_ndarray = bleep_audio_segment(audio_ndarray=audio_ndarray, audio_samplerate=audio_samplerate, start_timestamp=start_timestamp, end_timestamp=end_timestamp)
    return audio_ndarray

def censor_original_audio(original_audio: np.ndarray, original_audio_samplerate: int, model_audio: np.ndarray, model_audio_samplerate: int,
                          blacklist: list):
    """Function that bleeps out portions of the original_audio based on blacklisted
    words transcribed from the provided model_audio.
    
    Parameters
    ----------
    original_audio: np.ndarray
        Your original quality audio provided as a numpy ndarray.
    original_audio_samplerate:
        The sample rate of the original audio.
    model_audio:
        The potentially downsampled, lower quality audio that will be used to feed
        the transcription model.
    model_audio_samplerate:
        The sample rate of the downsampled model audio.
    blacklist: List(str)
        List of words that should be censored/removed/replaced in the audio.
    
    Returns
    ----------
    An ndarray of the ORIGINAL audio with regions corresponding to blacklisted words
    "bleeped out."
    """

    print("Beginning transcription process on audio")
    transcribe_start = time.time()
    # First, run audio ndarray through whisper to get transcription.
    model = whisper.load_model("base.en")
    results = model.transcribe(model_audio, word_timestamps=True)
    transcribe_end = time.time()
    print(f"Transcription completed in {transcribe_end - transcribe_start}s!")

    print("Transcription results:")
    segments = results["segments"]
    for segment in segments:
        print(f"ID: {segment['id']}\nStart: {segment['start']}, End: {segment['end']}\nText: {segment['text']}\nNoSpeechProb: {segment['no_speech_prob']}\n")
        formatted_words = [f"\t{segment['words'][i]['word']}: Start: {segment['words'][i]['start']}, End: {segment['words'][i]['end']}" for i in range(len(segment["words"]))]
        for word in formatted_words:
            print(word)
    print()

    # Translator used to clean detected words for list queries
    translator = str.maketrans('', '', string.punctuation)

    print("Searching for blacklisted words in transcription")
    # Parse results for blacklisted words. Append their start and end timestamps as
    # tuples as you find them.
    blacklisted_segment_times = []
    segments = results["segments"]
    for segment in segments:
        for word_dict in segment["words"]:
            word = word_dict["word"].translate(translator).lower().strip()
            if word in blacklist:
                print(f"\tFound blacklisted word \"{word}\" in audio at {word_dict['start']}-->{word_dict['end']}!")
                blacklisted_segment_times.append((word_dict["start"], word_dict["end"]))
    print()

    # Now, pass that list onto another function to remove it from the original audio.
    print("Censoring words in audio")
    censor_start = time.time()
    censored_audio = bleep_audio_segments(audio_ndarray=original_audio, audio_samplerate=original_audio_samplerate, segment_times=blacklisted_segment_times)
    censor_end = time.time()
    print(f"Censoring complete! It took {censor_end - censor_start}s to censor {len(blacklisted_segment_times)} blacklisted words from the provided audio.")

    return censored_audio


def bleep_blacklisted_audio(audio: np.ndarray, sample_rate: int, blacklist: list) -> np.ndarray:
    """Function that bleeps out the portions of the provided audio that correspond
    with words appearing on the provided blacklist.
    
    Parameters
    ----------

    audio: np.ndarray
        Audio you wish to be censored based on the provided blacklist. Audio should
        be provided as a one-dimensional numpy array, such that each entry
        corresponds with a single sample.
    sample_rate: int
        The rate at which the provided audio was sampled at. This really just tells
        the function how many samples one second of audio is made up of (so that it
        can modify it based on timestamps).
    blacklist: List(str)
        A list of blacklisted words as strings. Basically, just a list of words you
        want bleeped out if they appear in the transcription of the audio.

    Returns
    ----------
    An ndarray of the provided audio with regions corresponding to blacklisted words
    "bleeped out."
    """
    pass



def remove_speech(audio: np.ndarray, sample_rate: int):
    """More general function that looks for segments from whisper that are classified
    as speech and mutes the entire audio sequence during those times."""
    pass

if __name__ == "__main__":
    
    blacklist = []
    blacklist_filepath = r"./badwords.txt"
    # Load blacklist from file, one phrase/word per line.
    with open(blacklist_filepath, "r") as blf:
        for line in blf:
            blacklist.append(line.strip())

    # Open audio from a file.
    recording_path = r"C:\\users\nlitz88\Downloads\youtubedl\broccoli.wav"
    output_path = r"C:\\users\nlitz88\Downloads\youtubedl\broccoli_censored.wav"

    # Load the original audio as numpy array.
    wav = wavio.read(recording_path)
    original_samplerate = whisper.audio.SAMPLE_RATE
    # original_depth = wav.sampwidth
    original_audio = whisper.load_audio(recording_path)
    
    # Only feed in 16 KHz audio file into whisper--don't need to use full rate
    # original audio--only need to modify the original audio.
    # downsampled_audio = whisper.audio.load_audio(recording_path)
    # downsampled_samplerate = whisper.audio.SAMPLE_RATE
    downsampled_audio = original_audio
    downsampled_samplerate = original_samplerate
    
    # Begin censoring process
    censored_audio = censor_original_audio(original_audio=original_audio, original_audio_samplerate=original_samplerate,
                                           model_audio=downsampled_audio, model_audio_samplerate=downsampled_samplerate,
                                           blacklist=blacklist)

    wavio.write(output_path, censored_audio, original_samplerate, sampwidth=4)