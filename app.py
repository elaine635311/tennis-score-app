import streamlit as st
import pandas as pd
import numpy as np

# 设置页面
st.set_page_config(page_title="网球底线测试评分系统", layout="wide")
st.title("🎾 网球底线击球能力测试评分系统")

# --- 核心算法函数 ---
def get_z_score(series):
    if series.empty or series.std() == 0:
        return pd.Series(0, index=series.index)
    return (series - series.mean()) / series.std()

def calculate_scores(df):
    try:
        # 1. 击球精度测试计算 [cite: 4, 6, 8]
        # 选取指标：入界率(30%)，高质量率(70%) [cite: 8]
        df_prec = df.iloc[:, [0, 2, 3, 4, 5]].copy()
        df_prec.columns = ['Name', 'Task', 'Hand', 'Inbound', 'HQ']
        df_prec = df_prec.dropna(subset=['Name'])
        
        df_prec_avg = df_prec.groupby(['Name', 'Task'])[['Inbound', 'HQ']].mean().reset_index()
        df_prec_avg['Z_Inbound'] = df_prec_avg.groupby('Task')['Inbound'].transform(get_z_score)
        df_prec_avg['Z_HQ'] = df_prec_avg.groupby('Task')['HQ'].transform(get_z_score)
        df_prec_avg['Task_Z'] = 0.3 * df_prec_avg['Z_Inbound'] + 0.7 * df_prec_avg['Z_HQ']
        
        # 任务权重：斜线40%, 直线30%, 小斜线30% [cite: 6]
        prec_weights = {'斜线': 0.4, '直线': 0.3, '小斜线': 0.3}
        df_prec_avg['W'] = df_prec_avg['Task'].map(prec_weights).fillna(0.3)
        prec_final = df_prec_avg.groupby('Name').apply(lambda x: np.sum(x['Task_Z'] * x['W'])).reset_index(name='Score_Precision')

        # 2. 压力击球测试计算 [cite: 11, 13, 15]
        df_press = df.iloc[:, [7, 9, 10, 11, 12]].copy()
        df_press.columns = ['Name', 'Task', 'Hand', 'Inbound', 'HQ']
        df_press_avg = df_press.groupby(['Name', 'Task'])[['Inbound', 'HQ']].mean().reset_index()
        df_press_avg['Z_Inbound'] = df_press_avg.groupby('Task')['Inbound'].transform(get_z_score)
        df_press_avg['Z_HQ'] = df_press_avg.groupby('Task')['HQ'].transform(get_z_score)
        df_press_avg['Task_Z'] = 0.3 * df_press_avg['Z_Inbound'] + 0.7 * df_press_avg['Z_HQ']
        df_press_avg['W'] = df_press_avg['Task'].map(prec_weights).fillna(0.3)
        press_final = df_press_avg.groupby('Name').apply(lambda x: np.sum(x['Task_Z'] * x['W'])).reset_index(name='Score_Pressure')

        # 3. 底线回合控制测试计算 [cite: 18, 20, 22]
        # 指标权重：总拍数(15%)，失误(15%)，高质量率(30%)，连续高质量(40%) [cite: 22]
        df_rally = df.iloc[:, [14, 16, 17, 18, 19, 20]].copy()
        df_rally.columns = ['Name', 'Task', 'Vol', 'Err', 'Rate', 'Cons']
        for m in ['Vol', 'Err', 'Rate', 'Cons']:
            df_rally[f'Z_{m}'] = df_rally.groupby('Task')[m].transform(get_z_score)
        
        df_rally['Task_Z'] = (0.15 * df_rally['Z_Vol'] + 0.15 * (-df_rally['Z_Err']) + 
                              0.30 * df_rally['Z_Rate'] + 0.40 * df_rally['Z_Cons'])
        rally_final = df_rally.groupby('Name')['Task_Z'].mean().reset_index(name='Score_Rally')

        # 合并总评分 [cite: 3]
        # 权重：回合50%，压力30%，精度20% [cite: 3]
        res = pd.merge(prec_final, press_final, on='Name', how='outer')
        res = pd.merge(res, rally_final, on='Name', how='outer').fillna(res.min())
        res['Total_Z'] = 0.5 * res['Score_Rally'] + 0.3 * res['Score_Pressure'] + 0.2 * res['Score_Precision']
        
        return res
    except Exception as e:
        st.error(f"数据解析失败，请检查 Excel 格式是否符合要求。错误详情: {e}")
        return None

# --- UI 逻辑 ---
uploaded_file = st.file_uploader("📂 请上传测试数据 (Excel 格式)", type=["xlsx"])

if uploaded_file:
    df_raw = pd.read_excel(uploaded_file)
    with st.spinner('正在计算总分...'):
        results = calculate_scores(df_raw)
        
    if results is not None:
        # 分数转换 60-100 [cite: 10, 17, 24]
        z_min, z_max = results['Total_Z'].min(), results['Total_Z'].max()
        results['总评成绩'] = 60 + (results['Total_Z'] - z_min) / (z_max - z_min) * 40
        results = results.sort_values('总评成绩', ascending=False)
        
        st.success("✅ 计算完成")
        st.dataframe(results[['Name', '总评成绩']].round(1), use_container_width=True)
else:
    st.info("💡 系统已准备就绪，请上传 Excel 数据表以生成排名。")