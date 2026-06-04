"""
营业执照字段提取
支持新版营业执照格式（2018年后，统一社会信用代码18位）
"""
import re
from typing import Optional
from ocr_engine import read_text, extract_raw_text, join_lines
from utils import preprocess_document, pil_to_cv2
from data_types import BusinessLicenseData


# 营业执照标签映射（支持多种表述）
_COMPANY_NAME_KEYWORDS = [
    "企业名称", "公司名称", "名称", "字号", "公司名"
]

_UNIFIED_CODE_KEYWORDS = [
    "统一社会信用代码", "统一信用代码", "信用代码", "社会信用代码", "代码"
]

_LEGAL_REP_KEYWORDS = [
    "法定代表人", "法人代表", "法人", "负责人"
]

_LEGAL_REP_ID_KEYWORDS = [
    "法定代表人证件号码", "法人证件号码", "法人证件号", "法人证号"
]

_ADDRESS_KEYWORDS = [
    "住所", "地址", "注册地址", "经营场所", "营业场所"
]

# 统一社会信用代码正则（18位，大写字母+数字）
USCC_PATTERN = re.compile(r"[0-9A-Z]{18}")

# 身份证号正则（18位）
ID_PATTERN = re.compile(r"\d{17}[\dXx]")


def _find_by_keywords(lines: list[dict], keywords: list[str],
                      after_keyword: bool = True) -> Optional[str]:
    """在一行文本中查找关键标签，并提取其后的值"""
    for i, line in enumerate(lines):
        text = line["text"]
        conf = line["confidence"]
        # 检查本行是否有标签关键词
        for kw in keywords:
            if kw in text:
                if after_keyword:
                    # 去掉标签后的剩余文本
                    parts = text.split(kw, 1)
                    if len(parts) > 1 and len(parts[1].strip()) > 1:
                        return parts[1].strip()
                # 如果关键词行是纯标签（如"法定代表人"单独一行），找下一行
                if text.strip() == kw or text.strip() == kw + "：":
                    if i + 1 < len(lines):
                        return lines[i + 1]["text"].strip()
    return None


def _search_code(text: str, pattern: re.Pattern) -> Optional[str]:
    """全文搜索特定格式的代码"""
    matches = pattern.findall(text.upper())
    return matches[0] if matches else None


def _extract_from_text(text: str, confidence: float) -> BusinessLicenseData:
    """基于纯文本正则提取字段"""
    data = BusinessLicenseData(raw_text=text, confidence=confidence)

    lines = join_lines([{"text": line, "confidence": confidence,
                          "bbox": []} for line in text.split("\n")
                        if line.strip()])

    # 公司名称
    val = _find_by_keywords(lines, _COMPANY_NAME_KEYWORDS)
    if val:
        data.company_name = val

    # 统一社会信用代码
    val = _find_by_keywords(lines, _UNIFIED_CODE_KEYWORDS)
    if val:
        data.unified_credit_code = val.upper()
    else:
        data.unified_credit_code = _search_code(text, USCC_PATTERN) or ""

    # 法定代表人姓名
    val = _find_by_keywords(lines, _LEGAL_REP_KEYWORDS)
    if val:
        data.legal_rep_name = val

    # 法人证件号码
    val = _find_by_keywords(lines, _LEGAL_REP_ID_KEYWORDS)
    if val:
        data.legal_rep_id = val.upper()
    else:
        data.legal_rep_id = _search_code(text, ID_PATTERN) or ""

    # 注册地址
    val = _find_by_keywords(lines, _ADDRESS_KEYWORDS)
    if val:
        data.registered_address = val

    return data


def extract(image_pil) -> BusinessLicenseData:
    """
    主入口：输入 PIL.Image，输出结构化数据
    """
    import numpy as np
    image_cv = pil_to_cv2(image_pil)
    preprocessed = preprocess_document(image_cv)
    results = read_text(preprocessed)
    text = extract_raw_text(results)
    avg_conf = sum(r["confidence"] for r in results) / len(results) if results else 0.0
    return _extract_from_text(text, avg_conf)