from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import os
import re

# ====================== HÀM MÀN HÌNH CHI TIẾT (ĐẶT Ở ĐÂY - TRÊN CÙNG) ======================
@st.dialog("📋 Chi tiết", width="large")
def show_detail_dialog(row):
    st.subheader(f"Chi tiết - {row.get('so_phieu', 'N/A')}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Biển số:** {row.get('bien_so', 'N/A')}")
        st.write(f"**Tên chủ xe:** {row.get('ten_chu_xe', 'N/A')}")
        st.write(f"**Yêu cầu KH:** {row.get('yeu_cau_kh', 'N/A')}")
        st.write(f"**Người mang xe đến:** {row.get('nguoi_mang_xe', 'N/A')}")
    with col2:
        st.write(f"**Trạng thái:** {row.get('trang_thai', 'N/A')}")
        st.write(f"**CVDV:** {row.get('cvdv_name', 'N/A')}")
        if 'thoi_gian_ton_gio' in row:
            st.write(f"**Thời gian tồn:** {row['thoi_gian_ton_gio']:.1f} giờ")
        st.write(f"**Ngày tạo:** {str(row.get('ngay_tao', 'N/A'))[:10]}")
    
    st.divider()
    
    if st.session_state.role in ["admin", "manager"]:
        st.write("**Chỉnh sửa nhanh (Admin/Manager)**")
        new_trangthai = st.selectbox("Trạng thái mới", ["Báo Giá", "Lệnh Sửa Chữa (LSC)", "Hoàn Thành", "Hủy"], 
                                     index=["Báo Giá", "Lệnh Sửa Chữa (LSC)", "Hoàn Thành", "Hủy"].index(row.get('trang_thai', 'Báo Giá')))
        if st.button("💾 Lưu thay đổi"):
            mask = df['so_phieu'] == row['so_phieu']
            if mask.any():
                df.loc[mask, 'trang_thai'] = new_trangthai
                df.to_csv(DATA_FILE, index=False)
                st.success("✅ Đã cập nhật!")
                st.rerun()
    
    if st.button("Đóng", type="primary", use_container_width=True):
        st.rerun()

# ====================== ĐĂNG NHẬP ======================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.display_name = ""
    st.session_state.role = ""

USERS = {
    "quyennv": {"password": "123", "display_name": "Nguyễn Văn Quyền", "role": "cvdv"},
    "sonnt": {"password": "123", "display_name": "Nguyễn Trịnh Sơn", "role": "cvdv"},
    "pvgkhanh": {"password": "1234Ac12@", "display_name": "Phạm Viết Gia Khánh", "role": "admin"},
    "quyenttk": {"password": "090524@quyen", "display_name": "Trần Thị Kim Quyên", "role": "manager"},
}

if not st.session_state.logged_in:
    st.set_page_config(page_title="Đăng nhập - KPI", layout="centered")
    st.title("🚗 Đăng nhập Hệ thống KPI")
    st.markdown("**VinFast Thịnh Phát Bình Long**")

    username = st.text_input("Tên đăng nhập (Username)")
    password = st.text_input("Mật khẩu", type="password")

    if st.button("Đăng nhập", type="primary"):
        if username in USERS and USERS[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.display_name = USERS[username]["display_name"]
            st.session_state.role = USERS[username]["role"]
            st.success(f"Đăng nhập thành công! Chào {st.session_state.display_name}")
            st.rerun()
        else:
            st.error("❌ Sai tên đăng nhập hoặc mật khẩu!")
    st.stop()

# ====================== APP CHÍNH ======================
st.set_page_config(page_title="KPI Xe Tồn 24h", layout="wide", page_icon="🚗")
st.title("🚗 QUẢN LÝ XE TỒN 24H - KPI QUÝ II")
st.markdown(f"**Người dùng:** {st.session_state.display_name} | **Vai trò:** {st.session_state.role.upper()}")

if st.sidebar.button("🚪 Đăng xuất"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ====================== CẤU HÌNH DỮ LIỆU ======================
DATA_FOLDER = "data"
DATA_FILE = f"{DATA_FOLDER}/xe_ton.csv"

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    for col in ['ngay_tao', 'thoi_gian_bat_dau_lsc', 'thoi_gian_du_kien']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
else:
    df = pd.DataFrame(columns=[
        'so_phieu', 'bien_so', 'ten_chu_xe', 'yeu_cau_kh', 'ma_kieu_xe', 'so_khung',
        'nguoi_mang_xe', 'sdt_nguoi_mang', 'sdt', 'trang_thai', 'ngay_tao',
        'thoi_gian_bat_dau_lsc', 'is_xe_ton', 'ly_do_khong_ton',
        'thoi_gian_du_kien', 'cvdv_name', 'ghi_chu', 'httt',
        'baohiem_da_duyet', 'ngay_gui_baogia_baohiem', 'so_ngay_nhap_tre'
    ])

# ====================== SIDEBAR MENU - PHÂN QUYỀN ======================
menu_options = ["🚨 Danh sách Xe Đang Tồn", "📋 Tất cả Lệnh Sửa Chữa"]

if st.session_state.role in ["cvdv", "admin"]:
    menu_options = ["📤 Import Báo Giá PDF", "🚨 Danh sách Xe Đang Tồn", 
                   "📋 Tất cả Lệnh Sửa Chữa"]

menu = st.sidebar.radio(
    "Chọn chức năng",
    menu_options,
    index=0,                    # Mặc định chọn mục đầu tiên
    horizontal=False            # Hiển thị dạng dọc (cố định, đẹp)
)

cvdv_name = st.session_state.display_name

# ====================== 1. IMPORT PDF (GIỮ NGUYÊN + KIỂM TRA TRÙNG) ======================
if menu == "📤 Import Báo Giá PDF":
    st.header("📤 Import Báo Giá từ PDF")

    if 'preview_data' not in st.session_state:
        uploaded_file = st.file_uploader("Chọn file PDF Báo Giá", type=['pdf'], key="pdf_uploader")
        
        if uploaded_file:
            try:
                import pdfplumber
                with pdfplumber.open(uploaded_file) as pdf:
                    full_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
                    lines = [line.strip() for line in full_text.split('\n') if line.strip()]

                so_phieu = bien_so = ten_chu_xe = yeu_cau_kh = ma_kieu_xe = so_khung = ""
                nguoi_mang_xe = sdt = sdt_nguoi_mang = httt = ngay_tao = ""

                for i, line in enumerate(lines):
                    if "Số phiếu:" in line:
                        so_phieu = line.split(":")[1].split("Ngày")[0].strip()
                        ngay_tao = line.split(":")[2].strip() if len(line.split(":")) > 2 else ""
                    if "Biển số" in line and ":" in line:
                        bien_so = line.split(":")[-1].strip()
                    if "GSM" in full_text:
                        ten_chu_xe = "GSM"
                    else:
                        if "Chủ xe" in line:
                            ten_chu_xe = line.split(":")[1].split("Biển")[0].strip()
                    if "Điện thoại" in line and ten_chu_xe and not sdt:
                        sdt = line.split(":")[1].split("Email")[0].strip()
                    if "Người mang xe đến" in line:
                        nguoi_mang_xe = line.split(":")[1].split("Số")[0].strip()
                    if "Điện thoại" in line and nguoi_mang_xe and not sdt_nguoi_mang:
                        sdt_nguoi_mang = line.split(":")[1].split("Ngày")[0].strip()
                    if "Yêu cầu khách hàng" in line:
                        yeu_cau_kh = line.split(":")[1].strip()
                    if "Mã kiểu xe" in line:
                        ma_kieu_xe = line.split(":")[-1].strip()
                    if "Số khung" in line:
                        so_khung = line.split(":")[-1].split("Email")[0].strip()

                pattern = r"\d+%\s+\d+\s+\b([WCI])\b"
                httt_list = re.findall(pattern, full_text)
                httt = "I" if "I" in httt_list else "W" if "W" in httt_list else "C"

                converted_time = datetime.strptime(ngay_tao, "%Y/%m/%d") if ngay_tao else datetime.now()

                st.session_state.preview_data = {
                    'Số WO': so_phieu or "N/A",
                    'Biển số': bien_so or "",
                    'Tên chủ xe': ten_chu_xe.strip() or "",
                    'SĐT': sdt or "",
                    'Yêu cầu': yeu_cau_kh or "",
                    'Loại xe': ma_kieu_xe or "",
                    'Số khung': so_khung or "",
                    'Người mang xe đến': nguoi_mang_xe or "",
                    'SĐT người mang xe đến': sdt_nguoi_mang or "",
                }
                st.session_state.uploaded_file_name = so_phieu or uploaded_file.name
                st.session_state.ngay_tao = converted_time
                st.session_state.httt = httt

            except Exception as e:
                st.error(f"Lỗi: {str(e)}")

    if 'preview_data' in st.session_state:
        st.success(f"📄 Đã đọc báo giá số: **{st.session_state.uploaded_file_name}**")
        st.subheader("📋 Thông tin Preview")
        st.dataframe(pd.DataFrame([st.session_state.preview_data]), use_container_width=True, hide_index=True)

        so_phieu_moi = st.session_state.preview_data['Số WO']
        is_duplicate = (so_phieu_moi != "N/A" and not df.empty and so_phieu_moi in df['so_phieu'].values)

        if is_duplicate:
            st.error(f"❌ Số phiếu **{so_phieu_moi}** đã tồn tại!")
        else:
            st.success("✅ Số phiếu hợp lệ")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Thêm vào danh sách", type="primary", use_container_width=True, disabled=is_duplicate):
                new_row = {
                    'so_phieu': st.session_state.preview_data['Số WO'],
                    'bien_so': st.session_state.preview_data['Biển số'],
                    'ten_chu_xe': st.session_state.preview_data['Tên chủ xe'],
                    'sdt': st.session_state.preview_data['SĐT'],
                    'yeu_cau_kh': st.session_state.preview_data['Yêu cầu'],
                    'ma_kieu_xe': st.session_state.preview_data['Loại xe'],
                    'so_khung': st.session_state.preview_data['Số khung'],
                    'nguoi_mang_xe': st.session_state.preview_data['Người mang xe đến'],
                    'sdt_nguoi_mang': st.session_state.preview_data['SĐT người mang xe đến'],
                    'trang_thai': "Báo Giá",
                    'ngay_tao': st.session_state.ngay_tao,
                    'so_ngay_nhap_tre': (datetime.now().date() - st.session_state.ngay_tao.date()).days,
                    'thoi_gian_bat_dau_lsc': None,
                    'is_xe_ton': True,
                    'ly_do_khong_ton': "",
                    'thoi_gian_du_kien': None,
                    'cvdv_name': cvdv_name,
                    'ghi_chu': "",
                    'httt': st.session_state.httt,
                    'baohiem_da_duyet': "Chưa duyệt" if "BẢO HIỂM" in st.session_state.preview_data['Yêu cầu'].upper() or st.session_state.httt == "I" else "",
                    'ngay_gui_baogia_baohiem': datetime.now() if "BẢO HIỂM" in st.session_state.preview_data['Yêu cầu'].upper() or st.session_state.httt == "I" else None
                }

                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.success("✅ Đã thêm thành công!")
                del st.session_state.preview_data
                st.rerun()

        with col2:
            if st.button("❌ Hủy", use_container_width=True):
                if 'preview_data' in st.session_state:
                    del st.session_state.preview_data
                st.rerun()

# ====================== 2. DANH SÁCH XE ĐANG TỒN (CÓ CLICK MỞ MÀN HÌNH CHI TIẾT) ======================
elif menu == "🚨 Danh sách Xe Đang Tồn":
    st.header("🚨 DANH SÁCH XE ĐANG TỒN")
    df_ton = df[df['is_xe_ton'] == True].copy()
    
    if not df_ton.empty:
        df_ton['thoi_gian_ton_gio'] = 0.0
        mask = df_ton['thoi_gian_bat_dau_lsc'].notna()
        if mask.any():
            df_ton.loc[mask, 'thoi_gian_ton_gio'] = (
                (datetime.now() - df_ton.loc[mask, 'thoi_gian_bat_dau_lsc']).dt.total_seconds() / 3600
            ).round(2)
        
        df_ton = df_ton.sort_values('thoi_gian_ton_gio', ascending=False)
        
        def highlight(row):
            if row['thoi_gian_ton_gio'] > 24:
                return ['background-color: #ffcccc'] * len(row)
            return [''] * len(row)
        
        selected = st.dataframe(
            df_ton.style.apply(highlight, axis=1),
            column_order=['so_phieu', 'bien_so', 'ten_chu_xe', 'yeu_cau_kh',
                         'trang_thai', 'thoi_gian_ton_gio', 'cvdv_name'],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        if selected["selection"]["rows"]:
            idx = selected["selection"]["rows"][0]
            row = df_ton.iloc[idx].to_dict()
            show_detail_dialog(row)
        
        st.warning(f"**Tổng số xe đang tồn: {len(df_ton)} xe**")
    else:
        st.success("✅ Hiện không có xe nào đang tồn.")

# ====================== 4. TẤT CẢ LỆNH ======================
else:
    st.header("📋 TẤT CẢ LỆNH SỬA CHỮA")
    if df.empty:
        st.info("Chưa có dữ liệu nào.")
    else:
        selected = st.dataframe(
            df.sort_values('ngay_tao', ascending=False),
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        if selected["selection"]["rows"]:
            idx = selected["selection"]["rows"][0]
            row = df.iloc[idx].to_dict()
            show_detail_dialog(row)

# Auto save
if not df.empty:
    df.to_csv(DATA_FILE, index=False)