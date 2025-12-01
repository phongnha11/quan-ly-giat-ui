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

def update_invoice(old_receipt_no, data_row):
    """Tìm phiếu theo số phiếu cũ và cập nhật toàn bộ dòng"""
    sheet = get_sheet("Sheet1")
    try:
        # Tìm ô chứa số phiếu (Giả sử số phiếu là duy nhất)
        # Tìm chính xác số phiếu cũ để biết nó nằm ở dòng nào
        cell = sheet.find(str(old_receipt_no))
        if cell:
            # Cập nhật từ cột A của dòng tìm thấy
            # sheet.update dùng range A{row} để ghi đè dòng đó
            sheet.update(range_name=f"A{cell.row}", values=[data_row])
            return True
        else:
            return False
    except Exception as e:
        st.error(f"Lỗi khi cập nhật: {e}")
        return False

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
    tab1, tab2, tab3 = st.tabs(["📊 Báo Cáo", "👥 Quản Lý Khách", "📝 Nhập/Sửa Phiếu"])
    
    with tab1:
        st.subheader("Doanh thu")
        df = load_invoices()
        if not df.empty:
            df['Ngày'] = pd.to_datetime(df['Ngày'])
            # Sắp xếp theo ngày giảm dần để dễ xem
            df = df.sort_values(by='Ngày', ascending=False)
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
        # --- CHỌN CHẾ ĐỘ: NHẬP MỚI HAY SỬA ---
        mode = st.radio("Thao tác:", ["✨ Tạo phiếu mới", "🛠 Sửa phiếu cũ"], horizontal=True)
        
        # Biến để lưu dữ liệu form (mặc định là rỗng/ngày hiện tại)
        default_date = date.today()
        default_receipt = ""
        default_customer_idx = 0
        default_address = ""
        default_note = ""
        default_total_kg = 0.0
        default_items_qty = [0] * len(ITEMS)
        
        # Biến này dùng để xác định dòng cần sửa trong Google Sheet
        target_receipt_to_update = None 

        df_users = load_users()
        customers_list = df_users[df_users['Role'] == 'customer']
        customer_names = customers_list['FullName'].tolist()

        # LOGIC LOAD DỮ LIỆU CŨ KHI CHỌN "SỬA PHIẾU"
        if mode == "🛠 Sửa phiếu cũ":
            st.info("ℹ️ Chọn phiếu cần sửa từ danh sách bên dưới.")
            all_invoices = load_invoices()
            if not all_invoices.empty:
                # Tạo danh sách hiển thị dễ đọc: Ngày - Số phiếu - Khách
                all_invoices['Display'] = all_invoices['Ngày'].astype(str) + " - Số: " + all_invoices['Số phiếu'].astype(str) + " - " + all_invoices['Khách hàng']
                # Đảo ngược để phiếu mới nhất lên đầu
                invoice_options = all_invoices['Display'].tolist()[::-1]
                
                selected_invoice_str = st.selectbox("Tìm phiếu:", invoice_options)
                
                if selected_invoice_str:
                    # Lấy dữ liệu dòng tương ứng
                    row_data = all_invoices[all_invoices['Display'] == selected_invoice_str].iloc[0]
                    
                    # Cập nhật các biến mặc định
                    target_receipt_to_update = str(row_data['Số phiếu']) # Lưu số phiếu gốc để tìm trong sheet
                    
                    # Convert ngày từ string về date object
                    try:
                        default_date = datetime.strptime(str(row_data['Ngày']), "%Y-%m-%d").date()
                    except:
                        default_date = date.today()
                        
                    default_receipt = str(row_data['Số phiếu'])
                    
                    # Tìm index của khách hàng trong list để set default cho selectbox
                    if row_data['Khách hàng'] in customer_names:
                        default_customer_idx = customer_names.index(row_data['Khách hàng'])
                    
                    default_address = row_data['Địa chỉ']
                    default_note = row_data['Ghi chú']
                    default_total_kg = float(row_data['Tổng Kg']) if row_data['Tổng Kg'] else 0.0
                    
                    # Lấy số lượng từng món (Mapping lại từ tên cột)
                    # Cột trong Excel: ... | Tổng Kg | Áo gối | Áo choàng ...
                    # ITEMS list thứ tự phải khớp với Excel
                    loaded_qtys = []
                    for item in ITEMS:
                        if item in row_data:
                            try:
                                loaded_qtys.append(int(row_data[item]))
                            except:
                                loaded_qtys.append(0)
                        else:
                            loaded_qtys.append(0)
                    default_items_qty = loaded_qtys
            else:
                st.warning("Chưa có phiếu nào để sửa.")

        # --- FORM NHẬP LIỆU (DÙNG CHUNG CHO CẢ 2 CHẾ ĐỘ) ---
        # Dùng key khác nhau cho mỗi mode để reset form khi đổi chế độ
        form_key = "new_form" if mode == "✨ Tạo phiếu mới" else "edit_form"
        
        with st.form(form_key):
            st.subheader("1. Thông tin phiếu")
            c1, c2, c3 = st.columns([1, 1, 2])
            
            input_date = c1.date_input("Ngày", value=default_date)
            # Nếu sửa phiếu, ta cho phép sửa số phiếu nhưng cần cảnh báo
            receipt_no = c2.text_input("Số phiếu", value=default_receipt)
            
            selected_customer = c3.selectbox(
                "Khách hàng", 
                customer_names, 
                index=default_customer_idx
            )
            
            # Logic địa chỉ: Nếu đang nhập mới thì auto-fill, nếu sửa thì giữ nguyên cái đã load
            if mode == "✨ Tạo phiếu mới":
                current_addr = ""
                if selected_customer:
                    match = customers_list[customers_list['FullName'] == selected_customer]
                    if not match.empty:
                        current_addr = match.iloc[0]['Address']
            else:
                current_addr = default_address

            address = st.text_input("Địa chỉ", value=current_addr)
            note = st.text_area("Ghi chú", value=default_note, height=68)

            st.subheader("2. Chi tiết hàng hóa")
            # Tạo DataFrame cho bảng nhập liệu
            input_df = pd.DataFrame({
                "Tên mặt hàng": ITEMS,
                "Số lượng": default_items_qty
            })

            edited_df = st.data_editor(
                input_df,
                column_config={
                    "Số lượng": st.column_config.NumberColumn(
                        "Số lượng", min_value=0, step=1, required=True
                    ),
                    "Tên mặt hàng": st.column_config.TextColumn(
                        "Tên mặt hàng", disabled=True
                    )
                },
                hide_index=True,
                use_container_width=True,
                height=500,
                key=f"editor_{form_key}" # Key quan trọng để reset bảng
            )

            st.markdown("---")
            c_last1, c_last2 = st.columns([1, 3])
            total_weight = c_last1.number_input("⚖️ TỔNG KG", min_value=0.0, format="%.1f", value=default_total_kg)
            
            # Nút Submit đổi tên tùy chế độ
            btn_label = "💾 LƯU PHIẾU MỚI" if mode == "✨ Tạo phiếu mới" else "💾 CẬP NHẬT THAY ĐỔI"
            submit_btn = st.form_submit_button(btn_label, type="primary", use_container_width=True)

            if submit_btn:
                if not receipt_no:
                    st.error("Thiếu số phiếu!")
                else:
                    # Chuẩn bị dữ liệu
                    qty_map = dict(zip(edited_df["Tên mặt hàng"], edited_df["Số lượng"]))
                    
                    row_data = [
                        input_date.strftime("%Y-%m-%d"),
                        receipt_no,
                        selected_customer,
                        address,
                        note,
                        total_weight
                    ]
                    for item in ITEMS:
                        row_data.append(qty_map.get(item, 0))
                    
                    if mode == "✨ Tạo phiếu mới":
                        save_invoice(row_data)
                        st.success(f"✅ Đã tạo mới phiếu {receipt_no}!")
                    else:
                        # Logic cập nhật
                        if target_receipt_to_update:
                            success = update_invoice(target_receipt_to_update, row_data)
                            if success:
                                st.success(f"✅ Đã cập nhật phiếu {receipt_no} thành công!")
                        else:
                            st.error("Lỗi: Không xác định được phiếu gốc để sửa.")
                    
                    time.sleep(1)
                    st.rerun()

# === 3. KHÁCH HÀNG XEM ===
if role == 'customer':
    st.subheader(f"Lịch sử: {full_name}")
    df = load_invoices()
    if not df.empty:
        my_inv = df[df['Khách hàng'] == full_name]
        # Sắp xếp phiếu mới nhất lên đầu
        my_inv = my_inv.sort_values(by='Ngày', ascending=False)
        if not my_inv.empty:
            st.dataframe(my_inv, use_container_width=True)
            st.info(f"Tổng tích lũy: {my_inv['Tổng Kg'].sum():,.1f} Kg")
        else:
            st.warning("Chưa có đơn hàng.")
