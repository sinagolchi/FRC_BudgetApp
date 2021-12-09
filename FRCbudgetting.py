import streamlit as st
import pandas as pd
import psycopg2
import time
from stqdm import stqdm
st.set_page_config(layout='wide')
user_dict={'mayor' : "Mayor",'planner':'Planner','em':'Emergency Manager','cso':'Community Service','wr':'Waterfront Resident','F':'Farmer','LD':'Land Developer','LEF':'Large Engineering Firm'}
user_dict_inv= {v:k for k,v in user_dict.items()}

measure_dict_structural = {'Dry or Wet Proof Building':'P1','Elevate Buildings':'P2','Green Dike':'P3','Traditional Dike':'P4','Wetland':'P5','Wetland Protection':'P6','Road and Bridge Relocation':'P7','Road and Bridge Maintenace':'P8'}
measure_dict_social = {'Managed Retreat/Property Buyouts':'S1','Flood Bylaw':'S2','Flood Forecasting and Warning':'S3','Community Awareness':'S4','Emergency Response Planning':'S5','Post-Flood Recovery Resources': 'S6','Flood Insurance':'S7','Post-Flood Recovery Resources':'S8'}
all_measures = {**measure_dict_structural,**measure_dict_social}
all_measures_inv = {v:k for k,v in all_measures.items()}
st.title('FRC budget and measure management')
with st.sidebar:
    st.write('Please Login below:')
    st.selectbox(label='FRC Board number',options=[1,2,3,4,5])
    user_id = st.text_input('Your unique FRC ID')

st.header("Your role is: " + str(user_dict[user_id]))

roles = ['mayor','planner','em','cso','wr','F','LD','LEF']
other_roles = [x for x in roles if x != user_id]

#Connecting to database
def init_connection():
    return psycopg2.connect(**st.secrets["postgres"])

conn = init_connection()

@st.cache(ttl=2)
def run_query(query):
    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()

df = pd.read_sql("SELECT * from frcbudget1;",conn)
df.set_index('role',inplace=True)
rows = run_query("SELECT * from frcbudget1;")

df_m = pd.read_sql("SELECT * from measures;",conn)
df_m.set_index('measure_id',inplace=True)

with st.expander('Developer tools'):
    col_dv1 , col_dv2 = st.columns(2)
    with col_dv1:
        st.dataframe(df_m)
    with col_dv2:
        st.dataframe(df)

st.header('Your budget')
st.metric(value='$'+str(df.loc[user_id,'cb']),delta=int(df.loc[user_id,'delta']),label="My Current budget")
st.subheader('Participants budgets')

metric_cols = st.columns(7)
for col, role in zip(metric_cols,other_roles):
    with col:
        st.metric(label=user_dict[role],value='$'+str(df.loc[role,'cb']),delta=int(df.loc[role,'delta']))

update_bid_measure = ("UPDATE measures SET person_bid = %s, total_bid = total_bid + %s WHERE measure_ID=%s;")
update_bid_role =  ("UPDATE frcbudget1 SET r1_measure = %s, r1_bid = %s WHERE role=%s;")

def make_bid_func(measure, amount, dict):
    cur = conn.cursor()
    cur.execute(update_bid_role,(measure,amount,user_id))
    cur.execute(update_bid_measure,(user_id,amount,dict[measure]))
    conn.commit()
    with st.spinner('Registering your bid'):
        time.sleep(3)
    st.success('You bid on ' + measure + ' successfully')
    time.sleep(2)
    st.experimental_rerun()


st.header('Biding on features')
col1_f, col2_f, col3_f = st.columns(3)

with col1_f:
    mit_type = st.radio(label='Type of mitigation', options=['Structural','Social'])
    if mit_type=='Structural':
        bid_measure = st.selectbox(label='Measures',options=measure_dict_structural.keys())
        main_n = measure_dict_structural
    else:
        bid_measure = st.selectbox(label='Measures',options=measure_dict_social.keys())
        main_n = measure_dict_social
with col2_f:
    if int(df_m.loc[all_measures[bid_measure],'cost']) != 0:
        st.metric(label='Cost of '+bid_measure,value=int(df_m.loc[all_measures[bid_measure],'cost']))
        bid_amount = st.number_input(value=1,label='how much you would like to bid?',min_value=1)
    else:
        st.markdown('### The cost is covered by taxes')
  
with col3_f:
    st.metric(label='Your budget if bid sucessful', value=int(df.loc[user_id,'cb']-bid_amount),delta=-bid_amount)
    make_bid = st.button("Make the bid")

if make_bid:
    make_bid_func(bid_measure,bid_amount,all_measures)

st.subheader('Measures suggested')
for measure in all_measures.keys():
    if measure in df['r1_measure'].to_list():


        col1, col2 = st.columns([1,3])
        with col1:
            st.metric(label=measure,value=str(sum([int(i) for i in df[df['r1_measure'] == measure]['r1_bid'].to_list()]))+r"/"+str(df_m.loc[all_measures[measure],'cost']))
        with col2:
            biders = list(df[df['r1_measure'] == measure].index)
            amounts = df[df['r1_measure'] == measure]['r1_bid'].to_list()
            st.caption('Biders: ' + ',  '.join([user_dict[p] + ': $'+ str(b)  for p,b in zip(biders,amounts)]))
            st.progress(int(sum([int(i) for i in df[df['r1_measure'] == measure]['r1_bid'].to_list()])/df_m.loc[all_measures[measure],'cost']*100))

update_budget = ("UPDATE frcbudget1 SET cb = %s WHERE role=%s;")
update_delta =  ("UPDATE frcbudget1 SET delta = %s WHERE role=%s;")

def money_transfer(amount,r_party):
    curA = conn.cursor()
    curA.execute(update_budget,(int(df.loc[user_id,'cb'])-amount,user_id))
    curA.execute(update_delta,(-amount,user_id))
    curA.execute(update_budget,(int(df.loc[user_dict_inv[r_party],'cb']+amount),user_dict_inv[r_party]))
    curA.execute(update_delta,(+amount,user_dict_inv[r_party]))
    conn.commit()


st.subheader("Money Transfer")
col1 , col2, col3, col4 = st.columns(4)
with col1:
    t_amount = st.number_input(value=0, label='Budget to transfer',min_value=0)
with col2:
    party = st.selectbox(options=[user_dict[x] for x in other_roles], label='Stakeholder receiving')
with col4:
    transfer = st.button(label='Complete transaction',help='Only click when you are absolutely sure')
with col3:
    st.metric(label='Budget after transaction',value='$'+str(df.loc[user_id,'cb']-t_amount),delta=-t_amount)

if transfer:
    money_transfer(t_amount,party)
    with st.spinner('Performing transaction'):
        time.sleep(3)
    st.success('The transaction to ' + party + ' was successful')
    time.sleep(3)
    st.experimental_rerun()

    



