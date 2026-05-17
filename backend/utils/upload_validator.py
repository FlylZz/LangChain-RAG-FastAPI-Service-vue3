"""
文件上传安全校验工具
提供 MIME 类型检测、文件大小限制、扩展名白名单
"""
import os

from fastapi import HTTPException, UploadFile


# ==================== 预设白名单 ====================

AVATAR_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
AVATAR_ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp"
}
AVATAR_MAX_SIZE = 5 * 1024 * 1024  # 5MB

DOCUMENT_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".pptx"}
DOCUMENT_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
DOCUMENT_MAX_SIZE = 20 * 1024 * 1024  # 20MB


async def validate_upload(
    file: UploadFile,
    allowed_extensions: set[str] = None,
    allowed_mime_types: set[str] = None,
    max_size: int = 5 * 1024 * 1024,
    category: str = "文件",
) -> bytes:
    """
    校验上传文件的安全性

    :param file: FastAPI UploadFile 对象
    :param allowed_extensions: 允许的扩展名集合，如 {".jpg", ".png"}
    :param allowed_mime_types: 允许的 MIME 类型集合
    :param max_size: 最大文件大小（字节）
    :param category: 文件类别描述（用于错误提示）
    :return: 文件内容字节（已读取，调用方无需再 read）
    """
    # 1. 扩展名校验
    if allowed_extensions:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"{category}格式不支持，允许的类型：{', '.join(sorted(allowed_extensions))}，当前文件：{ext or '未知'}"
            )

    # 2. 读取文件内容 + 大小校验
    content = await file.read()
    if len(content) > max_size:
        max_mb = round(max_size / (1024 * 1024), 1)
        raise HTTPException(
            status_code=400,
            detail=f"{category}大小不能超过 {max_mb}MB"
        )

    # 3. MIME 类型校验（基于文件头魔数检测，比扩展名更可靠）
    if allowed_mime_types:
        detected_mime = _detect_mime_by_magic(content)
        if detected_mime and detected_mime not in allowed_mime_types:
            raise HTTPException(
                status_code=400,
                detail=f"{category}MIME类型不支持（检测到：{detected_mime}）"
            )

    # 重置文件指针（供后续使用）
    await file.seek(0)

    return content


def _detect_mime_by_magic(content: bytes) -> str | None:
    """
    通过文件头魔数检测 MIME 类型（不依赖 python-magic 系统库）
    覆盖常见图片和文档格式
    """
    if len(content) < 4:
        return None

    # 图片格式
    if content[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    if content[:2] == b'\xff\xd8':
        return "image/jpeg"
    if content[:6] in (b'GIF87a', b'GIF89a'):
        return "image/gif"
    if content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        return "image/webp"

    # PDF
    if content[:5] == b'%PDF-':
        return "application/pdf"

    # Office Open XML (docx, pptx, xlsx 都是 ZIP 包)
    if content[:4] == b'PK\x03\x04':
        # 无法仅凭魔数区分 docx/pptx/xlsx，返回通用类型
        return "application/zip"

    # 纯文本（简单启发式）
    try:
        content[:512].decode("utf-8")
        return "text/plain"
    except UnicodeDecodeError:
        pass

    return None
