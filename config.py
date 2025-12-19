"""
项目配置：路径、模型与端点。
在 Windows + CUDA 环境下安装 torch 示例（按需修改 CUDA 版本）：
    pip install torch --index-url https://download.pytorch.org/whl/cu121
"""
import logging
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
# 业务数据统一放到 data 目录，便于 Windows 下管理与备份
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "docs"  # 文件夹1：存放上传的 pdf/pptx
CHROMA_PATH = DATA_DIR / "vector_store"  # 文件夹2：向量库持久化
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"
MODEL_DIR = BASE_DIR / "models" / "bge-m3"
MODEL_DIR_OCR = BASE_DIR / "models" / "MinerU25"

@dataclass
class ModelConfig:
    """模型与服务配置。"""

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    embedding_model_name: str = str(MODEL_DIR)
    embedding_device: str = "cuda"  # Windows 下若显存紧张，可设为 "cpu"
    embedding_batch_size: int = 16
    # MinerU 2.5 模型配置
    mineru_model_path: str = str(MODEL_DIR_OCR)


model_config = ModelConfig()


def ensure_dirs() -> None:
    """确保必要的持久化目录存在。"""
    for path in (DATA_DIR, CHROMA_PATH, UPLOAD_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)


def setup_logging(level: int = logging.INFO) -> None:
    """配置全局日志，文件 + 控制台输出。"""
    ensure_dirs()
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,  # 覆盖已有配置，避免重复 handler
    )



if __name__ == "__main__":
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"UPLOAD_DIR: {UPLOAD_DIR}")
    print(f"CHROMA_PATH: {CHROMA_PATH}")
