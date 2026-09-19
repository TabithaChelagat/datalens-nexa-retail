import os, re
from typing import List, Tuple
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title='DataLens — Nexa Retail', page_icon='📊', layout='wide')

APPROVED_VIEWS = {
    'datalens.v_monthly_kpis','datalens.v_store_performance',
    'datalens.v_category_performance','datalens.v_target_attainment',
    'datalens.v_customer_summary','datalens.v_sales_detail',
    'datalens.v_data_quality_summary'
}
BLOCKED = re.compile(r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC|EXECUTE|CALL|COPY|VACUUM|ANALYZE|MERGE|REFRESH|COMMENT)\b', re.I)


def validate_sql(sql: str) -> Tuple[bool, str]:
    s = sql.strip()
    if not s: return False, 'SQL is empty.'
    if '--' in s or '/*' in s or '*/' in s: return False, 'SQL comments are not allowed.'
    if ';' in s.rstrip(';'): return False, 'Multiple SQL statements are not allowed.'
    if not re.match(r'^(SELECT|WITH)\b', s, re.I): return False, 'Only SELECT/WITH queries are allowed.'
    if BLOCKED.search(s): return False, 'A write/DDL operation was detected.'
    refs = re.findall(r'\b(?:FROM|JOIN)\s+([A-Za-z_][\w$]*(?:\.[A-Za-z_][\w$]*)?)', s, re.I)
    bad = [r.lower() for r in refs if r.lower() not in APPROVED_VIEWS]
    if bad: return False, f'Unapproved table/view reference: {bad[0]}'
    return True, 'OK'


def run_sql(engine, sql):
    ok, msg = validate_sql(sql)
    if not ok: raise ValueError(msg)
    return pd.read_sql(text(sql.rstrip(';')), engine)


def deterministic(question: str):
    q = question.lower()
    if any(x in q for x in ['data quality','quality score','quality issues']):
        return '''SELECT table_name, row_count, null_key_count FROM datalens.v_data_quality_summary ORDER BY table_name''', 'Data quality summary from the governed quality view.'
    if 'most profitable' in q or 'profitable categor' in q:
        return '''SELECT category, revenue, gross_profit, gross_margin_pct FROM datalens.v_category_performance ORDER BY gross_profit DESC LIMIT 10''', 'Categories ranked by governed gross profit.'
    if 'top store' in q or 'best store' in q or 'stores by revenue' in q:
        return '''SELECT store_name, region, revenue, gross_profit, gross_margin_pct FROM datalens.v_store_performance ORDER BY revenue DESC LIMIT 10''', 'Stores ranked by governed net revenue.'
    if 'missing target' in q or 'below target' in q:
        return '''SELECT month, store_name, region, revenue_target, actual_revenue, revenue_attainment_pct FROM datalens.v_target_attainment WHERE actual_revenue < revenue_target ORDER BY month, revenue_attainment_pct''', 'Stores below their monthly revenue target.'
    if 'repeat customer' in q:
        return '''SELECT COUNT(*) FILTER (WHERE is_repeat_customer) AS repeat_customers, COUNT(*) AS customers, 100.0 * COUNT(*) FILTER (WHERE is_repeat_customer) / NULLIF(COUNT(*),0) AS repeat_customer_rate_pct FROM datalens.v_customer_summary''', 'Repeat-customer rate based on customers with at least two non-cancelled/non-returned orders.'
    if 'monthly revenue' in q or 'revenue trend' in q:
        return '''SELECT month, revenue, gross_profit, gross_margin_pct, orders, units, average_order_value FROM datalens.v_monthly_kpis ORDER BY month''', 'Monthly revenue and profitability trend.'
    if '2025 revenue' in q:
        return '''SELECT SUM(revenue) AS revenue, SUM(gross_profit) AS gross_profit, SUM(orders) AS orders, SUM(units) AS units FROM datalens.v_monthly_kpis WHERE EXTRACT(YEAR FROM month)=2025''', '2025 totals from the governed monthly KPI view.'
    return None, None


def llm_sql(question: str):
    key = os.getenv('OPENAI_API_KEY')
    if not key: return None, 'OPENAI_API_KEY is not configured; use deterministic questions or configure the optional LLM mode.'
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        model = os.getenv('OPENAI_MODEL', 'gpt-5.6')
        schema = '\n'.join(sorted(APPROVED_VIEWS))
        prompt = f'''You generate PostgreSQL SELECT queries only for a retail analytics assistant.\nApproved views only:\n{schema}\nRules: one statement; SELECT or WITH only; no comments; never invent tables/columns; use only columns exposed by approved views. Return SQL only.'''
        r = client.chat.completions.create(model=model, messages=[{'role':'system','content':prompt},{'role':'user','content':question}], temperature=0)
        return r.choices[0].message.content.strip(), 'LLM-generated SQL; it is validated before execution.'
    except Exception as e:
        return None, f'LLM mode failed: {e}'

st.title('DataLens')
st.caption('AI-powered data quality, analytics & management assistant — Nexa Retail')

with st.sidebar:
    st.header('Connection')
    db_url = st.text_input('DATABASE_URL', value=os.getenv('DATABASE_URL',''), type='password')
    mode = st.radio('Query mode', ['Governed questions','Custom SQL','LLM (optional)'])
    st.divider()
    st.markdown('**Safety:** read-only, approved-view allow-list, single-statement validation.')

if not db_url:
    st.info('Set DATABASE_URL in the sidebar or environment to connect to PostgreSQL.')
    st.code('postgresql+psycopg2://USER:PASSWORD@HOST:5432/nexaretail')
    st.stop()

try:
    engine = create_engine(db_url, pool_pre_ping=True)
    with engine.connect() as c: c.execute(text('SELECT 1'))
except Exception as e:
    st.error(f'Database connection failed: {e}')
    st.stop()

question = st.text_input('Ask DataLens', placeholder='e.g. Which stores are below target?')
if mode == 'Custom SQL':
    sql = st.text_area('Approved-view SQL', height=180, placeholder='SELECT ... FROM datalens.v_monthly_kpis')
else:
    sql = None

if st.button('Run analysis', type='primary'):
    if mode == 'Governed questions':
        sql, explanation = deterministic(question)
        if not sql:
            st.warning('I do not have a deterministic template for that question. Try monthly revenue, top stores, profitable categories, missing target, repeat customer rate, 2025 revenue, or data quality.')
            st.stop()
    elif mode == 'LLM (optional)':
        sql, explanation = llm_sql(question)
        if not sql: st.error(explanation); st.stop()
    else:
        explanation = 'User-supplied SQL executed only after read-only and approved-view validation.'
    try:
        df = run_sql(engine, sql)
        st.subheader('Answer')
        if df.empty: st.info('The query returned no rows.')
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            if len(df.columns) == 1 and len(df) == 1:
                st.metric(df.columns[0].replace('_',' ').title(), str(df.iloc[0,0]))
        st.subheader('Evidence')
        st.caption(explanation)
        st.code(sql, language='sql')
    except Exception as e:
        st.error(f'Query rejected or failed: {e}')

st.divider()
st.caption('DataLens does not modify the database. KPI definitions are governed in PostgreSQL views and shared with BI.')
