from pydantic_settings import BaseSettings, SettingsConfigDict


class RunnerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KAME_RUNNER_", env_file=".env", extra="ignore")

    api_base: str = "http://127.0.0.1:8100"
    token: str = ""
    workspace_id: str = ""
    runner_id: str = "local-1"
    mode: str = "local"  # local | cloud
    headed: bool = False
    max_concurrency: int = 2
    poll_seconds: float = 2.0
    step_budget: int = 80
    terminal_checkpoints: bool = True
