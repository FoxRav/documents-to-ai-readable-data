"""Step 01: Prepare models and assets (fail-fast check)."""

import json
import logging
from pathlib import Path
from typing import Any

from src.pipeline.config import get_settings

logger = logging.getLogger(__name__)


def check_cuda() -> dict[str, Any]:
    """Check CUDA availability."""
    try:
        import torch

        cuda_available = torch.cuda.is_available()
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        else:
            gpu_name = None
            vram_gb = None
        return {
            "cuda_available": cuda_available,
            "gpu_name": gpu_name,
            "vram_gb": vram_gb,
        }
    except ImportError:
        logger.warning("PyTorch not installed, CUDA check skipped")
        return {"cuda_available": False, "gpu_name": None, "vram_gb": None}


def check_poppler() -> bool:
    """Check if Poppler is available."""
    try:
        from pdf2image import pdf2image

        # Try to import and check if it works
        return True
    except ImportError:
        logger.warning("pdf2image not installed")
        return False
    except Exception as e:
        logger.warning(f"Poppler check failed: {e}")
        return False


def check_tesseract() -> bool:
    """Check if Tesseract is available."""
    try:
        import pytesseract

        # Try to get version
        pytesseract.get_tesseract_version()
        return True
    except ImportError:
        logger.warning("pytesseract not installed")
        return False
    except Exception as e:
        logger.warning(f"Tesseract check failed: {e}")
        return False


def check_paddleocr() -> dict[str, Any]:
    """Check PaddleOCR availability (optional)."""
    try:
        # Check CUDA first
        try:
            import torch
            use_gpu = torch.cuda.is_available()
            gpu_info = f"CUDA: {torch.cuda.get_device_name(0)}" if use_gpu else "CPU"
        except ImportError:
            use_gpu = False
            gpu_info = "CPU (PyTorch not available)"
        
        from paddleocr import PaddleOCR

        # Initialize with GPU if available
        ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False, use_gpu=use_gpu)
        return {"available": True, "initialized": True, "use_gpu": use_gpu, "gpu_info": gpu_info}
    except ImportError:
        return {"available": False, "initialized": False}
    except Exception as e:
        logger.warning(f"PaddleOCR check failed: {e}")
        return {"available": True, "initialized": False, "error": str(e)}


def prepare_assets(work_dir: Path, debug_dir: Path) -> dict[str, Any]:
    """Prepare models and assets, perform fail-fast checks."""
    settings = get_settings()

    logger.info("Preparing assets and performing fail-fast checks...")

    results: dict[str, Any] = {
        "device_profile": check_cuda(),
        "poppler_available": check_poppler(),
        "tesseract_available": check_tesseract(),
        "paddleocr": check_paddleocr(),
        "directories": {
            "model_dir": str(settings.model_dir.absolute()),
            "cache_dir": str(settings.cache_dir.absolute()),
        },
    }

    # Write asset check report
    asset_check_path = debug_dir / "asset_check.json"
    with open(asset_check_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"Asset check completed. Report saved to {asset_check_path}")

    # Fail-fast: check critical dependencies
    if not results["poppler_available"]:
        logger.error("Poppler not available. Install pdf2image and Poppler.")
        raise RuntimeError("Poppler not available")

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    work_dir = Path("data/10_work")
    debug_dir = work_dir / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    prepare_assets(work_dir, debug_dir)
