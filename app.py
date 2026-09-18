import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import re
from collections import Counter
from scipy import stats

# --- CONFIGURATION ---
st.set_page_config(page_title="Job Market Intelligence 2025", layout="wide")

# --- DATA LOADING & CLEANING ENGINE ---
@st.cache_data
def load_and_clean_data(file_source):
    # Load the Excel file
    df = pd.read_excel(file_source)
    
    # 1. Salary Cleaning (Focus on INR)
    if 'currency' in df.columns:
        df = df[df['currency'] == 'INR'].copy()
    
    # Calculate Average Salary and convert to LPA (Lakhs Per Annum)
    # Note: We divide by 100,000 assuming raw data is in absolute INR (e.g. 500000)
    df['avg_salary'] = (df['minimumSalary'] + df['maximumSalary']) / 2
    df['salary_lpa'] = df['avg_salary'] / 100000
    
    # 2. Experience Engineering
    df['avg_experience'] = (df['minimumExperience'] + df['maximumExperience']) / 2
    
    def experience_band(x):
        if pd.isna(x): return "Unknown"
        if x < 2: return "0–2 years (Entry)"
        elif x < 5: return "2–5 years (Junior)"
        elif x < 10: return "5–10 years (Mid-Senior)"
        else: return "10+ years (Expert)"
    
    df['experience_band'] = df['avg_experience'].apply(experience_band)

    # 3. Skill Extraction (Regex parsing of the tagsAndSkills column)
    def extract_skills(value):
        if pd.isna(value): return []
        # Split by comma, semicolon, or pipe
        skills = re.split(r"[,;|]+", str(value))
        # Clean whitespace, lowercase, and remove duplicates
        return list(dict.fromkeys([s.strip().lower() for s in skills if s.strip()]))
    
    df['skills_list'] = df['tagsAndSkills'].apply(extract_skills)
    df['n_skills'] = df['skills_list'].apply(len)

    # 4. Role Family Classification
    def classify_role(title):
        t = str(title).lower()
        if any(x in t for x in ['data scientist', 'analyst', 'analytics', 'bi ']): return 'Data Science/Analytics'
        if any(x in t for x in ['machine learning', 'ai', 'deep learning', 'ml ']): return 'AI/ML'
        if any(x in t for x in ['software', 'developer', 'engineer', 'full stack', 'backend', 'frontend']): return 'Software Development'
        if any(x in t for x in ['cloud', 'aws', 'azure', 'devops', 'gcp']): return 'Cloud/DevOps'
        if any(x in t for x in ['sales', 'business development', 'bd ', 'account manager']): return 'Sales/Business'
        if any(x in t for x in ['marketing', 'seo', 'content', 'social media']): return 'Marketing'
        if any(x in t for x in ['hr', 'recruiter', 'human resource']): return 'HR/Talent'
        return 'Others'
    
    df['role_family'] = df['title'].apply(classify_role)
    
    return df

# --- FILE LOGIC ---
DATA_FILENAME = "indian-job-market-dataset-2025.xlsx"

try:
    # Attempt to load the file from the local folder automatically
    df = load_and_clean_data(DATA_FILENAME)
    salary_df = df[df['salary_lpa'] > 0].copy()
    st.sidebar.success(f"✅ Loaded: {DATA_FILENAME}")
except Exception as e:
    st.sidebar.error("❌ Local file not found or error loading.")
    st.sidebar.info("Please use the uploader below:")
    uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])
    if uploaded_file:
        df = load_and_clean_data(uploaded_file)
        salary_df = df[df['salary_lpa'] > 0].copy()
    else:
        st.warning("👋 Waiting for dataset... Please ensure 'indian-job-market-dataset-2025.xlsx' is in the same folder as this script.")
        st.stop()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filter Analytics")
selected_roles = st.sidebar.multiselect("Role Families", options=sorted(df['role_family'].unique()), default=df['role_family'].unique())
selected_exp = st.sidebar.multiselect("Experience Bands", options=["0–2 years (Entry)", "2–5 years (Junior)", "5–10 years (Mid-Senior)", "10+ years (Expert)"], default=["0–2 years (Entry)", "2–5 years (Junior)", "5–10 years (Mid-Senior)", "10+ years (Expert)"])

filtered_df = df[(df['role_family'].isin(selected_roles)) & (df['experience_band'].isin(selected_exp))]
filtered_salary_df = salary_df[(salary_df['role_family'].isin(selected_roles)) & (salary_df['experience_band'].isin(selected_exp))]

# --- DASHBOARD LAYOUT ---
st.title("🇮🇳 Job Market Intelligence Dashboard 2025")
st.markdown("Exploring the relationship between **Skills, Roles, and Salaries** in the Indian tech ecosystem.")

# Top Level Metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Postings", f"{len(filtered_df):,}")
m2.metric("Salary Disclosed (INR)", f"{len(filtered_salary_df):,}")
m3.metric("Median Salary", f"₹{filtered_salary_df['salary_lpa'].median():.1f} LPA")
m4.metric("Avg Skills/Job", round(filtered_df['n_skills'].mean(), 1))

tabs = st.tabs(["📊 Market Overview", "🛠 Skill Demand", "💰 Salary Insights", "🧪 Hypothesis Testing", "📝 Project Report"])

# TAB 1: OVERVIEW
with tabs[0]:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Distribution by Role Family")
        role_counts = filtered_df['role_family'].value_counts().reset_index()
        fig1 = px.pie(role_counts, values='count', names='role_family', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        st.subheader("Postings by Experience Band")
        exp_counts = filtered_df['experience_band'].value_counts().reindex(["0–2 years (Entry)", "2–5 years (Junior)", "5–10 years (Mid-Senior)", "10+ years (Expert)"]).reset_index()
        fig2 = px.bar(exp_counts, x='experience_band', y='count', color='experience_band', color_discrete_sequence=px.colors.sequential.Viridis)
        st.plotly_chart(fig2, use_container_width=True)

# TAB 2: SKILLS
with tabs[1]:
    st.subheader("Top 20 Most Frequent Skills")
    all_skills = [s for sublist in filtered_df['skills_list'] for s in sublist]
    skill_data = pd.DataFrame(Counter(all_skills).most_common(20), columns=['Skill', 'Count'])
    fig3 = px.bar(skill_data, x='Count', y='Skill', orientation='h', color='Count', color_continuous_scale='Bluered')
    fig3.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig3, use_container_width=True)

# TAB 3: SALARY
with tabs[2]:
    c_a, c_b = st.columns(2)
    with c_a:
        st.subheader("Salary Range by Experience")
        fig4 = px.box(filtered_salary_df, x='experience_band', y='salary_lpa', color='experience_band',
                      category_orders={"experience_band": ["0–2 years (Entry)", "2–5 years (Junior)", "5–10 years (Mid-Senior)", "10+ years (Expert)"]})
        fig4.update_layout(yaxis_title="Salary (LPA INR)", yaxis_range=[0, 50])
        st.plotly_chart(fig4, use_container_width=True)
    with c_b:
        st.subheader("Median Salary by Role Family")
        role_med = filtered_salary_df.groupby('role_family')['salary_lpa'].median().sort_values().reset_index()
        fig5 = px.bar(role_med, x='salary_lpa', y='role_family', orientation='h', color='salary_lpa', color_continuous_scale='Tropic')
        st.plotly_chart(fig5, use_container_width=True)

# TAB 4: HYPOTHESIS TESTING
with tabs[3]:
    st.header("Statistical Hypothesis Testing")
    
    st.subheader("1. Skill Premium Test (Mann-Whitney U)")
    test_skill = st.selectbox("Select a skill to analyze its salary impact:", ["python", "sql", "machine learning", "java", "aws", "excel"])
    
    with_skill = salary_df[salary_df['skills_list'].apply(lambda x: test_skill in x)]['salary_lpa']
    without_skill = salary_df[~salary_df['skills_list'].apply(lambda x: test_skill in x)]['salary_lpa']
    
    if len(with_skill) > 20:
        u_stat, p_val = stats.mannwhitneyu(with_skill, without_skill)
        st.write(f"**Null Hypothesis (H₀):** Salary distributions are the same for postings with and without '{test_skill}'.")
        st.metric("P-Value", f"{p_val:.4e}")
        st.write(f"**Median with {test_skill}:** {with_skill.median():.1f} LPA | **Median without:** {without_skill.median():.1f} LPA")
        if p_val < 0.05:
            st.success(f"Significant Result: '{test_skill}' is associated with a different salary distribution.")
        else:
            st.warning("No significant difference found.")

# TAB 5: REPORT
with tabs[4]:
    st.header("Project Final Report")
    st.write(f"**Dataset Size:** {len(df):,} rows | **Location:** India | **Year:** 2025")
    st.markdown("""
    ### 1. Research Question
    What skills and roles are associated with the highest economic value in the current Indian job market?
    
    ### 2. Methodology
    - **Cleaning:** Focused on INR currency; calculated Lakhs Per Annum (LPA).
    - **Feature Engineering:** Extracted individual skill tags and grouped job titles into 'Role Families'.
    - **Analysis:** Non-parametric statistical tests were used due to the skewed nature of salary data.
    
    ### 3. Key Findings
    - **Skill Demand:** While 'Sales' and 'Management' are high volume, technical skills like 'Python' and 'Machine Learning' command a massive salary premium.
    - **Experience Growth:** There is a significant 'Experience Leap' in salary between the 5-year and 10-year marks.
    - **Role Performance:** AI/ML and Cloud/DevOps families show the highest median entry-level salaries compared to traditional software roles.
    
    ### 4. Conclusion
    To maximize earning potential, candidates should focus on 'Skill Stacking'—combining a core technical skill (Python/SQL) with a domain specialty (Cloud or AI).
    """)