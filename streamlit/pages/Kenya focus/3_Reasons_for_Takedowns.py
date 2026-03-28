import streamlit as st
import duckdb
import plotly.express as px

st.title("Reasons for Takedowns: Kenya vs World")

con = duckdb.connect(database=':memory:')
con.execute("ATTACH 'data/civil_liberties_mart.parquet' AS mart;")
df = con.execute("SELECT * FROM mart.civil_liberties").df()

kenya = df[df['country'].str.upper() == 'KENYA']
global_df = df.groupby("reason").agg({"takedown_requests":"sum"}).reset_index()

fig_kenya = px.pie(kenya, names="reason", values="takedown_requests", title="Kenya Reasons")
st.plotly_chart(fig_kenya, use_container_width=True)

fig_global = px.pie(global_df, names="reason", values="takedown_requests", title="Global Reasons")
st.plotly_chart(fig_global, use_container_width=True)
elif choice == "Reasons for Takedowns":
    st.subheader("Reasons for Takedowns")

    kenya_df = df[df['country'].str.upper() == 'KENYA']
    global_df = df.groupby("reason").agg({"takedown_requests":"sum"}).reset_index()

    col1, col2 = st.columns(2)
    with col1:
        fig_kenya = px.pie(kenya_df, names="reason", values="takedown_requests", title="Kenya Reasons")
        st.plotly_chart(fig_kenya, use_container_width=True)
    with col2:
        fig_global = px.pie(global_df, names="reason", values="takedown_requests", title="Global Reasons")
        st.plotly_chart(fig_global, use_container_width=True)

    st.subheader("Kenya vs Global Comparison")
    combined = pd.DataFrame({
        "Reason": global_df["reason"],
        "Global Requests": global_df["takedown_requests"],
        "Kenya Requests": kenya_df.groupby("reason")["takedown_requests"].sum().reindex(global_df["reason"]).fillna(0).values
    })
    fig_compare = px.bar(combined.melt(id_vars="Reason", value_vars=["Global Requests","Kenya Requests"]),
                         x="Reason", y="value", color="variable", barmode="group",
                         title="Kenya vs Global Reasons")
    st.plotly_chart(fig_compare, use_container_width=True)
