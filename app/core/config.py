import os

class Settings:
    PROJECT_NAME: str = "NebulaVerse API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

settings = Settings()
