"""Configuration management using pydantic-settings."""

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Model and cache directories
    model_dir: Path = Path("./models")
    cache_dir: Path = Path("./cache")
    paddleocr_model_dir: Path = Path("./models/paddleocr")
    mineru_model_dir: Path = Path("./models/mineru")
    dolphin_model_dir: Path = Path("./models/dolphin")
    megaparse_model_dir: Path = Path("./models/megaparse")

    # HuggingFace cache
    hf_home: Path = Path("./cache/hf")
    transformers_cache: Path = Path("./cache/hf/transformers")

    # PyTorch cache
    torch_home: Path = Path("./cache/torch")

    # PaddlePaddle cache
    paddle_home: Path = Path("./cache/paddle")

    # OCR cache
    ocr_cache_dir: Path = Path("./cache/ocr")

    # System dependencies (Windows paths)
    poppler_bin: Path | None = None
    tesseract_cmd: Path | None = None

    # OCR settings (V5)
    ocr_primary: Literal["tesseract", "paddle"] = "tesseract"  # Primary OCR engine
    ocr_fallback: Literal["tesseract", "paddle", "none"] = "none"  # Fallback OCR engine
    ocr_device: Literal["cpu", "cuda", "auto"] = "cpu"  # For PaddleOCR only
    ocr_use_mkldnn: bool = False  # Disable MKLDNN to avoid OneDnnContext errors
    ocr_gpu_concurrency: int = 1  # Limit GPU concurrency

    # Tesseract OCR settings (V6)
    tess_lang: str = "fin+eng"  # Tesseract language(s)
    tess_psm: int = 6  # Page segmentation mode (6 = uniform block of text)
    tess_oem: int = 1  # OCR Engine Mode (1 = LSTM only)
    ocr_render_dpi: int = 400  # DPI for OCR rendering (higher = better quality)

    # GPU settings
    cuda_visible_devices: str = "0"
    gpu_concurrency: int = 1
    cpu_concurrency: int = 6

    # MinerU settings
    mineru_backend: Literal["hybrid-auto-engine", "pipeline", "vlm", "hybrid"] = "hybrid-auto-engine"
    mineru_ocr_lang: str = "fin"
    mineru_inline_formula: bool = False
    mineru_visualize: bool = True

    # Dolphin settings
    dolphin_mode: Literal["off", "qa", "fallback", "layout-only"] = "off"
    dolphin_max_batch_size: int = 4

    # Logging
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"

    def __init__(self, **kwargs: object) -> None:
        """Initialize settings and set environment variables."""
        super().__init__(**kwargs)
        self._set_env_vars()

    def _set_env_vars(self) -> None:
        """Set environment variables for model/cache paths."""
        os.environ["HF_HOME"] = str(self.hf_home.absolute())
        os.environ["TRANSFORMERS_CACHE"] = str(self.transformers_cache.absolute())
        os.environ["TORCH_HOME"] = str(self.torch_home.absolute())
        os.environ["PADDLE_HOME"] = str(self.paddle_home.absolute())
        os.environ["CUDA_VISIBLE_DEVICES"] = self.cuda_visible_devices

        # Create directories if they don't exist
        for path in [
            self.model_dir,
            self.cache_dir,
            self.paddleocr_model_dir,
            self.mineru_model_dir,
            self.dolphin_model_dir,
            self.hf_home,
            self.transformers_cache,
            self.torch_home,
            self.paddle_home,
            self.ocr_cache_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
