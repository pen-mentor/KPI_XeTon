from datetime import datetime
import streamlit as st
import pandas as pd
import time
import os
import re

# ====================== HÀM MÀN HÌNH CHI TIẾT ======================
@st.dialog("📋 Chi tiết", width="large")
def show_detail_dialog(row):
    st.subheader(f"Chi tiết - {row.get('so_phieu', 'N/A')}")
    current_status = row.get('trang_thai', 'Báo Giá')
    role = st.session_state.role

    # Khởi tạo edit_mode nếu chưa có
    if 'edit_mode' not in st.session_state:
        st.session_state.edit_mode = False
    
    # ====================== THÔNG TIN CƠ BẢN ======================
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Biển số:** {row.get('bien_so', 'N/A')}")
        st.write(f"**Tên chủ xe:** {row.get('ten_chu_xe', 'N/A')}")
        st.write(f"**SĐT chủ xe:** {row.get('sdt', 'N/A')}")
        st.write(f"**Người mang xe đến:** {row.get('nguoi_mang_xe', 'N/A')}")
        st.write(f"**SĐT người mang xe đến:** {row.get('sdt_nguoi_mang', 'N/A')}")
    
    with col2:
        st.write(f"**Trạng thái:** {row.get('trang_thai', 'N/A')}")
        st.write(f"**CVDV:** {row.get('cvdv_name', 'N/A')}")
        st.write(f"**Yêu cầu KH:** {row.get('yeu_cau_kh', 'N/A')}")
        st.write(f"**Mã kiểu xe:** {row.get('ma_kieu_xe', 'N/A')}")
        st.write(f"**Số khung:** {row.get('so_khung', 'N/A')}")

    st.divider()

    # ====================== TRẠNG THÁI TỒN / KHÔNG TỒN ======================
    st.subheader("Thông tin xe tồn")

    if not st.session_state.edit_mode:
        # Chế độ xem
        is_ton = row.get('is_xe_ton', True)
        ly_do = row.get('ly_do_khong_ton', '')

        if is_ton:
            st.error("🚨 Xe đang tồn")
            st.write(f"**Lý do tồn:** {ly_do if pd.notna(ly_do) else 'Chưa có lý do'}")
        else:
            st.success("✅ Xe không tồn")
            st.write(f"**Lý do không tồn:** {ly_do if pd.notna(ly_do) else 'Chưa có lý do'}")

        if st.session_state.role in ["admin", "cvdv"] and current_status not in ["Hoàn Thành", "Hủy"]:
            if st.button("✏️ Cập nhật thông tin", type="primary", key="btn_edit_mode"):
                st.session_state.edit_mode = True
                st.rerun()

    else:
        # Chế độ chỉnh sửa
        is_ton = st.toggle("Xe đang tồn", value=row.get('is_xe_ton', True), key="toggle_ton")

        if is_ton:
            options = ["Thiếu phụ tùng", "Thiếu nhân sự", "SC động cơ", "SC PIN", "Khác"]
        else:
            options = ["Lỗi DMS", "Đã cho KH mượn PIN", "Đã cho KH mượn xe", "KH đã đem xe về", "Khác"]

        ly_do = st.selectbox("Lý do", options=options, key="select_lydo")

        if ly_do == "Khác":
            ly_do = st.text_input("Nhập lý do khác:", placeholder="Nhập chi tiết...", key="text_lydo")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Lưu thay đổi", type="primary", key="btn_save_status"):
                if not ly_do or ly_do.strip() == "" or ly_do == "Khác":
                    st.error("❌ Vui lòng chọn hoặc nhập lý do!")
                else:
                    mask = df['so_phieu'] == row['so_phieu']
                    if mask.any():
                        df.loc[mask, 'is_xe_ton'] = is_ton
                        df.loc[mask, 'ly_do_khong_ton'] = ly_do.strip()
                        df.to_csv(DATA_FILE, index=False)
                        st.success("✅ Đã lưu thay đổi!")
                        st.session_state.edit_mode = False
                        st.rerun()

        with col2:
            if st.button("❌ Hủy", type="secondary", key="btn_cancel_edit"):
                st.session_state.edit_mode = False
                st.rerun()

    if st.session_state.role in ["admin", "cvdv"] and current_status not in ["Hoàn Thành", "Hủy"]:
        st.divider()

    # ====================== THỜI GIAN HOÀN THÀNH DỰ KIẾN ======================
    current_du_kien = row.get('thoi_gian_du_kien')
    today = datetime.now().date()

    if pd.notna(current_du_kien):
        default_date = pd.to_datetime(current_du_kien).date()
        if default_date < today:
            default_date = today
    else:
        default_date = today

    if st.session_state.role in ["admin", "cvdv"] and current_status not in ["Hoàn Thành", "Hủy"]:
        
        new_du_kien = st.date_input(
            "**Chọn ngày hoàn thành dự kiến**",
            value=default_date,
            min_value=today,
            key="date_du_kien"
        )

        # Kiểm tra xem người dùng có thay đổi ngày chưa
        original_date = pd.to_datetime(current_du_kien).date() if pd.notna(current_du_kien) else None
        is_changed = new_du_kien != original_date

        col1, col2 = st.columns([3, 2])
        with col1:
            save_btn = st.button("💾 Lưu ngày dự kiến", type="primary", key="save_du_kien")

        with col2:
            if is_changed:
                st.markdown("<span style='color: #ffaa00; font-weight: 600;'>⚠️ Chưa lưu</span>", unsafe_allow_html=True)
            else:
                st.write("")   # giữ chỗ

        if save_btn:
            if is_changed:
                with st.spinner("Đang lưu..."):
                    mask = df['so_phieu'] == row['so_phieu']
                    if mask.any():
                        df.loc[mask, 'thoi_gian_du_kien'] = pd.to_datetime(new_du_kien)
                        df.to_csv(DATA_FILE, index=False)
                    time.sleep(0.7)   # để thấy icon xoay rõ

                st.success("✅ Đã lưu!")
                st.rerun()
            else:
                st.info("Bạn chưa thay đổi ngày.")
    else:
        # Manager chỉ xem
        if pd.notna(current_du_kien):
            st.write(f"**Ngày dự kiến hoàn thành:** {pd.to_datetime(current_du_kien).strftime('%d/%m/%Y')}")
        else:
            st.write("**Ngày dự kiến hoàn thành:** Chưa có")

    # ====================== THỜI GIAN TỒN (HIỂN THỊ) ======================
    if row.get('trang_thai') in ["Hoàn Thành", "Hủy"] and 'thoi_gian_ton_seconds' in row and pd.notna(row.get('thoi_gian_ton_seconds')):
        seconds = int(row['thoi_gian_ton_seconds'])
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        st.write(f"**Thời gian tồn:** {h:02d}:{m:02d}:{s:02d}")
    elif 'thoi_gian_ton_gio' in row and pd.notna(row.get('thoi_gian_ton_gio')):
        st.write(f"**Thời gian tồn:** {row['thoi_gian_ton_gio']:.2f} giờ")
    else:
        st.write("**Thời gian tồn:** Đang tính...")

    # ====================== THÔNG TIN BẢO HIỂM ======================
    if pd.notna(row.get('baohiem_da_duyet')):
        st.divider()
        st.subheader("Thông tin bảo hiểm")

        baohiem_status = row.get('baohiem_da_duyet', '')
        ngay_gui = row.get('ngay_gui_baogia_baohiem')

        # Hiển thị trạng thái hiện tại
        if baohiem_status == "Đã duyệt":
            st.success("✅ Bảo hiểm đã duyệt")
        else:
            st.error("❌ Bảo hiểm chưa duyệt")

        if pd.notna(ngay_gui):
            st.write(f"**Ngày gửi báo giá bảo hiểm:** {pd.to_datetime(ngay_gui).strftime('%d/%m/%Y')}")

        # Chỉ cho phép chỉnh sửa nếu là admin hoặc cvdv và chưa hoàn thành/hủy
        if st.session_state.role in ["admin", "cvdv"] and current_status not in ["Hoàn Thành", "Hủy"]:
            
            # Switch để thay đổi trạng thái bảo hiểm
            is_approved = st.toggle(
                "Bảo hiểm đã duyệt",
                value=(baohiem_status == "Đã duyệt"),
                key="toggle_baohiem"
            )

            if st.button("💾 Lưu trạng thái bảo hiểm", type="primary", key="save_baohiem"):
                mask = df['so_phieu'] == row['so_phieu']
                if mask.any():
                    if is_approved:
                        df.loc[mask, 'baohiem_da_duyet'] = "Đã duyệt"
                        # Nếu chưa có ngày gửi thì tự động set ngày hôm nay
                        if pd.isna(ngay_gui):
                            df.loc[mask, 'ngay_gui_baogia_baohiem'] = datetime.now()
                    else:
                        df.loc[mask, 'baohiem_da_duyet'] = "Chưa duyệt"
                        # Khi chuyển về chưa duyệt thì xóa ngày gửi (nếu muốn)
                        # df.loc[mask, 'ngay_gui_baogia_baohiem'] = None

                    df.to_csv(DATA_FILE, index=False)
                    st.success("✅ Đã cập nhật trạng thái bảo hiểm!")
                    st.rerun()

    st.divider()

    # ====================== KIỂM TRA QUYỀN ======================
    if current_status in ["Hoàn Thành", "Hủy"] and role not in ["admin", "manager"]:
        st.info(f"⚠️ Trạng thái đã {current_status.lower()}. Không thể chỉnh sửa.")
        return

    if role == "manager":
        return

    # ====================== HIỂN THỊ FORM CHỈNH SỬA ======================
    st.write("**Chỉnh sửa trạng thái**")

    if role == "cvdv":
        if current_status == "Báo Giá":
            allowed_status = ["Lệnh Sửa Chữa", "Hủy"]
        elif current_status == "Lệnh Sửa Chữa":
            allowed_status = ["Hoàn Thành", "Hủy"]
        else:
            allowed_status = []
    else:  # admin
        allowed_status = ["Báo Giá", "Lệnh Sửa Chữa", "Hoàn Thành", "Hủy"]

    if not allowed_status:
        st.info("Không thể chỉnh sửa trạng thái này.")
        return

    new_trangthai = st.selectbox("Trạng thái mới", allowed_status, index=0)

    # ====================== NÚT LƯU ======================
    if st.button("💾 Lưu thay đổi", type="primary"):
        mask = df['so_phieu'] == row['so_phieu']
        if mask.any():
            if "E" in str(df.loc[mask, 'so_phieu'].values[0]) and new_trangthai == "Lệnh Sửa Chữa":
                st.session_state.show_new_so_phieu_input = True
                st.session_state.pending_mask = mask
                st.session_state.pending_trangthai = new_trangthai
                st.rerun()
            else:
                df.loc[mask, 'trang_thai'] = new_trangthai

                if new_trangthai in ["Hoàn Thành", "Hủy"]:
                    df.loc[mask, 'is_xe_ton'] = False
                    if pd.notna(row.get('thoi_gian_bat_dau_lsc')):
                        start_time = pd.to_datetime(row['thoi_gian_bat_dau_lsc'])
                        duration = datetime.now() - start_time
                        total_seconds = int(duration.total_seconds())
                        df.loc[mask, 'thoi_gian_ton_seconds'] = total_seconds
                    if new_trangthai == "Hoàn Thành":
                        df.loc[mask, 'ly_do_khong_ton'] = "Hoàn Thành"
                    elif new_trangthai == "Hủy":
                        df.loc[mask, 'ly_do_khong_ton'] = "KH đổi/ hủy lịch"
                elif new_trangthai == "Báo Giá" and role == "admin":
                    df.loc[mask, 'thoi_gian_bat_dau_lsc'] = None
                    if 'thoi_gian_ton_seconds' in df.columns:
                        df.loc[mask, 'thoi_gian_ton_seconds'] = None

                if new_trangthai == "Lệnh Sửa Chữa" and pd.isna(row.get('thoi_gian_bat_dau_lsc')):
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    df.loc[mask, 'thoi_gian_bat_dau_lsc'] = now_str

                df.to_csv(DATA_FILE, index=False)
                st.success("✅ Đã cập nhật trạng thái!")
                st.rerun()

    # ====================== FORM ĐỔI SỐ PHIẾU (cho phiếu E) ======================
    if st.session_state.get('show_new_so_phieu_input', False):
        st.warning("⚠️ Vui lòng cập nhật số phiếu chính xác cho lệnh sửa chữa.")
        with st.form(key="change_so_phieu_form"):
            new_so_phieu = st.text_input("Nhập số phiếu mới:", value=row['so_phieu'])
            submit_new_phieu = st.form_submit_button("Xác nhận đổi số phiếu & Lưu")
            
            if submit_new_phieu:
                if new_so_phieu.strip() == "":
                    st.error("Không được để trống số phiếu mới!")
                else:
                    active_mask = st.session_state.pending_mask
                    active_trangthai = st.session_state.pending_trangthai
                    
                    df.loc[active_mask, 'so_phieu'] = new_so_phieu
                    df.loc[active_mask, 'trang_thai'] = active_trangthai
                    
                    if active_trangthai == "Lệnh Sửa Chữa":
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        df.loc[active_mask, 'thoi_gian_bat_dau_lsc'] = now_str
                    
                    df.to_csv(DATA_FILE, index=False)
                    
                    st.session_state.show_new_so_phieu_input = False
                    st.session_state.pending_mask = None
                    st.session_state.pending_trangthai = None
                    st.success("✅ Đã đổi số phiếu và cập nhật trạng thái!")
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
    "ngocbt": {"password": "123", "display_name": "Bùi Tuấn Ngọc", "role": "cvdv"},
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
    # Khởi tạo từ đầu với kiểu dữ liệu đúng
    df = pd.DataFrame(columns=[
        'so_phieu', 'bien_so', 'ten_chu_xe', 'yeu_cau_kh', 'ma_kieu_xe', 'so_khung',
        'nguoi_mang_xe', 'sdt_nguoi_mang', 'sdt', 'trang_thai', 'ngay_tao',
        'thoi_gian_bat_dau_lsc', 'is_xe_ton', 'ly_do_khong_ton',
        'thoi_gian_du_kien', 'cvdv_name', 'ghi_chu', 'httt',
        'baohiem_da_duyet', 'ngay_gui_baogia_baohiem', 'so_ngay_nhap_tre'
    ])

    # Khởi tạo kiểu dữ liệu đúng ngay từ đầu
    df['ly_do_khong_ton'] = ""                    # string rỗng
    df['is_xe_ton'] = True                        # boolean
    df['thoi_gian_ton_seconds'] = None            # cho thời gian đóng băng
    df['thoi_gian_bat_dau_lsc'] = None
    df['thoi_gian_du_kien'] = None
    df['ngay_tao'] = None
    df['ngay_gui_baogia_baohiem'] = None

# Ép lại một số cột cho an toàn
df['ly_do_khong_ton'] = df['ly_do_khong_ton'].astype(str).replace('nan', '')

# ====================== KHỞI TẠO CỘT MỚI (QUAN TRỌNG) ======================
if 'thoi_gian_ton_seconds' not in df.columns:
    df['thoi_gian_ton_seconds'] = None

# ====================== SIDEBAR MENU ======================
menu_options = ["🚨 Danh sách Xe Đang Tồn", "📋 Tất cả Lệnh Sửa Chữa"]

if st.session_state.role in ["cvdv", "admin"]:
    menu_options = ["📤 Import Báo Giá PDF", "🚨 Danh sách Xe Đang Tồn", "📋 Tất cả Lệnh Sửa Chữa"]

menu = st.sidebar.radio("Chọn chức năng", menu_options, index=0, horizontal=False)

cvdv_name = st.session_state.display_name

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

# ====================== 2. DANH SÁCH XE ĐANG TỒN ======================
elif menu == "🚨 Danh sách Xe Đang Tồn":
    st.header("🚨 DANH SÁCH XE ĐANG TỒN")
    df_ton = df[df['is_xe_ton'] == True].copy()
    
    if not df_ton.empty:
        # Khởi tạo cột
        df_ton['thoi_gian_ton_display'] = "00:00:00"
        df_ton['thoi_gian_ton_gio'] = 0.0

        # === XE ĐANG HOẠT ĐỘNG ===
        active_mask = df_ton['trang_thai'].isin(["Báo Giá", "Lệnh Sửa Chữa"])
        if active_mask.any():
            for idx in df_ton[active_mask].index:
                try:
                    start = pd.to_datetime(df_ton.loc[idx, 'thoi_gian_bat_dau_lsc'])
                    seconds = int((datetime.now() - start).total_seconds())
                    
                    h = seconds // 3600
                    m = (seconds % 3600) // 60
                    s = seconds % 60
                    df_ton.loc[idx, 'thoi_gian_ton_display'] = f"{h:02d}:{m:02d}:{s:02d}"
                    df_ton.loc[idx, 'thoi_gian_ton_gio'] = round(seconds / 3600, 2)
                except:
                    pass

        # === XE ĐÃ HOÀN THÀNH / HỦY ===
        completed_mask = df_ton['trang_thai'].isin(["Hoàn Thành", "Hủy"]) & df_ton['thoi_gian_ton_seconds'].notna()
        if completed_mask.any():
            for idx in df_ton[completed_mask].index:
                try:
                    seconds = int(df_ton.loc[idx, 'thoi_gian_ton_seconds'])
                    h = seconds // 3600
                    m = (seconds % 3600) // 60
                    s = seconds % 60
                    df_ton.loc[idx, 'thoi_gian_ton_display'] = f"{h:02d}:{m:02d}:{s:02d}"
                    df_ton.loc[idx, 'thoi_gian_ton_gio'] = round(seconds / 3600, 2)
                except:
                    pass

        df_ton = df_ton.sort_values('thoi_gian_ton_gio', ascending=False)

        # ====================== TẠO DATAFRAME HIỂN THỊ ======================
        df_display = df_ton[['so_phieu', 'bien_so', 'ten_chu_xe', 'yeu_cau_kh',
                             'trang_thai', 'thoi_gian_ton_display', 'cvdv_name', 
                             'thoi_gian_ton_gio']].copy().reset_index(drop=True)   # ← Giữ lại thoi_gian_ton_gio

        # Đổi tên cột
        df_display.columns = [
            'Số phiếu', 
            'Biển số', 
            'Tên chủ xe', 
            'Yêu cầu KH', 
            'Trạng thái', 
            'Thời gian tồn (giờ:phút:giây)', 
            'CVDV',
            'thoi_gian_ton_gio'   # Giữ tên gốc để highlight dùng được
        ]

        # Hàm tô màu
        def highlight(row):
            if row['thoi_gian_ton_gio'] > 24:
                return ['background-color: #ffcccc'] * len(row)
            return [''] * len(row)

        # ====================== HIỂN THỊ BẢNG ======================
        selected = st.dataframe(
            df_display.style.apply(highlight, axis=1),
            column_order=['Số phiếu', 'Biển số', 'Tên chủ xe', 'Yêu cầu KH',
                         'Trạng thái', 'Thời gian tồn (giờ:phút:giây)', 'CVDV'],
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
        
# ====================== TẤT CẢ LỆNH SỬA CHỮA ======================
else:
    st.header("📋 TẤT CẢ LỆNH SỬA CHỮA")
    
    if df.empty:
        st.info("Chưa có dữ liệu nào.")
    else:
        # Tạo bảng hiển thị (giống cấu trúc màn hình Xe Đang Tồn)
        df_display = df[['so_phieu', 'bien_so', 'ten_chu_xe', 'ma_kieu_xe', 
                         'yeu_cau_kh', 'trang_thai', 'so_ngay_nhap_tre', 
                         'cvdv_name', 'ngay_tao']].copy()

        # Sắp xếp theo ngày tạo mới nhất
        df_display = df_display.sort_values('ngay_tao', ascending=False).reset_index(drop=True)

        # Đổi tên cột đẹp (tương tự màn hình Xe Đang Tồn)
        df_display = df_display.rename(columns={
            'so_phieu': 'Số phiếu',
            'bien_so': 'Biển số',
            'ten_chu_xe': 'Tên chủ xe',
            'ma_kieu_xe': 'Mã kiểu xe',
            'yeu_cau_kh': 'Yêu cầu KH',
            'trang_thai': 'Trạng thái',
            'so_ngay_nhap_tre': 'Số ngày nhập trễ',
            'cvdv_name': 'CVDV',
            'ngay_tao': "Ngày tạo"
        })

        # Hiển thị bảng
        selected = st.dataframe(
            df_display,
            column_order=[
                'Số phiếu', 
                'Biển số', 
                'Mã kiểu xe',
                'Tên chủ xe', 
                'Yêu cầu KH', 
                'Trạng thái', 
                'CVDV',
                'Số ngày nhập trễ'
            ],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )

        # Xử lý khi click vào dòng
        if selected["selection"]["rows"]:
            idx = selected["selection"]["rows"][0]
            # Lấy dòng từ df_display (đã reset index)
            selected_row = df_display.iloc[idx]
            
            # Lấy lại dòng đầy đủ từ df gốc theo số phiếu (an toàn nhất)
            row = df[df['so_phieu'] == selected_row['Số phiếu']].iloc[0].to_dict()
            show_detail_dialog(row)

# Auto save
if not df.empty:
    df.to_csv(DATA_FILE, index=False)