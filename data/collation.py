from pathlib import Path
from typing import List, Tuple

import numpy as np
import torch

from utils import SymbolTable


class TextTokenCollater:
    """Collate list of text tokens

    Map sentences to integers. Sentences are padded to equal length.
    Beginning and end-of-sequence symbols can be added.

    Example:
        >>> token_collater = TextTokenCollater(text_tokens)
        >>> tokens_batch, tokens_lens = token_collater(text)

    Returns:
        tokens_batch: IntTensor of shape (B, L)
            B: batch dimension, number of input sentences
            L: length of the longest sentence
        tokens_lens: IntTensor of shape (B,)
            Length of each sentence after adding <eos> and <bos>
            but before padding.
    """

    def __init__(
        self,
        text_tokens: List[str],
        add_eos: bool = True,
        add_bos: bool = True,
        pad_symbol: str = "<pad>",
        bos_symbol: str = "<bos>",
        eos_symbol: str = "<eos>",
        mode: bool = True, #True for training, false for inference
    ):
        self.pad_symbol = pad_symbol

        self.add_eos = add_eos
        self.add_bos = add_bos

        self.bos_symbol = bos_symbol
        self.eos_symbol = eos_symbol

        unique_tokens = (
            [pad_symbol]
            + ([bos_symbol] if add_bos else [])
            + ([eos_symbol] if add_eos else [])
            + sorted(text_tokens)
        )

        self.token2idx = {token: idx for idx, token in enumerate(unique_tokens)}
        self.idx2token = [token for token in unique_tokens]

        self.mode = mode

    def index(
        self, tokens_list: List[str]
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        seqs, seq_lens = [], []
        for tokens in tokens_list:
            assert (
                all([True if s in self.token2idx else False for s in tokens])
                is True
            )
            seq = (
                ([self.bos_symbol] if self.add_bos else [])
                + list(tokens)
                + ([self.eos_symbol] if self.add_eos else [])
            )
            seqs.append(seq)
            seq_lens.append(len(seq))

        max_len = max(seq_lens)
        for k, (seq, seq_len) in enumerate(zip(seqs, seq_lens)):
            seq.extend([self.pad_symbol] * (max_len - seq_len))

        tokens = torch.from_numpy(
            np.array(
                [[self.token2idx[token] for token in seq] for seq in seqs],
                dtype=np.int64,
            )
        )
        tokens_lens = torch.IntTensor(seq_lens)

        return tokens, tokens_lens

    def __call__(self, texts: List[str]) -> Tuple[torch.Tensor, torch.Tensor]:
        tokens_seqs = [[p for p in text] for text in texts]
        max_len = len(max(tokens_seqs, key=len))

        seqs = [
            ([self.bos_symbol] if self.add_bos else [])
            + list(seq)
            + ([self.eos_symbol] if self.add_eos else [])
            + [self.pad_symbol] * (max_len - len(seq))
            for seq in tokens_seqs
        ]

        '''
        由于下面initialize Collator方式的不同, plachtaa的这一步的seq和lifeitong不一样
        训练还是选择使用了后者
        '''

        if self.mode:
            tokens_batch = torch.from_numpy(
                np.array(
                    [[self.token2idx[token] for token in seq] for seq in seqs],
                    dtype=np.int64,
                )
            )
        else:
            tokens_batch = torch.from_numpy(
                np.array(
                    [seq for seq in seqs],
                    dtype=np.int64,
                )
            )
        tokens_lens = torch.IntTensor(
            [
                len(seq) + int(self.add_eos) + int(self.add_bos)
                for seq in tokens_seqs
            ]
        )

        return tokens_batch, tokens_lens

'''
Plachtaa这个函数的input argument不要了, 取决于inference的时候要不要用训练数据集的symboltable
这里并不清楚tradeoff, 选择保留两者
'''
def get_text_token_collater() -> TextTokenCollater:
    collater = TextTokenCollater(
        ['0'], add_bos=False, add_eos=False, pad_symbol = '0', mode=False
    )
    return collater

def get_text_token_collater_with_record(text_tokens_file: str) -> TextTokenCollater:
    text_tokens_path = Path(text_tokens_file)
    unique_tokens = SymbolTable.from_file(text_tokens_path)
    collater = TextTokenCollater(
        unique_tokens.symbols, add_bos=True, add_eos=True, mode=True
    )
    return collater
