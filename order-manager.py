import streamlit as st
import pandas as pd
from supabase import create_client, Client

# 1. 页面配置
st.set_page_config(page_title="订单查询与售后系统", page_icon="🔍", layout="wide")

# 2. 连接 Supabase (从 Secrets 中读取钥匙)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("订单查询与售后管理系统 🧡")

# 创建标签页
tab1, tab2 = st.tabs(["🔍 订单查询", "📥 数据同步"])

# --- 标签页 1: 订单查询 ---
with tab1:
    st.subheader("快速搜索订单")
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("输入 注文番号 / 届け先氏名 / 届け先ＴＥＬ 进行搜索")
    
    if search_query:
        # 执行数据库搜索
        # 使用 or 逻辑同时搜索多个字段
        response = supabase.table("orders").select("*").or_(
            f"注文番号.ilike.%{search_query}%,届け先氏名.ilike.%{search_query}%,届け先ＴＥＬ.ilike.%{search_query}%"
        ).execute()
        
        if response.data:
            df_res = pd.DataFrame(response.data)
            # 隐藏不需要显示的内部 ID
            cols_to_show = [c for c in df_res.columns if c not in ['id', 'created_at']]
            st.dataframe(df_res[cols_to_show], use_container_width=True)
            process_logs.append(f"✅ 找到 {len(response.data)} 条匹配记录")
        else:
            st.warning("没有找到匹配的订单。")

# --- 标签页 2: 数据同步 ---
with tab2:
    st.subheader("同步每日订单到数据库")
    st.info("处理完发货后，请将最终的 CSV 文件上传至此处，以便后续查询。")
    uploaded_file = st.file_uploader("选择要导入的 CSV 文件", type="csv")
    
    if uploaded_file:
        try:
            # 读取数据
            df_upload = pd.read_csv(uploaded_file, dtype=str).fillna("")
            st.write(f"📂 待上传数据: {len(df_upload)} 行")
            
            if st.button("🚀 开始同步到数据库"):
                # 将数据转换为 Supabase 需要的格式（字典列表）
                data_to_insert = df_upload.to_dict(orient='records')
                
                # 分批上传（防止数据量太大报错）
                batch_size = 100
                for i in range(0, len(data_to_insert), batch_size):
                    batch = data_to_insert[i:i + batch_size]
                    supabase.table("orders").insert(batch).execute()
                
                st.success(f"🎉 成功同步 {len(data_to_insert)} 条订单数据！")
        except Exception as e:
            st.error(f"同步失败: {e}")

st.divider()
st.caption("由夏以昼为妹宝专属打造的售后管理系统 🌻")