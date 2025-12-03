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
    page_title="Hải Âu Mũi Né - Hệ Thống Quản Lý",
    page_icon="🌊",
    layout="wide"
)

# --- CSS TÙY CHỈNH CHO HÓA ĐƠN ---
# Tạo giao diện in ấn giống mẫu thật
st.markdown("""
<style>
    @media print {
        body * {
            visibility: hidden;
        }
        .printable-area, .printable-area * {
            visibility: visible;
        }
        .printable-area {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
        }
    }
    .invoice-box {
        max-width: 800px;
        margin: auto;
        padding: 30px;
        border: 1px solid #eee;
        box-shadow: 0 0 10px rgba(0, 0, 0, .15);
        font-size: 16px;
        line-height: 24px;
        font-family: 'Times New Roman', serif;
        color: #555;
        background-color: white;
    }
    .invoice-header {
        text-align: center;
        color: #003366;
        margin-bottom: 20px;
    }
    .invoice-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 20px;
    }
    .invoice-table th, .invoice-table td {
        border: 1px solid #333;
        padding: 8px;
        text-align: left;
    }
    .invoice-table th {
        background-color: #f2f2f2;
        text-align: center;
    }
    .total-section {
        margin-top: 20px;
        text-align: right;
        font-weight: bold;
        font-size: 18px;
    }
    .signature-section {
        display: flex;
        justify-content: space-between;
        margin-top: 40px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- DANH SÁCH MẶT HÀNG ---
ITEMS = [
    "Áo gối", "Áo choàng", "Bọc lớn", "Bọc nhỏ", "Bảo vệ nệm",
    "Bọc mền", "Drap lớn", "Drap nhỏ", "Drap thun", "Khăn hồ bơi",
    "Khăn tắm lớn trắng", "Khăn tay", "Khăn mặt", "Khăn Welcome",
    "Khăn bàn", "Mền", "Thảm chân", "Tấm trang trí", "Rèm cửa",
    "Mùng", "Gối ghế"
]

SHEET_NAME = "QuanLyGiatUi_HaiAu" 

# --- HÀM KẾT NỐI ---
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
        st.error(f"❌ Không tìm thấy trang tính '{worksheet_name}'.")
        st.stop()

# --- HÀM DỮ LIỆU ---
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

# --- HÀM NGHIỆP VỤ ---
def authenticate(username, password, df_users):
    df_users['Password'] = df_users['Password'].astype(str)
    user = df_users[(df_users['Username'] == username) & (df_users['Password'] == str(password))]
    if not user.empty:
        return user.iloc[0]
    return None

# --- QUẢN LÝ USER MỚI (UPDATE) ---
def add_new_user(username, password, role, fullname, address):
    sheet = get_sheet("Users")
    new_row = [username, password, role, fullname, address]
    sheet.append_row(new_row)
    st.cache_data.clear()

def update_user_info(username, new_data_row):
    """Cập nhật thông tin user"""
    sheet = get_sheet("Users")
    try:
        cell = sheet.find(username)
        if cell:
            sheet.update(range_name=f"A{cell.row}", values=[new_data_row])
            st.cache_data.clear()
            return True
        return False
    except:
        return False

def delete_user_by_username(username):
    """Xóa user"""
    sheet = get_sheet("Users")
    try:
        cell = sheet.find(username)
        if cell:
            sheet.delete_rows(cell.row)
            st.cache_data.clear()
            return True
        return False
    except:
        return False

# --- QUẢN LÝ PHIẾU ---
def save_invoice(data_row):
    sheet = get_sheet("Sheet1")
    sheet.append_row(data_row)
    st.cache_data.clear()

def update_invoice(old_receipt_no, data_row):
    sheet = get_sheet("Sheet1")
    try:
        cell = sheet.find(str(old_receipt_no))
        if cell:
            sheet.update(range_name=f"A{cell.row}", values=[data_row])
            st.cache_data.clear()
            return True
        return False
    except Exception as e:
        st.error(f"Lỗi: {e}")
        return False

def delete_invoice(receipt_no):
    """Xóa phiếu giao hàng"""
    sheet = get_sheet("Sheet1")
    try:
        cell = sheet.find(str(receipt_no))
        if cell:
            sheet.delete_rows(cell.row)
            st.cache_data.clear()
            return True
        return False
    except Exception as e:
        st.error(f"Lỗi khi xóa: {e}")
        return False

# --- VIEW HÓA ĐƠN HTML ---
def render_invoice_html(data):
    """Tạo mã HTML hiển thị phiếu giống hệt ảnh"""
    items_html = ""
    stt = 1
    # data là Series pandas của dòng phiếu được chọn
    for item in ITEMS:
        qty = data.get(item, 0)
        try:
            qty_val = int(qty)
        except:
            qty_val = 0
            
        if qty_val > 0:
            items_html += f"""
            <tr>
                <td style="text-align:center">{stt}</td>
                <td>{item}</td>
                <td style="text-align:center">{qty_val}</td>
                <td></td>
                <td></td>
            </tr>
            """
            stt += 1
    
    # Lấp đầy bảng cho đủ dòng (giống mẫu giấy thường có nhiều dòng trống)
    while stt <= 10:
         items_html += f"""<tr><td style="text-align:center">{stt}</td><td></td><td></td><td></td><td></td></tr>"""
         stt += 1

    date_obj = pd.to_datetime(data['Ngày'])
    day, month, year = date_obj.day, date_obj.month, date_obj.year

    html_content = f"""
    <div class="printable-area invoice-box">
        <div style="display:flex; align-items:center;">
            <div style="flex:1;">
                <img src="https://cdn-icons-png.flaticon.com/512/2983/2983720.png" width="60" style="float:left; margin-right:10px;">
                <b style="color:#003366">CÔNG TY TNHH GIẶT ỦI HẢI ÂU MŨI NÉ</b><br>
                <small>Thôn Thiện Sơn, Phường Mũi Né, Tỉnh Lâm Đồng</small><br>
                <small>Hotline: 037 808 2088 / 0908 848 393</small>
            </div>
        </div>
        <hr>
        <div class="invoice-header">
            <h2>PHIẾU GIAO HÀNG SẠCH</h2>
            <span>Số: <b style="color:red; font-size:1.2em">{data['Số phiếu']}</b></span>
        </div>
        
        <table style="width:100%; margin-bottom:10px;">
            <tr>
                <td><b>Tên khách hàng:</b> {data['Khách hàng']}</td>
                <td style="text-align:right"><b>Loại hàng:</b> Hàng Sạch</td>
            </tr>
            <tr>
                <td colspan="2"><b>Địa chỉ:</b> {data['Địa chỉ']}</td>
            </tr>
        </table>

        <table class="invoice-table">
            <thead>
                <tr>
                    <th style="width:50px">STT</th>
                    <th>Tên mặt hàng</th>
                    <th style="width:100px">Số lượng</th>
                    <th style="width:150px">Tình trạng</th>
                    <th>Ghi chú</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>

        <div class="total-section">
            Tổng Cộng (Kg): {data['Tổng Kg']} Kg
        </div>
        
        <div style="margin-top:10px;">
            <i>Ghi chú chung: {data['Ghi chú']}</i>
        </div>

        <div style="text-align:right; margin-top:20px;">
            <i>Ngày {day} tháng {month} năm {year}</i>
        </div>

        <div class="signature-section">
            <div>
                <b>Người nhận hàng</b><br>
                <i>(Ký, họ tên)</i>
                <br><br><br><br>
            </div>
            <div>
                <b>Người giao hàng</b><br>
                <i>(Ký, họ tên)</i>
                <br><br><br><br>
            </div>
            <div>
                <b>Người lập phiếu</b><br>
                <i>(Ký, họ tên)</i>
                <br><br><br><br>
                Văn Thành
            </div>
        </div>
    </div>
    """
    return html_content

# --- GIAO DIỆN LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = None

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.title("🔐 Đăng Nhập")
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Vào hệ thống"):
                st.cache_data.clear()
                users = load_users()
                user = authenticate(u, p, users)
                if user is not None:
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    st.success("OK!")
                    st.rerun()
                else:
                    st.error("Sai thông tin")
    st.stop()

# --- MAIN APP ---
user = st.session_state.user_info
role = user['Role']
full_name = user['FullName']

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3003/3003984.png", width=80)
    st.markdown(f"**Xin chào, {full_name}**")
    st.caption(f"Vai trò: {role.upper()}")
    if st.button("Đăng xuất"):
        st.session_state.logged_in = False
        st.rerun()

st.title("HỆ THỐNG QUẢN LÝ GIẶT ỦI")

# === ADMIN: QUẢN LÝ KHÁCH & NHÂN VIÊN ===
if role == 'admin':
    tab1, tab2, tab3 = st.tabs(["📊 Báo cáo & In", "📝 Nhập/Sửa/Xóa Phiếu", "👥 Quản trị Người dùng"])
    
    # --- TAB QUẢN TRỊ USER ---
    with tab3:
        st.subheader("Quản lý tài khoản (Nhân viên & Khách)")
        
        col_user1, col_user2 = st.columns(2)
        
        # 1. Thêm mới
        with col_user1:
            with st.form("add_user_form"):
                st.markdown("#### ✨ Thêm người dùng mới")
                new_u = st.text_input("Tên đăng nhập (Username)")
                new_p = st.text_input("Mật khẩu", type="password")
                new_role = st.selectbox("Vai trò", ["customer", "staff", "admin"], help="Customer: Chỉ xem lịch sử | Staff: Nhập liệu | Admin: Toàn quyền")
                new_fn = st.text_input("Tên hiển thị (Tên Khách/NV)")
                new_ad = st.text_input("Địa chỉ (Cho khách hàng)")
                
                if st.form_submit_button("Tạo tài khoản"):
                    if new_u and new_fn:
                        add_new_user(new_u, new_p, new_role, new_fn, new_ad)
                        st.success(f"Đã tạo user {new_u}!")
                        time.sleep(1)
                        st.rerun()

        # 2. Sửa/Xóa User
        with col_user2:
            st.markdown("#### 🛠 Sửa / Xóa người dùng")
            df_users = load_users()
            user_list = df_users['Username'].tolist()
            selected_u = st.selectbox("Chọn tài khoản cần sửa:", user_list)
            
            if selected_u:
                # Lấy info cũ
                curr_info = df_users[df_users['Username'] == selected_u].iloc[0]
                
                with st.form("edit_user_form"):
                    e_pass = st.text_input("Mật khẩu mới (Để trống nếu không đổi)", type="password")
                    e_role = st.selectbox("Vai trò", ["customer", "staff", "admin"], index=["customer", "staff", "admin"].index(curr_info['Role']))
                    e_fn = st.text_input("Tên hiển thị", value=curr_info['FullName'])
                    e_ad = st.text_input("Địa chỉ", value=curr_info['Address'])
                    
                    c_btn1, c_btn2 = st.columns(2)
                    save_changes = c_btn1.form_submit_button("Lưu thay đổi")
                    delete_user = c_btn2.form_submit_button("🗑 XÓA USER NÀY", type="primary")
                    
                    if save_changes:
                        final_pass = e_pass if e_pass else curr_info['Password']
                        update_user_info(selected_u, [selected_u, final_pass, e_role, e_fn, e_ad])
                        st.success("Cập nhật thành công!")
                        time.sleep(1)
                        st.rerun()
                        
                    if delete_user:
                        if selected_u == user['Username']:
                            st.error("Không thể tự xóa chính mình!")
                        else:
                            delete_user_by_username(selected_u)
                            st.warning(f"Đã xóa {selected_u}")
                            time.sleep(1)
                            st.rerun()
        
        st.markdown("---")
        st.dataframe(df_users, use_container_width=True)

# === STAFF/ADMIN: NHẬP LIỆU ===
if role in ['staff', 'admin']:
    # Xác định vị trí hiển thị: Nếu là admin thì tab 2, staff thì trang chính
    container = tab2 if role == 'admin' else st.container()

    with container:
        mode = st.radio("Chế độ:", ["✨ Nhập phiếu mới", "🛠 Sửa / Xóa phiếu cũ"], horizontal=True)
        
        # Biến khởi tạo
        default_date = date.today()
        default_receipt = ""
        default_customer_idx = 0
        default_address = ""
        default_note = ""
        default_total_kg = 0.0
        default_items_qty = [0] * len(ITEMS)
        target_receipt_to_update = None
        editor_key_suffix = "new"

        df_users = load_users()
        customers_list = df_users[df_users['Role'] == 'customer']
        customer_names = customers_list['FullName'].tolist()

        if mode == "🛠 Sửa / Xóa phiếu cũ":
            col_search, col_act = st.columns([3, 1])
            all_invoices = load_invoices()
            
            if not all_invoices.empty:
                all_invoices['Display'] = all_invoices['Ngày'].astype(str) + " - Số: " + all_invoices['Số phiếu'].astype(str) + " - " + all_invoices['Khách hàng']
                invoice_options = all_invoices['Display'].tolist()[::-1]
                
                selected_invoice_str = col_search.selectbox("Tìm phiếu cần xử lý:", invoice_options)
                
                if selected_invoice_str:
                    editor_key_suffix = str(hash(selected_invoice_str))
                    row_data = all_invoices[all_invoices['Display'] == selected_invoice_str].iloc[0]
                    target_receipt_to_update = str(row_data['Số phiếu'])
                    
                    # Fill dữ liệu cũ vào form
                    try:
                        default_date = datetime.strptime(str(row_data['Ngày']), "%Y-%m-%d").date()
                    except: default_date = date.today()
                    
                    default_receipt = str(row_data['Số phiếu'])
                    if row_data['Khách hàng'] in customer_names:
                        default_customer_idx = customer_names.index(row_data['Khách hàng'])
                    default_address = row_data['Địa chỉ']
                    default_note = row_data['Ghi chú']
                    default_total_kg = float(row_data['Tổng Kg']) if row_data['Tổng Kg'] else 0.0
                    
                    loaded_qtys = []
                    for item in ITEMS:
                        val = row_data.get(item, 0)
                        try: loaded_qtys.append(int(val))
                        except: loaded_qtys.append(0)
                    default_items_qty = loaded_qtys
                    
                    # NÚT XÓA PHIẾU
                    with col_act:
                        st.write("") # Spacer
                        st.write("")
                        if st.button("🗑 XÓA PHIẾU NÀY", type="primary"):
                            delete_invoice(target_receipt_to_update)
                            st.success("Đã xóa phiếu thành công!")
                            time.sleep(1)
                            st.rerun()

        # FORM NHẬP / SỬA
        form_key = "new_form" if mode == "✨ Nhập phiếu mới" else "edit_form"
        with st.form(form_key):
            st.subheader("Thông tin phiếu")
            c1, c2, c3 = st.columns([1, 1, 2])
            input_date = c1.date_input("Ngày", value=default_date)
            receipt_no = c2.text_input("Số phiếu", value=default_receipt)
            selected_customer = c3.selectbox("Khách hàng", customer_names, index=default_customer_idx)
            
            # Logic địa chỉ
            curr_addr = default_address
            if mode == "✨ Nhập phiếu mới" and selected_customer:
                match = customers_list[customers_list['FullName'] == selected_customer]
                if not match.empty: curr_addr = match.iloc[0]['Address']
            
            address = st.text_input("Địa chỉ", value=curr_addr)
            
            # Bảng nhập liệu
            st.markdown("---")
            input_df = pd.DataFrame({"Tên mặt hàng": ITEMS, "Số lượng": default_items_qty})
            edited_df = st.data_editor(
                input_df,
                column_config={
                    "Số lượng": st.column_config.NumberColumn("Số lượng", min_value=0, step=1, required=True),
                    "Tên mặt hàng": st.column_config.TextColumn(disabled=True)
                },
                hide_index=True, use_container_width=True, height=500,
                key=f"editor_{mode}_{editor_key_suffix}"
            )
            
            c_bot1, c_bot2 = st.columns([1, 2])
            total_weight = c_bot1.number_input("TỔNG KG", min_value=0.0, format="%.1f", value=default_total_kg)
            note = c_bot2.text_area("Ghi chú", value=default_note, height=1)

            btn_label = "💾 LƯU PHIẾU MỚI" if mode == "✨ Nhập phiếu mới" else "💾 CẬP NHẬT THAY ĐỔI"
            if st.form_submit_button(btn_label, type="primary", use_container_width=True):
                if not receipt_no:
                    st.error("Thiếu số phiếu!")
                else:
                    qty_map = dict(zip(edited_df["Tên mặt hàng"], edited_df["Số lượng"]))
                    row_data = [
                        input_date.strftime("%Y-%m-%d"), receipt_no, selected_customer, address, note, total_weight
                    ]
                    for item in ITEMS: row_data.append(qty_map.get(item, 0))
                    
                    if mode == "✨ Nhập phiếu mới":
                        save_invoice(row_data)
                        st.success(f"Đã tạo phiếu {receipt_no}!")
                    else:
                        if target_receipt_to_update:
                            update_invoice(target_receipt_to_update, row_data)
                            st.success(f"Đã cập nhật phiếu {receipt_no}!")
                        else: st.error("Lỗi xác định phiếu gốc.")
                    time.sleep(1)
                    st.rerun()

# === TAB BÁO CÁO & IN (ADMIN) ===
if role == 'admin':
    with tab1:
        st.subheader("Báo cáo & In Hóa Đơn")
        if st.button("🔄 Làm mới dữ liệu"):
            st.cache_data.clear()
            st.rerun()

        df = load_invoices()
        if not df.empty:
            df['Ngày'] = pd.to_datetime(df['Ngày'])
            
            # 1. Bộ lọc
            c_date1, c_date2 = st.columns(2)
            d1 = c_date1.date_input("Từ ngày", value=date.today().replace(day=1))
            d2 = c_date2.date_input("Đến ngày", value=date.today())
            
            mask = (df['Ngày'].dt.date >= d1) & (df['Ngày'].dt.date <= d2)
            filtered_df = df.loc[mask].sort_values(by='Ngày', ascending=False)
            
            # Thống kê nhanh
            m1, m2 = st.columns(2)
            m1.metric("Số phiếu", len(filtered_df))
            m2.metric("Tổng lượng", f"{filtered_df['Tổng Kg'].sum() if not filtered_df.empty else 0:,.1f} Kg")
            
            # 2. Danh sách phiếu để chọn IN
            st.markdown("### 🖨 Chọn phiếu để in hóa đơn")
            if not filtered_df.empty:
                # Tạo cột display để selectbox
                filtered_df['Display_Print'] = filtered_df['Ngày'].dt.strftime('%d/%m') + " - Số: " + filtered_df['Số phiếu'].astype(str) + " - " + filtered_df['Khách hàng']
                
                c_sel, c_view = st.columns([3, 1])
                print_selection = c_sel.selectbox("Chọn phiếu:", filtered_df['Display_Print'])
                
                # Nút xuất Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    filtered_df.drop(columns=['Display_Print']).to_excel(writer, index=False)
                c_view.download_button("📥 Xuất Excel list này", buffer.getvalue(), "baocao.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                
                st.markdown("---")
                
                # 3. Hiển thị mẫu in
                if print_selection:
                    # Lấy dòng dữ liệu được chọn
                    selected_row = filtered_df[filtered_df['Display_Print'] == print_selection].iloc[0]
                    
                    # Render HTML
                    invoice_html = render_invoice_html(selected_row)
                    
                    st.info("💡 Mẹo: Nhấn Ctrl + P (hoặc Command + P) để in trang này. Hệ thống sẽ tự động ẩn các thanh menu, chỉ in phần hóa đơn bên dưới.")
                    
                    # Hiển thị khung hóa đơn
                    st.markdown(invoice_html, unsafe_allow_html=True)
            else:
                st.warning("Không có phiếu nào trong khoảng thời gian này.")

# === CUSTOMER VIEW ===
if role == 'customer':
    st.subheader(f"Lịch sử của {full_name}")
    df = load_invoices()
    if not df.empty:
        my_inv = df[df['Khách hàng'] == full_name].sort_values(by='Ngày', ascending=False)
        st.dataframe(my_inv, use_container_width=True)
