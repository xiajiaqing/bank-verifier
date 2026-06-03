"""
开户申请书字段提取
申请书格式多样，以标签+值模式为主，关键字匹配为核心
"""
import re
from ocr_engine import read_text, extract_raw_text, join_lines
from utils import preprocess_document, pil_to_cv2
from data_types import ApplicationFormData


# 申请书常见字段标签关键词（多种写法）
_COMPANY_NAME_KEYWORDS = ["单位名称", "客户名称", "企业名称", "公司名称", "名称"]
_UNIFIED_CODE_KEYWORDS = ["统一社会信用代码", "统一信用代码", "信用代码", "代码"]
_LEGAL_REP_KEYWORDS = ["法定代表人", "法人代表", "法人", "负责人"]
_LEGAL_REP_ID_KEYWORDS = ["法定代表人证件号码", "法人证件号码", "法人身份证号",
                            "法定代表人证件号", "法人证号"]
_HANDLER_NAME_KEYWORDS = ["经办人姓名", "经办人", "办理人", "经办"]
_HANDLER_ID_KEYWORDS = ["经办人证件号码", "经办人身份证号", "经办人证件号",
                          "经办人身份证", "经办证件号"]
_ADDRESS_KEYWORDS = ["注册地址", "单位地址", "地址", "营业场所", "经营场所"]
_DATE_KEYWORDS = ["申请日期", "填表日期", "日期", "填表时间"]


def _find_after_label(text: str, keywords: list[str]) -> str:
    """在文本中查找第一个匹配的标签，返回标签后的值"""
    for kw in keywords:
        if kw in text:
            # 分割，保留后半段
            parts = text.split(kw, 1)
            if len(parts) > 1:
                val = parts[1].strip()
                # 去掉冒号/空格
                val = re.sub(r"^[:：\s]+", "", val)
                if val:
                    return val
    return ""


def _first_chinese_phrase(text: str) -> str:
    """提取第一段连续中文字符，作为字段值"""
    m = re.search(r"[\u4e00-\u9fff]{2,}", text)
    return m.group() if m else text.strip()


def _extract_from_text(text: str, confidence: float) -> ApplicationFormData:
    """正则 + 关键词双重策略提取"""
    data = ApplicationFormData(raw_text=text, confidence=confidence)
    lines = join_lines([{"text": line, "confidence": confidence, "bbox": []}
                        for line in text.split("\n") if line.strip()])

    # 单位名称
    val = _find_after_label(text, _COMPANY_NAME_KEYWORDS)
    if not val and lines:
        for line in lines:
            for kw in _COMPANY_NAME_KEYWORDS:
                if kw in line["text"]:
                    parts = line["text"].split(kw, 1)
                    if len(parts) > 1:
                        val = parts[1].strip()
                        val = re.sub(r"^[:：\s]+", "", val)
                        if val:
                            break
            if val:
                break
    data.company_name = val

    # 统一社会信用代码
    val = _find_after_label(text, _UNIFIED_CODE_KEYWORDS)
    if not val:
        # 兜底：全文搜索18位代码
        m = re.search(r"[0-9A-Z]{18}", text.upper())
        if m:
            val = m.group()
    data.unified_credit_code = val.upper()

    # 法定代表人姓名
    val = _find_after_label(text, _LEGAL_REP_KEYWORDS)
    if val:
        data.legal_rep_name = _first_chinese_phrase(val)
    else:
        data.legal_rep_name = ""

    # 法定代表人证件号码
    val = _find_after_label(text, _LEGAL_REP_ID_KEYWORDS)
    if not val:
        m = re.search(r"\d{17}[\dXx]", text)
        if m:
            val = m.group()
    data.legal_rep_id = val.upper()

    # 经办人姓名
    val = _find_after_label(text, _HANDLER_NAME_KEYWORDS)
    if val:
        data.handler_name = _first_chinese_phrase(val)
    else:
        data.handler_name = ""

    # 经办人证件号码
    val = _find_after_label(text, _HANDLER_ID_KEYWORDS)
    if not val:
        # 找第二个18位身份证号（第一个可能是法人）
        matches = list(re.finditer(r"\d{17}[\dXx]", text))
        if len(matches) >= 2:
            val = matches[1].group()
    data.handler_id = val.upper()

    # 注册地址
    val = _find_after_label(text, _ADDRESS_KEYWORDS)
    data.registered_address = val

    # 申请日期
    val = _find_after_label(text, _DATE_KEYWORDS)
    # 规范化日期格式
    if val:
        m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", val)
        if m:
            val = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    data.application_date = val

    return data


def extract(image_pil) -> ApplicationFormData:
    """主入口"""
    import numpy as np
    image_cv = pil_to_cv2(image_pil)
    preprocessed = preprocess_document(image_cv)
    results = read_text(preprocessed)
    text = extract_raw_text(results)
    avg_conf = sum(r["confidence"] for r in results) / len(results) if results else 0.0
    return _extract_from_text(text, avg_conf)