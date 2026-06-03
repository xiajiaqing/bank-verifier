"""
开立单位银行结算账户申请书审核工具
主应用入口（Streamlit UI）
"""
import streamlit as st
from PIL import Image
import io

from extractor.business_license import extract as extract_bl
from extractor.id_card import extract as extract_id
from extractor.application_form import extract as extract_form
from validator import verify
from report import generate_pdf
from data_types import VerificationResult


st.set_page_config(
    page_title="银行账户开户审核工具",
    page_icon="🏦",
    layout="wide"
)


# ---- 自定义样式 ----
st.markdown("""
<style>
    .passed { color: #27AE60; font-weight: bold; }
    .failed { color: #E74C3C; font-weight: bold; }
    .section-header { font-size: 1.1em; font-weight: bold; margin-top: 1em; }
    .raw-text { font-size: 0.8em; color: #666; background: #F8F9FA;
                padding: 8px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ---- 初始化 session 状态 ----
if "result" not in st.session_state:
    st.session_state["result"] = None


def display_image_preview(uploaded_file, label: str):
    """显示上传图片预览"""
    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(img, width=160, caption=label)
        return img
    return None


def run_verification(bl_img, legal_id_img, handler_id_img, form_img) -> VerificationResult:
    """依次执行 OCR + 核验，返回结果对象"""
    import time
    status = st.status("正在处理...", expanded=True)

    with status:
        st.write("🔍 提取营业执照字段...")
        bl_data = extract_bl(bl_img)
        st.write(f"   公司名称: {bl_data.company_name or '（未识别）'}")
        st.write(f"   统一信用代码: {bl_data.unified_credit_code or '（未识别）'}")

        st.write("🔍 提取法人身份证字段...")
        legal_id_data = extract_id(legal_id_img)
        st.write(f"   姓名: {legal_id_data.name or '（未识别）'}")
        st.write(f"   证件号: {legal_id_data.id_number or '（未识别）'}")

        st.write("🔍 提取经办人身份证字段...")
        handler_id_data = extract_id(handler_id_img)
        st.write(f"   姓名: {handler_id_data.name or '（未识别）'}")
        st.write(f"   证件号: {handler_id_data.id_number or '（未识别）'}")

        st.write("🔍 提取开户申请书字段...")
        form_data = extract_form(form_img)
        st.write(f"   单位名称: {form_data.company_name or '（未识别）'}")
        st.write(f"   统一信用代码: {form_data.unified_credit_code or '（未识别）'}")

        st.write("⚖️ 执行交叉核验...")
        result = verify(form_data, bl_data, legal_id_data, handler_id_data)
        st.write(f"   核验项目: {len(result.items)} 项，"
                 f"通过 {sum(1 for i in result.items if i.passed)} 项")

    status.update(label="处理完成 ✓", state="complete")
    return result


def render_result_page(result: VerificationResult):
    """渲染核验结果页面"""
    st.divider()
    st.markdown("## 核验结果")

    # 总体状态
    if result.all_passed:
        st.success("🎉 所有核验项目均已通过，申请书填写内容与证件一致")
    else:
        failed_count = sum(1 for i in result.items if not i.passed)
        st.error(f"⚠️ 有 {failed_count} 项核验未通过，请人工复核后手动修改")

    # 核验明细
    st.markdown("#### 核验明细")
    cols = st.columns([2, 3, 3, 1])
    headers = ["核验项", "申请书填写", "证件参照值", "结果"]
    for col, header in zip(cols, headers):
        col.markdown(f"**{header}**")

    for item in result.items:
        cols = st.columns([2, 3, 3, 1])
        cols[0].write(item.field_name)
        cols[1].write(item.value_form or "（空）")
        cols[2].write(item.value_ref or "（未识别）")
        if item.passed:
            cols[3].markdown('<span class="passed">✓ 通过</span>',
                            unsafe_allow_html=True)
        else:
            cols[3].markdown(
                f'<span class="failed">✗ 不通过</span>'
                f'<br><small style="color:#999">{item.reason}</small>',
                unsafe_allow_html=True
            )
        st.divider()

    # 原始 OCR 文本（调试用）
    with st.expander("🔧 查看原始 OCR 文本（调试用）"):
        tabs = st.tabs(["申请书", "营业执照", "法人身份证", "经办人身份证"])
        with tabs[0]:
            st.code(result.form_data.raw_text or "（无）", language=None)
        with tabs[1]:
            st.code(result.bl_data.raw_text or "（无）", language=None)
        with tabs[2]:
            st.code(result.legal_id_data.raw_text or "（无）", language=None)
        with tabs[3]:
            st.code(result.handler_id_data.raw_text or "（无）", language=None)


def render_pdf_export(result: VerificationResult):
    """PDF 导出区块"""
    st.divider()
    st.markdown("### 📄 导出核验报告")

    if st.button("生成并下载 PDF 报告", type="primary"):
        with st.spinner("正在生成 PDF..."):
            import tempfile
            with tempfile.NamedTemporaryFile(
                    suffix=".pdf", delete=False) as tmp:
                tmp_path = tmp.name
            generate_pdf(result, tmp_path)
            with open(tmp_path, "rb") as f:
                st.download_button(
                    label="点击下载 PDF 报告",
                    data=f,
                    file_name="核验报告.pdf",
                    mime="application/pdf"
                )
        st.info("PDF 报告已生成，请点击上方按钮下载")


# ==================== 主界面 ====================
st.markdown("## 🏦 开立单位银行结算账户申请书审核工具")
st.caption("上传以下4张图片，系统自动 OCR 识别并交叉核验申请书填写内容")

col_bl, col_legal = st.columns(2)
col_handler, col_form = st.columns(2)

with col_bl:
    st.markdown("**📋 营业执照**")
    bl_upload = st.file_uploader(
        "上传营业执照", type=["jpg", "jpeg", "png", "bmp"],
        help="支持 JPG/PNG/BMP 格式，建议拍照时保持光线充足、对焦清晰"
    )
    bl_img = display_image_preview(bl_upload, "营业执照") if bl_upload else None

with col_legal:
    st.markdown("**🧑‍💼 法人身份证**")
    legal_id_upload = st.file_uploader(
        "上传法人身份证（正面）", type=["jpg", "jpeg", "png", "bmp"]
    )
    legal_id_img = display_image_preview(legal_id_upload, "法人身份证") if legal_id_upload else None

with col_handler:
    st.markdown("**👤 经办人身份证**")
    handler_id_upload = st.file_uploader(
        "上传经办人身份证（正面）", type=["jpg", "jpeg", "png", "bmp"]
    )
    handler_id_img = display_image_preview(handler_id_upload, "经办人身份证") if handler_id_upload else None

with col_form:
    st.markdown("**📝 开户申请书**")
    form_upload = st.file_uploader(
        "上传开户申请书", type=["jpg", "jpeg", "png", "bmp"]
    )
    form_img = display_image_preview(form_upload, "开户申请书") if form_upload else None

st.divider()

# 开始核验按钮
all_uploaded = all([bl_upload, legal_id_upload, handler_id_upload, form_upload])

if not all_uploaded:
    st.info("👆 请上传全部4张图片后，点击「开始核验」")
elif st.button("🚀 开始核验", type="primary", disabled=not all_uploaded):
    result = run_verification(bl_img, legal_id_img, handler_id_img, form_img)
    st.session_state["result"] = result
    render_result_page(result)
    render_pdf_export(result)

# 显示之前的结果（刷新页面后保留）
elif st.session_state.get("result") is not None and not all_uploaded:
    st.divider()
    render_result_page(st.session_state["result"])
    render_pdf_export(st.session_state["result"])