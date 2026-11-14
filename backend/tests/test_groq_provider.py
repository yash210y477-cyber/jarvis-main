from providers.groq import GroqProvider


def make_provider(available, preferred="minimaxai/minimax-m2.7"):
    provider = GroqProvider.__new__(GroqProvider)

    provider.model = preferred

    provider.fallback_model = "openai/gpt-oss-120b"

    provider._known = set(available)

    return provider


def test_model_that_the_account_cannot_reach_is_skipped():
    # MiniMax is not on this account, so the next preferred model answers.
    provider = make_provider({"openai/gpt-oss-120b", "whisper-large-v3"})

    assert provider.resolve_model() == "openai/gpt-oss-120b"


def test_preferred_model_is_kept_when_available():
    provider = make_provider({"minimaxai/minimax-m2.7", "openai/gpt-oss-120b"})

    assert provider.resolve_model() == "minimaxai/minimax-m2.7"


def test_only_audio_models_left_never_become_the_brain():
    provider = make_provider({"whisper-large-v3", "canopylabs/orpheus-v1-english"})

    # Nothing usable: the configured model is returned for a clear error.
    assert provider.resolve_model() == "minimaxai/minimax-m2.7"
