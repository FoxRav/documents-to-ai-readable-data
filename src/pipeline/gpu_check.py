"""GPU availability and usage checker."""

import logging

logger = logging.getLogger(__name__)


def check_gpu_availability() -> dict[str, any]:
    """Check GPU availability and log status."""
    result: dict[str, any] = {
        "cuda_available": False,
        "device_name": None,
        "vram_gb": None,
        "paddleocr_gpu": False,
        "opencv_cuda": False,
    }

    # Check PyTorch CUDA
    try:
        import torch

        if torch.cuda.is_available():
            result["cuda_available"] = True
            result["device_name"] = torch.cuda.get_device_name(0)
            result["vram_gb"] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"✅ CUDA available: {result['device_name']} ({result['vram_gb']:.1f} GB)")
        else:
            logger.warning("❌ CUDA not available in PyTorch")
    except ImportError:
        logger.warning("❌ PyTorch not installed")

    # Check PaddleOCR GPU support
    try:
        from paddleocr import PPStructure
        import torch

        if torch.cuda.is_available():
            # Try to initialize with GPU
            try:
                engine = PPStructure(show_log=False, use_gpu=True)
                result["paddleocr_gpu"] = True
                logger.info("✅ PaddleOCR PP-StructureV3 can use GPU")
            except Exception as e:
                logger.warning(f"⚠️ PaddleOCR GPU initialization failed: {e}")
                result["paddleocr_gpu"] = False
    except ImportError:
        logger.warning("⚠️ PaddleOCR not installed")
    except Exception as e:
        logger.warning(f"⚠️ PaddleOCR check failed: {e}")

    # Check OpenCV CUDA
    try:
        import cv2

        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            result["opencv_cuda"] = True
            logger.info(f"✅ OpenCV CUDA available: {cv2.cuda.getCudaEnabledDeviceCount()} device(s)")
        else:
            logger.info("ℹ️ OpenCV compiled without CUDA support (CPU only)")
    except Exception:
        logger.info("ℹ️ OpenCV CUDA not available (CPU only)")

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    check_gpu_availability()
