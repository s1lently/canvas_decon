import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

def upload_files(files, product):
    """预上传文件并返回元数据

    Returns:
        list[dict]: [{'filename': 'xxx.png', 'uri': '...', 'uploaded_obj': obj}, ...]
    """
    if product == 'Gemini':
        return _upload_gemini(files)
    elif product == 'Claude':
        return _upload_claude(files)
    raise ValueError(f"Unknown product: {product}")

def _upload_gemini(files):
    """Gemini 预上传 (使用新SDK)"""
    from google import genai
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    uploaded_info = []
    for f in files:
        if not os.path.exists(f):
            continue
        uploaded = client.files.upload(file=str(f))
        uploaded_info.append({
            'filename': os.path.basename(f),
            'uri': uploaded.name,
            'uploaded_obj': uploaded
        })
    return uploaded_info

def _upload_claude(files):
    """Claude 预处理（base64编码）"""
    import base64

    uploaded_info = []
    for f in files:
        if not os.path.exists(f):
            continue

        ext = os.path.splitext(f)[1].lower()
        data = base64.standard_b64encode(open(f, 'rb').read()).decode()

        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
            mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                   'gif': 'image/gif', 'webp': 'image/webp'}[ext[1:]]
            content_type = 'image'
        elif ext == '.pdf':
            mime = 'application/pdf'
            content_type = 'document'
        else:
            continue

        uploaded_info.append({
            'filename': os.path.basename(f),
            'size': os.path.getsize(f),
            'mime': mime,
            'type': content_type,
            'data': data
        })
    return uploaded_info

def call_ai(prompt, product, model, files=[], uploaded_info=None, thinking=False):
    """统一AI调用接口

    Args:
        prompt: 提示词
        product: 'Gemini' or 'Claude'
        model: 模型名称
        files: 文件路径列表（如果 uploaded_info 为 None）
        uploaded_info: 预上传的文件信息（来自 upload_files()）
        thinking: 是否启用thinking模式（仅Claude支持，默认False）

    Returns:
        str: AI生成的文本结果
    """
    if product == 'Gemini':
        return _gemini(prompt, model, uploaded_info=uploaded_info)
    elif product == 'Claude':
        return _claude(prompt, model, uploaded_info=uploaded_info, thinking=thinking)
    raise ValueError(f"Unknown product: {product}")

def _gemini(prompt, model, uploaded_info=None):
    """Gemini API调用 (使用新SDK)"""
    from google import genai
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    # 构建 contents
    contents = [prompt]
    if uploaded_info:
        # 添加上传的文件
        contents.extend([info['uploaded_obj'] for info in uploaded_info])

    # 调用 API
    response = client.models.generate_content(
        model=model,
        contents=contents
    )
    return response.text

def _claude(prompt, model, uploaded_info=None, thinking=False):
    """Claude API调用"""
    import anthropic

    # 强制使用官方API（忽略环境变量中的Claude Code代理设置）
    client = anthropic.Anthropic(
        api_key=config.CLAUDE_API_KEY,
        base_url="https://api.anthropic.com"
    )

    content = [{"type": "text", "text": prompt}]

    if uploaded_info:
        # 使用预处理的数据
        for info in uploaded_info:
            if info['type'] == 'image':
                content.append({"type": "image", "source": {"type": "base64", "media_type": info['mime'], "data": info['data']}})
            elif info['type'] == 'document':
                content.append({"type": "document", "source": {"type": "base64", "media_type": info['mime'], "data": info['data']}})

    # Build API parameters
    params = {
        "model": model,
        "max_tokens": 16384,
        "messages": [{"role": "user", "content": content}]
    }

    # Enable thinking mode if requested
    if thinking:
        params["thinking"] = {"type": "enabled", "budget_tokens": 8000}

    msg = client.messages.create(**params)

    # Extract text from response (thinking mode returns multiple blocks)
    for block in msg.content:
        if hasattr(block, 'text'):
            return block.text
    return ""
