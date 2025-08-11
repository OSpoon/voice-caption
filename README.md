
# 🎵 语音字幕提取器

一个基于 OpenAI Whisper 和 Gradio 的语音转文字工具，支持音频文件上传并自动生成 SRT 字幕文件。

## ✨ 功能特性

- 🎧 **音频文件支持** - 支持 MP3, WAV, FLAC, AAC, OGG 等常见音频格式
- 🤖 **AI 语音识别** - 基于 OpenAI Whisper 模型，识别准确度高
- 📊 **详细转录结果** - 表格形式展示转录结果，包含时间轴、时长、置信度等信息
- 📝 **SRT 字幕生成** - 自动生成标准 SRT 格式字幕文件
- 🌐 **Web 界面** - 简洁易用的 Web 界面，支持文件拖拽上传
- 📱 **响应式设计** - 适配桌面和移动设备

## 🚀 快速开始

### 环境要求

- Python 3.12+
- uv (推荐) 或 pip

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
   
   打开浏览器访问 `http://localhost:7860`

## 📖 使用说明

1. **上传音频文件** - 点击上传区域选择音频文件
2. **开始转录** - 点击"开始转录"按钮
3. **查看结果** - 在表格中查看详细的转录结果
4. **下载字幕** - 下载生成的 SRT 字幕文件

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

## 🛠️ 技术栈

- **AI 模型**: OpenAI Whisper
- **Web 框架**: Gradio
- **语言**: Python 3.12
- **包管理**: uv

## 📁 项目结构

```
voice-caption/
├── webui.py          # Web 界面主程序
├── main.py           # 命令行版本
├── pyproject.toml    # 项目配置文件
├── README.md         # 项目说明文档
└── models/           # Whisper 模型存储目录
```

## ⚙️ 配置说明

### 模型配置

默认使用 `medium` 模型，可在 `webui.py` 中修改：

```python
model = whisper.load_model("medium", download_root="models")
```

可选模型大小：
- `tiny` - 最快，准确度较低
- `base` - 平衡速度和准确度
- `small` - 较好的准确度
- `medium` - 推荐，准确度高
- `large` - 最高准确度，速度较慢

### 服务器配置

默认配置：
- 地址: `0.0.0.0`
- 端口: `7860`

可在 `webui.py` 末尾修改：

```python
demo.launch(server_name="0.0.0.0", server_port=7860)
```

## 🔧 开发说明

### 命令行版本

除了 Web 界面，还提供命令行版本：

```bash
python main.py
```

### 自定义开发

项目结构清晰，易于扩展：

- 修改 `transcribe_audio()` 函数添加新功能
- 调整 Gradio 界面布局
- 添加新的字幕格式支持

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 支持

如有问题，请提交 Issue 或联系开发者。

---

**享受语音转文字的便利！** 🎉