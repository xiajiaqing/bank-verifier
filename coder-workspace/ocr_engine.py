"""
EasyOCR 引擎封装
首次加载时自动下载模型到用户目录
"""
import os
import sys
from pathlib import Path
import numpy as np
import easyocr

# 模型缓存目录（用户目录，避免权限问题）
_model_dir = Path.home() / ".easyocr_models"
os.environ["EASYOCR_MODULE_PATH"] = str(_model_dir)

# 全局 reader 实例（只初始化一次）
_reader: easyocr.Reader = None


def get_reader() -> easyocr.Reader:
    """懒加载 EasyOCR Reader，中文+英文识别"""
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(
            ["ch_sim", "en"],
            model_storage_directory=str(_model_dir),
            download_enabled=True,
            gpu=False,        # 显存不够时用 CPU
            verbose=False
        )
    return _reader


def read_text(image: np.ndarray, min_confidence: float = 0.3) -> list[dict]:
    """
    对单张图片执行 OCR

    Returns:
        list[dict] — 每项含 text, confidence, bbox
    """
    reader = get_reader()
    results = reader.readtext(image)
    parsed = []
    for item in results:
        bbox, text, confidence = item
        if confidence >= min_confidence and len(text.strip()) > 0:
            parsed.append({
                "text": text.strip(),
                "confidence": float(confidence),
                "bbox": bbox
            })
    return parsed


def join_lines(results: list[dict], line_gap: float = 1.5) -> list[dict]:
    """
    将OCR结果按行合并（基于Y坐标相近）
    提升营业执照等结构化文档的提取效果
    """
    if not results:
        return []

    sorted_by_y = sorted(results, key=lambda r: np.mean(r["bbox"][0][1]))
    lines = []
    current_line = [sorted_by_y[0]]
    current_y = np.mean(sorted_by_y[0]["bbox"][0][1])

    for item in sorted_by_y[1:]:
        item_y = np.mean(item["bbox"][0][1])
        if abs(item_y - current_y) <= line_gap:
            current_line.append(item)
        else:
            lines.append(current_line)
            current_line = [item]
            current_y = item_y
    lines.append(current_line)

    merged = []
    for line in lines:
        line.sort(key=lambda r: np.mean(r["bbox"][0][0]))
        texts = [r["text"] for r in line]
        confidences = [r["confidence"] for r in line]
        merged.append({
            "text": "".join(texts),
            "confidence": sum(confidences) / len(confidences),
            "bbox": [r["bbox"] for r in line]
        })
    return merged


def extract_raw_text(results: list[dict]) -> str:
    """将OCR结果合并为纯文本字符串，便于正则匹配"""
    lines = join_lines(results)
    return "\n".join([line["text"] for line in lines])