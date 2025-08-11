import gradio as gr
import whisper
import tempfile
import os
from datetime import datetime, timedelta

# 加载 Whisper 模型
model = whisper.load_model("medium", download_root="models")

def format_timestamp(seconds):
    """将秒数转换为 SRT 时间格式"""
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{milliseconds:03d}"

def generate_srt(segments):
    """生成 SRT 字幕格式"""
    srt_content = ""
    for i, segment in enumerate(segments, 1):
        start_time = format_timestamp(segment['start'])
        end_time = format_timestamp(segment['end'])
        text = segment['text'].strip()
        srt_content += f"{i}\n{start_time} --> {end_time}\n{text}\n\n"
    return srt_content

def transcribe_audio(audio_file):
    """转录音频并生成字幕文件"""
    if audio_file is None:
        return [], None
    
    try:
        # 转录音频
        result = model.transcribe(audio_file)
        
        # 生成表格数据
        table_data = []
        for segment in result['segments']:
            start_time = format_timestamp(segment['start'])
            end_time = format_timestamp(segment['end'])
            duration = segment['end'] - segment['start']
            duration_str = f"{duration:.1f}s"
            text = segment['text'].strip()
            char_count = len(text)
            confidence = f"{(1 - segment.get('no_speech_prob', 0)) * 100:.1f}%"
            table_data.append([segment['id'], start_time, end_time, duration_str, char_count, confidence, text])
        
        # 生成 SRT 字幕文件
        subtitle_content = generate_srt(result['segments'])
        
        # 生成有意义的文件名
        audio_filename = os.path.basename(audio_file)
        audio_name = os.path.splitext(audio_filename)[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        subtitle_filename = f"{audio_name}_{timestamp}.srt"
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(subtitle_content)
            subtitle_file_path = f.name
        
        # 重命名文件为有意义的名称
        final_path = os.path.join(os.path.dirname(subtitle_file_path), subtitle_filename)
        os.rename(subtitle_file_path, final_path)
        subtitle_file_path = final_path
        
        return table_data, subtitle_file_path
    
    except Exception as e:
        return [], None

# 创建 Gradio 界面
with gr.Blocks(title="语音字幕提取器") as demo:
    gr.Markdown("# 🎵 语音字幕提取器")
    gr.Markdown("上传音频文件，自动提取语音并生成字幕文件")
    
    # 上传区域
    audio_input = gr.Audio(
        label="上传音频文件",
        type="filepath",
        sources=["upload"]
    )
    
    submit_btn = gr.Button("开始转录", variant="primary", size="lg")
    
    # 结果显示区域
    output_table = gr.DataFrame(
        label="转录结果",
        headers=["序号", "开始时间", "结束时间", "时长", "字符数", "置信度", "文本内容"],
        datatype=["number", "str", "str", "str", "number", "str", "str"],
        interactive=False,
        wrap=True
    )
    
    download_file = gr.File(
        label="下载字幕文件"
    )
    
    # 绑定事件
    submit_btn.click(
        fn=transcribe_audio,
        inputs=[audio_input],
        outputs=[output_table, download_file]
    )
    
    gr.Markdown("### 使用说明")
    gr.Markdown("""
    1. 点击上传区域选择音频文件
    2. 点击"开始转录"按钮
    3. 等待处理完成后查看结果和下载 SRT 字幕文件
    
    **支持的文件格式**: MP3, WAV, FLAC, AAC, OGG 等常见音频格式
    """)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)