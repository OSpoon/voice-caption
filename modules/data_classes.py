from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

# 模型内存使用量常量 (MB)
MODEL_MEMORY_ESTIMATES = {
    "tiny": 39,
    "base": 74,
    "small": 244,
    "medium": 769,
    "large-v1": 1550,
    "large-v2": 1550,
    "large-v3": 1550,
}


class WhisperImpl(Enum):
    """Whisper 实现类型枚举"""

    WHISPER = "whisper"


class Segment(BaseModel):
    """转录片段数据结构"""

    id: Optional[int] = Field(default=None, description="片段序号")
    text: Optional[str] = Field(default=None, description="转录文本")
    start: Optional[float] = Field(default=None, description="开始时间")
    end: Optional[float] = Field(default=None, description="结束时间")
    tokens: Optional[List[int]] = Field(
        default=None, description="Token ID 列表"
    )
    temperature: Optional[float] = Field(default=None, description="解码温度")
    avg_logprob: Optional[float] = Field(
        default=None, description="平均对数概率"
    )
    compression_ratio: Optional[float] = Field(
        default=None, description="压缩比"
    )
    no_speech_prob: Optional[float] = Field(
        default=None, description="非语音概率"
    )


class BaseParams(BaseModel):
    """基础参数类"""

    def to_dict(self) -> Dict:
        return self.model_dump()

    def to_list(self) -> List:
        return list(self.model_dump().values())

    @classmethod
    def from_list(cls, data_list: List) -> "BaseParams":
        field_names = list(cls.model_fields.keys())
        return cls(**dict(zip(field_names, data_list)))


class WhisperParams(BaseParams):
    """Whisper 转录参数"""

    model_size: str = Field(default="base", description="模型大小")
    language: Optional[str] = Field(default=None, description="源语言")
    is_translate: bool = Field(default=False, description="是否翻译为英文")
    beam_size: int = Field(default=5, ge=1, description="束搜索大小")
    temperature: float = Field(default=0.0, ge=0.0, description="采样温度")
    compression_ratio_threshold: float = Field(
        default=2.4, gt=0, description="压缩比阈值"
    )
    log_prob_threshold: float = Field(default=-1.0, description="对数概率阈值")
    no_speech_threshold: float = Field(
        default=0.6, ge=0.0, le=1.0, description="静音检测阈值"
    )
    condition_on_previous_text: bool = Field(
        default=True, description="基于前文条件"
    )
    initial_prompt: Optional[str] = Field(default=None, description="初始提示")
    word_timestamps: bool = Field(default=False, description="词级时间戳")
    prepend_punctuations: Optional[str] = Field(
        default="\"'¿([{-", description="前置标点"
    )
    append_punctuations: Optional[str] = Field(
        default='"\'.。,，!！?？:：")]}、', description="后置标点"
    )
    max_new_tokens: Optional[int] = Field(
        default=None, description="最大新 token 数"
    )
    chunk_length: Optional[int] = Field(
        default=30, description="音频块长度（秒）"
    )
    hallucination_silence_threshold: Optional[float] = Field(
        default=None, description="幻觉静音阈值"
    )
    hotwords: Optional[str] = Field(default=None, description="热词提示")
    suppress_tokens: Optional[List[int]] = Field(
        default=[-1], description="抑制的 token"
    )


class ModelConfig(BaseParams):
    """模型配置参数"""

    whisper_type: str = Field(
        default=WhisperImpl.WHISPER.value, description="Whisper 实现类型"
    )
    model_dir: str = Field(default="models", description="模型存储目录")
    device: str = Field(default="auto", description="计算设备")
    compute_type: str = Field(default="float16", description="计算精度")
    download_root: Optional[str] = Field(
        default=None, description="下载根目录"
    )
    hf_token: Optional[str] = Field(
        default=None, description="HuggingFace Token"
    )
    auto_download: bool = Field(default=True, description="自动下载模型")


class TranscriptionResult(BaseModel):
    """转录结果"""

    text: str = Field(description="完整转录文本")
    segments: List[Segment] = Field(description="分段结果")
    language: Optional[str] = Field(default=None, description="检测到的语言")
    duration: Optional[float] = Field(default=None, description="音频时长")
    model_info: Optional[Dict] = Field(default=None, description="模型信息")
