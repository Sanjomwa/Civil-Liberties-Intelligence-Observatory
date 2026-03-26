import streamlit as st
import duckdb
import plotly.graph_objects as go

st.title("Conflict vs Censorship Trends in Kenya")

con = duckdb.connect(database=':memory:')
con.execute("ATTACH 'data/civil_liberties_mart.parquet' AS mart;")
df = con.execute("SELECT * FROM mart.civil_liberties WHERE UPPER(country)='KENYA'").df()

fig = go.Figure()
fig.add_trace(go.Scatter(x=df['period'], y=df['conflict_events'], name="Conflict Events", mode="lines"))
fig.add_trace(go.Scatter(x=df['period'], y=df['censorship_tests'], name="Censorship Tests", mode="lines", yaxis="y2"))

fig.update_layout(
    title="Conflict vs Censorship in Kenya",
    yaxis=dict(title="Conflict Events"),
    yaxis2=dict(title="Censorship Tests", overlaying="y", side="right")
)
st.plotly_chart(fig, use_container_width=True)
elif choice == "Conflict vs Censorship":
    st.subheader("Conflict vs Censorship Trends")

    kenya_df = df[df['country'].str.upper() == 'KENYA']
    global_df = df.groupby("period").agg({"conflict_events":"sum","censorship_tests":"sum"}).reset_index()

    col1, col2 = st.columns(2)
    with col1:
        fig_kenya = px.line(kenya_df, x="period", y=["conflict_events","censorship_tests"],
                            title="Kenya Conflict vs Censorship")
        st.plotly_chart(fig_kenya, use_container_width=True)
    with col2:
        fig_global = px.line(global_df, x="period", y=["conflict_events","censorship_tests"],
                             title="Global Conflict vs Censorship")
        st.plotly_chart(fig_global, use_container_width=True)

    st.subheader("Kenya vs Global Comparison")
    combined = pd.DataFrame({
        "Period": global_df["period"],
        "Global Conflict": global_df["conflict_events"],
        "Kenya Conflict": kenya_df.groupby("period")["conflict_events"].sum().reindex(global_df["period"]).fillna(0).values,
        "Global Censorship": global_df["censorship_tests"],
        "Kenya Censorship": kenya_df.groupby("period")["censorship_tests"].sum().reindex(global_df["period"]).fillna(0).values
    })
    fig_compare = px.line(combined, x="Period", y=["Global Conflict","Kenya Conflict","Global Censorship","Kenya Censorship"],
                          title="Kenya vs Global Conflict & Censorship")
    st.plotly_chart(fig_compare, use_container_width=True)

