import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Callable, List, Optional, Union

import numpy as np

from .data_classes import (
    ModelConfig,
    Segment,
    TranscriptionResult,
    WhisperParams,
)


class BaseTranscriptionPipeline(ABC):
    """转录管道基础抽象类"""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.model = None
        self.current_model_size: Optional[str] = None
        self.current_compute_type: Optional[str] = None

        # 创建模型目录
        os.makedirs(self.config.model_dir, exist_ok=True)

        # 初始化可用模型列表
        self.available_models = self.get_available_models()
        self.device = self.get_device()

    @abstractmethod
    def transcribe(
        self,
        audio: Union[str, BinaryIO, np.ndarray],
        params: WhisperParams,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> TranscriptionResult:
        """转录音频

        Args:
            audio: 音频文件路径、二进制数据或 numpy 数组
            params: Whisper 参数
            progress_callback: 进度回调函数

        Returns:
            TranscriptionResult: 转录结果
        """
        pass

    @abstractmethod
    def load_model(
        self, model_size: str, compute_type: Optional[str] = None
    ) -> bool:
        """加载模型

        Args:
            model_size: 模型大小或路径
            compute_type: 计算类型

        Returns:
            bool: 是否加载成功
        """
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """获取可用模型列表

        Returns:
            List[str]: 可用模型列表
        """
        pass

    def get_device(self) -> str:
        """获取计算设备

        Returns:
            str: 设备类型
        """
        if self.config.device != "auto":
            return self.config.device

        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch, "xpu") and torch.xpu.is_available():
                return "xpu"
        except ImportError:
            pass
        return "cpu"

    def ensure_model_loaded(
        self, model_size: str, compute_type: Optional[str] = None
    ) -> bool:
        """确保模型已加载

        Args:
            model_size: 模型大小
            compute_type: 计算类型

        Returns:
            bool: 是否成功
        """
        compute_type = compute_type or self.config.compute_type

        if (
            self.model is None
            or self.current_model_size != model_size
            or self.current_compute_type != compute_type
        ):
            return self.load_model(model_size, compute_type)
        return True

    def validate_audio(self, audio: Union[str, BinaryIO, np.ndarray]) -> bool:
        """验证音频输入

        Args:
            audio: 音频输入

        Returns:
            bool: 是否有效
        """
        if isinstance(audio, str):
            return Path(audio).exists()
        elif isinstance(audio, np.ndarray):
            return audio.size > 0
        elif hasattr(audio, "read"):
            return True
        return False

    def format_timestamp(self, seconds: float) -> str:
        """格式化时间戳为 SRT 格式

        Args:
            seconds: 秒数

        Returns:
            str: SRT 时间格式
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    def generate_srt(self, segments: List[Segment]) -> str:
        """生成 SRT 字幕内容

        Args:
            segments: 转录片段列表

        Returns:
            str: SRT 内容
        """
        srt_content = ""
        for i, segment in enumerate(segments, 1):
            if segment.start is not None and segment.end is not None:
                start_time = self.format_timestamp(segment.start)
                end_time = self.format_timestamp(segment.end)
                text = segment.text.strip() if segment.text else ""
                srt_content += f"{i}\n{start_time} --> {end_time}\n{text}\n\n"
        return srt_content

    def offload_model(self):
        """卸载模型释放内存"""
        if self.model is not None:
            del self.model
            self.model = None
            self.current_model_size = None
            self.current_compute_type = None

            # 清理 GPU 内存
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

    def get_model_info(self) -> dict:
        """获取当前模型信息

        Returns:
            dict: 模型信息
        """
        return {
            "type": self.config.whisper_type,
            "model_size": self.current_model_size,
            "compute_type": self.current_compute_type,
            "device": self.device,
            "model_dir": self.config.model_dir,
        }
