"""
PDF 核验报告生成
"""
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from data_types import VerificationResult


# 注册中文字体（使用系统内置宋体/黑体）
def _register_font():
    try:
        pdfmetrics.registerFont(TTFont("SimSun", "C:/Windows/Fonts/simsun.ttc"))
        pdfmetrics.registerFont(TTFont("SimHei", "C:/Windows/Fonts/simhei.ttf"))
    except Exception:
        pass


_styles = None

def _get_styles():
    global _styles
    if _styles is None:
        _register_font()
        _styles = getSampleStyleSheet()
        # 添加自定义样式
        _styles.add(ParagraphStyle(
            name="ChineseTitle",
            fontName="SimHei",
            fontSize=16,
            alignment=1,  # 居中
            spaceAfter=6
        ))
        _styles.add(ParagraphStyle(
            name="ChineseBody",
            fontName="SimSun",
            fontSize=10,
            leading=16
        ))
        _styles.add(ParagraphStyle(
            name="ChineseSmall",
            fontName="SimSun",
            fontSize=8,
            leading=12
        ))
    return _styles


def generate_pdf(result: VerificationResult, output_path: str):
    """
    生成核验报告 PDF

    Args:
        result: 核验结果对象
        output_path: 输出文件路径（.pdf）
    """
    _register_font()
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm
    )
    styles = _get_styles()
    story = []

    # 标题
    story.append(Paragraph("单位银行结算账户开户申请书核验报告", styles["ChineseTitle"]))
    story.append(Spacer(1, 4*mm))

    # 基本信息表
    info_data = [
        ["核验时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["核验状态", "通过 ✓" if result.all_passed else "未通过 ✗"],
        ["申请书公司名称", result.form_data.company_name or "（未识别）"],
        ["营业执照公司名称", result.bl_data.company_name or "（未识别）"],
        ["申请书统一信用代码", result.form_data.unified_credit_code or "（未识别）"],
        ["营业执照统一信用代码", result.bl_data.unified_credit_code or "（未识别）"],
    ]
    info_table = Table(info_data, colWidths=[60*mm, 110*mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "SimSun"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2F7")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 6*mm))

    # 核验明细表
    story.append(Paragraph("核验明细", styles["ChineseTitle"]))
    story.append(Spacer(1, 3*mm))

    header = ["核验项", "申请书填写", "证件参照值", "结果"]
    rows = [header]
    for item in result.items:
        rows.append([
            item.field_name,
            item.value_form or "（空）",
            item.value_ref or "（未识别）",
            "通过" if item.passed else "不通过",
        ])

    detail_table = Table(rows, colWidths=[35*mm, 50*mm, 50*mm, 20*mm])
    detail_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "SimHei"),
        ("FONTNAME", (0, 1), (-1, -1), "SimSun"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        # 通过行绿色背景，不通过行红色背景
        *[("BACKGROUND", (3, i+1), (3, i+1),
           colors.HexColor("#D5F5E3") if item.passed else colors.HexColor("#FADBD8"))
          for i, item in enumerate(result.items)],
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 6*mm))

    # 不一致原因说明（仅不通过项）
    failed_items = [item for item in result.items if not item.passed]
    if failed_items:
        story.append(Paragraph("不通过原因说明", styles["ChineseTitle"]))
        story.append(Spacer(1, 3*mm))
        for item in failed_items:
            reason_text = item.reason or f"{item.field_name} 填写内容与证件不一致"
            story.append(Paragraph(f"• {reason_text}", styles["ChineseBody"]))
            story.append(Spacer(1, 2*mm))
    else:
        story.append(Paragraph("✓ 所有核验项目均已通过", styles["ChineseBody"]))

    story.append(Spacer(1, 10*mm))
    # 备注
    story.append(Paragraph(
        "备注：本报告由系统 OCR 自动生成，仅供辅助审核使用，最终结果以人工审核为准。",
        styles["ChineseSmall"]
    ))

    doc.build(story)
    return output_path