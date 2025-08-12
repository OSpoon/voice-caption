import time
from pathlib import Path
from typing import BinaryIO, Callable, List, Optional, Union

import numpy as np
import whisper

from .base_pipeline import BaseTranscriptionPipeline
from .data_classes import (
    MODEL_MEMORY_ESTIMATES,
    ModelConfig,
    Segment,
    TranscriptionResult,
    WhisperParams,
)


class WhisperPipeline(BaseTranscriptionPipeline):
    """原版 OpenAI Whisper 实现"""

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.available_models = whisper.available_models()

    def transcribe(
        self,
        audio: Union[str, BinaryIO, np.ndarray],
        params: WhisperParams,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> TranscriptionResult:
        """使用 Whisper 转录音频"""
        start_time = time.time()

        # 验证音频输入
        if not self.validate_audio(audio):
            raise ValueError("无效的音频输入")

        # 确保模型已加载
        if not self.ensure_model_loaded(params.model_size):
            raise RuntimeError(f"无法加载模型: {params.model_size}")

        # 准备转录参数（移除不兼容的参数）
        transcribe_options = {
            "language": params.language,
            "task": "translate" if params.is_translate else "transcribe",
            "temperature": params.temperature,
            "condition_on_previous_text": params.condition_on_previous_text,
            "initial_prompt": params.initial_prompt,
            "word_timestamps": params.word_timestamps,
        }

        # 只添加原版 Whisper 支持的参数
        if hasattr(whisper, "__version__"):
            # 检查版本兼容性，只添加支持的参数
            pass

        # 过滤 None 值
        transcribe_options = {
            k: v for k, v in transcribe_options.items() if v is not None
        }

        try:
            # 执行转录
            if progress_callback:
                progress_callback(0.1, "开始转录...")

            if self.model is None:
                raise RuntimeError("模型未加载")

            result = self.model.transcribe(audio, **transcribe_options)

            if progress_callback:
                progress_callback(0.9, "处理结果...")

            # 转换结果格式
            segments = []
            for segment_data in result.get("segments", []):
                segment = Segment(
                    id=segment_data.get("id"),
                    text=segment_data.get("text"),
                    start=segment_data.get("start"),
                    end=segment_data.get("end"),
                    tokens=segment_data.get("tokens"),
                    temperature=segment_data.get("temperature"),
                    avg_logprob=segment_data.get("avg_logprob"),
                    compression_ratio=segment_data.get("compression_ratio"),
                    no_speech_prob=segment_data.get("no_speech_prob"),
                )
                segments.append(segment)

            elapsed_time = time.time() - start_time

            if progress_callback:
                progress_callback(1.0, "转录完成")

            return TranscriptionResult(
                text=result.get("text", ""),
                segments=segments,
                language=result.get("language"),
                duration=elapsed_time,
                model_info=self.get_model_info(),
            )

        except Exception as e:
            raise RuntimeError(f"转录失败: {str(e)}")

    def load_model(
        self, model_size: str, compute_type: Optional[str] = None
    ) -> bool:
        """加载 Whisper 模型"""
        try:
            # 检查模型是否可用
            if model_size not in self.available_models:
                if self.config.auto_download:
                    print(f"模型 {model_size} 不在本地，将自动下载...")
                else:
                    raise ValueError(f"模型 {model_size} 不可用")

            # 设置下载根目录
            download_root = self.config.download_root or self.config.model_dir

            # 加载模型
            self.model = whisper.load_model(
                model_size, device=self.device, download_root=download_root
            )

            self.current_model_size = model_size
            self.current_compute_type = compute_type or "float32"

            print(f"成功加载模型: {model_size} (设备: {self.device})")
            return True

        except Exception as e:
            print(f"加载模型失败: {str(e)}")
            return False

    def get_available_models(self) -> List[str]:
        """获取可用的 Whisper 模型列表"""
        models = list(whisper.available_models())

        # 检查本地自定义模型
        model_dir = Path(self.config.model_dir)
        if model_dir.exists():
            for item in model_dir.iterdir():
                if item.is_dir() and item.name not in models:
                    # 检查是否包含模型文件
                    if any(item.glob("*.pt")) or any(item.glob("*.pth")):
                        models.append(item.name)

        return sorted(models)

    # get_device 方法继承自基类

    def get_model_path(self, model_size: str) -> Optional[str]:
        """获取模型文件路径"""
        if model_size in whisper.available_models():
            return None  # 使用默认路径

        # 检查本地模型
        model_path = Path(self.config.model_dir) / model_size
        if model_path.exists():
            return str(model_path)

        return None

    def estimate_memory_usage(self, model_size: str) -> dict:
        """估算模型内存使用量"""
        base_memory = MODEL_MEMORY_ESTIMATES.get(model_size, 1000)

        # 根据设备调整
        if self.device == "cuda":
            gpu_memory = base_memory * 1.2  # GPU 需要额外内存
        else:
            gpu_memory = 0

        return {
            "model_size_mb": base_memory,
            "gpu_memory_mb": gpu_memory,
            "total_mb": base_memory + gpu_memory,
        }
