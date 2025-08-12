from typing import Dict, List, Optional

from .base_pipeline import BaseTranscriptionPipeline
from .data_classes import ModelConfig, WhisperImpl
from .whisper_pipeline import WhisperPipeline


class ModelFactory:
    """模型工厂类，负责创建和管理不同类型的 Whisper 模型"""

    _instances: Dict[str, BaseTranscriptionPipeline] = {}

    @classmethod
    def create_pipeline(
        cls, whisper_type: str, config: Optional[ModelConfig] = None, **kwargs
    ) -> BaseTranscriptionPipeline:
        """创建转录管道实例

        Args:
            whisper_type: Whisper 实现类型
            config: 模型配置
            **kwargs: 额外配置参数

        Returns:
            BaseTranscriptionPipeline: 转录管道实例
        """
        # 标准化类型名称
        whisper_type = whisper_type.strip().lower().replace("_", "-")

        # 创建默认配置
        if config is None:
            config = ModelConfig(whisper_type=whisper_type, **kwargs)
        else:
            # 更新配置
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        # 生成实例键
        instance_key = f"{whisper_type}_{id(config)}"

        # 检查是否已存在实例
        if instance_key in cls._instances:
            return cls._instances[instance_key]

        # 创建新实例
        pipeline = cls._create_pipeline_instance(whisper_type, config)
        cls._instances[instance_key] = pipeline

        return pipeline

    @classmethod
    def _create_pipeline_instance(
        cls, whisper_type: str, config: ModelConfig
    ) -> BaseTranscriptionPipeline:
        """创建具体的管道实例"""
        if whisper_type == WhisperImpl.WHISPER.value:
            return WhisperPipeline(config)

        else:
            # 默认使用标准 Whisper
            print(f"未知的 Whisper 类型: {whisper_type}，使用默认的 Whisper")
            config.whisper_type = WhisperImpl.WHISPER.value
            return WhisperPipeline(config)

    @classmethod
    def get_available_types(cls) -> List[str]:
        """获取可用的 Whisper 实现类型

        Returns:
            List[str]: 可用类型列表
        """
        available_types = [WhisperImpl.WHISPER.value]

        # 检查其他实现...

        return available_types

    @classmethod
    def get_recommended_type(cls, device: str = "auto") -> str:
        """获取推荐的 Whisper 实现类型

        Args:
            device: 目标设备

        Returns:
            str: 推荐的实现类型
        """
        available_types = cls.get_available_types()

        # 使用标准 Whisper
        if WhisperImpl.WHISPER.value in available_types:
            return WhisperImpl.WHISPER.value

        raise RuntimeError("没有可用的 Whisper 实现")

    @classmethod
    def create_default_config(
        cls,
        whisper_type: Optional[str] = None,
        model_dir: str = "models",
        device: str = "auto",
        **kwargs,
    ) -> ModelConfig:
        """创建默认配置

        Args:
            whisper_type: Whisper 类型
            model_dir: 模型目录
            device: 计算设备
            **kwargs: 其他配置参数

        Returns:
            ModelConfig: 模型配置
        """
        if whisper_type is None:
            whisper_type = cls.get_recommended_type(device)

        return ModelConfig(
            whisper_type=whisper_type,
            model_dir=model_dir,
            device=device,
            **kwargs,
        )

    @classmethod
    def get_pipeline_info(cls, pipeline: BaseTranscriptionPipeline) -> Dict:
        """获取管道信息

        Args:
            pipeline: 转录管道

        Returns:
            Dict: 管道信息
        """
        return {
            "type": pipeline.config.whisper_type,
            "device": pipeline.device,
            "model_dir": pipeline.config.model_dir,
            "available_models": pipeline.available_models,
            "current_model": pipeline.current_model_size,
            "compute_type": pipeline.current_compute_type,
        }

    @classmethod
    def cleanup_instances(cls):
        """清理所有实例"""
        for pipeline in cls._instances.values():
            try:
                pipeline.offload_model()
            except Exception as e:
                print(f"清理模型时出错: {e}")

        cls._instances.clear()

    @classmethod
    def auto_select_implementation(
        cls, requirements: Optional[Dict] = None
    ) -> str:
        """根据需求自动选择最佳实现

        Args:
            requirements: 需求字典，可包含 'speed', 'accuracy', 'memory' 等

        Returns:
            str: 推荐的实现类型
        """
        available_types = cls.get_available_types()

        if requirements is None:
            requirements = {}

        if requirements.get("speed", False):
            if WhisperImpl.WHISPER.value in available_types:
                return WhisperImpl.WHISPER.value

        if requirements.get("memory", False):
            if WhisperImpl.WHISPER.value in available_types:
                return WhisperImpl.WHISPER.value

        # 如果优先考虑兼容性
        if requirements.get("compatibility", False):
            if WhisperImpl.WHISPER.value in available_types:
                return WhisperImpl.WHISPER.value

        # 默认推荐
        return cls.get_recommended_type()

    @classmethod
    def validate_model_availability(
        cls, whisper_type: str, model_size: str, model_dir: str = "models"
    ) -> Dict[str, bool]:
        """验证模型可用性

        Args:
            whisper_type: Whisper 类型
            model_size: 模型大小
            model_dir: 模型目录

        Returns:
            Dict[str, bool]: 验证结果
        """
        result = {
            "implementation_available": False,
            "model_exists_locally": False,
            "can_download": False,
        }

        # 检查实现是否可用
        available_types = cls.get_available_types()
        result["implementation_available"] = whisper_type in available_types

        if not result["implementation_available"]:
            return result

        # 创建临时配置检查模型
        try:
            config = ModelConfig(
                whisper_type=whisper_type,
                model_dir=model_dir,
                auto_download=False,
            )
            pipeline = cls._create_pipeline_instance(whisper_type, config)

            # 检查模型是否存在
            available_models = pipeline.get_available_models()
            result["model_exists_locally"] = model_size in available_models

            # 检查是否可以下载
            result["can_download"] = True  # 大多数情况下都可以下载

        except Exception as e:
            print(f"验证模型可用性时出错: {e}")

        return result


# 便捷函数
def create_whisper_pipeline(
    whisper_type: str = "faster-whisper",
    model_dir: str = "models",
    device: str = "auto",
    **kwargs,
) -> BaseTranscriptionPipeline:
    """创建 Whisper 转录管道的便捷函数

    Args:
        whisper_type: Whisper 实现类型
        model_dir: 模型目录
        device: 计算设备
        **kwargs: 其他配置参数

    Returns:
        BaseTranscriptionPipeline: 转录管道实例
    """
    config = ModelFactory.create_default_config(
        whisper_type=whisper_type, model_dir=model_dir, device=device, **kwargs
    )

    return ModelFactory.create_pipeline(whisper_type, config)


def get_available_implementations() -> Dict[str, Dict]:
    """获取所有可用实现的详细信息

    Returns:
        Dict[str, Dict]: 实现信息字典
    """
    implementations = {}

    for impl_type in ModelFactory.get_available_types():
        try:
            # 创建临时实例获取信息
            config = ModelFactory.create_default_config(whisper_type=impl_type)
            pipeline = ModelFactory._create_pipeline_instance(
                impl_type, config
            )

            implementations[impl_type] = {
                "available_models": pipeline.get_available_models(),
                "device": pipeline.get_device(),
                "description": {
                    "whisper": "原版 OpenAI Whisper，兼容性最好",
                    "faster-whisper": "优化版本，速度更快，内存使用更少",
                    "insanely-fast-whisper": "极速版本，适合批量处理",
                }.get(impl_type, "未知实现"),
            }

        except Exception as e:
            implementations[impl_type] = {
                "available_models": [],
                "device": "unknown",
                "description": f"Error: {str(e)}",
            }

    return implementations
