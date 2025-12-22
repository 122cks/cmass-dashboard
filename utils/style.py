import streamlit as st

def apply_custom_style():
    st.markdown("""
        <style>
        /* Import Pretendard Font */
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

        /* Global Font Settings */
        html, body, [class*="css"] {
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, 'Helvetica Neue', 'Segoe UI', 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif;
        }

        /* Header Styling */
        h1, h2, h3 {
            color: #1E293B;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        
        h1 {
            border-bottom: 2px solid #E2E8F0;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }

        /* Metric Cards Styling */
        div[data-testid="stMetric"] {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transition: transform 0.2s ease-in-out;
        }
        
        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }

        div[data-testid="stMetricLabel"] {
            color: #64748B;
            font-size: 0.875rem;
            font-weight: 500;
        }

        div[data-testid="stMetricValue"] {
            color: #0F172A;
            font-weight: 700;
        }

        /* DataFrame Styling */
        div[data-testid="stDataFrame"] {
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #F8FAFC;
            border-right: 1px solid #E2E8F0;
        }
        
        section[data-testid="stSidebar"] .block-container {
            padding-top: 2rem;
        }

        /* Button Styling */
        div.stButton > button {
            background-color: #3B82F6;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 0.5rem 1rem;
            font-weight: 600;
            transition: background-color 0.2s;
        }

        div.stButton > button:hover {
            background-color: #2563EB;
            border-color: #2563EB;
        }
        
        div.stButton > button:focus {
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.5);
        }

        /* Selectbox & Input Styling */
        div[data-baseweb="select"] > div {
            background-color: #FFFFFF;
            border-color: #CBD5E1;
            border-radius: 6px;
        }
        
        /* Tabs Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: transparent;
        }

        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: #F1F5F9;
            border-radius: 8px 8px 0 0;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
            color: #64748B;
            font-weight: 600;
        }

        .stTabs [aria-selected="true"] {
            background-color: #FFFFFF;
            color: #3B82F6;
            border-bottom: 2px solid #3B82F6;
        }

        /* Expander Styling */
        .streamlit-expanderHeader {
            background-color: #F8FAFC;
            border-radius: 8px;
            font-weight: 600;
            color: #334155;
        }
        
        /* Info/Warning/Success Box Styling */
        div[data-testid="stAlert"] {
            border-radius: 8px;
            border: none;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        }

        </style>
    """, unsafe_allow_html=True)
