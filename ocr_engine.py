"""
EasyOCR 引擎封装
首次加载时自动下载模型到用户目录
"""
import os
import sys
from pathlib import Path
import numpy as np
import easyocr

_model_dir = Path.home() / ".easyocr_models"
os.environ["EASYOCR_MODULE_PATH"] = str(_model_dir)
_reader = None

def get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["ch_sim", "en"], model_storage_directory=str(_model_dir), download_enabled=True, gpu=False, verbose=False)
    return _reader

def read_text(image, min_confidence=0.3):
    reader = get_reader()
    results = reader.readtext(image)
    parsed = []
    for item in results:
        bbox, text, confidence = item
        if confidence >= min_confidence and len(text.strip()) > 0:
            parsed.append({"text": text.strip(), "confidence": float(confidence), "bbox": bbox})
    return parsed

def join_lines(results, line_gap=1.5):
    if not results:
        return []
    sorted_by_y = sorted(results, key=lambda r: np.mean([p[1] for p in r["bbox"]]) if r.get("bbox") and len(r["bbox"]) > 0 else 0)
    lines = []
    current_line = [sorted_by_y[0]]
    current_y = np.mean([p[1] for p in sorted_by_y[0]["bbox"]]) if sorted_by_y[0].get("bbox") and len(sorted_by_y[0]["bbox"]) > 0 else 0
    for item in sorted_by_y[1:]:
        item_y = np.mean([p[1] for p in item["bbox"]]) if item.get("bbox") and len(item["bbox"]) > 0 else 0
        if abs(item_y - current_y) <= line_gap:
            current_line.append(item)
        else:
            lines.append(current_line)
            current_line = [item]
            current_y = item_y
    lines.append(current_line)
    merged = []
    for line in lines:
        line.sort(key=lambda r: np.mean([p[0] for p in r["bbox"]]) if r.get("bbox") and len(r["bbox"]) > 0 else 0)
        texts = [r["text"] for r in line]
        confidences = [r["confidence"] for r in line]
        merged.append({"text": "".join(texts), "confidence": sum(confidences)/len(confidences), "bbox": [r["bbox"] for r in line]})
    return merged

def extract_raw_text(results):
    lines = join_lines(results)
    return "\n".join([line["text"] for line in lines])