import random
import re
from dataclasses import dataclass


@dataclass
class MCQ:
    question: str
    choices: list[str]
    answer_index: int


@dataclass
class ShortQuestion:
    prompt: str
    hint: str


WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)


def _sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 20]


def _distractors(sentence: str, pool: list[str], answer: str, n: int = 3) -> list[str]:
    words = [w for w in WORD_RE.findall(sentence.lower()) if len(w) > 3]
    random.shuffle(pool)
    out = []
    for w in pool:
        if w.lower() == answer.lower():
            continue
        if w not in out:
            out.append(w)
        if len(out) >= n:
            break
    while len(out) < n:
        out.append(f"option_{len(out)+1}")
    return out[:n]


def generate_quiz(text: str, max_mcq: int = 5, max_short: int = 3) -> dict:
    sents = _sentences(text)
    if not sents:
        return {"mcqs": [], "short": []}

    pool = WORD_RE.findall(text.lower())
    pool = list({p for p in pool if len(p) > 4})[:80]

    mcqs: list[MCQ] = []
    used = set()
    for s in sents:
        if len(mcqs) >= max_mcq:
            break
        words = WORD_RE.findall(s)
        if len(words) < 6:
            continue
        idx = random.randint(1, len(words) - 2)
        answer = words[idx]
        key = (s[:40], answer.lower())
        if key in used:
            continue
        used.add(key)
        blanks = words[:]
        blanks[idx] = "_____"
        qtext = " ".join(blanks)
        distr = _distractors(s, pool, answer, 3)
        choices = distr + [answer]
        random.shuffle(choices)
        ans_i = choices.index(answer)
        mcqs.append(MCQ(question=qtext, choices=choices, answer_index=ans_i))

    shorts: list[ShortQuestion] = []
    for s in sents[: max_short * 2]:
        if len(shorts) >= max_short:
            break
        if "?" in s:
            continue
        first = s.split(",")[0]
        if len(first) < 30:
            continue
        shorts.append(
            ShortQuestion(
                prompt=f"Explain in your own words: {first[:180]}...",
                hint="Use a definition + one example.",
            )
        )

    return {
        "mcqs": mcqs,
        "short": shorts,
    }
