# -------------------- Shortlist Dashboard --------------------
if menu == "Shortlist Dashboard":
    st.header("Placement Team Dashboard")
    st.subheader("Resume Shortlisting Table")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT e.id, j.title, e.resume_name, e.score, e.verdict, e.missing 
            FROM evaluations e 
            JOIN jds j ON e.jd_id = j.id
        """)
        evals = cur.fetchall()
    except sqlite3.OperationalError:
        evals = []
    conn.close()

    if not evals:
        st.info("No evaluations yet.")
    else:
        df = pd.DataFrame(evals, columns=["ID","JD Title","Resume","Score","Verdict","Missing"])
        df[['Job Title','Company','Location']] = df['JD Title'].str.split('|', expand=True)
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        # ===== Filters (Top Bar) =====
        col1, col2, col3 = st.columns(3)
        with col1:
            role_filter = st.selectbox("Filter by Role", options=["All"] + sorted(df['Job Title'].unique().tolist()))
        with col2:
            loc_filter = st.selectbox("Filter by Location", options=["All"] + sorted(df['Location'].unique().tolist()))
        with col3:
            shortlist_filter = st.selectbox("Shortlisted Only?", options=["All", "YES", "NO"])

        # Apply filters
        df['Shortlisted'] = df['Verdict'].apply(lambda v: "YES" if v in ["High","Medium"] else "NO")
        if role_filter != "All":
            df = df[df['Job Title'] == role_filter]
        if loc_filter != "All":
            df = df[df['Location'] == loc_filter]
        if shortlist_filter != "All":
            df = df[df['Shortlisted'] == shortlist_filter]

        # ===== Display Table =====
        st.dataframe(
            df[['Resume','Job Title','Company','Location','Score','Verdict','Shortlisted','Missing']],
            use_container_width=True
        )
