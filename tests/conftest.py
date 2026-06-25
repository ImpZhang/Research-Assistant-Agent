import os


if os.getenv("ALLOW_REAL_MODEL_PROVIDER_TESTS") != "1":
    os.environ["RETRIEVAL_EMBEDDING_PROVIDER"] = "local"
    os.environ["RETRIEVAL_RERANK_PROVIDER"] = "disabled"
