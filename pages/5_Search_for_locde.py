import pandas as pd
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
import streamlit as st

from utils import db_query_city_name

with st.sidebar:
    st.header("Search for locode by city")
    city_name = st.text_input("city name", value="new york")

    st.markdown("---")

    st.subheader("What is the query?")
    st.markdown("When a `city_name` is entered, the following query is executed:")
    st.code("""
            SELECT locode, name, display_name FROM osm
            WHERE name ILIKE '%:city_name%' """)


with st.container():
    database_uri = "postgresql://ccglobal:@localhost/ccglobal"
    engine = create_engine(database_uri)
    metadata_obj = MetaData()
    Session = sessionmaker(bind=engine)

    with Session() as session:
        records = db_query_city_name(session, city_name)

    df = (pd.DataFrame(records)
          .rename(columns={0: "locode", 1: "name", 2: "display_name"})
          )

    st.dataframe(df)