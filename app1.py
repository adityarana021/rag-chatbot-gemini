import streamlit as  st
import pandas as pd
import numpy as np

st.title("Hello Guy's")

df=pd.DataFrame({"First":[1,2,3,4,5],
                 "Second":["A","B","C","D","E"]})

st.write("Here is the dataframe")
st.write(df)

df1=pd.DataFrame(np.random.randn(20,3),columns=["X","Y","Z"])

st.text_input("Enter input here....")

uploded_file=st.file_uploader("choose a csv file",type="csv")
st.write(uploded_file)

st.line_chart(df1)



if uploded_file is not None:
    df2=pd.read_clipboard(uploded_file)
    st.write(df2)