import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import datetime

# 1. 页面配置
st.set_page_config(page_title="オーダー検索システム🔍", page_icon="🔍", layout="wide")

# 2. 连接 Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 检查连接状态 ---
try:
    supabase.table("orders").select("id").limit(1).execute()
    db_status = "✅ データベースエラーなし"
except Exception as e:
    db_status = f"❌ データベースエラー: {e}"

# --- 🔒 登录门禁 (插入在原本的第 21 行位置) ---
def check_password():
    """只有当天登录过且密码正确才返回 True"""
    def password_entered():
        if st.session_state["password"] == st.secrets["LOGIN_PASSWORD"]:
            st.session_state["password_correct"] = True
            # 记录今天的日期，实现每日刷新的效果
            st.session_state["login_date"] = datetime.date.today().isoformat()
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    is_correct = st.session_state.get("password_correct", False)
    login_date = st.session_state.get("login_date", "")
    is_today = (login_date == datetime.date.today().isoformat())

    if is_correct and is_today:
        return True

    st.title("🔐 システムログイン")
    st.info("セキュリティ保護のため、24時間ごとに再ログインが必要です。🧡")
    st.text_input("アクセスパスワードを入力してください：", type="password", on_change=password_entered, key="password")
    
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 パスワードが正しくありません。再入力してください。")
    return False

if not check_password():
    st.stop()  # 没通过就停在这里，不显示后面的内容
# ------------------------------------------

st.title("オーダー検索システム 🧡")
st.caption(db_status)

# 创建标签页
tab1, tab2 = st.tabs(["🔍 オーダー検索", "📥 データアップロード"])

# --- 标签页 1: 订单查询 ---
with tab1:
    st.subheader("オーダー検索")
    st.caption("部分一致搜索OK")

    # 日期选择：默认当天
    col_date, col_check = st.columns([2, 1])
    with col_date:
        s_date_obj = st.date_input("📅 発送日", value=datetime.date.today())
        # 自动适配常见的日期格式
        s_date_str = s_date_obj.strftime("%Y/%m/%d")
    with col_check:
        use_date = st.checkbox("発送日検索", value=False)

    st.divider()

    # 11个属性分三列排布
    c1, c2, c3 = st.columns(3)
    with c1:
        s_order_no = st.text_input("注文番号")
        s_name = st.text_input("届け先氏名")
        s_tel = st.text_input("届け先ＴＥＬ")
        s_zip = st.text_input("届け先郵便番号")
    with c2:
        s_delivery_no = st.text_input("配送番号")
        s_jan = st.text_input("JANコード")
        s_sku = st.text_input("商品コード")
        s_pref = st.text_input("届け先都道府県")
    with c3:
        s_prod_name = st.text_input("商品名")
        s_addr1 = st.text_input("届け先住所1") # 对应数据库中的 住所1
        s_addr2 = st.text_input("届け先住所2") # 对应数据库中的 住所2

    if st.button("🔍 検索", use_container_width=True):
        query = supabase.table("orders").select("*")
        
        # 动态添加过滤条件 (模糊匹配)
        if use_date:
            query = query.ilike("発送日", f"%{s_date_str}%")
        if s_order_no:
            query = query.ilike("注文番号", f"%{s_order_no}%")
        if s_name:
            query = query.ilike("届け先氏名", f"%{s_name}%")
        if s_tel:
            query = query.ilike("届け先ＴＥＬ", f"%{s_tel}%")
        if s_zip:
            query = query.ilike("届け先郵便番号", f"%{s_zip}%")
        if s_pref:
            query = query.ilike("届け先都道府県", f"%{s_pref}%")
        if s_addr1:
            # 注意：这里的列名必须和 SQL 修改后的名字一致
            query = query.ilike("住所1", f"%{s_addr1}%")
        if s_addr2:
            query = query.ilike("住所2", f"%{s_addr2}%")
        if s_delivery_no:
            query = query.ilike("配送番号", f"%{s_delivery_no}%")
        if s_jan:
            query = query.ilike("JANコード", f"%{s_jan}%")
        if s_sku:
            query = query.ilike("商品コード", f"%{s_sku}%")
        if s_prod_name:
            query = query.ilike("商品名", f"%{s_prod_name}%")
            
        response = query.execute()
        
        if response.data:
            df_res = pd.DataFrame(response.data)
            # 整理显示列（隐藏内部ID）
            cols_to_show = [c for c in df_res.columns if c not in ['id', 'created_at']]
            st.success(f"找到 {len(response.data)} 条订单")
            st.dataframe(df_res[cols_to_show], use_container_width=True)
        else:
            st.warning("一致する注文なし")

# --- 标签页 2: 数据同步 ---
with tab2:
    st.subheader("CSVフェイルをデータベースにアップロード")
    uploaded_file = st.file_uploader("CSVフェイルを選択", type="csv")
    
    if uploaded_file:
        try:
            # 自动识别日本 CSV 编码
            content = uploaded_file.read()
            detected_df = None
            for enc in ['utf-8-sig', 'shift-jis', 'cp932']:
                try:
                    detected_df = pd.read_csv(io.BytesIO(content), encoding=enc, dtype=str)
                    break
                except: continue
            
            if detected_df is not None:
                # 【核心修改点】：在这里加入重命名逻辑
                # 它会自动把 CSV 里的旧名字映射到数据库的新名字
                df_upload = detected_df.rename(columns={
                    '届け先住所１': '住所1',
                    '届け先住所２': '住所2'
                })
                df_upload = df_upload.fillna("")

                st.write(f"📂 アップロード注文データ: {len(df_upload)} 行")
                
                if st.button("🚀 アップロード"):
                    data_to_insert = df_upload.to_dict(orient='records')
                    
                    # 使用进度条，让等待不再无聊
                    progress_bar = st.progress(0)
                    batch_size = 100
                    total_batches = (len(data_to_insert) // batch_size) + 1
                    
                    for i in range(0, len(data_to_insert), batch_size):
                        batch = data_to_insert[i:i + batch_size]
                        supabase.table("orders").insert(batch).execute()
                        progress_bar.progress(min((i + batch_size) / len(data_to_insert), 1.0))
                    
                    st.success(f"🎉 成功同步 {len(data_to_insert)} 条订单数据！")
            else:
                st.error("无法识别文件编码，请确保是标准的 CSV 格式。")
                
        except Exception as e:
            st.error(f"同步失败: {e}")

st.divider()
st.caption("オーダー検索システム")