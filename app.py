from supabase import create_client, Client
from datetime import datetime, timezone
import streamlit as st
import pandas as pd
import time
import re

# ====================== KẾT NỐI SUPABASE ======================
@st.cache_resource
def init_supabase() -> Client:
    url: str = st.secrets["supabase"]["url"]
    key: str = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase: Client = init_supabase()

# ====================== HÀM LẤY DỮ LIỆU TỪ SUPABASE ======================
EXPECTED_COLUMNS = [
    'so_phieu', 'bien_so', 'ten_chu_xe', 'yeu_cau_kh', 'ma_kieu_xe', 'so_khung',
    'nguoi_mang_xe', 'sdt_nguoi_mang', 'sdt', 'trang_thai', 'ngay_tao',
    'thoi_gian_bat_dau_lsc', 'is_xe_ton', 'ly_do_khong_ton',
    'thoi_gian_du_kien', 'cvdv_name', 'ghi_chu', 'httt',
    'baohiem_da_duyet', 'ngay_gui_baogia_baohiem', 'so_ngay_nhap_tre',
    'thoi_gian_ton_seconds'
]

def get_all_data():
    try:
        response = supabase.table("kpi_xe_ton").select("*").execute()
        data = response.data or []

        if not data:
            df = pd.DataFrame(columns=EXPECTED_COLUMNS)
        else:
            df = pd.DataFrame(data)
            for col in EXPECTED_COLUMNS:
                if col not in df.columns:
                    df[col] = None

        for col in ['ngay_tao', 'thoi_gian_bat_dau_lsc', 'thoi_gian_du_kien', 'ngay_gui_baogia_baohiem']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        return df

    except Exception as e:
        st.error(f"Lỗi khi kết nối Supabase: {e}")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

def refresh_data():
    global df
    df = get_all_data()

df = get_all_data()

# ====================== HÀM MÀN HÌNH CHI TIẾT  ======================
@st.dialog("📋 Chi tiết", width="large")
def show_detail_dialog(row):
    st.subheader(f"Chi tiết - {row.get('so_phieu', 'N/A')}")
    current_status = row.get('trang_thai', 'Báo Giá')
    role = st.session_state.role

    if 'edit_mode' not in st.session_state:
        st.session_state.edit_mode = False

    # THÔNG TIN CƠ BẢN
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

    # ====================== XEM BÁO GIÁ (Mở tab mới ngay) ======================
    if row.get('file_bao_gia'):
        try:
            # Lấy Signed URL
            signed_url = supabase.storage.from_("bao-gia").create_signed_url(
                path=row['file_bao_gia'],
                expires_in=3600
            )['signedURL']

            # Tạo nút HTML mở tab mới ngay khi click
            button_html = f"""
            <a href="{signed_url}" target="_blank" style="text-decoration: none;">
                <button style="
                    background-color: #4CAF50; 
                    color: white; 
                    padding: 10px 20px; 
                    border: none; 
                    border-radius: 6px; 
                    cursor: pointer;
                    font-size: 16px;
                    width: 100%;
                ">
                    📄 Xem báo giá
                </button>
            </a>
            """
            st.markdown(button_html, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Không thể tạo link xem file: {e}")
        
        st.divider()

    # ====================== TRẠNG THÁI TỒN / KHÔNG TỒN ======================
    st.subheader("Thông tin xe tồn")

    if not st.session_state.edit_mode:
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
        is_ton = st.toggle("Xe đang tồn", value=row.get('is_xe_ton', True), key="toggle_ton")
        options = ["Thiếu phụ tùng", "Thiếu nhân sự", "SC động cơ", "SC PIN", "Khác"] if is_ton else \
                  ["Lỗi DMS", "Đã cho KH mượn PIN", "Đã cho KH mượn xe", "KH đã đem xe về", "Khác"]
        ly_do = st.selectbox("Lý do", options=options, key="select_lydo")
        if ly_do == "Khác":
            ly_do = st.text_input("Nhập lý do khác:", placeholder="Nhập chi tiết...", key="text_lydo")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Lưu thay đổi", type="primary", key="btn_save_status"):
                if not ly_do or ly_do.strip() == "" or ly_do == "Khác":
                    st.error("❌ Vui lòng chọn hoặc nhập lý do!")
                else:
                    try:
                        supabase.table("kpi_xe_ton").update({
                            "is_xe_ton": is_ton,
                            "ly_do_khong_ton": ly_do.strip()
                        }).eq("so_phieu", row['so_phieu']).execute()
                        refresh_data()
                        st.success("✅ Đã lưu thay đổi!")
                        st.session_state.edit_mode = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi cập nhật Supabase: {e}")
        with col2:
            if st.button("❌ Hủy", type="secondary", key="btn_cancel_edit"):
                st.session_state.edit_mode = False
                st.rerun()

    # ====================== THỜI GIAN HOÀN THÀNH DỰ KIẾN ======================
    current_du_kien = row.get('thoi_gian_du_kien')
    today = datetime.now().date()

    if pd.notna(current_du_kien):
        default_date = pd.to_datetime(current_du_kien).date()
    else:
        default_date = today

    if st.session_state.role in ["admin", "cvdv"] and current_status not in ["Hoàn Thành", "Hủy"]:
        new_du_kien = st.date_input(
            "**Chọn ngày hoàn thành dự kiến**",
            value=default_date,
            min_value=today,                  
            key=f"date_du_kien_{row['so_phieu']}"
        )

        original_date = pd.to_datetime(current_du_kien).date() if pd.notna(current_du_kien) else None
        is_changed = new_du_kien != original_date

        col1, col2 = st.columns([3, 2])
        with col1:
            save_btn = st.button("💾 Lưu ngày dự kiến", type="primary", key=f"save_du_kien_{row['so_phieu']}")

        with col2:
            if is_changed:
                st.markdown("<span style='color:#ffaa00; font-weight:600;'>⚠️ Chưa lưu</span>", unsafe_allow_html=True)

        if save_btn and is_changed:
            with st.spinner("Đang lưu..."):
                try:
                    supabase.table("kpi_xe_ton").update({
                        "thoi_gian_du_kien": pd.to_datetime(new_du_kien).isoformat()
                    }).eq("so_phieu", row['so_phieu']).execute()
                    refresh_data()
                    time.sleep(0.6)
                    st.success("✅ Đã lưu!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi: {e}")
    else:
        if pd.notna(current_du_kien):
            st.write(f"**Ngày dự kiến hoàn thành:** {pd.to_datetime(current_du_kien).strftime('%d/%m/%Y')}")
        else:
            st.write("**Ngày dự kiến hoàn thành:** Chưa có")

    # ====================== THỜI GIAN TỒN ===========================
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
    if pd.notna(row.get('baohiem_da_duyet')) and row.get('baohiem_da_duyet') != "":
        st.divider()
        st.subheader("Thông tin bảo hiểm")
        baohiem_status = row.get('baohiem_da_duyet', '')
        
        if baohiem_status == "Đã duyệt":
            st.success("✅ Bảo hiểm đã duyệt")
        else:
            st.error("❌ Bảo hiểm chưa duyệt")

        if pd.notna(row.get('ngay_gui_baogia_baohiem')):
            st.write(f"**Ngày gửi báo giá bảo hiểm:** {pd.to_datetime(row.get('ngay_gui_baogia_baohiem')).strftime('%d/%m/%Y')}")

        if st.session_state.role in ["admin", "cvdv"] and current_status not in ["Hoàn Thành", "Hủy"]:
            toggle_key = f"toggle_baohiem_{row['so_phieu']}"
            
            is_approved = st.toggle(
                "Bảo hiểm đã duyệt",
                value=(baohiem_status == "Đã duyệt"),
                key=toggle_key
            )

            if st.button("💾 Lưu trạng thái bảo hiểm", type="primary", key=f"save_baohiem_{row['so_phieu']}"):
                try:
                    update_data = {
                        "baohiem_da_duyet": "Đã duyệt" if is_approved else "Chưa duyệt"
                    }
                    if is_approved and pd.isna(row.get('ngay_gui_baogia_baohiem')):
                        update_data["ngay_gui_baogia_baohiem"] = datetime.now().isoformat()

                    supabase.table("kpi_xe_ton").update(update_data).eq("so_phieu", row['so_phieu']).execute()
                    refresh_data()
                    st.success("✅ Đã cập nhật trạng thái bảo hiểm!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi cập nhật: {e}")

    st.divider()

    # ====================== KIỂM TRA QUYỀN ======================
    if current_status in ["Hoàn Thành", "Hủy"] and role not in ["admin", "manager"]:
        st.info(f"⚠️ Trạng thái đã {current_status.lower()}. Không thể chỉnh sửa.")
        return
    if role == "manager":
        return

    # ====================== CHỈNH SỬA TRẠNG THÁI LỆNH ======================
    st.write("**Chỉnh sửa trạng thái**")
    if role == "cvdv":
        allowed_status = ["Lệnh Sửa Chữa", "Hủy"] if current_status == "Báo Giá" else \
                         (["Hoàn Thành", "Hủy"] if current_status == "Lệnh Sửa Chữa" else [])
    else:
        allowed_status = ["Báo Giá", "Lệnh Sửa Chữa", "Hoàn Thành", "Hủy"]

    if not allowed_status:
        st.info("Không thể chỉnh sửa trạng thái này.")
        return

    new_trangthai = st.selectbox("Trạng thái mới", allowed_status, index=0)

    if st.button("💾 Lưu thay đổi", type="primary"):
        try:
            update_data = {"trang_thai": new_trangthai}
            if new_trangthai in ["Hoàn Thành", "Hủy"]:
                update_data["is_xe_ton"] = False
                if pd.notna(row.get('thoi_gian_bat_dau_lsc')):
                    start_time = pd.to_datetime(row['thoi_gian_bat_dau_lsc'])
                    print(start_time)
                    duration = pd.Timestamp.now(tz='UTC') - start_time
                    print(duration)
                    update_data["thoi_gian_ton_seconds"] = max(0, int(duration.total_seconds()))
                    print(max(0, int(duration.total_seconds())))
                update_data["ly_do_khong_ton"] = "Hoàn Thành" if new_trangthai == "Hoàn Thành" else "KH đổi/ hủy lịch"
            elif new_trangthai == "Báo Giá" and role == "admin":
                update_data["thoi_gian_bat_dau_lsc"] = None
                update_data["thoi_gian_ton_seconds"] = None
            if new_trangthai == "Lệnh Sửa Chữa" and pd.isna(row.get('thoi_gian_bat_dau_lsc')):
                update_data["thoi_gian_bat_dau_lsc"] = datetime.now(timezone.utc).isoformat()

            supabase.table("kpi_xe_ton").update(update_data).eq("so_phieu", row['so_phieu']).execute()
            refresh_data()
            st.success("✅ Đã cập nhật trạng thái!")
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi khi cập nhật: {e}")

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

cvdv_name = st.session_state.display_name

# ====================== SIDEBAR MENU ======================
menu_options = ["🚨 Danh sách Xe Đang Tồn", "📋 Tất cả Lệnh Sửa Chữa"]
if st.session_state.role in ["cvdv", "admin"]:
    menu_options = ["📤 Import Báo Giá PDF", "🚨 Danh sách Xe Đang Tồn", "📋 Tất cả Lệnh Sửa Chữa"]

menu = st.sidebar.radio("Chọn chức năng", menu_options, index=0, horizontal=False)

# ====================== IMPORT PDF ======================
if menu == "📤 Import Báo Giá PDF":
    st.header("📤 Import Báo Giá từ PDF")

    # ====================== UPLOAD FILE ======================
    if 'preview_data' not in st.session_state:
        uploaded_file = st.file_uploader(
            "Chọn file PDF Báo Giá", 
            type=['pdf'], 
            key="pdf_uploader"
        )

        if uploaded_file:
            try:
                import pdfplumber

                with pdfplumber.open(uploaded_file) as pdf:
                    full_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
                    lines = [line.strip() for line in full_text.split('\n') if line.strip()]

                # ==================== PARSE DỮ LIỆU ====================
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

                # Xác định HTTT
                pattern = r"\d+%\s+\d+\s+\b([WCI])\b"
                httt_list = re.findall(pattern, full_text)
                httt = "I" if "I" in httt_list else "W" if "W" in httt_list else "C"

                converted_time = datetime.strptime(ngay_tao, "%Y/%m/%d") if ngay_tao else datetime.now()

                # Lưu file vào session_state
                uploaded_file.seek(0)
                st.session_state.pdf_file_bytes = uploaded_file.read()
                st.session_state.pdf_file_name = uploaded_file.name

                # Lưu thông tin preview
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
                st.error(f"Lỗi khi đọc file PDF: {str(e)}")

    # ====================== HIỂN THỊ PREVIEW ======================
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

        # ====================== NÚT THÊM VÀ HỦY ======================
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Thêm vào danh sách", type="primary", use_container_width=True, disabled=is_duplicate):
                try:
                    file_bytes = st.session_state.get('pdf_file_bytes')
                    file_path = None

                    # Upload file lên Supabase Storage
                    if file_bytes:
                        file_path = f"{so_phieu_moi}.pdf"
                        supabase.storage.from_("bao-gia").upload(
                            file_path,
                            file_bytes,
                            {"content-type": "application/pdf"}
                        )

                    # Tạo dữ liệu mới
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
                        'ngay_tao': st.session_state.ngay_tao.isoformat() if st.session_state.ngay_tao else None,
                        'so_ngay_nhap_tre': (datetime.now().date() - st.session_state.ngay_tao.date()).days,
                        'thoi_gian_bat_dau_lsc': None,
                        'is_xe_ton': True,
                        'ly_do_khong_ton': "",
                        'thoi_gian_du_kien': None,
                        'cvdv_name': cvdv_name,
                        'ghi_chu': "",
                        'httt': st.session_state.httt,
                        'baohiem_da_duyet': "Chưa duyệt" if "BẢO HIỂM" in st.session_state.preview_data['Yêu cầu'].upper() or st.session_state.httt == "I" else "",
                        'ngay_gui_baogia_baohiem': datetime.now().isoformat() if ("BẢO HIỂM" in st.session_state.preview_data['Yêu cầu'].upper() or st.session_state.httt == "I") else None,
                        'file_bao_gia': file_path
                    }

                    supabase.table("kpi_xe_ton").insert(new_row).execute()
                    refresh_data()
                    st.success("✅ Đã thêm thành công và lưu file PDF!")

                    # Xóa dữ liệu tạm
                    for key in ['preview_data', 'pdf_file_bytes', 'pdf_file_name', 'uploaded_file_name', 'ngay_tao', 'httt']:
                        if key in st.session_state:
                            del st.session_state[key]

                    st.rerun()

                except Exception as e:
                    st.error(f"Lỗi khi thêm vào Supabase: {e}")

        with col2:
            if st.button("❌ Hủy", use_container_width=True):
                for key in ['preview_data', 'pdf_file_bytes', 'pdf_file_name', 'uploaded_file_name', 'ngay_tao', 'httt']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

# ====================== DANH SÁCH XE ĐANG TỒN ======================
elif menu == "🚨 Danh sách Xe Đang Tồn":
    st.header("🚨 DANH SÁCH XE ĐANG TỒN")

    # === PHẦN SỬA LỖI: Kiểm tra cột trước khi lọc ===
    if df.empty or 'is_xe_ton' not in df.columns:
        df_ton = pd.DataFrame()
    else:
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

        df_ton = df_ton.sort_values(by=['thoi_gian_ton_gio', 'so_phieu'], ascending=[False, True])

        # ====================== TẠO DATAFRAME HIỂN THỊ ======================
        df_display = df_ton[['so_phieu', 'bien_so', 'ten_chu_xe', 'yeu_cau_kh',
                             'trang_thai', 'thoi_gian_ton_display', 'cvdv_name', 
                             'thoi_gian_ton_gio']].copy().reset_index(drop=True)

        df_display.columns = [
            'Số phiếu', 'Biển số', 'Tên chủ xe', 'Yêu cầu KH',
            'Trạng thái', 'Thời gian tồn (giờ:phút:giây)', 'CVDV', 'thoi_gian_ton_gio'
        ]

        def highlight(row):
            if row['thoi_gian_ton_gio'] > 24:
                return ['background-color: #ffcccc'] * len(row)
            return [''] * len(row)

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
        df_display = df[['so_phieu', 'bien_so', 'ten_chu_xe', 'ma_kieu_xe', 
                         'yeu_cau_kh', 'trang_thai', 'so_ngay_nhap_tre', 
                         'cvdv_name', 'ngay_tao']].copy()
        df_display = df_display.sort_values(by=['ngay_tao', 'so_phieu'], ascending=False).reset_index(drop=True)
        df_display = df_display.rename(columns={
            'so_phieu': 'Số phiếu', 'bien_so': 'Biển số', 'ten_chu_xe': 'Tên chủ xe',
            'ma_kieu_xe': 'Mã kiểu xe', 'yeu_cau_kh': 'Yêu cầu KH', 'trang_thai': 'Trạng thái',
            'so_ngay_nhap_tre': 'Số ngày nhập trễ', 'cvdv_name': 'CVDV', 'ngay_tao': 'Ngày tạo'
        })

        selected = st.dataframe(
            df_display,
            column_order=['Số phiếu', 'Biển số', 'Mã kiểu xe', 'Tên chủ xe', 'Yêu cầu KH',
                         'Trạng thái', 'CVDV', 'Số ngày nhập trễ'],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )

        if selected["selection"]["rows"]:
            idx = selected["selection"]["rows"][0]
            selected_row = df_display.iloc[idx]
            row = df[df['so_phieu'] == selected_row['Số phiếu']].iloc[0].to_dict()
            show_detail_dialog(row)