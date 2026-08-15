import re

from .text_utils import normalize_whitespace


def _ensure_nltk_punkt() -> None:
    try:
        import nltk

        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt", quiet=True)
            nltk.download("punkt_tab", quiet=True)
    except Exception:
        pass


def summarize_text(text: str, sentences_count: int = 5) -> dict:
    clean = normalize_whitespace(text)
    if len(clean) < 80:
        return {
            "summary_bullets": [clean] if clean else ["(Not enough text to summarize.)"],
            "key_points": [],
            "exam_tips": [
                "Add more note content or PDF text to get richer summaries.",
            ],
        }

    bullets: list[str] = []
    summary_para = ""

    try:
        from sumy.nlp.stemmers import Stemmer
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.summarizers.text_rank import TextRankSummarizer

        parser = PlaintextParser.from_string(clean, Tokenizer("english"))
        summarizer = TextRankSummarizer(Stemmer("english"))
        summarizer.stop_words = summarizer.stop_words or set()
        summary_sentences = summarizer(parser.document, sentences_count)
        bullets = [str(s) for s in summary_sentences]
        summary_para = " ".join(bullets[:3])
    except Exception:
        _ensure_nltk_punkt()
        try:
            from nltk.tokenize import sent_tokenize

            sents = sent_tokenize(clean)
            n = max(1, min(sentences_count, len(sents)))
            step = max(1, len(sents) // n)
            picked = [sents[i] for i in range(0, len(sents), step)][:n]
            bullets = picked
            summary_para = " ".join(bullets[:3])
        except Exception:
            chunks = re.split(r"(?<=[.!?])\s+", clean)
            bullets = [c for c in chunks if len(c) > 40][:sentences_count]
            summary_para = " ".join(bullets[:2])

    key_candidates = []
    for line in clean.split(". "):
        low = line.lower()
        if any(
            k in low
            for k in (
                "definition",
                "theorem",
                "important",
                "remember",
                "formula",
                "steps",
                "because",
                "therefore",
            )
        ):
            key_candidates.append(line.strip()[:240])
    key_points = key_candidates[:5] or bullets[:3]

    exam_tips = [
        "Re-derive formulas from memory, then check against your summary.",
        "For each bullet, write one practice question you could be asked.",
        "Schedule review 1-3 days before the exam for these topics.",
    ]

    return {
        "summary_bullets": bullets or [summary_para],
        "key_points": key_points,
        "exam_tips": exam_tips,
        "summary_paragraph": summary_para,
    }
