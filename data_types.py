"""
银行账户审核工具 —— 核心数据结构
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BusinessLicenseData:
    """营业执照提取数据"""
    company_name: str = ""
    unified_credit_code: str = ""      # 统一社会信用代码
    legal_rep_name: str = ""            # 法定代表人姓名
    legal_rep_id: str = ""              # 法人证件号码
    registered_address: str = ""        # 注册地址
    # 以下为原始OCR行，供调试
    raw_text: str = ""
    confidence: float = 0.0


@dataclass
class IDCardData:
    """身份证提取数据"""
    name: str = ""
    id_number: str = ""               # 公民身份号码
    gender: str = ""                   # 性别（辅助核验）
    ethnicity: str = ""                # 民族（辅助核验）
    birth_date: str = ""               # 出生日期
    address: str = ""                  # 住址
    raw_text: str = ""
    confidence: float = 0.0


@dataclass
class ApplicationFormData:
    """开户申请书提取数据"""
    company_name: str = ""
    unified_credit_code: str = ""
    legal_rep_name: str = ""
    legal_rep_id: str = ""
    handler_name: str = ""             # 经办人姓名
    handler_id: str = ""               # 经办人证件号码
    registered_address: str = ""
    application_date: str = ""         # 申请日期
    has_stamp: bool = False            # 是否加盖公章
    raw_text: str = ""
    confidence: float = 0.0


@dataclass
class VerificationItem:
    """单个核验项"""
    field_name: str                    # 字段名称（中文）
    value_form: str                    # 申请书原始值
    value_ref: str                     # 参照证件原始值
    passed: bool
    reason: str = ""                   # 不一致原因

    def to_display(self) -> dict:
        return {
            "field": self.field_name,
            "form_value": self.value_form,
            "ref_value": self.value_ref,
            "passed": self.passed,
            "reason": self.reason
        }


@dataclass
class VerificationResult:
    """整体核验结果"""
    items: list[VerificationItem] = field(default_factory=list)
    all_passed: bool = False
    form_data: ApplicationFormData = field(default_factory=ApplicationFormData)
    bl_data: BusinessLicenseData = field(default_factory=BusinessLicenseData)
    legal_id_data: IDCardData = field(default_factory=IDCardData)
    handler_id_data: IDCardData = field(default_factory=IDCardData)

    def summary(self) -> dict:
        total = len(self.items)
        passed = sum(1 for i in self.items if i.passed)
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "all_passed": self.all_passed
        }