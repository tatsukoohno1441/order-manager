import streamlit as st
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
    st.subheader("快速搜索订单")
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("输入 注文番号 / 届け先氏名 / 届け先ＴＥＬ 进行搜索")
    
    if search_query:
        # 执行数据库搜索
        response = supabase.table("orders").select("*").or_(
            f"注文番号.ilike.%{search_query}%,届け先氏名.ilike.%{search_query}%,届け先ＴＥＬ.ilike.%{search_query}%"
        ).execute()
        
        if response.data:
            df_res = pd.DataFrame(response.data)
            # 隐藏内部 ID 列
            cols_to_show = [c for c in df_res.columns if c not in ['id', 'created_at']]
            st.dataframe(df_res[cols_to_show], use_container_width=True)
            st.success(f"找到 {len(response.data)} 条匹配记录")
        else:
            st.warning("没有找到匹配的订单。")

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