import pandas as pd
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
import streamlit as st

from utils import db_query_climatetrace_locode

with st.sidebar:
    st.header("Query ClimateTRACE by locode and sector")
    locode = st.text_input("Locode", value="US NYC")
    sector = st.text_input("Sector", value="II")

with st.container():
    database_uri = "postgresql://ccglobal:@localhost/ccglobal"
    engine = create_engine(database_uri)
    metadata_obj = MetaData()
    Session = sessionmaker(bind=engine)

    with Session() as session:
        records = db_query_climatetrace_locode(session, locode, sector)

    df = (pd.DataFrame(records)
          .rename(columns={0: "locode", 1: "year", 2: "reference_number"})
          )

    st.dataframe(df)