from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Research Assistant Agent")
    app_env: str = os.getenv("APP_ENV", "development")
    research_db_url: str = os.getenv(
        "RESEARCH_DB_URL",
        "sqlite:///./data/research/research_assistant.db",
    )
    paper_upload_dir: str = os.getenv("PAPER_UPLOAD_DIR", "./data/papers")
    paper_upload_allowed_extensions: str = os.getenv(
        "PAPER_UPLOAD_ALLOWED_EXTENSIONS",
        ".txt,.md,.pdf",
    )
    paper_upload_max_bytes: int = int(os.getenv("PAPER_UPLOAD_MAX_BYTES", "20971520"))
    graph_rag_lite_enabled: bool = os.getenv("GRAPH_RAG_LITE_ENABLED", "true").lower() != "false"
    mcp_enabled: bool = os.getenv("MCP_ENABLED", "false").lower() == "true"
    api_key_auth_enabled: bool = os.getenv("API_KEY_AUTH_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    api_key: str = os.getenv("API_KEY") or os.getenv("RESEARCH_ASSISTANT_API_KEY", "")
    api_key_header_name: str = os.getenv("API_KEY_HEADER_NAME", "X-Research-Assistant-Key")
    write_audit_enabled: bool = os.getenv("WRITE_AUDIT_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    write_audit_dir: str = os.getenv("WRITE_AUDIT_DIR", "./data/audit")
    write_audit_client_header_name: str = os.getenv(
        "WRITE_AUDIT_CLIENT_HEADER_NAME",
        "X-Research-Assistant-Client",
    )
    audit_admin_export_enabled: bool = os.getenv(
        "AUDIT_ADMIN_EXPORT_ENABLED",
        "false",
    ).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    audit_admin_key: str = os.getenv("AUDIT_ADMIN_KEY", "")
    audit_admin_key_header_name: str = os.getenv(
        "AUDIT_ADMIN_KEY_HEADER_NAME",
        "X-Research-Assistant-Admin-Key",
    )
    request_id_header_name: str = os.getenv("REQUEST_ID_HEADER_NAME", "X-Request-ID")
    external_literature_search_enabled: bool = (
        os.getenv("EXTERNAL_LITERATURE_SEARCH_ENABLED", "false").lower() == "true"
    )
    external_literature_providers: str = os.getenv(
        "EXTERNAL_LITERATURE_PROVIDERS",
        "openalex,arxiv,semantic_scholar",
    )
    openalex_base_url: str = os.getenv("OPENALEX_BASE_URL", "https://api.openalex.org")
    arxiv_base_url: str = os.getenv("ARXIV_BASE_URL", "https://export.arxiv.org/api/query")
    semantic_scholar_base_url: str = os.getenv(
        "SEMANTIC_SCHOLAR_BASE_URL",
        "https://api.semanticscholar.org/graph/v1/paper/search",
    )
    semantic_scholar_api_key: str = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    external_literature_request_timeout_seconds: float = float(
        os.getenv("EXTERNAL_LITERATURE_REQUEST_TIMEOUT_SECONDS", "30")
    )
    external_literature_user_agent: str = os.getenv(
        "EXTERNAL_LITERATURE_USER_AGENT",
        "Research Assistant Agent external-literature/1.0",
    )

    main_model: str = os.getenv("MAIN_MODEL") or os.getenv("MODEL", "")
    main_base_url: str = os.getenv("MAIN_BASE_URL") or os.getenv("BASE_URL", "")
    main_api_key: str = os.getenv("MAIN_API_KEY") or os.getenv("ARK_API_KEY", "")

    extraction_model: str = os.getenv("EXTRACTION_MODEL") or main_model
    extraction_base_url: str = os.getenv("EXTRACTION_BASE_URL") or main_base_url
    extraction_api_key: str = os.getenv("EXTRACTION_API_KEY") or main_api_key

    judge_model: str = os.getenv("JUDGE_MODEL") or main_model
    judge_base_url: str = os.getenv("JUDGE_BASE_URL") or main_base_url
    judge_api_key: str = os.getenv("JUDGE_API_KEY") or main_api_key

    embedder: str = os.getenv("EMBEDDER", "")
    embedder_base_url: str = os.getenv("EMBEDDER_BASE_URL", "")
    embedder_api_key: str = os.getenv("EMBEDDER_API_KEY", "")
    embedder_path: str = os.getenv("EMBEDDER_PATH", "/embeddings")
    retrieval_embedding_provider: str = os.getenv("RETRIEVAL_EMBEDDING_PROVIDER", "auto")

    rerank_model: str = os.getenv("RERANK_MODEL", "")
    rerank_binding_host: str = os.getenv("RERANK_BINDING_HOST", "")
    rerank_api_key: str = os.getenv("RERANK_API_KEY", "")
    rerank_path: str = os.getenv("RERANK_PATH", "/rerank")
    retrieval_rerank_provider: str = os.getenv("RETRIEVAL_RERANK_PROVIDER", "auto")

    model_provider_timeout_seconds: float = float(os.getenv("MODEL_PROVIDER_TIMEOUT_SECONDS", "60"))

    workflow_background_tasks_enabled: bool = os.getenv(
        "WORKFLOW_BACKGROUND_TASKS_ENABLED",
        "true",
    ).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    benchmark_runner_enabled: bool = os.getenv("BENCHMARK_RUNNER_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    benchmark_runner_output_dir: str = os.getenv(
        "BENCHMARK_RUNNER_OUTPUT_DIR",
        "./outputs/benchmark-runs",
    )
    benchmark_runner_timeout_seconds: int = int(
        os.getenv("BENCHMARK_RUNNER_TIMEOUT_SECONDS", "120")
    )
    benchmark_runner_allowed_commands: str = os.getenv(
        "BENCHMARK_RUNNER_ALLOWED_COMMANDS",
        "python,python3,.venv/bin/python",
    )
    benchmark_runner_max_output_chars: int = int(
        os.getenv("BENCHMARK_RUNNER_MAX_OUTPUT_CHARS", "200000")
    )
    benchmark_profile_manifest_path: str = os.getenv(
        "BENCHMARK_PROFILE_MANIFEST_PATH",
        "./configs/benchmark_profiles.json",
    )


settings = Settings()
