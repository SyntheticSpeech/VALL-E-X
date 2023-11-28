#!/usr/bin/env python
# coding: utf-8
import os
from utils.generation import SAMPLE_RATE, generate_audio, preload_models
from scipy.io.wavfile import write as write_wav
from utils.prompt_making import make_prompt
# In[4]:
def generate_synthetic_audio(text_prompt, uploaded_file_path):

# download and load all models
     preload_models()

# generate audio from text
     text_prompt = """
     Hello, my name is Nose. And uh, and I like hamburger. Hahaha... But I also have other interests such as playing tactic toast.
     """
     audio_array = generate_audio(text_prompt)

# save audio to disk
     write_wav("vallex_generation.wav", SAMPLE_RATE, audio_array)

###use whisper
     print(f"uploaded file path {uploaded_file_path}")
     absolute_path = os.path.abspath(uploaded_file_path)
     print(f"uploaded file path {absolute_path}")
     make_prompt(name="vtck", audio_prompt_path=absolute_path)

     preload_models()
     text_prompt = """
     Hey, Traveler, Listen to this, This machine has taken my voice, and now it can talk just like me!
     """

     audio_array = generate_audio(text_prompt, prompt="vtck")

     write_wav("cloned.wav", SAMPLE_RATE, audio_array)
     synthetic_audio_path = os.path.abspath("cloned.wav")
     return synthetic_audio_path
