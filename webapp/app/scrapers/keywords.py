"""KeyBERT-based keyword extraction, replacing yake.

yake has a documented O(k^2) pairwise-Levenshtein deduplication step
(https://github.com/LIAAD/yake/issues/80, open/unfixed) that can blow up on
a page with an unusually large candidate-phrase count - this is what hung a
real production crawl for 2h40+ minutes on one page. KeyBERT's cost scales
with candidate count, not pairwise comparisons between them - measured
directly against a large synthetic page (5000 repeated phrases, ~324KB of
text): ~59s, slow but bounded and roughly linear, not a runaway hang. Still
slow enough that callers should wrap this in a timeout (see crawl.py's
PER_PAGE_TIMEOUT) - KeyBERT being better-behaved than yake doesn't mean
unbounded.

Score direction is the opposite of yake's: KeyBERT's cosine-similarity
scores are higher-is-more-relevant, not lower-is-better.
"""

from keybert import KeyBERT

_MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def _get_model():
    global _model
    if _model is None:
        # Lazy singleton, same pattern as summarizer.py's bert model - load
        # once per worker process, not once per page.
        _model = KeyBERT(model=_MODEL_NAME)
    return _model


def extract_keywords(text, top=15):
    model = _get_model()
    keywords = model.extract_keywords(
        text,
        keyphrase_ngram_range=(1, 2),
        stop_words="english",
        top_n=top,
        use_mmr=True,
        diversity=0.5,
    )
    return [{"keyword": kw, "score": float(score)} for kw, score in keywords]
