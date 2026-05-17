from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import os
import re

# ====================== ĐĂNG NHẬP ======================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.display_name = ""
    st.session_state.role = ""

# Danh sách người dùng
USERS = {
    "quyennv": {"password": "123", "display_name": "Nguyễn Văn Quyền", "role": "cvdv"},
    "sonnt": {"password": "123", "display_name": "Nguyễn Trịnh Sơn", "role": "cvdv"},
    "pvgkhanh": {"password": "1234Ac12@", "display_name": "Phạm Viết Gia Khánh", "role": "admin"},
    "quyenttk": {"password": "090524@quyen", "display_name": "Trần Thị Kim Quyên", "role": "manager"},
}

# Form đăng nhập
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
                   "📋 Tất cả Lệnh Sửa Chữa", "⚙️ Quản lý Trạng thái"]

menu = st.sidebar.selectbox("Chọn chức năng", menu_options)

cvdv_name = st.session_state.display_name   # Tên hiển thị thay vì username

# ====================== 1. IMPORT PDF ======================
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

                # ==================== PARSE (GIỮ NGUYÊN CỦA BẠN) ====================
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

    # Preview
    if 'preview_data' in st.session_state:
        st.success(f"📄 Đã đọc báo giá số: **{st.session_state.uploaded_file_name}**")
        st.subheader("📋 Thông tin Preview")
        st.dataframe(pd.DataFrame([st.session_state.preview_data]), use_container_width=True, hide_index=True)

        # Kiểm tra trùng
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
                    'baohiem_da_duyet': "BẢO" in st.session_state.preview_data['Yêu cầu'].upper(),
                    'ngay_gui_baogia_baohiem': datetime.now() if "BẢO" in st.session_state.preview_data['Yêu cầu'].upper() else None
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

# ====================== DANH SÁCH XE TỒN ======================
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
        
        st.dataframe(
            df_ton.style.apply(highlight, axis=1),
            column_order=['so_phieu', 'bien_so', 'ten_chu_xe', 'yeu_cau_kh',
                         'trang_thai', 'thoi_gian_ton_gio', 'cvdv_name'],
            use_container_width=True,
            hide_index=True
        )
        st.warning(f"**Tổng số xe đang tồn: {len(df_ton)} xe**")
    else:
        st.success("✅ Hiện không có xe nào đang tồn.")

# ====================== QUẢN LÝ TRẠNG THÁI ======================
elif menu == "⚙️ Quản lý Trạng thái":
    st.header("⚙️ Cập nhật Trạng thái Xe")
    if df.empty:
        st.info("Chưa có dữ liệu nào.")
    else:
        selected = st.selectbox("Chọn Số Phiếu để cập nhật", df['so_phieu'].unique())
        row_idx = df[df['so_phieu'] == selected].index[0]
        row = df.loc[row_idx]

        col1, col2 = st.columns(2)
        with col1:
            new_trangthai = st.selectbox("Trạng thái", ["Báo Giá", "Lệnh Sửa Chữa (LSC)", "Hoàn Thành", "Hủy"])
            is_ton = st.checkbox("Xe đang tồn", value=bool(row['is_xe_ton']))
            if not is_ton:
                ly_do = st.text_area("Lý do không tồn", value=row.get('ly_do_khong_ton', ""))
        
        with col2:
            du_kien = st.date_input("Dự kiến hoàn thành",
                value=row['thoi_gian_du_kien'] if pd.notna(row.get('thoi_gian_du_kien')) else datetime.now() + timedelta(days=2))
            ghi_chu = st.text_area("Ghi chú", value=row.get('ghi_chu', ""))

        if st.button("💾 Lưu thay đổi", type="primary"):
            df.at[row_idx, 'trang_thai'] = new_trangthai
            df.at[row_idx, 'is_xe_ton'] = is_ton
            df.at[row_idx, 'ly_do_khong_ton'] = ly_do if 'ly_do' in locals() and not is_ton else ""
            df.at[row_idx, 'thoi_gian_du_kien'] = pd.to_datetime(du_kien)
            df.at[row_idx, 'ghi_chu'] = ghi_chu
            df.at[row_idx, 'cvdv_name'] = cvdv_name

            if new_trangthai == "Lệnh Sửa Chữa (LSC)" and pd.isna(df.at[row_idx, 'thoi_gian_bat_dau_lsc']):
                df.at[row_idx, 'thoi_gian_bat_dau_lsc'] = datetime.now()

            df.to_csv(DATA_FILE, index=False)
            st.success("✅ Đã lưu thay đổi!")
            st.rerun()

# ====================== TẤT CẢ LỆNH ======================
else:
    st.header("📋 TẤT CẢ LỆNH SỬA CHỮA")
    if df.empty:
        st.info("Chưa có dữ liệu nào.")
    else:
        st.dataframe(df.sort_values('ngay_tao', ascending=False), use_container_width=True, hide_index=True)

# Auto save
if not df.empty:
    df.to_csv(DATA_FILE, index=False)