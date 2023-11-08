#!/usr/bin/env python3
# Copyright    2023                            (authors: Feiteng Li)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Phonemize Text and EnCodec Audio.

Usage example:
    python3 bin/infer.py \
        --decoder-dim 128 --nhead 4 --num-decoder-layers 4 --model-name valle \
        --text-prompts "Go to her." \
        --audio-prompts ./prompts/61_70970_000007_000001.wav \
        --output-dir infer/demo_valle_epoch20 \
        --checkpoint exp/valle_nano_v2/epoch-20.pt

"""
import argparse
import logging
import os
from pathlib import Path
import langid
langid.set_languages(['en', 'zh', 'ja'])

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import torch
import torchaudio
from icefall.utils import AttributeDict, str2bool
from vocos import Vocos
from scipy.io.wavfile import write as write_wav

from data import (
    AudioTokenizer,
    TextTokenizer,
    tokenize_audio,
    tokenize_text,
)
from data.collation import get_text_token_collater_with_record, get_text_token_collater
from models import get_model
from macros import *
from utils.g2p import PhonemeBpeTokenizer

def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--text-prompts",
        type=str,
        default="",
        help="Text prompts which are separated by |.",
    )

    parser.add_argument(
        "--audio-prompts",
        type=str,
        default="",
        help="Audio prompts which are separated by | and should be aligned with --text-prompts.",
    )

    parser.add_argument(
        "--text",
        type=str,
        default="To get up and running quickly just follow the steps below.",
        help="Text to be synthesized.",
    )

    # model
    # add_model_arguments(parser)
    # parser.add_argument(
    #     "--text-tokens",
    #     type=str,
    #     default="data/tokenized/unique_text_tokens.k2symbols",
    #     help="Path to the unique text tokens file.",
    # )

    parser.add_argument(
        "--text-extractor",
        type=str,
        default="espeak",
        help="espeak or pypinyin or pypinyin_initials_finals",
    )

    parser.add_argument(
        "--checkpoint",
        type=str,
        default="exp/vallf_nano_full/checkpoint-100000.pt",
        help="Path to the saved checkpoint.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("infer/demo"),
        help="Path to the tokenized files.",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=-100,
        help="Whether AR Decoder do top_k(if > 0) sampling.",
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=1.0,
        help="The temperature of AR Decoder top_k sampling.",
    )

    parser.add_argument(
        "--continual",
        type=str2bool,
        default=False,
        help="Do continual task.",
    )

    parser.add_argument(
        "--name",
        type=str,
        default="hao",
        help="Name of the prompt speaker",
    )

    return parser.parse_args()


def load_model(checkpoint, device):
    if not checkpoint:
        return None

    checkpoint = torch.load(checkpoint, map_location=device)

    args = AttributeDict(checkpoint)
    model = get_model(args)

    missing_keys, unexpected_keys = model.load_state_dict(
        checkpoint["model"], strict=True
    )
    assert not missing_keys
    model.to(device)
    model.eval()

    text_tokens = args.text_tokens

    return model, text_tokens

def make_transcript(name, wav, sr, transcript=None):
    if not isinstance(wav, torch.FloatTensor):
        wav = torch.tensor(wav)
    if wav.abs().max() > 1:
        wav /= wav.abs().max()
    if wav.size(-1) == 2:
        wav = wav.mean(-1, keepdim=False)
    if wav.ndim == 1:
        wav = wav.unsqueeze(0)
    assert wav.ndim and wav.size(0) == 1
    #Hao deleted whisper processing
    text = transcript
    lang, _ = langid.classify(text)
    lang_token = lang2token[lang]
    text = lang_token + text + lang_token

    torch.cuda.empty_cache()
    return text, lang

@torch.no_grad()
def main():
    args = get_args()
    device = torch.device("cpu")
    if torch.cuda.is_available():
        device = torch.device("cuda", 0)
    model, _ = load_model(args.checkpoint, device)

    text_collater = get_text_token_collater()
    # text_tokenizer = TextTokenizer(backend=args.text_extractor)
    text_tokenizer = PhonemeBpeTokenizer(tokenizer_path="./utils/g2p/bpe_69.json")
    audio_tokenizer = AudioTokenizer()
    vocos = Vocos.from_pretrained('charactr/vocos-encodec-24khz').to(device)

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    wav_pr, sr = torchaudio.load(args.audio_prompts)
    # check length
    if wav_pr.size(-1) / sr > 15:
        raise ValueError(f"Prompt too long, expect length below 15 seconds, got {wav_pr / sr} seconds.")
    if wav_pr.size(0) == 2:
        wav_pr = wav_pr.mean(0, keepdim=True)
    text_pr, lang_pr = make_transcript(args.name, wav_pr, sr, args.text_prompts)
    print(f"Detected language: {lang_pr}\n Detected text {text_pr}")

    # tokenize audio
    encoded_frames = tokenize_audio(audio_tokenizer, (wav_pr, sr))
    audio_prompts = encoded_frames[0][0].transpose(2, 1).cpu().numpy()

    # tokenize transcript text
    phonemes, langs = text_tokenizer.tokenize(text=f"{text_pr}".strip())
    text_prompts, enroll_x_lens = text_collater(
        [
            phonemes
        ]
    )

    audio_prompts = torch.tensor(audio_prompts).type(torch.int32).to(device)
    text_prompts = torch.tensor(text_prompts).type(torch.int32)

    # process text prompt
    language='en'
    accent='no-accent'
    #text_prompts = " ".join(args.text_prompts.split("|"))
    text = args.text.replace("\n", "").strip(" ")
    # detect language
    if language == "auto":
        language = langid.classify(text)[0]
    lang_token = lang2token[language]
    lang = token2lang[lang_token]
    text = lang_token + text + lang_token

    # tokenize synthesize text
    enroll_x_lens = text_prompts.shape[-1]
    print(f"synthesize text: {text}")
    phone_tokens, langs = text_tokenizer.tokenize(text=f"_{text}".strip())
    text_tokens, text_tokens_lens = text_collater(
        [
            phone_tokens
        ]
    )
    text_tokens = torch.cat([text_prompts, text_tokens], dim=-1)
    text_tokens_lens += enroll_x_lens
    # accent control
    lang = lang if accent == "no-accent" else token2lang[langdropdown2token[accent]]
    encoded_frames = model.inference(
        text_tokens.to(device),
        text_tokens_lens.to(device),
        audio_prompts,
        enroll_x_lens=enroll_x_lens,
        top_k=-100,
        temperature=1,
        prompt_language=lang_pr,
        text_language=langs if accent == "no-accent" else lang,
    )
    # Decode with Vocos
    frames = encoded_frames.permute(2,0,1)
    features = vocos.codes_to_features(frames)
    samples = vocos.decode(features, bandwidth_id=torch.tensor([2], device=device))

    samples = samples.squeeze().cpu().numpy()
    write_wav(f"{args.output_dir}/0.wav", SAMPLE_RATE, samples)
    # audio_prompts = []
    # if args.audio_prompts:
    #     for n, audio_file in enumerate(args.audio_prompts.split("|")):
    #         # Hao: 前置计算
    #         wav_pr, sr = torchaudio.load(audio_file)
    #         if wav_pr.size(-1) / sr > 15:
    #             raise ValueError(f"Prompt too long, expect length below 15 seconds, got {wav_pr / sr} seconds.")
    #         if wav_pr.size(0) == 2:
    #             wav_pr = wav_pr.mean(0, keepdim=True)
    #         encoded_frames = tokenize_audio(audio_tokenizer, (wav_pr, sr))
    #         audio_prompts.append(encoded_frames[0][0])

    #     assert len(args.text_prompts.split("|")) == len(audio_prompts)
    #     audio_prompts = torch.concat(audio_prompts, dim=-1).transpose(2, 1)
    #     audio_prompts = audio_prompts.to(device)

    # if os.path.isfile(args.text):  # for demos
    #     # https://github.com/lifeiteng/lifeiteng.github.com/blob/main/valle/prepare.py
    #     with open(args.text) as f:
    #         for line in f:
    #             fields = line.strip().split("\t")
    #             assert len(fields) == 4
    #             prompt_text, prompt_audio, text, audio_path = fields
    #             logging.info(f"synthesize text: {text}")
    #             text_tokens, text_tokens_lens = text_collater(
    #                 [
    #                     tokenize_text(
    #                         text_tokenizer, text=f"{prompt_text} {text}".strip()
    #                     )
    #                 ]
    #             )
    #             _, enroll_x_lens = text_collater(
    #                 [
    #                     tokenize_text(
    #                         text_tokenizer, text=f"{prompt_text}".strip()
    #                     )
    #                 ]
    #             )

    #             audio_prompts = tokenize_audio(audio_tokenizer, prompt_audio)
    #             audio_prompts = audio_prompts[0][0].transpose(2, 1).to(device)

    #             # synthesis
    #             encoded_frames = model.inference(
    #                 text_tokens.to(device),
    #                 text_tokens_lens.to(device),
    #                 audio_prompts,
    #                 enroll_x_lens=enroll_x_lens,
    #                 top_k=args.top_k,
    #                 temperature=args.temperature,
    #                 prompt_language="en",
    #                 text_language="en",
    #             )

    #             samples = audio_tokenizer.decode(
    #                 [(encoded_frames.transpose(2, 1), None)]
    #             )
    #             # store
    #             torchaudio.save(audio_path, samples[0].cpu(), 24000)
    #     return

    # for n, text in enumerate(args.text.split("|")):
    #     logging.info(f"synthesize text: {text}")
    #     text_tokens, text_tokens_lens = text_collater(
    #         [
    #             tokenize_text(
    #                 text_tokenizer, text=f"{text_prompts} {text}".strip()
    #             )
    #         ]
    #     )

    #     # synthesis
    #     if args.continual:
    #         assert text == ""
    #         encoded_frames = model.continual(
    #             text_tokens.to(device),
    #             text_tokens_lens.to(device),
    #             audio_prompts,
    #         )
    #     else:
    #         enroll_x_lens = None
    #         if text_prompts:
    #             _, enroll_x_lens = text_collater(
    #                 [
    #                     tokenize_text(
    #                         text_tokenizer, text=f"{text_prompts}".strip()
    #                     )
    #                 ]
    #             )
    #         encoded_frames = model.inference(
    #             text_tokens.to(device),
    #             text_tokens_lens.to(device),
    #             audio_prompts,
    #             enroll_x_lens=enroll_x_lens,
    #             top_k=args.top_k,
    #             temperature=args.temperature,
    #             prompt_language="en",
    #             text_language="en",
    #         )

    #     if audio_prompts != []:
    #         samples = audio_tokenizer.decode(
    #             [(encoded_frames.transpose(2, 1), None)]
    #         )
    #         # store
    #         torchaudio.save(
    #             f"{args.output_dir}/{n}.wav", samples[0].cpu(), 24000
    #         )
    #     else:  # Transformer
    #         pass


torch.set_num_threads(1)
torch.set_num_interop_threads(1)
torch._C._jit_set_profiling_executor(False)
torch._C._jit_set_profiling_mode(False)
torch._C._set_graph_executor_optimize(False)
if __name__ == "__main__":
    formatter = (
        "%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s"
    )
    logging.basicConfig(format=formatter, level=logging.INFO)
    main()
