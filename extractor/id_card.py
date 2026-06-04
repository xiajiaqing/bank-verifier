"""
身份证字段提取
支持二代身份证正面（头像面）
"""
import re
from typing import Optional
from ocr_engine import read_text, extract_raw_text
from utils import preprocess_document, pil_to_cv2
from data_types import IDCardData


ID_PATTERN = re.compile(r"\d{17}[\dXx]")
DATE_PATTERN = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")

# 标签关键词
_NAME_KEYWORDS = ["姓名"]
_GENDER_KEYWORDS = ["性别"]
_ETHNICITY_KEYWORDS = ["民族"]
_ADDRESS_KEYWORDS = ["住址", "住  址", "地址"]
_ID_KEYWORDS = ["公民身份号码", "身份号码", "身份证号", "证号"]


def _clean_text(text: str) -> str:
    """去掉OCR常见的粘连字符"""
    text = text.replace("〇", "0").replace("０", "0")
    text = re.sub(r"[\[\]【】]", "", text)
    return text.strip()


def _extract_by_section(text: str) -> IDCardData:
    """
    将文本分成上半区（姓名/性别/民族/出生）和下半区（地址/号码），
    再分别匹配字段，提升准确率。
    """
    data = IDCardData(raw_text=text)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return data

    mid = len(lines) // 2
    upper_lines = "".join(lines[:max(mid, 1)])
    lower_lines = "".join(lines[mid:])

    # 姓名：上半区首个非标签词
    for kw in _NAME_KEYWORDS:
        idx = upper_lines.find(kw)
        if idx >= 0:
            rest = upper_lines[idx + len(kw):].strip()
            rest = re.sub(r"^[:：\s]+", "", rest)
            if rest:
                # 取第一个连续中文字符串
                m = re.search(r"[\u4e00-\u9fff]{2,}", rest)
                if m:
                    data.name = m.group()
                    break

    # 性别
    for kw in _GENDER_KEYWORDS:
        if kw in upper_lines:
            idx = upper_lines.find(kw) + len(kw)
            rest = upper_lines[idx:idx + 4]
            if "男" in rest:
                data.gender = "男"
            elif "女" in rest:
                data.gender = "女"
            break

    # 民族
    for kw in _ETHNICITY_KEYWORDS:
        if kw in upper_lines:
            idx = upper_lines.find(kw) + len(kw)
            rest = upper_lines[idx:idx + 6]
            m = re.search(r"[\u4e00-\u9fff]{2,}", rest)
            if m:
                data.ethnicity = m.group()
            break

    # 出生日期
    m = DATE_PATTERN.search(text)
    if m:
        data.birth_date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # 住址
    for kw in _ADDRESS_KEYWORDS:
        if kw in lower_lines:
            idx = lower_lines.find(kw) + len(kw)
            rest = lower_lines[idx:].strip()
            # 取一长串字符直到换行或出现号码
            m = re.match(r"([^0-9A-Za-z\n]{5,})", rest)
            if m:
                data.address = m.group(1).strip()
            break

    # 证件号码
    for kw in _ID_KEYWORDS:
        if kw in lower_lines:
            idx = lower_lines.find(kw) + len(kw)
            rest = lower_lines[idx:].strip()
            m = ID_PATTERN.search(rest)
            if m:
                data.id_number = m.group().upper()
                break
    # 兜底：全文搜索
    if not data.id_number:
        m = ID_PATTERN.search(text)
        if m:
            data.id_number = m.group().upper()

    return data


def extract(image_pil) -> IDCardData:
    """主入口"""
    import numpy as np
    image_cv = pil_to_cv2(image_pil)
    preprocessed = preprocess_document(image_cv)
    results = read_text(preprocessed)

    # 只取上半区（头像面布局稳定，下半区地址文字不规整）
    h, w = preprocessed.shape[:2]
    upper_half = preprocessed[0:int(h * 0.65), :]

    upper_results = read_text(upper_half)
    lower_results = read_text(preprocessed[int(h * 0.6):, :])

    upper_text = extract_raw_text(upper_results)
    lower_text = extract_raw_text(lower_results)
    full_text = upper_text + "\n" + lower_text

    avg_conf = sum(r["confidence"] for r in results) / len(results) if results else 0.0

    data = _extract_by_section(full_text)
    data.confidence = avg_conf
    return data