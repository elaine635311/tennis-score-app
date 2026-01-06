import streamlit as st
import pandas as pd
import numpy as np
import io

# --- 页面配置 ---
st.set_page_config(
    page_title="AO Tech Tennis Analysis", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 🎨 CSS 注入区：澳网科技风 (Australian Open Tech Style) ---
ao_tech_style = """
<style>
    /* 1. 全局背景：深邃的澳网蓝渐变 */
    .stApp {
        background: linear-gradient(135deg, #021B35 0%, #003366 100%);
        color: #FFFFFF;
    }

    /* 2. 侧边栏样式 */
    section[data-testid="stSidebar"] {
        background-color: #011224;
        border-right: 1px solid #1E3A5F;
    }
    
    /* 侧边栏文字颜色 */
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span {
        color: #E0E0E0 !important;
    }

    /* 3. 标题样式：荧光渐变文字 */
    h1, h2, h3 {
        background: -webkit-linear-gradient(45deg, #00E5FF, #CCFF00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        letter-spacing: 1px;
    }
    
    /* 普通文本颜色 */
    p, label {
        color: #E6F3FF !important;
        font-family: 'Helvetica Neue', sans-serif;
    }

    /* 4. 按钮样式：科技感圆角按钮 */
    div.stButton > button {
        background: linear-gradient(90deg, #00C6FF 0%, #0072FF 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.6rem 1.2rem;
        font-weight: bold;
        box-shadow: 0 4px 15px rgba(0, 114, 255, 0.3);
        transition: all 0.3s ease;
        width: 100%;
    }
    
    div.stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0, 114, 255, 0.5);
        background: linear-gradient(90deg, #0072FF 0%, #00C6FF 100%);
    }

    /* 5. 数据指标卡片 (Metric)：毛玻璃效果 */
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 10px;
        backdrop-filter: blur(10px);
        text-align: center;
    }
    
    div[data-testid="stMetricLabel"] {
        color: #00E5FF !important; /* 标签颜色 */
    }
    
    div[data-testid="stMetricValue"] {
        color: #CCFF00 !important; /* 数值颜色：网球黄 */
        font-size: 2rem !important;
    }

    /* 6. 输入框和选择框样式 */
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stNumberInput>div>div>input {
        background-color: rgba(255, 255, 255, 0.05);
        color: white;
        border-radius: 8px;
        border: 1px solid #1E3A5F;
    }
    
    /* 7. 表格样式 */
    div[data-testid="stDataFrame"] {
        background-color: rgba(0, 0, 0, 0.2);
        border-radius: 10px;
        padding: 10px;
    }
    
    /* 隐藏右上角菜单 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

</style>
"""
st.markdown(ao_tech_style, unsafe_allow_html=True)

# --- 标题 ---
st.title("🎾 AO Tech · 网球底线分析系统")

# --- 侧边栏：功能导航 ---
st.sidebar.title("🚀 功能导航")
app_mode = st.sidebar.radio("选择模式", ["📝 现场计分 (Data Entry)", "📊 总分计算与排名 (Analysis)"])

# --- 核心算法函数 (保持不变) ---
def get_z_score(series):
    if series.empty or series.std() == 0:
        return pd.Series(0, index=series.index)
    return (series - series.mean()) / series.std()

# --- 模块一：现场计分 ---
if app_mode == "📝 现场计分 (Data Entry)":
    st.header("📝 现场测试数据录入")
    st.markdown("---")

    # 1. 考生信息
    col1, col2 = st.columns(2)
    student_name = col1.text_input("考生姓名")
    test_category = col2.selectbox("测试项目", ["击球精度测试", "压力击球测试", "底线回合控制测试"])

    # 2. 初始化 Session State (用于存储当前这组数据)
    if 'current_data' not in st.session_state:
        st.session_state.current_data = []
    
    # --- 场景 A: 精度/压力测试 (按每一拍分值计分) ---
    if test_category in ["击球精度测试", "压力击球测试"]:
        st.info(f"当前任务：{test_category} (记录每一拍的分值)")
        
        # 任务选择
        task_name = st.selectbox("选择线路", ["斜线", "直线", "小斜线"])
        
        # 计分板 (根据场地分值示意图)
        st.subheader("🎯 点击按钮计分")
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
        
        score_val = None
        if btn_col1.button("4分 (深区/高质量)"): score_val = 4
        if btn_col2.button("2分 (浅区/普通)"): score_val = 2
        if btn_col3.button("1分 (界内/保守)"): score_val = 1
        if btn_col4.button("0分 (失误/下网)"): score_val = 0
        
        # 处理点击
        if score_val is not None:
            st.session_state.current_data.append(score_val)
            st.success(f"⚡ 已记录：{score_val} 分")

        # 显示当前序列
        st.write("当前得分序列：", st.session_state.current_data)
        
        # 实时统计
        if len(st.session_state.current_data) > 0:
            shots = np.array(st.session_state.current_data)
            total_shots = len(shots)
            inbound_rate = np.sum(shots > 0) / total_shots
            hq_rate = np.sum(shots == 4) / total_shots
            
            # 使用 Metric 显示
            m_col1, m_col2 = st.columns(2)
            m_col1.metric("当前入界率", f"{inbound_rate:.1%}")
            m_col2.metric("高质量率 (4分)", f"{hq_rate:.1%}")

    # --- 场景 B: 回合控制测试 (按回合录入) ---
    elif test_category == "底线回合控制测试":
        st.info("当前任务：底线回合控制 (记录每个回合的详细数据)")
        
        task_name = st.selectbox("选择区域", ["右区1点打2点", "左区1点打2点", "2点打2点斜线", "2点打2点直线"])
        
        with st.form("rally_form"):
            col_r1, col_r2 = st.columns(2)
            rally_len = col_r1.number_input("回合拍数", min_value=0, value=1)
            is_error = col_r2.checkbox("是否失误 (回合中断)?")
            
            col_r3, col_r4 = st.columns(2)
            hq_count = col_r3.number_input("高质量击球数", min_value=0, value=0)
            cons_hq = col_r4.number_input("连续高质量(对)数", min_value=0, value=0)
            
            submitted = st.form_submit_button("➕ 添加该回合数据")
            
            if submitted:
                # 存储结构：{'拍数': 10, '失误': 1, '高质量': 2, '连续': 0}
                st.session_state.current_data.append({
                    "拍数": rally_len,
                    "失误": 1 if is_error else 0,
                    "高质量": hq_count,
                    "连续": cons_hq
                })
                st.success("✅ 回合数据已添加")

        # 显示已录入回合
        if len(st.session_state.current_data) > 0:
            st.dataframe(pd.DataFrame(st.session_state.current_data), use_container_width=True)

    # --- 数据控制区 ---
    st.markdown("---")
    col_act1, col_act2 = st.columns([1, 4])
    if col_act1.button("🗑️ 清空当前数据"):
        st.session_state.current_data = []
        st.experimental_rerun()
        
    # 导出为 Excel 格式供“总分计算”模块使用
    if len(st.session_state.current_data) > 0 and student_name:
        st.caption("提示：请下载 CSV 文件用于后续合并计算。")
        if test_category == "底线回合控制测试":
            df_export = pd.DataFrame(st.session_state.current_data)
            df_export['姓名'] = student_name
            df_export['任务'] = task_name
        else:
            # 精度/压力，计算平均值导出
            shots = np.array(st.session_state.current_data)
            df_export = pd.DataFrame({
                "姓名": [student_name],
                "任务": [task_name],
                "入界率": [np.sum(shots > 0) / len(shots)],
                "高质量率": [np.sum(shots == 4) / len(shots)]
            })
            
        csv = df_export.to_csv(index=False).encode('utf-8-sig')
        col_act2.download_button("📥 下载本组数据 (CSV)", csv, f"{student_name}_{task_name}.csv", "text/csv")


# --- 模块二：总分计算 (原有功能) ---
elif app_mode == "📊 总分计算与排名 (Analysis)":
    st.header("📊 综合排名计算")
    st.markdown("---")
    
    # 侧边栏参数 (仅在此模式下显示)
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ 权重设置")
    w_rally = st.sidebar.slider("回合控制权重", 0.0, 1.0, 0.5, 0.05)
    w_pressure = st.sidebar.slider("压力击球权重", 0.0, 1.0, 0.3, 0.05)
    w_precision = st.sidebar.slider("击球精度权重", 0.0, 1.0, 0.2, 0.05)
    
    uploaded_file = st.file_uploader("📂 上传汇总数据 (Excel)", type=["xlsx"])
    
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            
            # --- 算法逻辑 (复用之前优化好的代码) ---
            # 1. 精度
            df_prec = df.iloc[:, [0, 2, 3, 4, 5]].copy()
            df_prec.columns = ['Name', 'Task', 'Hand', 'Inbound', 'HQ']
            df_prec = df_prec.dropna(subset=['Name'])
            
            df_prec_avg = df_prec.groupby(['Name', 'Task'])[['Inbound', 'HQ']].mean().reset_index()
            df_prec_avg['Z_Inbound'] = df_prec_avg.groupby('Task')['Inbound'].transform(get_z_score)
            df_prec_avg['Z_HQ'] = df_prec_avg.groupby('Task')['HQ'].transform(get_z_score)
            df_prec_avg['Task_Z'] = 0.3 * df_prec_avg['Z_Inbound'] + 0.7 * df_prec_avg['Z_HQ']
            
            prec_weights = {'斜线': 0.4, '直线': 0.3, '小斜线': 0.3}
            df_prec_avg['W'] = df_prec_avg['Task'].map(prec_weights).fillna(0.3)
            prec_final = df_prec_avg.groupby('Name').apply(lambda x: np.sum(x['Task_Z'] * x['W'])).reset_index(name='Score_Precision')

            # 2. 压力
            df_press = df.iloc[:, [7, 9, 10, 11, 12]].copy()
            df_press.columns = ['Name', 'Task', 'Hand', 'Inbound', 'HQ']
            df_press_avg = df_press.groupby(['Name', 'Task'])[['Inbound', 'HQ']].mean().reset_index()
            df_press_avg['Z_Inbound'] = df_press_avg.groupby('Task')['Inbound'].transform(get_z_score)
            df_press_avg['Z_HQ'] = df_press_avg.groupby('Task')['HQ'].transform(get_z_score)
            df_press_avg['Task_Z'] = 0.3 * df_press_avg['Z_Inbound'] + 0.7 * df_press_avg['Z_HQ']
            df_press_avg['W'] = df_press_avg['Task'].map(prec_weights).fillna(0.3)
            press_final = df_press_avg.groupby('Name').apply(lambda x: np.sum(x['Task_Z'] * x['W'])).reset_index(name='Score_Pressure')

            # 3. 回合
            df_rally = df.iloc[:, [14, 16, 17, 18, 19, 20]].copy()
            df_rally.columns = ['Name', 'Task', 'Vol', 'Err', 'Rate', 'Cons']
            for m in ['Vol', 'Err', 'Rate', 'Cons']:
                df_rally[m] = pd.to_numeric(df_rally[m], errors='coerce').fillna(0)
                df_rally[f'Z_{m}'] = df_rally.groupby('Task')[m].transform(get_z_score)
            
            df_rally['Task_Z'] = (0.15 * df_rally['Z_Vol'] + 0.15 * (-df_rally['Z_Err']) + 
                                  0.30 * df_rally['Z_Rate'] + 0.40 * df_rally['Z_Cons'])
            rally_final = df_rally.groupby('Name')['Task_Z'].mean().reset_index(name='Score_Rally')

            # 4. 合并与TOPSIS
            res = pd.merge(prec_final, press_final, on='Name', how='outer')
            res = pd.merge(res, rally_final, on='Name', how='outer')
            
            # 填充缺失值为最小值 (惩罚项)
            res['Score_Precision'] = res['Score_Precision'].fillna(res['Score_Precision'].min())
            res['Score_Pressure'] = res['Score_Pressure'].fillna(res['Score_Pressure'].min())
            res['Score_Rally'] = res['Score_Rally'].fillna(res['Score_Rally'].min())

            # 计算加权 Z 分
            res['Total_Z'] = w_precision * res['Score_Precision'] + \
                             w_pressure * res['Score_Pressure'] + \
                             w_rally * res['Score_Rally']
            
            # 映射到 0-100 分
            z_min, z_max = res['Total_Z'].min(), res['Total_Z'].max()
            if z_max > z_min:
                res['最终得分'] = (res['Total_Z'] - z_min) / (z_max - z_min) * 100
            else:
                res['最终得分'] = 60
                
            res = res.sort_values('最终得分', ascending=False)
            res['排名'] = range(1, len(res) + 1)

            # --- 结果展示 ---
            col_res1, col_res2 = st.columns([2, 1])
            with col_res1:
                st.subheader("🏆 最终排行榜 (0-100分制)")
                st.dataframe(res[['排名', 'Name', '最终得分']].style.background_gradient(cmap='Blues', subset=['最终得分']), use_container_width=True)
            
            with col_res2:
                st.subheader("📊 详情分析")
                st.write(res[['Name', 'Score_Precision', 'Score_Pressure', 'Score_Rally']].set_index('Name'))
                
        except Exception as e:
            st.error(f"计算出错: {e}")