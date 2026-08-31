from transformers import pipeline

_summarizer = None


def _get_summarizer():
    global _summarizer
    if _summarizer is None:
        # Lazy singleton: loading the model is expensive, do it once per
        # worker process rather than on every task (the old bert-extractive-
        # summarizer call re-instantiated its model on every call).
        _summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    return _summarizer


def summarizer_bert(text):
    summarizer = _get_summarizer()
    result = summarizer(text, min_length=60, max_length=200, truncation=True)
    return result[0]["summary_text"]
