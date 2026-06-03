"""
交叉核验逻辑
将开户申请书内容与三份证件（营业执照、法人身份证、经办人身份证）逐项比对
"""
import re
from data_types import (
    BusinessLicenseData, IDCardData, ApplicationFormData,
    VerificationResult, VerificationItem
)


def _normalize_code(code: str) -> str:
    """统一格式化证件号码：大写、去除空格和特殊字符"""
    return re.sub(r"[^0-9A-Za-z]", "", code.upper())


def _normalize_name(name: str) -> str:
    """统一格式化姓名：去除空格，保留中文字符"""
    import re
    return re.sub(r"[^\u4e00-\u9fff]", "", name.strip())


def _fuzzy_address_match(addr1: str, addr2: str) -> bool:
    """
    地址省级/市级匹配，允许OCR误差（常见"省"/"市"/"区"缺失）
    """
    def strip_address(addr: str) -> str:
        return (addr.replace("省", "").replace("市", "")
                   .replace("区", "").replace("县", "")
                   .replace(" ", "").replace("　", ""))

    a1 = strip_address(addr1)
    a2 = strip_address(addr2)
    if not a1 or not a2:
        return False
    # 取前10个字符做模糊匹配（处理省级名称OCR误差）
    return a1[:10] == a2[:10] or a1[:8] == a2[:8]


def _compare_company_name(form_val: str, bl_val: str) -> VerificationItem:
    """核验单位名称"""
    f = _normalize_name(form_val)
    b = _normalize_name(bl_val)
    if not bl_val:
        return VerificationItem(
            field_name="单位名称",
            value_form=form_val,
            value_ref="（营业执照未提取到公司名称）",
            passed=False,
            reason="营业执照中未识别到公司名称"
        )
    passed = (f == b) or (b in f) or (f in b)
    reason = "" if passed else f"申请书填写「{form_val}」，营业执照为「{bl_val}」"
    return VerificationItem(
        field_name="单位名称",
        value_form=form_val,
        value_ref=bl_val,
        passed=passed,
        reason=reason
    )


def _compare_uscc(form_val: str, bl_val: str) -> VerificationItem:
    """核验统一社会信用代码"""
    f = _normalize_code(form_val)
    b = _normalize_code(bl_val)
    passed = (f == b) if (f and b) else False
    reason = "" if passed else f"申请书填写「{form_val}」，营业执照为「{bl_val}」"
    return VerificationItem(
        field_name="统一社会信用代码",
        value_form=form_val,
        value_ref=bl_val,
        passed=passed,
        reason=reason
    )


def _compare_legal_rep_name(form_val: str, bl_val: str,
                            id_val: str) -> VerificationItem:
    """核验法定代表人姓名（三方比对）"""
    f = _normalize_name(form_val)
    b = _normalize_name(bl_val)
    i = _normalize_name(id_val)
    # 三者中任意两者相同即通过（允许OCR误差）
    matches = [f, b, i]
    passed = len(set(matches) - {""}) >= 2
    reason = "" if passed else f"申请书「{form_val}」，营业执照「{bl_val}」，身份证「{id_val}」"
    return VerificationItem(
        field_name="法定代表人姓名",
        value_form=form_val,
        value_ref=f"{bl_val} / {id_val}",
        passed=passed,
        reason=reason
    )


def _compare_legal_rep_id(form_val: str, id_val: str) -> VerificationItem:
    """核验法定代表人证件号码"""
    f = _normalize_code(form_val)
    i = _normalize_code(id_val)
    if not id_val:
        return VerificationItem(
            field_name="法人证件号码",
            value_form=form_val,
            value_ref="（身份证未提取到证件号）",
            passed=False,
            reason="法人身份证中未识别到证件号码"
        )
    passed = (f == i)
    reason = "" if passed else f"申请书填写「{form_val}」，身份证为「{id_val}」"
    return VerificationItem(
        field_name="法人证件号码",
        value_form=form_val,
        value_ref=id_val,
        passed=passed,
        reason=reason
    )


def _compare_handler_name(form_val: str, id_val: str) -> VerificationItem:
    """核验经办人姓名"""
    f = _normalize_name(form_val)
    i = _normalize_name(id_val)
    if not id_val:
        return VerificationItem(
            field_name="经办人姓名",
            value_form=form_val,
            value_ref="（身份证未提取到姓名）",
            passed=False,
            reason="经办人身份证中未识别到姓名"
        )
    passed = (f == i)
    reason = "" if passed else f"申请书填写「{form_val}」，身份证为「{id_val}」"
    return VerificationItem(
        field_name="经办人姓名",
        value_form=form_val,
        value_ref=id_val,
        passed=passed,
        reason=reason
    )


def _compare_handler_id(form_val: str, id_val: str) -> VerificationItem:
    """核验经办人证件号码"""
    f = _normalize_code(form_val)
    i = _normalize_code(id_val)
    passed = (f == i) if (f and i) else False
    reason = "" if passed else f"申请书填写「{form_val}」，身份证为「{id_val}」"
    return VerificationItem(
        field_name="经办人证件号码",
        value_form=form_val,
        value_ref=id_val,
        passed=passed,
        reason=reason
    )


def _compare_address(form_val: str, bl_val: str) -> VerificationItem:
    """核验注册地址（模糊匹配）"""
    if not bl_val:
        return VerificationItem(
            field_name="注册地址",
            value_form=form_val,
            value_ref="（营业执照未提取到地址）",
            passed=False,
            reason="营业执照中未识别到注册地址"
        )
    passed = _fuzzy_address_match(form_val, bl_val)
    reason = "" if passed else f"申请书填写「{form_val}」，营业执照为「{bl_val}」"
    return VerificationItem(
        field_name="注册地址",
        value_form=form_val,
        value_ref=bl_val,
        passed=passed,
        reason=reason
    )


def verify(form_data: ApplicationFormData,
           bl_data: BusinessLicenseData,
           legal_id_data: IDCardData,
           handler_id_data: IDCardData) -> VerificationResult:
    """
    执行全部7项核验，返回 VerificationResult
    """
    items = [
        _compare_company_name(form_data.company_name, bl_data.company_name),
        _compare_uscc(form_data.unified_credit_code, bl_data.unified_credit_code),
        _compare_legal_rep_name(
            form_data.legal_rep_name, bl_data.legal_rep_name,
            legal_id_data.name
        ),
        _compare_legal_rep_id(form_data.legal_rep_id, legal_id_data.id_number),
        _compare_handler_name(form_data.handler_name, handler_id_data.name),
        _compare_handler_id(form_data.handler_id, handler_id_data.id_number),
        _compare_address(form_data.registered_address, bl_data.registered_address),
    ]

    all_passed = all(item.passed for item in items)
    return VerificationResult(
        items=items,
        all_passed=all_passed,
        form_data=form_data,
        bl_data=bl_data,
        legal_id_data=legal_id_data,
        handler_id_data=handler_id_data
    )