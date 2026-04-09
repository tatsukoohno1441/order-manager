import streamlit as st
import datetime  # 在代码最顶端加上这一行
import pandas as pd
from supabase import create_client, Client
import io

# 1. 页面配置
st.set_page_config(page_title="订单查询与售后系统", page_icon="🔍", layout="wide")

# 2. 连接 Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 【显形测试：检查数据库连接状态】 ---
# 这段代码会自动运行，帮你确认程序是否真的看到了 orders 表
try:
    # 尝试读取 1 条数据来测试连接
    test_res = supabase.table("orders").select("id").limit(1).execute()
    db_status = "✅ 数据库连接正常"
except Exception as e:
    db_status = f"❌ 数据库连接异常: {e}"

st.title("订单查询与售后管理系统 🧡")
st.caption(db_status) # 在标题下面显示连接状态

# 初始化日志列表 (修复之前的 NameError)
process_logs = []

# 创建标签页
tab1, tab2 = st.tabs(["🔍 订单查询", "📥 数据同步"])

# --- 标签页 1: 订单查询 ---
with tab1:
    st.subheader("🕵️ 多维度售后精准搜索")
    st.caption("填写条件进行筛选，留空则不限制该项。支持部分一致搜索。")

    # 1. 顶部日期选择：默认当天
    col_date, col_check = st.columns([2, 1])
    with col_date:
        s_date_obj = st.date_input("📅 発送日 (选择日期)", value=datetime.date.today())
        # 将日期转换为字符串，这里格式要和你上传的CSV日期格式一致（比如 2026/04/09 或 2026-04-09）
        s_date = s_date_obj.strftime("%Y/%m/%d") 
    with col_check:
        use_date = st.checkbox("启用日期筛选", value=True)

    st.divider()

    # 2. 其他 10 个属性的搜索框，分三列排布
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
        s_addr1 = st.text_input("届け先住所１")
        s_addr2 = st.text_input("届け先住所２")

    if st.button("🔍 执行组合搜索", use_container_width=True):
        # 启动基础查询
        query = supabase.table("orders").select("*")
        
        # 动态添加过滤条件
        if use_date:
            query = query.ilike("発送日", f"%{s_date}%")
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
            query = query.ilike("届け先住所１", f"%{s_addr1}%")
        if s_addr2:
            query = query.ilike("届け先住所２", f"%{s_addr2}%")
        if s_delivery_no:
            query = query.ilike("配送番号", f"%{s_delivery_no}%")
        if s_jan:
            query = query.ilike("JANコード", f"%{s_jan}%")
        if s_sku:
            query = query.ilike("商品コード", f"%{s_sku}%")
        if s_prod_name:
            query = query.ilike("商品名", f"%{s_prod_name}%")
            
        # 执行查询
        response = query.execute()
        
        if response.data:
            df_res = pd.DataFrame(response.data)
            # 隐藏内部列，按照你想要的顺序排列（如果需要的话）
            display_cols = ["発送日", "注文番号", "届け先氏名", "届け先ＴＥＬ", "配送番号", "商品名", "处理备注"] 
            # 如果你想显示全部 11 个属性，也可以直接用下面这行
            cols_to_show = [c for c in df_res.columns if c not in ['id', 'created_at']]
            
            st.success(f"找到 {len(response.data)} 条符合条件的订单")
            st.dataframe(df_res[cols_to_show], use_container_width=True)
        else:
            st.warning("没找到符合条件的订单。")

# --- 标签页 2: 数据同步 ---
with tab2:
    st.subheader("同步每日订单到数据库")
    st.info("处理完发货后，将最终的 CSV 上传，即可永久保存至数据库。")
    uploaded_file = st.file_uploader("选择要导入的 CSV 文件", type="csv")
    
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
                df_upload = detected_df.fillna("")
                st.write(f"📂 待上传数据: {len(df_upload)} 行")
                
                if st.button("🚀 开始同步到数据库"):
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
st.caption("售后管理系统")