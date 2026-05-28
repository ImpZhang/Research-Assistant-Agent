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
    graph_rag_lite_enabled: bool = os.getenv("GRAPH_RAG_LITE_ENABLED", "true").lower() != "false"
    mcp_enabled: bool = os.getenv("MCP_ENABLED", "false").lower() == "true"

    main_model: str = os.getenv("MAIN_MODEL") or os.getenv("MODEL", "")
    main_base_url: str = os.getenv("MAIN_BASE_URL") or os.getenv("BASE_URL", "")
    main_api_key: str = os.getenv("MAIN_API_KEY") or os.getenv("ARK_API_KEY", "")

    extraction_model: str = os.getenv("EXTRACTION_MODEL") or main_model
    extraction_base_url: str = os.getenv("EXTRACTION_BASE_URL") or main_base_url
    extraction_api_key: str = os.getenv("EXTRACTION_API_KEY") or main_api_key

    judge_model: str = os.getenv("JUDGE_MODEL") or main_model
    judge_base_url: str = os.getenv("JUDGE_BASE_URL") or main_base_url
    judge_api_key: str = os.getenv("JUDGE_API_KEY") or main_api_key


settings = Settings()
