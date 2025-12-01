import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import time

# --- CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="Hải Âu Mũi Né - Hệ Thống",
    page_icon="🌊",
    layout="wide"
)

# --- DANH SÁCH MẶT HÀNG ---
ITEMS = [
    "Áo gối", "Áo choàng", "Bọc lớn", "Bọc nhỏ", "Bảo vệ nệm",
    "Bọc mền", "Drap lớn", "Drap nhỏ", "Drap thun", "Khăn hồ bơi",
    "Khăn tắm lớn trắng", "Khăn tay", "Khăn mặt", "Khăn Welcome",
    "Khăn bàn", "Mền", "Thảm chân", "Tấm trang trí", "Rèm cửa",
    "Mùng", "Gối ghế"
]

# --- HÀM KẾT NỐI GOOGLE SHEET ---
def get_gspread_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"⚠️ Lỗi kết nối: {str(e)}")
        st.stop()

SHEET_NAME = "QuanLyGiatUi_HaiAu" 

def get_sheet(worksheet_name="Sheet1"):
    client = get_gspread_client()
    try:
        sheet = client.open(SHEET_NAME).worksheet(worksheet_name)
        return sheet
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ Không tìm thấy trang tính '{worksheet_name}'. Hãy tạo nó trong Google Sheet!")
        st.stop()

# --- HÀM DATA & AUTH ---
def load_users():
    sheet = get_sheet("Users")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def authenticate(username, password, df_users):
    # Chuyển đổi password trong df sang string để so sánh an toàn
    df_users['Password'] = df_users['Password'].astype(str)
    user = df_users[(df_users['Username'] == username) & (df_users['Password'] == str(password))]
    if not user.empty:
        return user.iloc[0]
    return None

def add_new_customer(username, password, fullname, address):
    sheet = get_sheet("Users")
    new_row = [username, password, "customer", fullname, address]
    sheet.append_row(new_row)

def save_invoice(data_row):
    sheet = get_sheet("Sheet1")
    sheet.append_row(data_row)

def load_invoices():
    sheet = get_sheet("Sheet1")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# --- GIAO DIỆN ĐĂNG NHẬP ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = None

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.title("🔐 Đăng Nhập")
        with st.form("login_form"):
            username = st.text_input("Tên đăng nhập")
            password = st.text_input("Mật khẩu", type="password")
            submit = st.form_submit_button("Đăng nhập")
            
            if submit:
                df_users = load_users()
                user = authenticate(username, password, df_users)
                if user is not None:
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    st.success("Đăng nhập thành công!")
                    st.rerun()
                else:
                    st.error("Sai thông tin đăng nhập")
    st.stop()

# --- GIAO DIỆN CHÍNH ---
user = st.session_state.user_info
role = user['Role']
full_name = user['FullName']

with st.sidebar:
    st.write(f"👤 **{full_name}** ({role})")
    if st.button("Đăng xuất"):
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.rerun()

st.title("🌊 CÔNG TY GIẶT ỦI HẢI ÂU")

# === 1. ADMIN PANEL ===
if role == 'admin':
    tab1, tab2, tab3 = st.tabs(["📊 Báo Cáo", "👥 Quản Lý Khách", "📝 Nhập Phiếu"])
    
    with tab1:
        st.subheader("Doanh thu")
        df = load_invoices()
        if not df.empty:
            df['Ngày'] = pd.to_datetime(df['Ngày'])
            st.dataframe(df, use_container_width=True)
            total_kg = df['Tổng Kg'].sum() if 'Tổng Kg' in df.columns else 0
            st.metric("Tổng sản lượng", f"{total_kg:,.1f} Kg")
    
    with tab2:
        st.subheader("Thêm khách hàng")
        with st.form("add_user"):
            c1, c2 = st.columns(2)
            u = c1.text_input("Username")
            p = c2.text_input("Password")
            fn = st.text_input("Tên hiển thị")
            ad = st.text_input("Địa chỉ")
            if st.form_submit_button("Tạo tài khoản"):
                if u and fn:
                    add_new_customer(u, p, fn, ad)
                    st.success(f"Đã thêm {fn}")

# === 2. NHẬP LIỆU (STAFF + ADMIN) ===
if role in ['staff', 'admin']:
    container = st.container() if role == 'staff' else tab3

    with container:
        df_users = load_users()
        customers_list = df_users[df_users['Role'] == 'customer']
        
        # --- Form Thông tin chung ---
        with st.form("invoice_header"):
            st.subheader("1. Thông tin phiếu")
            c1, c2, c3 = st.columns([1, 1, 2])
            input_date = c1.date_input("Ngày", value=date.today())
            receipt_no = c2.text_input("Số phiếu")
            
            selected_customer = c3.selectbox("Khách hàng", customers_list['FullName'].tolist())
            
            # Auto-fill địa chỉ (chỉ để hiển thị, xử lý logic sau)
            current_addr = ""
            if selected_customer:
                match = customers_list[customers_list['FullName'] == selected_customer]
                if not match.empty:
                    current_addr = match.iloc[0]['Address']
            
            address = st.text_input("Địa chỉ", value=current_addr)
            note = st.text_area("Ghi chú", height=68)

            # --- NÂNG CẤP: BẢNG NHẬP LIỆU (Excel Style) ---
            st.subheader("2. Chi tiết hàng hóa (Nhập số lượng)")
            st.info("💡 Mẹo: Nhấn vào ô số lượng, nhập số rồi bấm **Enter** hoặc **Tab** để xuống dòng nhanh.")

            # Tạo DataFrame mẫu cho bảng nhập liệu
            # Cột "Mặt hàng" bị khóa không cho sửa, cột "Số lượng" cho phép nhập số
            input_df = pd.DataFrame({
                "Tên mặt hàng": ITEMS,
                "Số lượng": [0] * len(ITEMS)
            })

            # Hiển thị bảng Data Editor
            edited_df = st.data_editor(
                input_df,
                column_config={
                    "Số lượng": st.column_config.NumberColumn(
                        "Số lượng",
                        min_value=0,
                        step=1,
                        required=True,
                        default=0
                    ),
                    "Tên mặt hàng": st.column_config.TextColumn(
                        "Tên mặt hàng",
                        disabled=True  # Khóa cột tên để không bị sửa nhầm
                    )
                },
                hide_index=True,
                use_container_width=True,
                height=500 # Chiều cao vừa đủ để hiện hết các món
            )

            # Tổng trọng lượng (để ở cuối)
            st.markdown("---")
            c_last1, c_last2 = st.columns([1, 3])
            total_weight = c_last1.number_input("⚖️ TỔNG KG", min_value=0.0, format="%.1f")
            
            # Nút Lưu nằm trong Form để gom tất cả dữ liệu
            submit_btn = st.form_submit_button("💾 LƯU PHIẾU NGAY", type="primary", use_container_width=True)

            if submit_btn:
                if not receipt_no:
                    st.error("Thiếu số phiếu!")
                else:
                    # Chuyển đổi dữ liệu từ bảng edited_df thành list để lưu
                    # Tạo dictionary {Tên món: Số lượng} để map cho chính xác
                    qty_map = dict(zip(edited_df["Tên mặt hàng"], edited_df["Số lượng"]))
                    
                    row_data = [
                        input_date.strftime("%Y-%m-%d"),
                        receipt_no,
                        selected_customer,
                        address,
                        note,
                        total_weight
                    ]
                    # Duyệt qua list ITEMS gốc để đảm bảo đúng thứ tự cột trong Google Sheet
                    for item in ITEMS:
                        row_data.append(qty_map.get(item, 0))
                    
                    save_invoice(row_data)
                    st.success(f"✅ Đã lưu phiếu {receipt_no} cho {selected_customer}!")
                    time.sleep(1)
                    st.rerun()

# === 3. KHÁCH HÀNG XEM ===
if role == 'customer':
    st.subheader(f"Lịch sử: {full_name}")
    df = load_invoices()
    if not df.empty:
        my_inv = df[df['Khách hàng'] == full_name]
        if not my_inv.empty:
            st.dataframe(my_inv, use_container_width=True)
            st.info(f"Tổng tích lũy: {my_inv['Tổng Kg'].sum():,.1f} Kg")
        else:
            st.warning("Chưa có đơn hàng.")
