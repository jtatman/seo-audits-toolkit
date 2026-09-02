from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

_MODEL_NAME = "facebook/bart-large-cnn"

_tokenizer = None
_model = None


def _get_model():
    global _tokenizer, _model
    if _model is None:
        # Lazy singleton: loading the model is expensive, do it once per
        # worker process rather than on every task.
        #
        # Deliberately not using transformers.pipeline("summarization", ...):
        # that task was removed from the pipeline registry in transformers
        # 5.x. Falling back to pipeline("text-generation", ...) silently
        # loads the wrong architecture for this model (BartForCausalLM,
        # decoder-only) and produces garbage with no error.
        # AutoModelForSeq2SeqLM explicitly requests the correct
        # encoder-decoder architecture regardless of what pipeline tasks
        # exist. (Same approach already proven working in this project's
        # Django server rewrite - server/bert/src/bertSummarizer.py.)
        _tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
        _model = AutoModelForSeq2SeqLM.from_pretrained(_MODEL_NAME)
    return _tokenizer, _model


def summarize(text):
    tokenizer, model = _get_model()
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=1024)
    summary_ids = model.generate(inputs["input_ids"], min_length=60, max_length=200)
    return {"summary": tokenizer.decode(summary_ids[0], skip_special_tokens=True)}
