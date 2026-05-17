from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import os
import re

st.set_page_config(page_title="KPI Xe Tồn 24h", layout="wide", page_icon="🚗")
st.title("🚗 QUẢN LÝ XE TỒN 24H - KPI QUÝ II")
st.markdown("**VinFast Thịnh Phát Bình Long**")

# ====================== CẤU HÌNH ======================
DATA_FOLDER = "data"
DATA_FILE = f"{DATA_FOLDER}/xe_ton.csv"

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# Load dữ liệu
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    for col in ['ngay_tao', 'thoi_gian_bat_dau_lsc', 'thoi_gian_du_kien']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
else:
    df = pd.DataFrame(columns=[
        'so_phieu', 'bien_so', 'ten_chu_xe', 'yeu_cau_kh', 'ma_kieu_xe', 'so_khung',
        'trang_thai', 'ngay_tao', 'thoi_gian_bat_dau_lsc', 'is_xe_ton',
        'ly_do_khong_ton', 'thoi_gian_du_kien', 'cvdv_name', 'ghi_chu',
        'httt', 'baohiem_da_duyet', 'ngay_gui_baogia_baohiem'
    ])

# ====================== SIDEBAR ======================
menu = st.sidebar.selectbox("Chọn chức năng", [
    "📤 Import Báo Giá Excel",
    "🚨 Danh sách Xe Đang Tồn",
    "📋 Tất cả Lệnh Sửa Chữa",
    "⚙️ Quản lý Trạng thái"
])

cvdv_name = st.sidebar.text_input("Tên CVDV", value="Nguyễn Văn A")

# ====================== IMPORT PDF - PHIÊN BẢN SẠCH HƠN ======================
if menu == "📤 Import Báo Giá Excel":
    st.header("📤 Import Báo Giá từ PDF")
    uploaded_file = st.file_uploader("Chọn file PDF Báo Giá", type=['pdf'])
    
    if uploaded_file:
        try:
            import pdfplumber
            with pdfplumber.open(uploaded_file) as pdf:
                full_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
                lines = [line.strip() for line in full_text.split('\n') if line.strip()]

            so_phieu = bien_so = ten_chu_xe = yeu_cau_kh = ma_kieu_xe = so_khung = ""
            nguoi_mang_xe = sdt_nguoi_mang = httt = ""

            for i, line in enumerate(lines):
                # Số phiếu
                if "Số phiếu:" in line:
                    so_phieu = line.split(":")[1].split("Ngày")[0].strip()
                    # so_phieu = line.split("Số phiếu:")[1].strip()

                # Biển số
                if "Biển số" in line and ":" in line:
                    bien_so = line.split(":")[-1].strip()

                # Chủ xe - Xử lý dòng nhiều
                if "Chủ xe" in line:
                    ten_chu_xe = line.split(":")[1].split("Biển")[0].strip()

                # Người mang xe đến
                if "Người mang xe đến" in line:
                    nguoi_mang_xe = line.split(":")[1].split("Số")[0].strip()

                # SĐT người mang xe
                if "Điện thoại" in line and nguoi_mang_xe and not sdt_nguoi_mang:
                    sdt_nguoi_mang = line.split(":")[1].split("Ngày")[0].strip()

                # Yêu cầu khách hàng
                if "Yêu cầu khách hàng" in line:
                    yeu_cau_kh = line.split(":")[1].strip()

                # Mã kiểu xe
                if "Mã kiểu xe" in line:
                    ma_kieu_xe = line.split(":")[-1].strip()

                # Số khung
                if "Số khung" in line:
                    so_khung = line.split(":")[-1].split("Email")[0].strip()

            # Xác định HTTT
            pattern = r"\d+%\s+\d+\s+\b([WC])\b"
            httt = re.findall(pattern, full_text)

            new_row = {
                'Số WO': so_phieu or "N/A",
                'Biển số': bien_so or "",
                'Tên chủ xe': ten_chu_xe.strip() or "",
                'Yêu cầu': yeu_cau_kh or "",
                'Loại xe': ma_kieu_xe or "",
                'Số khung': so_khung or "",
                'Người mang xe đến': nguoi_mang_xe or "",
                'SĐT người mang xe đến': sdt_nguoi_mang or "",
                'Trạng thái': "Báo Giá",
                'Ngày tạo': datetime.now(),
                'thoi_gian_bat_dau_lsc': None,
                'is_xe_ton': True,
                'ly_do_khong_ton': "",
                'thoi_gian_du_kien': None,
                'cvdv_name': cvdv_name,
                'ghi_chu': "",
                'httt': httt,
                'baohiem_da_duyet': "BẢO" in (yeu_cau_kh.upper() or ""),
                'ngay_gui_baogia_baohiem': datetime.now() if "BẢO" in (yeu_cau_kh.upper() or "") else None
            }

            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            
            st.success(f"✅ Import thành công: **{so_phieu}**")
            st.json(new_row)
            
            # if st.checkbox("Debug - Xem full text"):
            #     st.text(full_text[:3000])
                
        except Exception as e:
            st.error(f"Lỗi: {str(e)}")

# ====================== DANH SÁCH XE TỒN ======================
elif menu == "🚨 Danh sách Xe Đang Tồn":
    st.header("🚨 DANH SÁCH XE ĐANG TỒN")
    
    df_ton = df[df['is_xe_ton'] == True].copy()
    
    if not df_ton.empty:
        # Tính thời gian tồn
        df_ton['thoi_gian_ton_gio'] = 0.0
        mask = df_ton['thoi_gian_bat_dau_lsc'].notna()
        df_ton.loc[mask, 'thoi_gian_ton_gio'] = (
            (datetime.now() - df_ton.loc[mask, 'thoi_gian_bat_dau_lsc']).dt.total_seconds() / 3600
        ).round(2)
        
        df_ton = df_ton.sort_values('thoi_gian_ton_gio', ascending=False)
        
        # Highlight xe tồn > 24h
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
        st.info("Xe màu đỏ là xe tồn **trên 24 giờ** (cần xử lý gấp)")
    else:
        st.success("✅ Hiện không có xe nào đang tồn.")

# ====================== QUẢN LÝ TRẠNG THÁI ======================
elif menu == "⚙️ Quản lý Trạng thái":
    st.header("⚙️ Cập nhật Trạng thái Xe")
    
    if df.empty:
        st.info("Chưa có dữ liệu nào.")
    else:
        selected = st.selectbox("Chọn Số Phiếu để cập nhật", df['so_phieu'].unique())
        row = df[df['so_phieu'] == selected].iloc[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_trangthai = st.selectbox("Trạng thái", 
                ["Báo Giá", "Lệnh Sửa Chữa (LSC)", "Hoàn Thành", "Hủy"], 
                index=["Báo Giá", "Lệnh Sửa Chữa (LSC)", "Hoàn Thành", "Hủy"].index(row['trang_thai']) if row['trang_thai'] in ["Báo Giá", "Lệnh Sửa Chữa (LSC)", "Hoàn Thành", "Hủy"] else 0)
            
            is_ton = st.checkbox("Xe đang tồn", value=row['is_xe_ton'])
            
            if not is_ton:
                ly_do = st.text_area("Lý do không tồn", value=row['ly_do_khong_ton'])
        
        with col2:
            if new_trangthai == "Lệnh Sửa Chữa (LSC)" and pd.isna(row['thoi_gian_bat_dau_lsc']):
                st.success("✅ Sẽ bắt đầu tính thời gian tồn từ lúc lưu")
            
            du_kien = st.date_input("Dự kiến hoàn thành", 
                                  value=row['thoi_gian_du_kien'] if pd.notna(row['thoi_gian_du_kien']) else datetime.now() + timedelta(days=2))
            
            ghi_chu = st.text_area("Ghi chú thêm", value=row['ghi_chu'])
        
        if st.button("💾 Lưu thay đổi", type="primary"):
            idx = df[df['so_phieu'] == selected].index[0]
            
            df.at[idx, 'trang_thai'] = new_trangthai
            df.at[idx, 'is_xe_ton'] = is_ton
            df.at[idx, 'ly_do_khong_ton'] = ly_do if not is_ton else ""
            df.at[idx, 'thoi_gian_du_kien'] = pd.to_datetime(du_kien)
            df.at[idx, 'ghi_chu'] = ghi_chu
            df.at[idx, 'cvdv_name'] = cvdv_name
            
            # Bắt đầu tính thời gian khi chuyển sang LSC
            if new_trangthai == "Lệnh Sửa Chữa (LSC)" and pd.isna(df.at[idx, 'thoi_gian_bat_dau_lsc']):
                df.at[idx, 'thoi_gian_bat_dau_lsc'] = datetime.now()
            
            df.to_csv(DATA_FILE, index=False)
            st.success("✅ Đã lưu thay đổi!")
            st.rerun()

# ====================== TẤT CẢ LỆNH ======================
else:
    st.header("📋 Tất cả Lệnh Sửa Chữa")
    st.dataframe(df.sort_values('ngay_tao', ascending=False), use_container_width=True, hide_index=True)

# Auto save
if not df.empty:
    df.to_csv(DATA_FILE, index=False)