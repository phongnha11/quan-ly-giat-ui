import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import time
import io
import openpyxl

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

SHEET_NAME = "QuanLyGiatUi_HaiAu" 

# --- HÀM KẾT NỐI GOOGLE SHEET ---
# Sử dụng cache_resource cho kết nối API để không phải kết nối lại liên tục
@st.cache_resource
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

def get_sheet(worksheet_name="Sheet1"):
    client = get_gspread_client()
    try:
        sheet = client.open(SHEET_NAME).worksheet(worksheet_name)
        return sheet
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ Không tìm thấy trang tính '{worksheet_name}'. Hãy tạo nó trong Google Sheet!")
        st.stop()

# --- HÀM DATA & AUTH (CÓ CACHE) ---
# Thêm TTL=60s: Dữ liệu tự làm mới sau 60s, nhưng ta sẽ ép làm mới ngay khi có thay đổi
@st.cache_data(ttl=60)
def load_users():
    sheet = get_sheet("Users")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

@st.cache_data(ttl=60)
def load_invoices():
    sheet = get_sheet("Sheet1")
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
    st.cache_data.clear() # Xóa cache ngay sau khi thêm

def save_invoice(data_row):
    sheet = get_sheet("Sheet1")
    sheet.append_row(data_row)
    st.cache_data.clear() # QUAN TRỌNG: Xóa cache để app tải dữ liệu mới ngay lập tức

def update_invoice(old_receipt_no, data_row):
    """Tìm phiếu theo số phiếu cũ và cập nhật toàn bộ dòng"""
    sheet = get_sheet("Sheet1")
    try:
        # Tìm ô chứa số phiếu (Giả sử số phiếu là duy nhất)
        cell = sheet.find(str(old_receipt_no))
        if cell:
            # Cập nhật dòng đó
            # Chú ý: gspread update dùng index bắt đầu từ 1
            # data_row là list giá trị. Cần update cả hàng.
            # Range ví dụ: A2:Z2
            end_col_char = chr(ord('A') + len(data_row) - 1) # Tính toán chữ cái cột cuối (chỉ đúng nếu < 26 cột, nhưng tạm ổn)
            # Cách an toàn hơn với gspread:
            sheet.update(range_name=f"A{cell.row}", values=[data_row])
            st.cache_data.clear() # QUAN TRỌNG: Xóa cache sau khi sửa
            return True
        else:
            return False
    except Exception as e:
        st.error(f"Lỗi khi cập nhật: {e}")
        return False

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
                # Load users trực tiếp không qua cache để đảm bảo đúng nhất lúc login
                st.cache_data.clear() 
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
    tab1, tab2, tab3 = st.tabs(["📊 Báo Cáo & Xuất File", "👥 Quản Lý Khách", "📝 Nhập/Sửa Phiếu"])
    
    with tab1:
        st.subheader("Thống kê doanh thu")
        if st.button("🔄 Làm mới dữ liệu"):
            st.cache_data.clear()
            st.rerun()

        df = load_invoices()
        
        if not df.empty:
            df['Ngày'] = pd.to_datetime(df['Ngày'])
            
            # --- BỘ LỌC THỜI GIAN ---
            st.write("📅 **Chọn thời gian báo cáo:**")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                start_date = st.date_input("Từ ngày", value=date.today().replace(day=1))
            with col_d2:
                end_date = st.date_input("Đến ngày", value=date.today())
            
            mask = (df['Ngày'].dt.date >= start_date) & (df['Ngày'].dt.date <= end_date)
            filtered_df = df.loc[mask]
            
            if not filtered_df.empty:
                filtered_df = filtered_df.sort_values(by='Ngày', ascending=False)
                
                total_kg = filtered_df['Tổng Kg'].sum() if 'Tổng Kg' in filtered_df.columns else 0
                count_phieu = len(filtered_df)
                
                m1, m2 = st.columns(2)
                m1.metric("Số lượng phiếu", f"{count_phieu} phiếu")
                m2.metric("Tổng trọng lượng", f"{total_kg:,.1f} Kg")
                
                st.dataframe(filtered_df, use_container_width=True)
                
                st.markdown("---")
                # Xuất Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    filtered_df.to_excel(writer, index=False, sheet_name='BaoCao')
                    
                file_name_excel = f"BaoCao_{start_date.strftime('%d-%m')}_den_{end_date.strftime('%d-%m')}.xlsx"
                st.download_button(
                    label="📥 Tải file Excel (.xlsx)",
                    data=buffer.getvalue(),
                    file_name=file_name_excel,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
            else:
                st.warning(f"Không tìm thấy phiếu nào từ ngày {start_date} đến {end_date}.")
        else:
            st.info("Chưa có dữ liệu trong hệ thống.")
    
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
                    time.sleep(1)
                    st.rerun()

# === 2. NHẬP LIỆU (STAFF + ADMIN) ===
if role in ['staff', 'admin']:
    container = st.container() if role == 'staff' else tab3

    with container:
        mode = st.radio("Thao tác:", ["✨ Tạo phiếu mới", "🛠 Sửa phiếu cũ"], horizontal=True)
        
        default_date = date.today()
        default_receipt = ""
        default_customer_idx = 0
        default_address = ""
        default_note = ""
        default_total_kg = 0.0
        default_items_qty = [0] * len(ITEMS)
        target_receipt_to_update = None 
        
        # Biến này dùng để tạo key động cho data_editor giúp refresh dữ liệu
        editor_key_suffix = "new"

        df_users = load_users()
        customers_list = df_users[df_users['Role'] == 'customer']
        customer_names = customers_list['FullName'].tolist()

        if mode == "🛠 Sửa phiếu cũ":
            st.info("ℹ️ Chọn phiếu cần sửa từ danh sách bên dưới.")
            all_invoices = load_invoices()
            
            if not all_invoices.empty:
                all_invoices['Display'] = all_invoices['Ngày'].astype(str) + " - Số: " + all_invoices['Số phiếu'].astype(str) + " - " + all_invoices['Khách hàng']
                invoice_options = all_invoices['Display'].tolist()[::-1]
                
                selected_invoice_str = st.selectbox("Tìm phiếu:", invoice_options)
                
                if selected_invoice_str:
                    # Gán suffix để data_editor hiểu là dữ liệu đã đổi
                    editor_key_suffix = str(hash(selected_invoice_str))

                    row_data = all_invoices[all_invoices['Display'] == selected_invoice_str].iloc[0]
                    target_receipt_to_update = str(row_data['Số phiếu'])
                    
                    try:
                        default_date = datetime.strptime(str(row_data['Ngày']), "%Y-%m-%d").date()
                    except:
                        default_date = date.today()
                        
                    default_receipt = str(row_data['Số phiếu'])
                    
                    if row_data['Khách hàng'] in customer_names:
                        default_customer_idx = customer_names.index(row_data['Khách hàng'])
                    
                    default_address = row_data['Địa chỉ']
                    default_note = row_data['Ghi chú']
                    default_total_kg = float(row_data['Tổng Kg']) if row_data['Tổng Kg'] else 0.0
                    
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

        form_key = "new_form" if mode == "✨ Tạo phiếu mới" else "edit_form"
        
        with st.form(form_key):
            st.subheader("1. Thông tin phiếu")
            c1, c2, c3 = st.columns([1, 1, 2])
            
            input_date = c1.date_input("Ngày", value=default_date)
            receipt_no = c2.text_input("Số phiếu", value=default_receipt)
            
            selected_customer = c3.selectbox(
                "Khách hàng", 
                customer_names, 
                index=default_customer_idx
            )
            
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
            input_df = pd.DataFrame({
                "Tên mặt hàng": ITEMS,
                "Số lượng": default_items_qty
            })

            # Sử dụng editor_key_suffix để ép bảng làm mới khi chọn phiếu khác
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
                key=f"editor_{mode}_{editor_key_suffix}" 
            )

            st.markdown("---")
            c_last1, c_last2 = st.columns([1, 3])
            total_weight = c_last1.number_input("⚖️ TỔNG KG", min_value=0.0, format="%.1f", value=default_total_kg)
            
            btn_label = "💾 LƯU PHIẾU MỚI" if mode == "✨ Tạo phiếu mới" else "💾 CẬP NHẬT THAY ĐỔI"
            submit_btn = st.form_submit_button(btn_label, type="primary", use_container_width=True)

            if submit_btn:
                if not receipt_no:
                    st.error("Thiếu số phiếu!")
                else:
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
                        if target_receipt_to_update:
                            success = update_invoice(target_receipt_to_update, row_data)
                            if success:
                                st.success(f"✅ Đã cập nhật phiếu {receipt_no} thành công!")
                        else:
                            st.error("Lỗi: Không xác định được phiếu gốc để sửa.")
                    
                    time.sleep(0.5)
                    st.rerun()

# === 3. KHÁCH HÀNG XEM ===
if role == 'customer':
    st.subheader(f"Lịch sử: {full_name}")
    if st.button("🔄 Làm mới"):
        st.cache_data.clear()
        st.rerun()
        
    df = load_invoices()
    if not df.empty:
        my_inv = df[df['Khách hàng'] == full_name]
        my_inv = my_inv.sort_values(by='Ngày', ascending=False)
        if not my_inv.empty:
            st.dataframe(my_inv, use_container_width=True)
            st.info(f"Tổng tích lũy: {my_inv['Tổng Kg'].sum():,.1f} Kg")
        else:
            st.warning("Chưa có đơn hàng.")
