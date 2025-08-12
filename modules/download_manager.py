import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class DownloadManager:
    """模型下载管理器，支持断点续传、进度回调和缓存管理"""

    def __init__(
        self, cache_dir: str = "models", max_cache_size_gb: float = 10.0
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_cache_size = (
            max_cache_size_gb * 1024 * 1024 * 1024
        )  # 转换为字节

        # 缓存元数据文件
        self.metadata_file = self.cache_dir / ".download_cache.json"
        self.metadata = self._load_metadata()

        # 下载锁，防止重复下载
        self._download_locks: Dict[str, threading.Lock] = {}

    def _load_metadata(self) -> Dict[str, Any]:
        """加载缓存元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    metadata: Dict[str, Any] = json.load(f)
                    return metadata
            except Exception as e:
                print(f"加载缓存元数据失败: {e}")

        return {"downloads": {}, "last_cleanup": None, "total_size": 0}

    def _save_metadata(self):
        """保存缓存元数据"""
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存缓存元数据失败: {e}")

    def download_whisper_model(
        self,
        model_name: str,
        whisper_type: str = "whisper",
        progress_callback: Optional[Callable[[float, str], None]] = None,
        force_download: bool = False,
    ) -> str:
        """下载 Whisper 模型

        Args:
            model_name: 模型名称
            whisper_type: Whisper 类型
            progress_callback: 进度回调函数
            force_download: 是否强制重新下载

        Returns:
            str: 模型文件路径
        """
        # 生成下载键
        download_key = f"{whisper_type}_{model_name}"

        # 检查是否已在下载
        if download_key in self._download_locks:
            print(f"模型 {model_name} 正在下载中，请等待...")
            while download_key in self._download_locks:
                time.sleep(1)

        # 检查本地是否已存在
        local_path = self._get_local_model_path(model_name, whisper_type)
        if local_path and not force_download:
            if progress_callback:
                progress_callback(1.0, "模型已存在")
            return str(local_path)

        # 开始下载
        self._download_locks[download_key] = threading.Lock()

        try:
            return self._download_model_impl(
                model_name, whisper_type, progress_callback
            )
        finally:
            # 清理下载锁
            if download_key in self._download_locks:
                del self._download_locks[download_key]

    def _download_model_impl(
        self,
        model_name: str,
        whisper_type: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> str:
        """实际的模型下载实现"""
        if whisper_type == "whisper":
            return self._download_openai_whisper(model_name, progress_callback)
        else:
            raise ValueError(f"不支持的 Whisper 类型: {whisper_type}")

    def _download_openai_whisper(
        self,
        model_name: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> str:
        """下载 OpenAI Whisper 模型"""
        try:
            import whisper

            if progress_callback:
                progress_callback(0.1, "开始下载 OpenAI Whisper 模型...")

            # 使用 whisper 库的下载功能
            whisper.load_model(model_name, download_root=str(self.cache_dir))

            if progress_callback:
                progress_callback(1.0, "下载完成")

            # 更新元数据
            model_path = self._get_local_model_path(model_name, "whisper")
            self._update_download_metadata(
                model_name, "whisper", str(model_path)
            )

            return str(model_path)

        except Exception as e:
            raise RuntimeError(f"下载 OpenAI Whisper 模型失败: {str(e)}")

    def _get_local_model_path(
        self, model_name: str, whisper_type: str
    ) -> Optional[Path]:
        """获取本地模型路径"""
        if whisper_type == "whisper":
            # OpenAI Whisper 模型路径
            model_file = self.cache_dir / f"{model_name}.pt"
            if model_file.exists():
                return model_file

        return None

    def _update_download_metadata(
        self, model_name: str, whisper_type: str, path: str
    ):
        """更新下载元数据"""
        download_key = f"{whisper_type}_{model_name}"

        # 计算文件大小
        size = self._calculate_path_size(Path(path))

        self.metadata["downloads"][download_key] = {
            "model_name": model_name,
            "whisper_type": whisper_type,
            "path": path,
            "size": size,
            "download_time": datetime.now().isoformat(),
            "last_access": datetime.now().isoformat(),
        }

        self.metadata["total_size"] = sum(
            item["size"] for item in self.metadata["downloads"].values()
        )

        self._save_metadata()

    def _calculate_path_size(self, path: Path) -> int:
        """计算路径大小"""
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            return sum(
                f.stat().st_size for f in path.rglob("*") if f.is_file()
            )
        return 0

    def list_cached_models(self) -> List[Dict]:
        """列出已缓存的模型"""
        models = []
        for key, info in self.metadata["downloads"].items():
            # 检查文件是否仍然存在
            if Path(info["path"]).exists():
                models.append(
                    {
                        "key": key,
                        "model_name": info["model_name"],
                        "whisper_type": info["whisper_type"],
                        "path": info["path"],
                        "size_mb": info["size"] / (1024 * 1024),
                        "download_time": info["download_time"],
                        "last_access": info["last_access"],
                    }
                )
            else:
                # 清理不存在的条目
                self._remove_from_metadata(key)

        return sorted(models, key=lambda x: x["last_access"], reverse=True)

    def cleanup_cache(
        self, target_size_gb: Optional[float] = None
    ) -> Dict[str, int]:
        """清理缓存

        Args:
            target_size_gb: 目标缓存大小（GB），如果为 None 则使用默认限制

        Returns:
            Dict[str, int]: 清理统计信息
        """
        target_size = (
            (target_size_gb or (self.max_cache_size / 1024 / 1024 / 1024))
            * 1024
            * 1024
            * 1024
        )

        current_size = self.metadata["total_size"]
        if current_size <= target_size:
            return {"removed_count": 0, "freed_bytes": 0}

        # 按最后访问时间排序，删除最旧的
        models = self.list_cached_models()
        models.sort(key=lambda x: x["last_access"])

        removed_count = 0
        freed_bytes = 0

        for model in models:
            if current_size <= target_size:
                break

            # 删除模型文件
            model_path = Path(model["path"])
            if model_path.exists():
                try:
                    if model_path.is_file():
                        model_path.unlink()
                    elif model_path.is_dir():
                        import shutil

                        shutil.rmtree(model_path)

                    freed_bytes += model["size_mb"] * 1024 * 1024
                    current_size -= model["size_mb"] * 1024 * 1024
                    removed_count += 1

                    # 从元数据中移除
                    self._remove_from_metadata(model["key"])

                    print(
                        f"已删除模型: {model['model_name']} \
                            ({model['whisper_type']})"
                    )

                except Exception as e:
                    print(f"删除模型失败 {model['model_name']}: {e}")

        self.metadata["last_cleanup"] = datetime.now().isoformat()
        self._save_metadata()

        return {"removed_count": removed_count, "freed_bytes": freed_bytes}

    def _remove_from_metadata(self, key: str):
        """从元数据中移除条目"""
        if key in self.metadata["downloads"]:
            del self.metadata["downloads"][key]
            self.metadata["total_size"] = sum(
                item["size"] for item in self.metadata["downloads"].values()
            )

    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        total_size_mb = self.metadata["total_size"] / (1024 * 1024)
        max_size_mb = self.max_cache_size / (1024 * 1024)

        return {
            "total_models": len(self.metadata["downloads"]),
            "total_size_mb": total_size_mb,
            "max_size_mb": max_size_mb,
            "usage_percent": (
                (total_size_mb / max_size_mb) * 100 if max_size_mb > 0 else 0
            ),
            "last_cleanup": self.metadata.get("last_cleanup"),
            "cache_dir": str(self.cache_dir),
        }

    def verify_model_integrity(
        self, model_name: str, whisper_type: str
    ) -> bool:
        """验证模型完整性

        Args:
            model_name: 模型名称
            whisper_type: Whisper 类型

        Returns:
            bool: 模型是否完整
        """
        model_path = self._get_local_model_path(model_name, whisper_type)
        if not model_path or not model_path.exists():
            return False

        try:
            if whisper_type == "whisper":
                # 检查 .pt 文件
                import torch

                torch.load(model_path, map_location="cpu")
                return True

        except Exception as e:
            print(f"验证模型完整性时出错: {e}")
            return False

        return False

    def remove_model(self, model_name: str, whisper_type: str) -> bool:
        """删除指定模型

        Args:
            model_name: 模型名称
            whisper_type: Whisper 类型

        Returns:
            bool: 是否删除成功
        """
        download_key = f"{whisper_type}_{model_name}"

        if download_key not in self.metadata["downloads"]:
            return False

        model_info = self.metadata["downloads"][download_key]
        model_path = Path(model_info["path"])

        try:
            if model_path.exists():
                if model_path.is_file():
                    model_path.unlink()
                elif model_path.is_dir():
                    import shutil

                    shutil.rmtree(model_path)

            self._remove_from_metadata(download_key)
            self._save_metadata()

            print(f"已删除模型: {model_name} ({whisper_type})")
            return True

        except Exception as e:
            print(f"删除模型失败: {e}")
            return False


# 全局下载管理器实例
_global_download_manager = None


def get_download_manager(cache_dir: str = "models") -> DownloadManager:
    """获取全局下载管理器实例"""
    global _global_download_manager
    if _global_download_manager is None:
        _global_download_manager = DownloadManager(cache_dir)
    return _global_download_manager
