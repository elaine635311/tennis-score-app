import streamlit as st
import pandas as pd
import numpy as np

# 设置页面标题
st.set_page_config(page_title="网球底线测试评分系统", layout="wide")

st.title("🎾 网球底线击球能力测试评分系统")
st.markdown("---")

# --- 侧边栏：权重设置 ---
st.sidebar.header("⚙️ 参数设置")

st.sidebar.subheader("1. 三大模块权重")
w_rally = st.sidebar.slider("底线回合控制权重", 0.0, 1.0, 0.5, 0.05)
w_pressure = st.sidebar.slider("压力击球权重", 0.0, 1.0, 0.3, 0.05)
w_precision = st.sidebar.slider("击球精度权重", 0.0, 1.0, 0.2, 0.05)

# 校验权重和
total_w = w_rally + w_pressure + w_precision
if total_w != 1.0:
    st.sidebar.warning(f"⚠️ 当前权重之和为 {total_w:.2f}，建议调整为 1.0")

st.sidebar.subheader("2. 评分模式")
score_mode = st.sidebar.radio("选择分数显示模式", ("T分数 (50分基准)", "标准分 (0-100强制拉伸)"))

# --- 核心算法函数 ---
def get_z_score(series):
    std = series.std()
    if std == 0: return pd.Series(0, index=series.index)
    return (series - series.mean()) / std

def process_data(df, w_rally, w_pressure, w_precision):
    # 1. 数据预处理（根据你提供的表结构读取）
    # 精度测试
    df_prec = df.iloc[:, [0, 2, 3, 4, 5]].copy()
    df_prec.columns = ['Name', 'Task', 'Hand', 'Inbound', 'HQ']
    df_prec = df_prec.dropna(subset=['Name'])
    
    # 压力测试
    df_press = df.iloc[:, [7, 9, 10, 11, 12]].copy()
    df_press.columns = ['Name', 'Task', 'Hand', 'Inbound', 'HQ']
    df_press = df_press.dropna(subset=['Name'])
    
    # 回合控制
    df_rally = df.iloc[:, [14, 16, 17, 18, 19, 20]].copy()
    df_rally.columns = ['Name', 'Task', 'TotalShots', 'Errors', 'HQRate', 'Consecutive']
    df_rally = df_rally.dropna(subset=['Name'])
    
    # 2. 计算各模块 Z 分数
    # --- 精度 ---
    df_prec_avg = df_prec.groupby(['Name', 'Task'])[['Inbound', 'HQ']].mean().reset_index()
    df_prec_avg['Z_Inbound'] = df_prec_avg.groupby('Task')['Inbound'].transform(get_z_score)
    df_prec_avg['Z_HQ'] = df_prec_avg.groupby('Task')['HQ'].transform(get_z_score)
    df_prec_avg['Task_Z'] = 0.3 * df_prec_avg['Z_Inbound'] + 0.7 * df_prec_avg['Z_HQ']
    task_weights = {'斜线': 0.4, '直线': 0.3, '小斜线': 0.3}
    df_prec_avg['Weight'] = df_prec_avg['Task'].map(task_weights)
    prec_score = df_prec_avg.groupby('Name').apply(lambda x: np.sum(x['Task_Z'] * x['Weight'])).reset_index(name='Score_Precision')

    # --- 压力 ---
    df_press_avg = df_press.groupby(['Name', 'Task'])[['Inbound', 'HQ']].mean().reset_index()
    df_press_avg['Z_Inbound'] = df_press_avg.groupby('Task')['Inbound'].transform(get_z_score)
    df_press_avg['Z_HQ'] = df_press_avg.groupby('Task')['HQ'].transform(get_z_score)
    df_press_avg['Task_Z'] = 0.3 * df_press_avg['Z_Inbound'] + 0.7 * df_press_avg['Z_HQ']
    df_press_avg['Weight'] = df_press_avg['Task'].map(task_weights)
    press_score = df_press_avg.groupby('Name').apply(lambda x: np.sum(x['Task_Z'] * x['Weight'])).reset_index(name='Score_Pressure')

    # --- 回合 ---
    for col in ['TotalShots', 'Errors', 'HQRate', 'Consecutive']:
        df_rally[col] = pd.to_numeric(df_rally[col], errors='coerce').fillna(0)
    for m in ['TotalShots', 'Errors', 'HQRate', 'Consecutive']:
        df_rally[f'Z_{m}'] = df_rally.groupby('Task')[m].transform(get_z_score)
    
    df_rally['Task_Z'] = (
        0.15 * df_rally['Z_TotalShots'] + 
        0.15 * (-1 * df_rally['Z_Errors']) + 
        0.30 * df_rally['Z_HQRate'] + 
        0.40 * df_rally['Z_Consecutive']
    )
    rally_score = df_rally.groupby('Name')['Task_Z'].mean().reset_index(name='Score_Rally')

    # 3. 合并与填充
    # 统一名字（防止录入错误）
    for d in [prec_score, press_score, rally_score]:
        d['Name'] = d['Name'].replace('王睿琪', '王睿琦')

    df_final = pd.merge(prec_score, press_score, on='Name', how='outer')
    df_final = pd.merge(df_final, rally_score, on='Name', how='outer')

    # 缺项按最低分填充
    df_final['Score_Precision'] = df_final['Score_Precision'].fillna(df_final['Score_Precision'].min())
    df_final['Score_Pressure'] = df_final['Score_Pressure'].fillna(df_final['Score_Pressure'].min())
    df_final['Score_Rally'] = df_final['Score_Rally'].fillna(df_final['Score_Rally'].min())

    # 4. 总分计算
    df_final['Total_Z'] = (
        w_precision * df_final['Score_Precision'] + 
        w_pressure * df_final['Score_Pressure'] + 
        w_rally * df_final['Score_Rally']
    )
    
    return df_final

# --- 主界面逻辑 ---
uploaded_file = st.file_uploader("📂 请上传测试数据 (Excel文件)", type=['xlsx'])

if uploaded_file is not None:
    try:
        # 读取数据
        df_raw = pd.read_excel(uploaded_file)
        
        # 运行计算
        results = process_data(df_raw, w_rally, w_pressure, w_precision)
        
        # 分数转换
        if score_mode == "T分数 (50分基准)":
            results['最终得分'] = 50 + 10 * results['Total_Z']
        else:
            z_min = results['Total_Z'].min()
            z_max = results['Total_Z'].max()
            if z_max > z_min:
                results['最终得分'] = 0 + (results['Total_Z'] - z_min) / (z_max - z_min) * 100
            else:
                results['最终得分'] = 50
        
        results['最终得分'] = results['最终得分'].round(1)
        results['排名'] = results['最终得分'].rank(ascending=False).astype(int)
        results = results.sort_values('排名')
        
        # 展示结果
        st.success("计算完成！")
        
        # 核心指标卡
        top1 = results.iloc[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("🏆 第一名", top1['Name'], f"{top1['最终得分']}分")
        col2.metric("👥 参与人数", f"{len(results)}人")
        col3.metric("📊 平均分", f"{results['最终得分'].mean():.1f}分")
        
        # 详细表格
        st.subheader("排行榜")
        
        # 格式化显示列
        display_cols = ['排名', 'Name', '最终得分', 'Score_Precision', 'Score_Pressure', 'Score_Rally']
        df_display = results[display_cols].copy()
        df_display.columns = ['排名', '姓名', '总分', '精度Z分', '压力Z分', '回合Z分']
        
        # 高亮显示第一名
        def highlight_top(s):
            is_max = s['排名'] == 1
            return ['background-color: #ffeb3b' if is_max else '' for _ in s]

        st.dataframe(df_display.style.apply(highlight_top, axis=1), use_container_width=True)
        
        # 图表分析
        st.subheader("📊 能力分布图")
        chart_data = df_display[['姓名', '精度Z分', '压力Z分', '回合Z分']].set_index('姓名')
        st.bar_chart(chart_data)

        # 下载按钮
        csv = df_display.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 下载排名表 (CSV)",
            data=csv,
            file_name='网球测试排名.csv',
            mime='text/csv',
        )
        
    except Exception as e:
        st.error(f"文件格式有误或数据缺失，请检查上传的 Excel 文件。\n错误信息: {e}")
else:
    st.info("👆 请在上方上传 '计算测试总分.xlsx' 文件开始计算")
    st.markdown("""
    **使用说明：**
    1. 点击上方按钮上传 Excel 文件。
    2. 左侧侧边栏可以调整各项权重。
    3. 系统会自动计算排名和得分。
    4. 手机端点击左上角箭头可展开/收起设置菜单。
    """)