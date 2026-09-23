import io, json, os, urllib.request
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'public' / 'data' / 'raw'
MAX_ROWS = 100
SUPPORTED = {'.csv'}


def json_default(v):
    if pd.isna(v): return None
    if hasattr(v, 'item'): return v.item()
    return str(v)


def send(h, status, payload):
    body = json.dumps(payload, default=json_default).encode('utf-8')
    h.send_response(status)
    h.send_header('Content-Type','application/json; charset=utf-8')
    h.send_header('Access-Control-Allow-Origin','*')
    h.send_header('Access-Control-Allow-Headers','Content-Type')
    h.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS')
    h.end_headers(); h.wfile.write(body)


def files():
    return sorted([p.name for p in RAW.glob('*.csv')])


def load(name):
    if name not in files(): raise ValueError('Unknown demo dataset.')
    return pd.read_csv(RAW/name)


def profile(df):
    miss = df.isna().sum()
    dups = int(df.duplicated().sum())
    cols=[]
    for c in df.columns:
        s=df[c]
        cols.append({'column':str(c),'dtype':str(s.dtype),'missing':int(s.isna().sum()),'unique':int(s.nunique(dropna=True)),'sample_values':[x for x in s.dropna().astype(str).head(4).tolist()]})
    numeric=df.select_dtypes(include='number')
    stats=[]
    for c in numeric.columns:
        x=numeric[c]
        stats.append({'column':str(c),'min':x.min(),'mean':x.mean(),'median':x.median(),'max':x.max()})
    return {'rows':int(len(df)),'columns':int(df.shape[1]),'duplicates':dups,'missing_cells':int(miss.sum()),'column_profile':cols,'numeric_summary':stats,'preview':df.head(20).where(pd.notna(df.head(20)),None).to_dict('records')}


def quality(df):
    issues=[]
    for c,n in df.isna().sum().items():
        if n: issues.append({'type':'Missing values','column':str(c),'count':int(n),'severity':'High' if n/len(df)>.05 else 'Medium','suggested_action':'Mean / median for numeric, mode for categorical'})
    d=int(df.duplicated().sum())
    if d: issues.append({'type':'Duplicate rows','column':'—','count':d,'severity':'Medium','suggested_action':'Remove duplicates'})
    for c in df.select_dtypes(include='number').columns:
        neg=int((df[c]<0).sum())
        if neg: issues.append({'type':'Negative values','column':str(c),'count':neg,'severity':'High','suggested_action':'Review or replace invalid values'})
    if 'age' in df.columns:
        bad=int(((df.age<0)|(df.age>120)).sum())
        if bad: issues.append({'type':'Out-of-range age','column':'age','count':bad,'severity':'High','suggested_action':'Replace invalid values with median'})
    return {'issue_count':len(issues),'issues':issues}


def clean_df(df, ops):
    out=df.copy()
    log=[]
    if ops.get('drop_duplicates'):
        before=len(out); out=out.drop_duplicates(); log.append({'action':'Remove duplicate rows','changed':before-len(out)})
    fills=ops.get('fill_nulls',{})
    for col,method in fills.items():
        if col not in out.columns: continue
        before=int(out[col].isna().sum())
        if not before: continue
        s=out[col]
        if method=='mean' and pd.api.types.is_numeric_dtype(s): val=s.mean()
        elif method=='median' and pd.api.types.is_numeric_dtype(s): val=s.median()
        elif method=='mode': val=s.mode().iloc[0] if not s.mode().empty else 0
        elif method=='zero': val=0
        else: continue
        out[col]=s.fillna(val); log.append({'action':f'Fill {col} with {method}','changed':before,'value':val})
    # safe generic invalid age repair
    if ops.get('fix_age') and 'age' in out.columns:
        bad=(out.age<0)|(out.age>120); n=int(bad.sum()); med=out.loc[~bad,'age'].median(); out.loc[bad,'age']=med; log.append({'action':'Repair invalid age values','changed':n,'value':med})
    return out,log


def apply_transform(df, spec):
    out=df.copy(); name=spec.get('new_column','derived_column'); typ=spec.get('type'); source=spec.get('source_column')
    if source not in out.columns: raise ValueError('Source column not found.')
    if typ in ('year','month','quarter'):
        dt=pd.to_datetime(out[source],errors='coerce')
        if typ=='year': out[name]=dt.dt.year
        elif typ=='month': out[name]=dt.dt.month_name()
        else: out[name]='Q'+dt.dt.quarter.astype('Int64').astype(str)
    elif typ=='age_group':
        bins=[0,25,35,45,55,10**9]; labels=['18–25','26–35','36–45','46–55','56+']; out[name]=pd.cut(pd.to_numeric(out[source],errors='coerce'),bins=bins,labels=labels,right=True,include_lowest=True)
    elif typ=='calculation':
        second=spec.get('second_column'); op=spec.get('operator','multiply')
        if second not in out.columns: raise ValueError('Second column not found.')
        a=pd.to_numeric(out[source],errors='coerce'); b=pd.to_numeric(out[second],errors='coerce')
        out[name]={'multiply':a*b,'add':a+b,'subtract':a-b,'divide':a/b.replace(0,pd.NA)}.get(op,a*b)
    else: raise ValueError('Unsupported transformation.')
    return out


def analytics():
    c=load('customers.csv'); o=load('orders.csv'); i=load('order_items.csv'); p=load('products.csv'); s=load('stores.csv')
    c,_=clean_df(c,{'drop_duplicates':True,'fill_nulls':{'age':'median'},'fix_age':True})
    o,_=clean_df(o,{'drop_duplicates':True})
    i,_=clean_df(i,{'drop_duplicates':True,'fill_nulls':{'quantity':'median'}})
    p,_=clean_df(p,{'fill_nulls':{'unit_price':'median'}})
    i=i.merge(p[['product_id','product_name','category','unit_price','unit_cost']],on='product_id',how='left')
    i['revenue']=i['quantity']*i['unit_price']*(1-i['discount'].fillna(0))
    i['profit']=i['revenue']-i['quantity']*i['unit_cost']
    i=i.merge(o[['order_id','order_date','store_id','status']],on='order_id',how='left')
    completed=i[i.status.eq('Completed')].copy(); completed['month']=pd.to_datetime(completed.order_date,errors='coerce').dt.to_period('M').astype(str)
    revenue=float(completed.revenue.sum()); profit=float(completed.profit.sum()); orders=int(completed.order_id.nunique()); customers=int(completed.customer_id.nunique()) if 'customer_id' in completed else int(o[o.status.eq('Completed')].customer_id.nunique())
    monthly=completed.groupby('month',dropna=True).agg(revenue=('revenue','sum'),profit=('profit','sum')).reset_index().tail(24)
    by_store=completed.groupby('store_id').agg(revenue=('revenue','sum'),profit=('profit','sum')).reset_index().merge(s,on='store_id',how='left').sort_values('revenue',ascending=False).head(10)
    by_cat=completed.groupby('category').agg(revenue=('revenue','sum'),profit=('profit','sum')).reset_index().sort_values('revenue',ascending=False)
    top_products=completed.groupby(['product_id','product_name']).agg(revenue=('revenue','sum'),profit=('profit','sum')).reset_index().sort_values('revenue',ascending=False).head(10)
    return {'kpis':{'revenue':revenue,'profit':profit,'orders':orders,'customers':customers,'aov':revenue/orders if orders else 0,'profit_margin':profit/revenue if revenue else 0},'monthly':monthly.to_dict('records'),'stores':by_store.to_dict('records'),'categories':by_cat.to_dict('records'),'top_products':top_products.to_dict('records')}


def tool_result(tool, args):
    if tool=='get_kpi_summary': return analytics()['kpis']
    if tool=='top_categories': return analytics()['categories'][:int(args.get('n',3))]
    if tool=='top_products': return analytics()['top_products'][:int(args.get('n',5))]
    if tool=='store_performance': return analytics()['stores']
    if tool=='monthly_trend': return analytics()['monthly']
    if tool=='data_quality_report':
        return {f:quality(load(f)) for f in files()}
    raise ValueError('Unknown tool')


def ask_llm(question):
    key=os.getenv('ANTHROPIC_API_KEY')
    if not key:
        return {'mode':'grounded-demo','answer':local_answer(question),'evidence':'Computed from the governed Nexa Retail demo functions. Set ANTHROPIC_API_KEY in Vercel to enable the Claude tool-calling layer.'}
    tools=[
      {'name':'get_kpi_summary','description':'Return computed Nexa Retail KPI values.','input_schema':{'type':'object','properties':{},'required':[]}},
      {'name':'top_categories','description':'Return categories ranked by computed revenue.','input_schema':{'type':'object','properties':{'n':{'type':'integer'}},'required':[]}},
      {'name':'top_products','description':'Return products ranked by computed revenue.','input_schema':{'type':'object','properties':{'n':{'type':'integer'}},'required':[]}},
      {'name':'store_performance','description':'Return computed store revenue and profit.','input_schema':{'type':'object','properties':{},'required':[]}},
      {'name':'monthly_trend','description':'Return computed monthly revenue and profit.','input_schema':{'type':'object','properties':{},'required':[]}},
      {'name':'data_quality_report','description':'Return raw-dataset data-quality findings.','input_schema':{'type':'object','properties':{},'required':[]}}
    ]
    messages=[{'role':'user','content':question}]
    for _ in range(3):
        payload={'model':os.getenv('ANTHROPIC_MODEL','claude-haiku-4-5-20251001'),'max_tokens':700,'system':'You are DataLens, an evidence-first retail analytics assistant. Never invent numbers. Use tools for every factual business metric. Explain results clearly and cite the tool evidence by naming it.','tools':tools,'messages':messages}
        req=urllib.request.Request('https://api.anthropic.com/v1/messages',data=json.dumps(payload).encode(),headers={'x-api-key':key,'anthropic-version':'2023-06-01','content-type':'application/json'})
        with urllib.request.urlopen(req,timeout=25) as resp: data=json.load(resp)
        messages.append({'role':'assistant','content':data.get('content',[])})
        uses=[x for x in data.get('content',[]) if x.get('type')=='tool_use']
        if not uses:
            txt=' '.join(x.get('text','') for x in data.get('content',[]) if x.get('type')=='text')
            return {'mode':'claude-tool-calling','answer':txt,'evidence':'Tool calls executed against computed DataLens functions.'}
        results=[]
        for u in uses:
            results.append({'type':'tool_result','tool_use_id':u['id'],'content':json.dumps(tool_result(u['name'],u.get('input',{})),default=json_default)})
        messages.append({'role':'user','content':results})
    return {'mode':'error','answer':'The model requested too many tool steps. Try a narrower question.'}


def local_answer(q):
    a=analytics(); ql=q.lower()
    if 'top' in ql and 'categor' in ql: return 'Top categories by revenue: '+', '.join(f"{x['category']} ({x['revenue']:.2f})" for x in a['categories'][:3])
    if 'top' in ql and 'product' in ql: return 'Top products by revenue: '+', '.join(f"{x['product_name']} ({x['revenue']:.2f})" for x in a['top_products'][:3])
    if 'margin' in ql: return f"Overall profit margin is {a['kpis']['profit_margin']:.1%}, based on computed revenue and profit."
    if 'revenue' in ql or 'profit' in ql or 'kpi' in ql: return f"Revenue is {a['kpis']['revenue']:.2f}, profit is {a['kpis']['profit']:.2f}, with {a['kpis']['orders']} completed orders and AOV of {a['kpis']['aov']:.2f}."
    if 'quality' in ql or 'issue' in ql: return 'The raw datasets contain intentionally injected missing values, duplicates and invalid values. Use the Data Quality stage to inspect the exact counts.'
    return 'I can answer questions about revenue, profit, margin, stores, categories, products, monthly trends and data quality using computed DataLens functions.'


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self): send(self,200,{'ok':True})
    def do_GET(self):
        path=self.path.split('?',1)[0]
        try:
            if path=='/api/files': return send(self,200,{'files':files()})
            if path=='/api/explore':
                name=dict(x.split('=',1) for x in self.path.split('?',1)[1].split('&') if '=' in x).get('file','') if '?' in self.path else ''
                return send(self,200,{'file':name,**profile(load(name))})
            if path=='/api/quality':
                name=dict(x.split('=',1) for x in self.path.split('?',1)[1].split('&') if '=' in x).get('file','') if '?' in self.path else ''
                return send(self,200,{'file':name,**quality(load(name))})
            if path=='/api/analytics': return send(self,200,analytics())
            return send(self,404,{'error':'Route not found'})
        except Exception as e: return send(self,422,{'error':str(e)})
    def do_POST(self):
        try:
            length=int(self.headers.get('Content-Length','0')); raw=self.rfile.read(length); body=json.loads(raw or '{}'); path=self.path.split('?',1)[0]
            if path=='/api/clean':
                df=load(body['file']); cleaned,log=clean_df(df,body.get('operations',{})); return send(self,200,{'file':body['file'],'before':profile(df),'after':profile(cleaned),'log':log,'preview':cleaned.head(20).where(pd.notna(cleaned.head(20)),None).to_dict('records')})
            if path=='/api/transform':
                df=load(body['file']); out=apply_transform(df,body['spec']); return send(self,200,{'file':body['file'],'new_column':body['spec'].get('new_column'),'before_columns':list(df.columns),'after_columns':list(out.columns),'preview':out.head(20).where(pd.notna(out.head(20)),None).to_dict('records')})
            if path=='/api/ask': return send(self,200,ask_llm(body.get('question','')))
            return send(self,404,{'error':'Route not found'})
        except Exception as e: return send(self,422,{'error':str(e)})
