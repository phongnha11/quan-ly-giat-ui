import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date

# --- CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="Hải Âu Mũi Né - Quản Lý Giặt Ủi",
    page_icon="🌊",
    layout="wide"
)

# --- DANH SÁCH MẶT HÀNG (Cố định theo mẫu in) ---
ITEMS = [
    "Áo gối", "Áo choàng", "Bọc lớn", "Bọc nhỏ", "Bảo vệ nệm",
    "Bọc mền", "Drap lớn", "Drap nhỏ", "Drap thun", "Khăn hồ bơi",
    "Khăn tắm lớn trắng", "Khăn tay", "Khăn mặt", "Khăn Welcome",
    "Khăn bàn", "Mền", "Thảm chân", "Tấm trang trí", "Rèm cửa",
    "Mùng", "Gối ghế"
]

# --- HÀM KẾT NỐI GOOGLE SHEET (DÙNG SECRETS) ---
def get_gspread_client():
    """
    Kết nối Google Sheet an toàn thông qua Streamlit Secrets.
    Không lộ file key trên GitHub.
    """
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Đọc thông tin từ Secrets của Streamlit Cloud
        # Yêu cầu phải cấu hình trong phần Settings của App trên web
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"⚠️ Lỗi cấu hình bảo mật: {str(e)}")
        st.stop()

def get_sheet():
    """Lấy về đối tượng sheet để thao tác"""
    client = get_gspread_client()
    # Tên file Google Sheet của bạn (Cần chính xác 100%)
    SHEET_NAME = "QuanLyGiatUi_HaiAu" 
    try:
        sheet = client.open(SHEET_NAME).sheet1
        return sheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"❌ Không tìm thấy file Google Sheet tên là '{SHEET_NAME}'. Vui lòng kiểm tra lại tên file và quyền chia sẻ.")
        st.stop()

# --- HÀM XỬ LÝ DỮ LIỆU ---
def load_data():
    """Tải dữ liệu về để làm báo cáo"""
    sheet = get_sheet()
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.warning("Chưa có dữ liệu hoặc lỗi đọc bảng.")
        return pd.DataFrame()

def save_invoice(data_row):
    """Gửi dữ liệu lên Google Sheet"""
    sheet = get_sheet()
    try:
        sheet.append_row(data_row)
        st.toast("✅ Đã lưu phiếu thành công!", icon="🎉")
        st.balloons()
    except Exception as e:
        st.error(f"❌ Lỗi khi lưu: {e}")

# --- GIAO DIỆN CHÍNH ---
st.title("🌊 CÔNG TY TNHH GIẶT ỦI HẢI ÂU MŨI NÉ")
st.markdown("*Hệ thống quản lý phiếu giao hàng sạch*")
st.markdown("---")

# Tạo Tabs cho gọn gàng
tab1, tab2 = st.tabs(["📝 NHẬP PHIẾU MỚI", "📊 BÁO CÁO THỐNG KÊ"])

# ================= TAB 1: NHẬP LIỆU =================
with tab1:
    with st.form("invoice_form", clear_on_submit=True):
        st.subheader("Thông tin phiếu")
        col1, col2, col3 = st.columns(3)
        with col1:
            input_date = st.date_input("Ngày lập phiếu", value=date.today())
        with col2:
            receipt_no = st.text_input("Số phiếu (VD: 000128)")
        with col3:
            customer = st.text_input("Tên khách hàng", value="Potique")
        
        col4, col5 = st.columns([2, 1])
        with col4:
            address = st.text_input("Địa chỉ", value="Nha Trang")
        
        st.markdown("---")
        st.subheader("Chi tiết hàng hóa")
        
        # Dictionary để lưu số lượng từng món
        item_quantities = {}
        
        # Dùng container và columns để tạo lưới nhập liệu đẹp mắt
        with st.container():
            # Chia lưới 3 cột cho các mặt hàng
            grid_cols = st.columns(3)
            for index, item in enumerate(ITEMS):
                with grid_cols[index % 3]:
                    # Key giúp streamlit phân biệt các ô input
                    qty = st.number_input(f"{index+1}. {item}", min_value=0, step=1, key=f"item_{index}")
                    item_quantities[item] = qty

        st.markdown("---")
        # Phần tổng kết
        f_col1, f_col2 = st.columns([1, 2])
        with f_col1:
            total_weight = st.number_input("⚖️ TỔNG TRỌNG LƯỢNG (KG)", min_value=0.0, format="%.1f")
        with f_col2:
            note = st.text_area("Ghi chú", placeholder="Ghi chú thêm về tình trạng hàng vải...")

        # Nút Submit
        submitted = st.form_submit_button("LƯU PHIẾU GIAO HÀNG", use_container_width=True, type="primary")

        if submitted:
            if not customer or not receipt_no:
                st.error("⚠️ Vui lòng nhập Số phiếu và Tên khách hàng!")
            else:
                # Chuẩn bị dữ liệu theo đúng thứ tự cột trong Excel
                # Cột: Ngày | Số phiếu | Khách hàng | Địa chỉ | Ghi chú | Tổng Kg | ...Các món...
                row_data = [
                    input_date.strftime("%Y-%m-%d"), # Định dạng ngày cho dễ đọc
                    receipt_no,
                    customer,
                    address,
                    note,
                    total_weight
                ]
                # Thêm số lượng từng món
                for item in ITEMS:
                    row_data.append(item_quantities[item])
                
                # Gọi hàm lưu
                with st.spinner("Đang gửi dữ liệu lên mây..."):
                    save_invoice(row_data)

# ================= TAB 2: BÁO CÁO =================
with tab2:
    st.subheader("Thống kê hoạt động")
    
    if st.button("🔄 Tải lại dữ liệu mới nhất"):
        st.cache_data.clear() # Xóa cache để lấy dữ liệu mới
    
    df = load_data()
    
    if not df.empty:
        # Xử lý cột Ngày
        if 'Ngày' in df.columns:
            df['Ngày'] = pd.to_datetime(df['Ngày'])
            
            # Bộ lọc
            c1, c2 = st.columns(2)
            with c1:
                start_date = st.date_input("Từ ngày", value=date.today().replace(day=1))
            with c2:
                end_date = st.date_input("Đến ngày", value=date.today())
            
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)
            
            # Lọc
            mask = (df['Ngày'] >= start_date) & (df['Ngày'] <= end_date)
            filtered_df = df.loc[mask]
            
            # Metrics
            total_kg = filtered_df['Tổng Kg'].sum() if 'Tổng Kg' in filtered_df.columns else 0
            total_phieu = len(filtered_df)
            
            m1, m2 = st.columns(2)
            m1.metric("Tổng Phiếu", f"{total_phieu} phiếu")
            m2.metric("Tổng Khối Lượng", f"{total_kg:,.1f} Kg")
            
            st.markdown("### Chi tiết dữ liệu")
            st.dataframe(filtered_df, use_container_width=True)
            
            # Download
            csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 Tải báo cáo Excel (CSV)",
                csv,
                f"bao_cao_{date.today()}.csv",
                "text/csv"
            )
        else:
            st.error("File Google Sheet thiếu cột 'Ngày'. Vui lòng kiểm tra lại file Excel.")
    else:
        st.info("Chưa có dữ liệu nào. Hãy nhập phiếu đầu tiên!")