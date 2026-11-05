"""Language simplifier: plain-word substitution, sentence splitting and reading grade."""
import re

WORDS = {
    "commence": "start", "shortly": "soon", "imperative": "very important", "remain": "stay",
    "refrain from": "do not", "refrain": "stop", "communicating": "talking", "examination": "test",
    "utilize": "use", "approximately": "about", "purchase": "buy", "assist": "help", "difficult": "hard",
    "require": "need", "requires": "needs", "subsequently": "later", "insufficient": "not enough",
    "obtain": "get", "attend": "go to", "consume": "eat", "inform": "tell", "frustrated": "upset",
    "appropriate": "right", "immediately": "right now", "prior": "before", "sufficient": "enough",
    "terminate": "end", "endeavor": "try", "proceed": "go", "necessary": "needed", "concentrate": "focus",
}


def _syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", w)))


def grade(text: str) -> float:
    words = text.split()
    if not words:
        return 0.0
    sentences = max(1, len(re.findall(r"[.!?]", text)))
    syl = sum(_syllables(w) for w in words)
    return round(max(0.0, 0.39 * len(words) / sentences + 11.8 * syl / len(words) - 15.59), 1)


def simplify(text: str) -> dict:
    out = text.strip()
    for k in sorted(WORDS, key=len, reverse=True):
        out = re.sub(rf"\b{k}\b", WORDS[k], out, flags=re.I)
    out = re.sub(r"it is (?:very important|needed) that you ", "You must ", out, flags=re.I)
    out = re.sub(r"in order to ", "to ", out, flags=re.I)
    parts = [p.strip() for p in re.split(r",\s*(?:and then|and|which|so)\s+", out, flags=re.I) if p.strip()]
    out = " ".join(p[0].upper() + p[1:].rstrip(".") + "." for p in parts)
    return {"simple": out, "grade_before": grade(text), "grade_after": grade(out)}
