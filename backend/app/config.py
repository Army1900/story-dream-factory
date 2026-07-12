from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 存储
    database_url: str = "sqlite:///./data/story.db"
    image_storage_path: str = "./data/images"

    # LLM 密钥
    zhipu_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # LLM 分层模型
    llm_tier1_model: str = "openai/glm-4-plus"
    llm_tier2_model: str = "openai/glm-4-plus"
    llm_tier3_model: str = "openai/glm-4-flash"
    llm_embedding_model: str = ""

    # 生图
    imagegen_provider: str = "zhipu"
    zhipu_image_model: str = "cogview-3"


def get_settings() -> Settings:
    return Settings()
