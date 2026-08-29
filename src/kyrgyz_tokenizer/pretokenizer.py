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

# Embedded in the official ai-sage/GigaChat3-10B-A1.8B-base tokenizer at
# revision 8092e7006e188b65fe10526a1b6472576645e5ed. Unlike the DeepSeek
# sequence, this keeps case transitions in the same regex decision and has no
# separate CJK branch.
GIGACHAT_PATTERN = (
    r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*"
    r"[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?"
    r"|[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+"
    r"[\p{Ll}\p{Lm}\p{Lo}\p{M}]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?"
    r"|\p{N}{1,3}"
    r"| ?[^\s\p{L}\p{N}]+[\r\n/]*"
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


def build_gigachat_style_byte_bpe() -> Tokenizer:
    tokenizer = Tokenizer(models.BPE(unk_token=None, byte_fallback=False))
    tokenizer.pre_tokenizer = pre_tokenizers.Sequence(
        [
            pre_tokenizers.Split(
                Regex(GIGACHAT_PATTERN),
                behavior="removed",
                invert=True,
            ),
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


def build_category_aware_byte_bpe(style: str) -> Tokenizer:
    if style == "deepseek":
        return build_deepseek_style_byte_bpe()
    if style == "gigachat":
        return build_gigachat_style_byte_bpe()
    raise ValueError(f"Unknown pre-tokenizer style: {style}")
