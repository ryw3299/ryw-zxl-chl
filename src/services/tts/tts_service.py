"""语音合成服务：基于 edge-tts，将脚本章节文本批量合成为音频文件。

业务侧只暴露两个函数：
- ``synthesize_section`` 合成单段
- ``synthesize_sections`` 批量合成多段并返回每段的时长与文件路径

音色名称使用业务层命名（``female_standard`` 等），内部映射到具体 Edge TTS 音色。
后续替换为阿里云/火山等其他 TTS 提供商，只需修改本模块。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


VOICE_MAP: dict[str, str] = {
    "female_standard": "zh-CN-XiaoxiaoNeural",
    "female_sweet": "zh-CN-XiaoyiNeural",
    "female_news": "zh-CN-XiaohanNeural",
    "male_standard": "zh-CN-YunyangNeural",
    "male_professional": "zh-CN-YunxiNeural",
    "male_warm": "zh-CN-YunjianNeural",
}

DEFAULT_VOICE = "female_standard"


def resolve_voice(voice_type: str) -> str:
    return VOICE_MAP.get(voice_type) or VOICE_MAP[DEFAULT_VOICE]


@dataclass
class SectionAudio:
    section_id: str
    file_path: Path
    duration_seconds: float
    file_size: int


async def _synthesize_one(text: str, voice: str, output_path: Path) -> float:
    """调用 edge-tts 合成一段文本，写入 mp3 文件，返回时长（秒）。"""
    import edge_tts

    output_path.parent.mkdir(parents=True, exist_ok=True)

    communicator = edge_tts.Communicate(text, voice)
    last_offset_100ns = 0
    last_duration_100ns = 0

    with open(output_path, "wb") as audio_file:
        async for chunk in communicator.stream():
            chunk_type = chunk.get("type")
            if chunk_type == "audio":
                audio_file.write(chunk["data"])
            elif chunk_type == "WordBoundary":
                last_offset_100ns = chunk.get("offset", last_offset_100ns)
                last_duration_100ns = chunk.get("duration", last_duration_100ns)

    total_100ns = last_offset_100ns + last_duration_100ns
    if total_100ns <= 0:
        return max(1.0, len(text) / 5.0)
    return total_100ns / 10_000_000.0


def synthesize_section(
    *,
    text: str,
    voice: str,
    output_path: Path,
) -> float:
    """合成单段文本为音频文件，返回时长（秒）。同步接口。"""
    if not text or not text.strip():
        raise ValueError("合成文本为空")
    return asyncio.run(_synthesize_one(text.strip(), voice, output_path))


def synthesize_sections(
    *,
    sections: Iterable[dict],
    voice_type: str,
    output_dir: Path,
    audio_format: str = "mp3",
    section_filter: Optional[set[str]] = None,
) -> list[SectionAudio]:
    """按章节批量合成音频。

    ``sections`` 是 ``script_structure``：每项需包含 ``sectionId`` 和 ``content``。
    ``section_filter`` 可选，仅合成指定 sectionId（对应 API 的 ``sectionIds``）。
    """
    voice = resolve_voice(voice_type)
    results: list[SectionAudio] = []

    for item in sections:
        section_id = str(item.get("sectionId") or "").strip()
        text = (item.get("content") or "").strip()
        if not section_id or not text:
            continue
        if section_filter and section_id not in section_filter:
            continue

        file_path = output_dir / f"{section_id}.{audio_format}"
        try:
            duration = asyncio.run(_synthesize_one(text, voice, file_path))
        except Exception as exc:
            logger.exception("TTS 合成章节失败: section=%s, voice=%s", section_id, voice)
            raise RuntimeError(f"章节 {section_id} 合成失败: {exc}") from exc

        file_size = file_path.stat().st_size if file_path.exists() else 0
        results.append(
            SectionAudio(
                section_id=section_id,
                file_path=file_path,
                duration_seconds=duration,
                file_size=file_size,
            )
        )

    return results
