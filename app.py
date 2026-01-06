import streamlit as st
import pandas as pd
import numpy as np
import streamlit_antd_components as sac # 引入高级UI库

# --- 页面配置 ---
st.set_page_config(
    page_title="AO Tennis Tech Analysis", 
    page_icon="🎾",
    layout="wide", 
    initial_sidebar_state="collapsed" # 默认收起侧边栏，视野更开阔
)

# --- 🎨 CSS 注入区：澳网科技风 (Australian Open Tech Style) ---
ao_style = """
<style>
    /* 1. 全局背景：深海蓝 -> 午夜蓝 渐变 */
    .stApp {
        background: linear-gradient(180deg, #021B79 0%, #000000 100%);
        color: white;
    }

    /* 2. 隐藏默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 3. 标题样式：澳网荧光色 */
    h1, h2, h3 {
        color: #00dbff !important; /* 荧光青 */
        font-family: 'Arial', sans-serif !important;
        font-weight: 800 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* 4. 数据指标卡片 (Metric)：玻璃拟态 */
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(0, 219, 255, 0.3);
        padding: 15px;
        border-radius: 15px;
        backdrop-filter: blur(10px);
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetricLabel"] {
        color: #ccff00 !important; /* 网球黄 */
    }
    div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 2.2rem !important;
    }

    /* 5. 表格样式：深色科技风 */
    div[data-testid="stDataFrame"] {
        background-color: rgba(0, 0, 0, 0.4);
        border-radius: 10px;
        padding: 10px;
        border: 1px solid #333;
    }
    
    /* 6. 输入框样式 */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background-color: rgba(255,255,255,0.1) !important;
        color: white !important;
        border: 1px solid #00dbff;
        border-radius: 8px;
    }

    /* 7. 成功/信息 提示框颜色覆写 */
    .stAlert {
        background-color: rgba(0, 27, 121, 0.8);
        border: 1px solid #00dbff;
        color: white;
    }
</style>
"""
st.markdown(ao_style, unsafe_allow_html=True)

# --- 标题区 ---
st.markdown("<h1 style='text-align: center;'>🎾 AO Tennis Tech Analysis</h1>", unsafe_allow_html=True)

# --- 顶部导航栏 (替代侧边栏单选框) ---
app_mode = sac.segmented(
    items=[
        sac.SegmentedItem(label='现场计分 (Entry)', icon='pencil-square'),
        sac.SegmentedItem(label='数据分析 (Analysis)', icon='bar-chart-fill'),
    ],
    align='center',
    color='yellow', # 澳网黄高亮
    bg_color='rgba(255,255,255,0.1)',
    size='md'
)

# --- 核心算法函数 (保持不变) ---
def get_z_score(series):
    if series.empty or series.std() == 0:
        return pd.Series(0, index=series.index)
    return (series - series.mean()) / series.std()

# ==========================================
# 模块一：现场计分 (Data Entry)
# ==========================================
if app_mode == '现场计分 (Entry)':
    
    # 1. 基础信息行
    col1, col2 = st.columns(2)
    with col1:
        student_name = st.text_input("Player Name (姓名)")
    with col2:
        # 使用 SAC 分段控制器替代 Selectbox，更直观
        test_category = sac.segmented(
            items=[
                sac.SegmentedItem(label='击球精度', icon='crosshair'),
                sac.SegmentedItem(label='压力击球', icon='speedometer'),
                sac.SegmentedItem(label='回合控制', icon='arrow-repeat'),
            ],
            label='测试项目',
            size='sm',
            color='cyan'
        )

    # 2. 初始化 Session State
    if 'current_data' not in st.session_state:
        st.session_state.current_data = []
    
    st.markdown("---")

    # --- 场景 A: 精度/压力测试 (点按计分) ---
    if test_category in ['击球精度', '压力击球']:
        
        # 任务/线路选择
        task_name = sac.chip(
            items=[
                sac.ChipItem(label='斜线 Cross'),
                sac.ChipItem(label='直线 Line'),
                sac.ChipItem(label='小斜线 Short'),
            ],
            label='击球线路 (Line)',
            align='center',
            radius='md',
            multiple=False,
            color='yellow'
        )
        if not task_name: task_name = '斜线 Cross' # 默认值

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("👇 点击下方按钮记录每一拍 (Click to record shot)")

        # 使用 SAC 按钮组，图标更好看，布局更紧凑
        # 注意：sac.buttons 点击后会触发 rerun，并返回被点击的 label
        action_shot = sac.buttons(
            items=[
                sac.ButtonsItem(label='4分 (High Quality)', icon='stars', color='#ccff00'),
                sac.ButtonsItem(label='2分 (Normal)', icon='circle', color='#00dbff'),
                sac.ButtonsItem(label='1分 (Safe)', icon='check-circle', color='#ffffff'),
                sac.ButtonsItem(label='0分 (Error)', icon='x-circle', color='#ff4b4b'),
            ],
            format_func='title',
            align='center',
            gap='md',
            radius='lg',
            variant='filled',
            direction='horizontal' # 横向排列
        )

        # 处理计分逻辑
        if action_shot:
            score_map = {'4分 (High Quality)': 4, '2分 (Normal)': 2, '1分 (Safe)': 1, '0分 (Error)': 0}
            val = score_map.get(action_shot)
            
            # 防止页面刷新导致的重复添加 (简单防抖)
            # 实际上 SAC 点击即刷新，不需要额外的 st.button 包裹
            st.session_state.current_data.append(val)
            st.toast(f"已记录: {val} 分", icon="✅") 
            # 不需要手动 rerun，组件自带刷新

        # 实时数据显示区
        if len(st.session_state.current_data) > 0:
            st.markdown("---")
            shots = np.array(st.session_state.current_data)
            
            # 指标卡片
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("总拍数 (Shots)", len(shots))
            with m2: st.metric("入界率 (In)", f"{np.sum(shots > 0) / len(shots):.1%}")
            with m3: st.metric("高质量率 (HQ)", f"{np.sum(shots == 4) / len(shots):.1%}")
            
            # 显示最近的数据条
            st.text(f"当前序列: {st.session_state.current_data[-10:]} ...")

    # --- 场景 B: 回合控制测试 (表单录入) ---
    elif test_category == '回合控制':
        
        task_name = sac.chip(
            items=[sac.ChipItem(l) for l in ["右区1打2", "左区1打2", "2打2斜线", "2打2直线"]],
            label='测试区域', align='center', color='cyan'
        )
        if not task_name: task_name = "右区1打2"

        with st.form("rally_form"):
            c1, c2 = st.columns(2)
            rally_len = c1.number_input("回合拍数 (Rally Length)", min_value=0, value=1)
            is_error = c2.checkbox("是否失误 (Error)?")
            
            c3, c4 = st.columns(2)
            hq_count = c3.number_input("高质量球 (HQ Count)", min_value=0, value=0)
            cons_hq = c4.number_input("连续高质量 (Consecutive HQ)", min_value=0, value=0)
            
            submitted = st.form_submit_button("➕ 添加回合数据 (Add Rally)", type="primary")
            
            if submitted:
                st.session_state.current_data.append({
                    "拍数": rally_len,
                    "失误": 1 if is_error else 0,
                    "高质量": hq_count,
                    "连续": cons_hq
                })
                st.success("✅ 数据已添加")

        if len(st.session_state.current_data) > 0:
            st.dataframe(pd.DataFrame(st.session_state.current_data), use_container_width=True)

    # --- 底部操作区 ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_undo, col_dl, col_clear = st.columns([1, 2, 1])
    
    with col_undo:
        if st.button("↩️ 撤销 (Undo)"):
            if len(st.session_state.current_data) > 0:
                st.session_state.current_data.pop()
                st.rerun() # 使用新版命令

    with col_clear:
        if st.button("🗑️ 清空数据 (Clear)", type="secondary"):
            st.session_state.current_data = []
            st.rerun() # 修复了这里的报错！

    with col_dl:
        if len(st.session_state.current_data) > 0:
            if test_category == '回合控制':
                df_export = pd.DataFrame(st.session_state.current_data)
                df_export['姓名'] = student_name
                df_export['任务'] = task_name
            else:
                shots = np.array(st.session_state.current_data)
                df_export = pd.DataFrame({
                    "姓名": [student_name],
                    "任务": [task_name],
                    "入界率": [np.sum(shots > 0) / len(shots)],
                    "高质量率": [np.sum(shots == 4) / len(shots)]
                })
            csv = df_export.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下载 CSV", csv, f"{student_name}_Data.csv", "text/csv", type="primary", use_container_width=True)

# ==========================================
# 模块二：数据分析 (Analysis)
# ==========================================
elif app_mode == '数据分析 (Analysis)':
    st.markdown("### 📊 综合排名计算")
    
    # 侧边栏设置移到主界面顶部展开，更符合移动端逻辑
    with st.expander("⚙️ 权重设置 (Settings)", expanded=False):
        w_rally = st.slider("回合控制权重", 0.0, 1.0, 0.5, 0.05)
        w_pressure = st.slider("压力击球权重", 0.0, 1.0, 0.3, 0.05)
        w_precision = st.slider("击球精度权重", 0.0, 1.0, 0.2, 0.05)
    
    uploaded_file = st.file_uploader("📂 上传 Excel 数据文件", type=["xlsx"])
    
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            
            # --- 原始算法逻辑 (保持不变) ---
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

            # 合并
            res = pd.merge(prec_final, press_final, on='Name', how='outer')
            res = pd.merge(res, rally_final, on='Name', how='outer')
            
            res['Score_Precision'] = res['Score_Precision'].fillna(res['Score_Precision'].min())
            res['Score_Pressure'] = res['Score_Pressure'].fillna(res['Score_Pressure'].min())
            res['Score_Rally'] = res['Score_Rally'].fillna(res['Score_Rally'].min())

            res['Total_Z'] = w_precision * res['Score_Precision'] + \
                             w_pressure * res['Score_Pressure'] + \
                             w_rally * res['Score_Rally']
            
            z_min, z_max = res['Total_Z'].min(), res['Total_Z'].max()
            if z_max > z_min:
                res['最终得分'] = (res['Total_Z'] - z_min) / (z_max - z_min) * 100
            else:
                res['最终得分'] = 60
                
            res = res.sort_values('最终得分', ascending=False)
            res['排名'] = range(1, len(res) + 1)

            # --- 结果展示区 (美化) ---
            st.success("✅ 计算完成")
            st.dataframe(
                res[['排名', 'Name', '最终得分']].style.background_gradient(cmap='Teal'), 
                use_container_width=True
            )
            
            st.markdown("#### 📈 详细得分分解")
            st.dataframe(res[['Name', 'Score_Precision', 'Score_Pressure', 'Score_Rally']], use_container_width=True)
                
        except Exception as e:
            st.error(f"❌ 计算出错: {e}")