from __future__ import annotations

from tokenizers import Tokenizer, Regex, decoders, models, pre_tokenizers, processors


# Reproduces the four-stage pre-tokenizer embedded in the published
# deepseek-ai/DeepSeek-V3 tokenizer.json. The CJK branch is retained so the
# tokenizer remains well-defined for incidental multilingual text.
DIGIT_PATTERN = r"\p{N}{1,3}"
CJK_PATTERN = r"[一-龥぀-ゟ゠-ヿ]+"
CATEGORY_PATTERN = (
    r"[!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~][A-Za-z]+"
    r"|[^\r\n\p{L}\p{P}\p{S}]?[\p{L}\p{M}]+"
    r"| ?[\p{P}\p{S}]+[\r\n]*"
    r"|\s*[\r\n]+"
    r"|\s+(?!\S)"
    r"|\s+"
)


def build_deepseek_style_byte_bpe() -> Tokenizer:
    tokenizer = Tokenizer(models.BPE(unk_token=None, byte_fallback=False))
    tokenizer.pre_tokenizer = pre_tokenizers.Sequence(
        [
            pre_tokenizers.Split(Regex(DIGIT_PATTERN), behavior="isolated"),
            pre_tokenizers.Split(Regex(CJK_PATTERN), behavior="isolated"),
            pre_tokenizers.Split(Regex(CATEGORY_PATTERN), behavior="isolated"),
            pre_tokenizers.ByteLevel(
                add_prefix_space=False,
                trim_offsets=True,
                use_regex=False,
            ),
        ]
    )
    tokenizer.decoder = decoders.ByteLevel()
    tokenizer.post_processor = processors.ByteLevel(trim_offsets=False)
    return tokenizer
