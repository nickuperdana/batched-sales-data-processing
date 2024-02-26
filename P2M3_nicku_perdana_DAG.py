'''
=================================================

Phase 2 - Milestone 3

Nama  : Nicku R. Perdana
Batch : HCK-012

This program automates the data engineering process for an online dataset, connecting it to a server via Postgres, and pooling and visualizing it using Airflow, Elasticsearch, and Kibana. 
The program executes a sequence of tasks, starting with fetching data from a Postgres database server. It then preprocesses the data using Airflow before sending it to an Elasticsearch server running in a Docker Container.

=================================================
'''

from airflow.models import DAG # working with DAGs
from airflow.operators.python import PythonOperator # working with airflow using some python operators
# from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta # working with timing
from sqlalchemy import create_engine # connect script to postgres
import pandas as pd # working with dataset

from elasticsearch import Elasticsearch # working with ElasticSearch

def fetch_data():
    '''
    This function is intended to fetch data by doing a query to the PostgreS database and then save it directly to a csv that will be mirrored locally to the dags folder 
    INPUT: database name, username, password, and host platform (arbitrary input within function)
    OUTPUT: Raw CSV file
    Steps:
    - establish connection to PostgreS database
    - run a select all query to a specified table
    - save the query output into a csv as an output of this job/function
    '''    
    # fetch data
    database = "milestone_3" # database name created in PostgreS that connected to PostgreS docker image synced via .env
    username = "milestone_3" # username/role created through .venv to access the PostgreS database
    password = "milestone_3" # password for username/role created through .venv to access the PostgreS database
    host = "postgres" # platform used

    # Membuat URL koneksi PostgreSQL
    postgres_url = f"postgresql+psycopg2://{username}:{password}@{host}/{database}" # connect to PostgreS query tool using this address

    # establish SQLAlchemy connection to PostgreS image in docker
    engine = create_engine(postgres_url)
    conn = engine.connect()
    
    # run SQL query of SELECT * FROM table_m3 in database=milestone_3, to PostgreS
    df = pd.read_sql_query("select * from table_m3", conn) 
    df.to_csv('/opt/airflow/dags/P2M3_nicku_perdana_data_new.csv', sep=',', index=False) # save the query result to a csv
     
def preprocessing(): 
    '''
    This function is created to perform a serial of automated process to the fetched CSV file
    INPUT: Raw CSV file (arbitrary input within function)
    OUTPUT: Clean CSV file
    Steps:
    - read the raw data fetched from PostgreS
    - Drop duplicate data
    - Drop records of data that contains null value in any columns
    - Standardize column name to a snake case format
    - manipulate any column's data type
    '''
    # read raw CSV file
    data = pd.read_csv("/opt/airflow/dags/P2M3_nicku_perdana_data_new.csv")
    
    # clean null data
    data.dropna(inplace=True)
    # clean duplicated data
    data.drop_duplicates(inplace=True)
    # format column name to a snake case form
    newSnakeCaseCols = []
    for column in data.columns:
        newSnakeCaseCols.append(column.strip().lower().replace(' ', '_').replace('-', '_')) 
        # strip=delete unnecessary white spaces; lower=make every words in lowercase style; replace=replace spaces and strips as underscore
    data = data.rename(columns=dict(zip(data.columns.to_list(), newSnakeCaseCols)))
    # format data in 'order_date' as datetime
    data['order_date'] = pd.to_datetime(data['order_date'], format='%d-%m-%y')
    # save cleaned data as an output to this function
    data.to_csv('/opt/airflow/dags/P2M3_nicku_perdana_data_clean.csv', index=False)
        
def upload_to_elasticsearch():
    '''
    This function will connect to the Elasticsearch server and upload every given data records
    INPUT: ElasticSearch host with its port number (arbitrary input within function), Clean CSV file (arbitrary input within function)
    OUTPUT: Respone from ElasticSearch
    '''
    es = Elasticsearch("http://elasticsearch:9200")
    df = pd.read_csv('/opt/airflow/dags/P2M3_nicku_perdana_data_clean.csv', parse_dates=['order_date'])
    
    for i, r in df.iterrows():
        doc = r.to_dict()  # Convert the row to a dictionary
        res = es.index(index="table_m3", id=i+1, body=doc)
        print(f"Response from Elasticsearch: {res}")
                 
# set a default arguments for working with DAG
default_args = {
    'owner': 'Nicku RP', # define the owner of DAG that will be shown in airflow webserver UI
    'start_date': datetime(2024, 2, 22, 12, 00) - timedelta(hours=7) # define the initial run time; future=will be run in the future; past=will run immediately after or without trigger (see DAG.catchup)
}

with DAG(
    "P2M3_Nicku_DAG_hck", # the DAG name
    description='Airflow for Milestone_3', # the DAG description
    schedule_interval='30 6 * * *', # set an update interval time that will automatically rerun the DAG every 6.30 (using format Cronguru)
    default_args=default_args, # insert the defined default_args
    catchup=False # when default_arg's start date is set in the past, it will not immediately run unless is triggered manually
) as dag:
    
    # entering airflow realm
    # task number 2: fetch data from PostgreS
    fetch_data_postgres = PythonOperator(
        task_id='fetch_data_postgres',
        python_callable=fetch_data) # run `fetch_data` function using python interpretor function
    
    # Task number 3: clean data from fetched data
    edit_data = PythonOperator(
        task_id='edit_data',
        python_callable=preprocessing) # run `preprocessing` function using python interpretor function

    # Task number 4: upload clean data to Elasticsearch webserver
    upload_data = PythonOperator(
        task_id='upload_data_elastic',
        python_callable=upload_to_elasticsearch) # run `upload_to_elasticsearch` function using python interpretor function

    # create task flow for airflow
    fetch_data_postgres >> edit_data >> upload_data