
# 🎵 语音字幕提取器

一个现代化的语音转文字工具，基于 OpenAI Whisper 和 Gradio 构建，提供智能模型管理和自动字幕生成功能。

## ✨ 功能特性

- 🎧 **多格式音频支持** - 支持 MP3, WAV, FLAC, AAC, OGG 等主流音频格式
- 🤖 **高精度语音识别** - 基于 OpenAI Whisper 模型，提供专业级识别准确度
- 🧠 **智能模型管理** - 自动检测、下载和缓存模型，无需手动管理
- 📊 **详细转录分析** - 实时显示转录进度，包含时间轴、置信度、文本内容等
- 📝 **标准字幕格式** - 自动生成 SRT 格式字幕文件，兼容主流播放器
- 🌐 **现代化界面** - 响应式 Web 界面，支持拖拽上传和实时反馈
- 🔄 **自动语言检测** - 智能识别音频语言，支持多语言转录
- 💾 **缓存优化** - 智能模型缓存管理，节省存储空间和下载时间

## 🚀 快速开始

### 系统要求

- **Python**: 3.12+
- **内存**: 建议 4GB+ (取决于模型大小)
- **存储**: 1-5GB (用于模型缓存)
- **包管理器**: uv (推荐) 或 pip

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/ospoon/voice-caption.git
   cd voice-caption
   ```

2. **安装依赖**
   ```bash
   # 使用 uv (推荐)
   uv sync
   
   # 或使用 pip
   pip install -r requirements.txt
   ```

3. **启动应用**
   ```bash
   python webui.py
   ```

4. **访问界面**
   
   打开浏览器访问 `http://localhost:17860`

## 📖 使用指南

### 基本使用流程

1. **选择模型** - 系统默认推荐 `medium` 模型，平衡速度和精度
2. **模型管理** - 首次使用时会自动下载所需模型
3. **上传音频** - 支持拖拽或点击上传音频文件
4. **配置参数** - 可选择翻译模式和调整高级参数
5. **开始转录** - 点击转录按钮，实时查看进度
6. **查看结果** - 在表格中浏览详细转录结果
7. **下载字幕** - 一键下载 SRT 格式字幕文件

### 模型选择建议

| 模型 | 大小 | 速度 | 精度 | 推荐场景 |
|------|------|------|------|----------|
| tiny | ~39MB | 最快 | 基础 | 快速预览、实时转录 |
| base | ~74MB | 快 | 良好 | 日常使用、播客转录 |
| small | ~244MB | 中等 | 较好 | 会议记录、采访转录 |
| **medium** | ~769MB | 较慢 | **推荐** | **专业转录、字幕制作** |
| large-v3 | ~1550MB | 最慢 | 最佳 | 高质量要求、多语言 |

### 转录结果表格说明

| 列名 | 说明 |
|------|------|
| 序号 | 语音片段的序列号 |
| 开始时间 | 片段开始时间 (HH:MM:SS,mmm) |
| 结束时间 | 片段结束时间 (HH:MM:SS,mmm) |
| 时长 | 片段持续时间 |
| 字符数 | 文本字符数量 |
| 置信度 | 识别置信度百分比 |
| 文本内容 | 转录的文本内容 |

## 🛠️ 技术架构

### 核心技术
- **AI 引擎**: OpenAI Whisper (官方实现)
- **Web 框架**: Gradio 4.x
- **语言**: Python 3.12
- **包管理**: uv (现代化 Python 包管理)

### 架构特点
- **模块化设计**: 清晰的代码结构，易于维护和扩展
- **智能缓存**: 自动管理模型下载和存储
- **异步处理**: 非阻塞的转录处理流程
- **错误恢复**: 完善的异常处理和用户反馈

## 📁 项目结构

```
voice-caption/
├── webui.py                 # Web 界面主程序
├── modules/                 # 核心模块目录
│   ├── __init__.py         # 模块初始化
│   ├── base_pipeline.py    # 基础管道抽象
│   ├── data_classes.py     # 数据类定义
│   ├── download_manager.py # 模型下载管理
│   ├── model_factory.py    # 模型工厂
│   └── whisper_pipeline.py # Whisper 实现
├── pyproject.toml          # 项目配置
├── requirements.txt        # 依赖列表
├── README.md              # 项目文档
└── models/                # 模型缓存目录
    ├── .download_cache.json # 缓存元数据
    └── *.pt               # Whisper 模型文件
```

## ⚙️ 高级配置

### 模型管理

系统采用智能模型管理策略：

```python
# 自动模型选择（在 webui.py 中）
recommended_type = ModelFactory.get_recommended_type()  # 返回 "whisper"
default_model = "medium"  # 默认推荐模型
```

### 转录参数

可在界面中调整的参数：

```python
params = WhisperParams(
    model_size="medium",      # 模型大小
    language=None,            # 自动检测语言
    is_translate=False,       # 是否翻译为英文
    temperature=0.0,          # 采样温度 (0.0-1.0)
    beam_size=5,             # 束搜索大小
)
```

### 服务器配置

默认启动配置：
- **地址**: `0.0.0.0` (允许外部访问)
- **端口**: `17860`
- **调试模式**: 根据环境自动检测

自定义启动：
```python
# 在 webui.py 中修改
demo.launch(
    server_name="127.0.0.1",  # 仅本地访问
    server_port=8080,         # 自定义端口
    share=True               # 生成公共链接
)
```

## 🔧 开发指南

### 代码架构

项目采用现代化的模块化架构：

```python
# 主要类和方法
class VoiceCaptionUI:
    def setup_transcription_interface(self)     # 设置转录界面
    def setup_model_management_interface(self)  # 设置模型管理
    def process_audio_transcription(self)       # 处理音频转录
    def check_model_download_status(self)       # 检查模型状态
    def download_model(self)                    # 下载模型
```

### 扩展开发

**添加新功能**：
```python
# 1. 在 modules/ 中创建新模块
# 2. 继承 BaseTranscriptionPipeline
# 3. 在 ModelFactory 中注册
```

**自定义界面**：
```python
# 修改 setup_transcription_interface() 方法
# 添加新的 Gradio 组件和事件绑定
```

**新增字幕格式**：
```python
# 在 whisper_pipeline.py 中扩展
# 添加新的格式生成方法
```

## 🤝 贡献指南

我们欢迎各种形式的贡献：

1. **报告问题** - 提交详细的 Issue
2. **功能建议** - 分享您的想法和需求
3. **代码贡献** - 提交 Pull Request
4. **文档改进** - 帮助完善文档

### 开发流程

```bash
# 1. Fork 项目
# 2. 创建功能分支
git checkout -b feature/your-feature

# 3. 提交更改
git commit -m "Add your feature"

# 4. 推送分支
git push origin feature/your-feature

# 5. 创建 Pull Request
```

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 📞 支持与反馈

- **问题报告**: [GitHub Issues](https://github.com/ospoon/voice-caption/issues)
- **功能请求**: [GitHub Discussions](https://github.com/ospoon/voice-caption/discussions)
- **技术交流**: 欢迎提交 Issue 讨论

---

**让语音转文字变得简单高效！** 🎉✨