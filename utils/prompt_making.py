import os
import torch
import torchaudio
import logging
import whisper
import time
# [Hao] Removed langid requirement, langid is always en in our case
# import langid
# langid.set_languages(['en', 'zh', 'ja'])

import numpy as np
from data.tokenizer import (
    AudioTokenizer,
    tokenize_audio,
)
from data.collation import get_text_token_collater
from utils.g2p import PhonemeBpeTokenizer

from macros import *

text_tokenizer = PhonemeBpeTokenizer(tokenizer_path="./utils/g2p/bpe_69.json")
text_collater = get_text_token_collater()

device = torch.device("cpu")
if torch.cuda.is_available():
    device = torch.device("cuda", 0)
if torch.backends.mps.is_available():
    device = torch.device("mps")
codec = AudioTokenizer(device)

if not os.path.exists("./whisper/"): os.mkdir("./whisper/")
whisper_model = None

@torch.no_grad()
def transcribe_one(model, audio_path):
    t1 = time.perf_counter(), time.process_time()
    # load audio and pad/trim it to fit 30 seconds
    audio = whisper.load_audio(audio_path)
    audio = whisper.pad_or_trim(audio)

    # make log-Mel spectrogram and move to the same device as the model
    mel = whisper.log_mel_spectrogram(audio).to(model.device)

    # detect the spoken language
    # _, probs = model.detect_language(mel)
    # print(f"Detected language: {max(probs, key=probs.get)}")
    # lang = max(probs, key=probs.get)
    # decode the audio
    options = whisper.DecodingOptions(temperature=1.0, best_of=5, fp16=False if device == torch.device("cpu") else True, sample_len=150)
    result = whisper.decode(model, mel, options)

    # print the recognized text
    print(result.text)

    text_pr = result.text
    if text_pr.strip(" ")[-1] not in "?!.,。，？！。、":
        text_pr += "."
    t2 = time.perf_counter(), time.process_time()
    print(f"[Transcribe One] Real time: {t2[0] - t1[0]:.2f} seconds")
    print(f"[Transcribe One] CPU time: {t2[1] - t1[1]:.2f} seconds")
    return text_pr

def make_prompt(name, audio_prompt_path, transcript=None):
    global model, text_collater, text_tokenizer, codec
    wav_pr, sr = torchaudio.load(audio_prompt_path)
    # check length
    if wav_pr.size(-1) / sr > 15:
        raise ValueError(f"Prompt too long, expect length below 15 seconds, got {wav_pr / sr} seconds.")
    if wav_pr.size(0) == 2:
        wav_pr = wav_pr.mean(0, keepdim=True)
    text_pr, lang_pr = make_transcript(name, wav_pr, sr, transcript)

    # tokenize audio
    encoded_frames = tokenize_audio(codec, (wav_pr, sr))
    audio_tokens = encoded_frames[0][0].transpose(2, 1).cpu().numpy()

    # tokenize text
    phonemes, langs = text_tokenizer.tokenize(text=f"{text_pr}".strip())
    text_tokens, enroll_x_lens = text_collater(
        [
            phonemes
        ]
    )

    message = f"Detected language: {lang_pr}\n Detected text {text_pr}\n"
    print(message)

    # save as npz file
    save_path = os.path.join("./customs/", f"{name}.npz")
    np.savez(save_path, audio_tokens=audio_tokens, text_tokens=text_tokens, lang_code=lang2code[lang_pr])
    logging.info(f"Successful. Prompt saved to {save_path}")

def download_whisper():
    global whisper_model
    if whisper_model is None:
        logging.info(f"Downloading whisper model")
        whisper_model = whisper.load_model("medium", download_root=os.path.join(os.getcwd(), "whisper"))
        whisper_model.to(device)

def make_transcript(name, wav, sr, transcript=None):
    t1 = time.perf_counter(), time.process_time()
    if not isinstance(wav, torch.FloatTensor):
        wav = torch.tensor(wav)
    if wav.abs().max() > 1:
        wav /= wav.abs().max()
    if wav.size(-1) == 2:
        wav = wav.mean(-1, keepdim=False)
    if wav.ndim == 1:
        wav = wav.unsqueeze(0)
    assert wav.ndim and wav.size(0) == 1
    lang = "en" # Fix to English
    if transcript is None or transcript == "":
        logging.info("Transcript not given, using Whisper...")
        assert whisper_model is not None
        torchaudio.save(f"./prompts/{name}.wav", wav, sr)
        transcript = transcribe_one(whisper_model, f"./prompts/{name}.wav")
        os.remove(f"./prompts/{name}.wav")
        whisper_model.cpu()
    # else:
    #     text = transcript
        # lang, _ = langid.classify(text)
        # lang_token = lang2token[lang]
        # text = lang_token + text + lang_token
    lang_token = lang2token[lang]
    text = lang_token + transcript + lang_token

    torch.cuda.empty_cache()
    t2 = time.perf_counter(), time.process_time()
    print(f"[make_transcript] Real time: {t2[0] - t1[0]:.2f} seconds")
    print(f"[make_transcript] CPU time: {t2[1] - t1[1]:.2f} seconds")
    return text, lang
