import os
import tempfile
from typing import List, Tuple

import gradio as gr

from modules.data_classes import ModelConfig, WhisperParams
from modules.download_manager import get_download_manager
from modules.model_factory import (
    ModelFactory,
    get_available_implementations,
)


class VoiceCaptionUI:
    """语音字幕提取界面"""

    def __init__(self):
        self.current_pipeline = None
        self.download_manager = get_download_manager()
        self.available_implementations = get_available_implementations()

    def create_interface(self):
        """创建 Gradio 界面"""
        with gr.Blocks(title="语音字幕提取器") as demo:
            gr.Markdown("# 🎵 语音字幕提取器")
            gr.Markdown("支持多种 Whisper 实现，智能模型管理，自动下载功能")

            # 主要转录功能
            self.setup_transcription_interface()

            # 系统信息（使用 Accordion，默认关闭）
            with gr.Accordion("📊 系统信息", open=False):
                self.render_system_info()

        return demo

    def setup_transcription_interface(self):
        """创建转录标签页"""
        # 配置区域
        gr.Markdown("### ⚙️ 配置选项")

        with gr.Row():
            # Whisper 实现选择
            whisper_type = gr.Dropdown(
                choices=list(self.available_implementations.keys()),
                value=ModelFactory.get_recommended_type(),
                label="🤖 Whisper 实现",
                info="选择 Whisper 实现类型",
            )

        # 模型选择（智能下载）
        recommended_type = ModelFactory.get_recommended_type()
        available_models = self.get_available_models(recommended_type)
        # 优先选择 medium 模型，如果不可用则选择第一个
        default_model = None
        if available_models:
            if "medium" in available_models:
                default_model = "medium"
            else:
                default_model = available_models[0]

            model_size = gr.Dropdown(
                choices=available_models,
                value=default_model,
                label="📦 模型大小",
                info="选择模型大小，未下载的模型将自动下载",
                interactive=True,
            )

        # 模型下载按钮（初始化时检查状态）
        initial_whisper_type = ModelFactory.get_recommended_type()
        initial_models = self.get_available_models(initial_whisper_type)
        # 优先选择 medium 模型，如果不可用则选择第一个
        initial_model = None
        if initial_models:
            if "medium" in initial_models:
                initial_model = "medium"
            else:
                initial_model = initial_models[0]

        # 检查初始模型状态
        if initial_model:
            _, initial_btn_state = self.check_model_download_status(
                initial_whisper_type, initial_model
            )
            download_model_btn = initial_btn_state
        else:
            download_model_btn = gr.Button(
                "📥 下载模型", variant="primary", visible=False
            )

        # 音频上传区域
        gr.Markdown("### 🎵 音频上传")
        audio_input = gr.Audio(
            label="上传音频文件", type="filepath", sources=["upload"]
        )

        # 高级参数区域
        with gr.Accordion("⚙️ 高级参数", open=False):
            with gr.Row():
                is_translate = gr.Checkbox(
                    label="🔄 翻译为英文",
                    value=False,
                    info="是否将结果翻译为英文",
                )

            with gr.Row():
                temperature = gr.Slider(
                    minimum=0.0,
                    maximum=1.0,
                    value=0.0,
                    step=0.1,
                    label="🌡️ 温度",
                    info="采样温度，0为确定性输出",
                )

                beam_size = gr.Slider(
                    minimum=1,
                    maximum=10,
                    value=5,
                    step=1,
                    label="🔍 束搜索大小",
                    info="束搜索大小，越大质量越高但速度越慢",
                )

        # 转录按钮
        transcribe_btn = gr.Button("🚀 开始转录", variant="primary", size="lg")

        # 结果显示区域
        gr.Markdown("### 📋 转录结果")

        # 转录结果表格
        result_table = gr.DataFrame(
            headers=[
                "序号",
                "开始时间",
                "结束时间",
                "时长",
                "置信度",
                "文本内容",
            ],
            datatype=["number", "str", "str", "str", "str", "str"],
            interactive=False,
        )

        # SRT 字幕文件下载
        srt_file = gr.File(
            label="下载 SRT 字幕文件", visible=False, interactive=False
        )

        # 绑定事件
        # 检查模型状态
        def check_model_status(whisper_type, model_size):
            return self.check_model_download_status(whisper_type, model_size)

        # 更新模型选择和下载按钮
        def update_models_and_button(whisper_type):
            available_models = self.get_available_models(whisper_type)
            # 优先选择 medium 模型，如果不可用则选择第一个
            default_model = None
            if available_models:
                if "medium" in available_models:
                    default_model = "medium"
                else:
                    default_model = available_models[0]

            if default_model:
                _, btn = self.check_model_download_status(
                    whisper_type, default_model
                )
            else:
                btn = gr.Button(visible=False)
            return (
                gr.Dropdown(choices=available_models, value=default_model),
                btn,
            )

        whisper_type.change(
            fn=update_models_and_button,
            inputs=[whisper_type],
            outputs=[model_size, download_model_btn],
        )

        def check_download_button(whisper_type, model_size):
            _, btn = self.check_model_download_status(whisper_type, model_size)
            return btn

        model_size.change(
            fn=check_download_button,
            inputs=[whisper_type, model_size],
            outputs=[download_model_btn],
        )

        # 下载模型 - 分两步：先显示进度，再执行下载
        def start_download_progress(whisper_type, model_size):
            return self.show_download_progress(whisper_type, model_size)

        def complete_download(whisper_type, model_size):
            _, btn = self.download_model(whisper_type, model_size)
            return btn

        # 点击下载按钮时立即显示进度
        download_model_btn.click(
            fn=start_download_progress,
            inputs=[whisper_type, model_size],
            outputs=[download_model_btn],
        ).then(
            fn=complete_download,
            inputs=[whisper_type, model_size],
            outputs=[download_model_btn],
        )

        transcribe_btn.click(
            fn=self.process_audio_transcription,
            inputs=[
                audio_input,
                whisper_type,
                model_size,
                is_translate,
                temperature,
                beam_size,
            ],
            outputs=[
                result_table,
                srt_file,
            ],
        )

    def setup_model_management_interface(self):
        """设置模型管理界面"""
        # 已缓存模型区域
        gr.Markdown("### 📦 已缓存模型")

        # 刷新按钮
        refresh_btn = gr.Button("🔄 刷新列表")

        # 模型列表
        model_list = gr.DataFrame(
            label="模型列表",
            headers=["模型名称", "类型", "大小(MB)", "下载时间"],
            datatype=["str", "str", "number", "str"],
        )

        # 缓存统计
        cache_stats = gr.JSON(
            label="📊 缓存统计",
            value=self.download_manager.get_cache_stats(),
        )

        # 缓存管理区域
        gr.Markdown("### 🗑️ 缓存管理")

        # 清理缓存
        cleanup_size = gr.Slider(
            minimum=1.0,
            maximum=20.0,
            value=10.0,
            step=0.5,
            label="目标缓存大小 (GB)",
        )

        cleanup_btn = gr.Button("🧹 清理缓存", variant="secondary")

        cleanup_result = gr.Textbox(label="清理结果", interactive=False)

        # 手动下载区域
        gr.Markdown("### ⬇️ 手动下载")

        with gr.Row():
            download_type = gr.Dropdown(
                choices=list(self.available_implementations.keys()),
                label="Whisper 类型",
            )

            download_model = gr.Textbox(
                label="模型名称",
                placeholder="例如: base, medium, large-v3",
            )

        manual_download_btn = gr.Button("⬇️ 下载模型", variant="primary")

        download_progress = gr.Textbox(label="下载进度", interactive=False)

        # 绑定事件
        refresh_btn.click(
            fn=self.refresh_model_cache_list, outputs=[model_list, cache_stats]
        )

        cleanup_btn.click(
            fn=self.cleanup_model_cache,
            inputs=[cleanup_size],
            outputs=[cleanup_result, model_list, cache_stats],
        )

        manual_download_btn.click(
            fn=self.manual_download_model,
            inputs=[download_type, download_model],
            outputs=[download_progress, model_list],
        )

    def render_system_info(self):
        """创建系统信息内容"""
        # 获取系统信息并转换为表格数据
        system_info = self.get_system_info_data()

        gr.Dataframe(
            value=system_info,
            headers=["项目", "值"],
            datatype=["str", "str"],
            interactive=False,
            wrap=True,
        )

    def get_available_models(self, whisper_type: str) -> List[str]:
        """获取指定类型的可用模型列表"""
        try:
            config = ModelFactory.create_default_config(
                whisper_type=whisper_type
            )
            pipeline = ModelFactory.create_pipeline(whisper_type, config)
            return pipeline.get_available_models()
        except Exception as e:
            print(f"获取可用模型失败: {e}")
            # 返回默认模型列表作为后备
            return ["tiny", "base", "small", "medium", "large-v3"]

    def check_model_download_status(
        self, whisper_type: str, model_size: str
    ) -> tuple:
        """检查模型状态（仅显示未下载的模型）"""
        try:
            # 获取已缓存的模型
            cached_models = self.download_manager.list_cached_models()

            # 检查模型是否已下载
            model_exists = any(
                model["model_name"] == model_size
                and model["whisper_type"] == whisper_type
                for model in cached_models
            )

            if model_exists:
                # 已下载的模型不显示状态信息
                return ("", gr.Button(visible=False))
            else:
                return (
                    f"⚠️ 模型 {model_size} ({whisper_type}) 未下载，需要下载后使用",
                    gr.Button(
                        "📥 下载模型",
                        visible=True,
                        variant="primary",
                        interactive=True,
                    ),
                )
        except Exception as e:
            print(f"检查模型状态失败: {e}")
            return (f"❌ 检查模型状态失败: {str(e)}", gr.Button(visible=False))

    def download_model(self, whisper_type: str, model_size: str) -> tuple:
        """下载模型"""
        try:
            # 下载模型
            model_path = self.download_manager.download_whisper_model(
                model_size, whisper_type
            )

            return (
                f"✅ 模型 {model_size} ({whisper_type}) 下载完成: {model_path}",
                gr.Button(visible=False),
            )
        except Exception as e:
            error_msg = f"❌ 下载失败: {str(e)}"
            print(error_msg)
            return (
                error_msg,
                gr.Button(
                    "📥 重试下载",
                    visible=True,
                    variant="primary",
                    interactive=True,
                ),
            )

    def show_download_progress(
        self, whisper_type: str, model_size: str
    ) -> gr.Button:
        """开始下载并显示进度状态"""
        # 立即返回进度状态按钮
        return gr.Button(
            f"⏳ 正在下载 {model_size}...",
            variant="secondary",
            visible=True,
            interactive=False,
        )

    def update_model_dropdown(self, whisper_type: str) -> gr.Dropdown:
        """更新模型选择下拉菜单"""
        try:
            # 获取已缓存的模型
            cached_models = self.download_manager.list_cached_models()

            # 筛选出对应类型的模型
            available_models = [
                model["model_name"]
                for model in cached_models
                if model["whisper_type"] == whisper_type
            ]

            if not available_models:
                # 如果没有已下载的模型，显示提示
                return gr.Dropdown(
                    choices=["请先在模型管理中下载模型"],
                    value="请先在模型管理中下载模型",
                    interactive=False,
                )

            return gr.Dropdown(
                choices=available_models,
                value=available_models[0],
                interactive=True,
            )
        except Exception as e:
            print(f"更新模型列表失败: {e}")
            return gr.Dropdown(
                choices=["请先在模型管理中下载模型"],
                value="请先在模型管理中下载模型",
                interactive=False,
            )

    def process_audio_transcription(
        self,
        audio_file: str,
        whisper_type: str,
        model_size: str,
        is_translate: bool,
        temperature: float,
        beam_size: int,
    ) -> Tuple[List[List], gr.File]:
        """转录音频"""
        if not audio_file:
            return (
                [],
                gr.File(visible=False),
            )

        # 自动下载模型（如果未下载）
        try:
            cached_models = self.download_manager.list_cached_models()
            model_exists = any(
                model["model_name"] == model_size
                and model["whisper_type"] == whisper_type
                for model in cached_models
            )

            if not model_exists:
                print(
                    f"模型 {model_size} ({whisper_type}) 未下载，开始自动下载..."
                )
                self.download_manager.download_whisper_model(
                    model_size, whisper_type
                )
                print(f"模型 {model_size} ({whisper_type}) 下载完成")
        except Exception as e:
            print(f"自动下载模型失败: {e}")
            return (
                [],
                gr.File(visible=False),
            )

        try:
            # 更新进度
            progress_msg = "🔄 初始化模型..."

            # 创建配置
            config = ModelConfig(
                whisper_type=whisper_type,
                model_dir="models",
                auto_download=True,
            )

            # 创建管道
            self.current_pipeline = ModelFactory.create_pipeline(
                whisper_type, config
            )

            # 创建参数
            params = WhisperParams(
                model_size=model_size,  # 使用用户选择的模型
                language=None,  # None 表示自动检测语言
                is_translate=is_translate,
                temperature=temperature,
                beam_size=int(beam_size),
            )

            # 进度回调
            def progress_callback(progress: float, message: str):
                nonlocal progress_msg
                progress_msg = f"📈 {message} ({progress * 100:.1f}%)"

            # 执行转录
            result = self.current_pipeline.transcribe(
                audio_file, params, progress_callback=progress_callback
            )

            # 格式化结果
            table_data = []
            for i, segment in enumerate(result.segments):
                if segment.start is not None and segment.end is not None:
                    duration = segment.end - segment.start
                    confidence = (
                        f"{(1 - (segment.no_speech_prob or 0)) * 100:.1f}%"
                    )
                    text = segment.text.strip() if segment.text else ""

                    table_data.append(
                        [
                            i + 1,
                            self.current_pipeline.format_timestamp(
                                segment.start
                            ),
                            self.current_pipeline.format_timestamp(
                                segment.end
                            ),
                            f"{duration:.1f}s",
                            confidence,
                            text,
                        ]
                    )

            # 生成 SRT 文件
            srt_content = self.current_pipeline.generate_srt(result.segments)

            # 生成有意义的文件名
            import datetime

            audio_name = os.path.splitext(os.path.basename(audio_file))[0]
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{audio_name}_{timestamp}.srt"

            # 创建临时 SRT 文件
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, filename)

            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

            return (
                table_data,
                gr.File(value=temp_path, visible=True),
            )

        except Exception as e:
            error_msg = f"❌ 转录失败: {str(e)}"
            print(error_msg)  # 输出到控制台
            return (
                [],
                gr.File(visible=False),
            )

    def generate_subtitle_file(
        self, table_data: List[List], audio_file: str
    ) -> gr.File:
        """生成字幕文件"""
        # Check if table_data is empty (handle both list and DataFrame)
        is_empty = (
            not table_data
            if isinstance(table_data, list)
            else table_data is None or len(table_data) == 0
        )
        if is_empty or not self.current_pipeline:
            return gr.File(visible=False)

        try:
            # 重建 segments
            segments = []
            for row in table_data:
                try:
                    # 验证数据格式
                    if len(row) < 6:
                        continue

                    # 解析时间戳，添加错误处理
                    start_parts = str(row[1]).split(":")
                    if len(start_parts) != 3:
                        continue

                    start_seconds = (
                        int(start_parts[0]) * 3600
                        + int(start_parts[1]) * 60
                        + float(start_parts[2].replace(",", "."))
                    )

                    end_parts = str(row[2]).split(":")
                    if len(end_parts) != 3:
                        continue

                    end_seconds = (
                        int(end_parts[0]) * 3600
                        + int(end_parts[1]) * 60
                        + float(end_parts[2].replace(",", "."))
                    )

                    from modules.data_classes import Segment

                    segment = Segment(
                        id=int(row[0]) if str(row[0]).isdigit() else 0,
                        start=start_seconds,
                        end=end_seconds,
                        text=str(row[5]) if len(row) > 5 else "",
                    )
                    segments.append(segment)

                except (ValueError, IndexError) as e:
                    # 跳过无法解析的行
                    print(f"跳过无效数据行: {row}, 错误: {e}")
                    continue

            # 检查是否有有效的 segments
            if not segments:
                print("警告: 没有有效的字幕段落数据")
                return gr.File(visible=False)

            print(f"成功解析 {len(segments)} 个字幕段落")

            # 生成 SRT 内容
            srt_content = self.current_pipeline.generate_srt(segments)

            if not srt_content or not srt_content.strip():
                print("警告: 生成的 SRT 内容为空")
                return gr.File(visible=False)

            print(f"生成的 SRT 内容长度: {len(srt_content)} 字符")

            # 创建临时文件
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".srt", delete=False, encoding="utf-8"
            ) as f:
                f.write(srt_content)
                temp_path = f.name

            return gr.File(value=temp_path, visible=True)

        except Exception as e:
            print(f"生成字幕文件失败: {e}")
            return gr.File(visible=False)

    def refresh_model_cache_list(self) -> Tuple[List[List], dict]:
        """刷新模型列表"""
        try:
            models = self.download_manager.list_cached_models()
            table_data = []

            for model in models:
                table_data.append(
                    [
                        model["model_name"],
                        model["whisper_type"],
                        round(model["size_mb"], 1),
                        model["download_time"][:19].replace("T", " "),
                    ]
                )

            stats = self.download_manager.get_cache_stats()
            return table_data, stats

        except Exception as e:
            print(f"刷新模型列表失败: {e}")
            return [], {"downloads": {}, "last_cleanup": None, "total_size": 0}

    def cleanup_model_cache(
        self, target_size: float
    ) -> Tuple[str, List[List], dict]:
        """清理模型缓存"""
        try:
            result = self.download_manager.cleanup_cache(target_size)

            freed_mb = result["freed_bytes"] / (1024 * 1024)
            message = (
                f"清理完成：删除了 {result['removed_count']} 个模型，"
                f"释放了 {freed_mb:.1f} MB 空间"
            )

            # 刷新列表
            models, stats = self.refresh_model_cache_list()

            return message, models, stats

        except Exception as e:
            return f"清理失败: {str(e)}", [], {}

    def manual_download_model(
        self, whisper_type: str, model_name: str
    ) -> Tuple[str, List[List]]:
        """手动下载模型"""
        if not whisper_type or not model_name:
            return "请选择 Whisper 类型和模型名称", []

        try:
            progress_msg = "开始下载..."

            def progress_callback(progress: float, message: str):
                nonlocal progress_msg
                progress_msg = f"{message} ({progress * 100:.1f}%)"

            # 下载模型
            model_path = self.download_manager.download_whisper_model(
                model_name, whisper_type, progress_callback
            )

            # 刷新列表
            models, _ = self.refresh_model_cache_list()

            return f"✅ 下载完成: {model_path}", models

        except Exception as e:
            return f"❌ 下载失败: {str(e)}", []

    def get_system_info_data(self) -> List[List[str]]:
        """获取系统信息表格数据"""
        import platform

        try:
            import torch

            cuda_available = torch.cuda.is_available()
            cuda_version = torch.version.cuda if cuda_available else None
        except ImportError:
            cuda_available = False
            cuda_version = None

        try:
            import psutil

            cpu_count = psutil.cpu_count()
            memory_gb = round(psutil.virtual_memory().total / (1024**3), 1)
        except ImportError:
            cpu_count = 0
            memory_gb = 0

        # 转换为表格数据，使用中文字段名
        table_data = [
            ["操作系统", platform.platform()],
            ["Python 版本", platform.python_version()],
            ["CPU 核心数", str(cpu_count)],
            ["内存大小", f"{memory_gb} GB"],
            ["CUDA 支持", "是" if cuda_available else "否"],
        ]

        # 只有在 CUDA 可用时才显示版本
        if cuda_available and cuda_version:
            table_data.append(["CUDA 版本", cuda_version])

        return table_data


def main():
    """主函数"""
    app = VoiceCaptionUI()
    demo = app.create_interface()

    demo.launch(
        server_name="0.0.0.0", server_port=17860, share=False, show_error=False
    )


if __name__ == "__main__":
    main()
