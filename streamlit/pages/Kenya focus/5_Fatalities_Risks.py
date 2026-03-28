import streamlit as st
import duckdb
import plotly.express as px

st.title("Fatalities & Civil Liberties Risks in Kenya")

con = duckdb.connect(database=':memory:')
con.execute("ATTACH 'data/civil_liberties_mart.parquet' AS mart;")
df = con.execute("SELECT * FROM mart.civil_liberties WHERE UPPER(country)='KENYA'").df()

fig = px.bar(df, x="period", y="fatalities", title="Fatalities in Kenya")
st.plotly_chart(fig, use_container_width=True)

fig2 = px.line(df, x="period", y="takedown_requests", title="Takedown Requests Over Time")
st.plotly_chart(fig2, use_container_width=True)
elif choice == "Fatalities & Risks":
    st.subheader("Fatalities & Risks")

    kenya_df = df[df['country'].str.upper() == 'KENYA']
    global_df = df.groupby("period").agg({"fatalities":"sum"}).reset_index()

    col1, col2 = st.columns(2)
    with col1:
        fig_kenya = px.bar(kenya_df, x="period", y="fatalities", title="Fatalities in Kenya")
        st.plotly_chart(fig_kenya, use_container_width=True)
    with col2:
        fig_global = px.bar(global_df, x="period", y="fatalities", title="Global Fatalities")
        st.plotly_chart(fig_global, use_container_width=True)

    st.subheader("Kenya vs Global Comparison")
    combined = pd.DataFrame({
        "Period": global_df["period"],
        "Global Fatalities": global_df["fatalities"],
        "Kenya Fatalities": kenya_df.groupby("period")["fatalities"].sum().reindex(global_df["period"]).fillna(0).values
    })
    fig_compare = px.bar(combined.melt(id_vars="Period", value_vars=["Global Fatalities","Kenya Fatalities"]),
                         x="Period", y="value", color="variable", barmode="group",
                         title="Kenya vs Global Fatalities")
    st.plotly_chart(fig_compare, use_container_width=True)
