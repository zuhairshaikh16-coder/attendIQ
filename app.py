import streamlit as st
import pandas as pd
import plotly.express as px
from database import init_db, get_connection, add_student, delete_student, save_attendance, save_assessment, get_students, get_attendance, get_assessments, attendance_summary, performance_summary
from datetime import date, timedelta

st.set_page_config(page_title="AttendIQ | Student Insights", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
init_db()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: Inter, sans-serif; }
.block-container {padding-top: 1.7rem; padding-bottom: 2rem; max-width: 1500px;}
[data-testid="stSidebar"] {border-right: 1px solid rgba(120,130,150,.18);}
.hero {padding: 1.35rem 1.5rem; border-radius: 18px; background: linear-gradient(120deg,#172554,#1d4ed8 68%,#0ea5e9); color:white; margin-bottom:1.2rem;}
.hero h1 {font-size:2rem; margin:0; color:white;} .hero p {margin:.35rem 0 0 0; opacity:.88;}
.metric-card {padding:1rem 1.1rem; border:1px solid rgba(120,130,150,.22); border-radius:16px; background:var(--secondary-background-color); min-height:112px;}
.metric-label {font-size:.82rem; color:var(--text-color); opacity:.7;} .metric-value {font-size:1.85rem; font-weight:800; margin-top:.2rem;}
.small-note {font-size:.82rem; opacity:.7;}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 📊 AttendIQ")
    st.caption("Attendance & Performance Analyzer")
    page = st.radio("WORKSPACE", ["Overview", "Students", "Attendance", "Assessments", "Reports", "Data tools"], label_visibility="visible")
    st.divider()
    st.caption("A lightweight, local-first school analytics tool.")
    st.caption("Data is stored in `attendiq.db`.")

def metric(label, value, note=""):
    st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="small-note">{note}</div></div>', unsafe_allow_html=True)

def students_df():
    rows = get_students()
    return pd.DataFrame(rows, columns=["id","student_code","full_name","class_name","email","created_at"]) if rows else pd.DataFrame(columns=["id","student_code","full_name","class_name","email","created_at"])

st.markdown('<div class="hero"><h1>AttendIQ</h1><p>Understand attendance. Track performance. Support every student.</p></div>', unsafe_allow_html=True)

if page == "Overview":
    sdf = students_df()
    att = attendance_summary()
    perf = performance_summary()
    total_students = len(sdf)
    avg_att = round(att["attendance_rate"].mean(),1) if not att.empty else 0
    avg_perf = round(perf["average_percent"].mean(),1) if not perf.empty else 0
    at_risk = int(((att["attendance_rate"] < 75) if not att.empty else pd.Series(dtype=bool)).sum())
    c = st.columns(4)
    with c[0]: metric("Total students", total_students, "Registered learners")
    with c[1]: metric("Average attendance", f"{avg_att}%", "Present + late / marked sessions")
    with c[2]: metric("Average performance", f"{avg_perf}%", "Across recorded assessments")
    with c[3]: metric("Attendance alerts", at_risk, "Below 75% attendance")
    st.write("")
    left, right = st.columns([1.2,1])
    with left:
        st.subheader("Attendance by student")
        if not att.empty:
            fig = px.bar(att.sort_values("attendance_rate"), x="attendance_rate", y="full_name", color="attendance_rate", orientation="h", range_color=[0,100], range_x=[0,100], labels={"attendance_rate":"Attendance (%)","full_name":"Student"}, color_continuous_scale="Blues")
            fig.update_layout(height=420, margin=dict(l=10,r=10,t=20,b=10), coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("Mark attendance to see student attendance analytics.")
    with right:
        st.subheader("Performance distribution")
        if not perf.empty:
            fig = px.histogram(perf, x="average_percent", nbins=10, labels={"average_percent":"Average score (%)"}, color_discrete_sequence=["#2563eb"])
            fig.update_layout(height=420, margin=dict(l=10,r=10,t=20,b=10), xaxis_range=[0,100])
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("Record assessments to see performance analytics.")
    st.subheader("Students who may need support")
    if not att.empty:
        risk = att[att["attendance_rate"] < 75][["student_code","full_name","class_name","attendance_rate","sessions"]]
        if not perf.empty:
            risk = risk.merge(perf[["student_code","average_percent"]], on="student_code", how="left")
        if risk.empty: st.success("No students are currently below the 75% attendance threshold.")
        else: st.dataframe(risk.rename(columns={"student_code":"Student ID","full_name":"Name","class_name":"Class","attendance_rate":"Attendance %","sessions":"Marked sessions","average_percent":"Average score %"}), use_container_width=True, hide_index=True)
    else: st.caption("Risk alerts appear after attendance is recorded.")

elif page == "Students":
    st.subheader("Student management")
    st.caption("Create and maintain your student register. Student IDs must be unique.")
    with st.expander("＋ Add a student", expanded=not bool(len(students_df()))):
        with st.form("add_student", clear_on_submit=True):
            a,b = st.columns(2)
            code = a.text_input("Student ID *", placeholder="e.g. STU-001")
            name = b.text_input("Full name *", placeholder="Student full name")
            c,d = st.columns(2)
            class_name = c.text_input("Class / group", placeholder="e.g. Grade 10-A")
            email = d.text_input("Email (optional)")
            submitted = st.form_submit_button("Add student", type="primary")
            if submitted:
                if not code.strip() or not name.strip(): st.error("Student ID and full name are required.")
                else:
                    try:
                        add_student(code.strip(), name.strip(), class_name.strip(), email.strip())
                        st.success(f"Added {name.strip()}.")
                        st.rerun()
                    except Exception as e: st.error("Could not add student. Check that the Student ID is unique.")
    df = students_df()
    if not df.empty:
        search = st.text_input("Search by ID, name, or class")
        if search:
            df = df[df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)]
        st.dataframe(df[["student_code","full_name","class_name","email","created_at"]].rename(columns={"student_code":"Student ID","full_name":"Name","class_name":"Class","email":"Email","created_at":"Added"}), use_container_width=True, hide_index=True)
        with st.expander("Delete a student"):
            st.warning("Deleting a student also deletes their attendance and assessment records.")
            choices = {f'{r.student_code} — {r.full_name}': int(r.id) for r in df.itertuples()}
            selected = st.selectbox("Choose student", list(choices))
            confirm = st.checkbox("I understand this permanently deletes this student's records.")
            if st.button("Delete selected student", disabled=not confirm):
                delete_student(choices[selected]); st.success("Student and related records deleted."); st.rerun()
    else: st.info("No students yet. Add your first student above.")

elif page == "Attendance":
    st.subheader("Attendance register")
    sdf = students_df()
    if sdf.empty: st.info("Add students first in Student management."); st.stop()
    a,b = st.columns([1,2])
    with a: selected_date = st.date_input("Attendance date", value=date.today())
    with b:
        class_options = ["All classes"] + sorted([x for x in sdf["class_name"].dropna().unique().tolist() if x])
        selected_class = st.selectbox("Filter class", class_options)
    filtered = sdf if selected_class == "All classes" else sdf[sdf["class_name"] == selected_class]
    existing = get_attendance(selected_date.isoformat())
    existing_map = {int(r["student_id"]): r["status"] for r in existing}
    with st.form("attendance_form"):
        st.caption(f"Set the status for {len(filtered)} student(s). Saving updates records for {selected_date.isoformat()}.")
        entries = {}
        for r in filtered.itertuples():
            status_options = ["Present","Absent","Late","Excused"]
            current = existing_map.get(int(r.id), "Present")
            entries[int(r.id)] = st.selectbox(f"{r.student_code} · {r.full_name}", status_options, index=status_options.index(current), key=f"att_{selected_date}_{r.id}")
        save = st.form_submit_button("Save attendance", type="primary")
        if save:
            save_attendance(selected_date.isoformat(), entries)
            st.success("Attendance saved successfully.")
            st.rerun()
    st.divider()
    st.subheader("Saved attendance for selected date")
    if existing:
        edf = pd.DataFrame(existing)
        st.dataframe(edf[["student_code","full_name","class_name","status"]].rename(columns={"student_code":"Student ID","full_name":"Name","class_name":"Class","status":"Status"}), use_container_width=True, hide_index=True)
    else: st.caption("No attendance has been saved for this date yet.")

elif page == "Assessments":
    st.subheader("Assessment results")
    sdf = students_df()
    if sdf.empty: st.info("Add students first in Student management."); st.stop()
    with st.form("assessment_form", clear_on_submit=True):
        a,b = st.columns(2)
        student_options = {f"{r.student_code} — {r.full_name}": int(r.id) for r in sdf.itertuples()}
        selected_student = st.selectbox("Student", list(student_options))
        title = b.text_input("Assessment title *", placeholder="e.g. Mathematics Test 1")
        c,d,e = st.columns(3)
        score = c.number_input("Marks obtained", min_value=0.0, value=0.0, step=1.0)
        maximum = d.number_input("Maximum marks", min_value=1.0, value=100.0, step=1.0)
        assessment_date = e.date_input("Assessment date", value=date.today())
        notes = st.text_input("Notes (optional)")
        save = st.form_submit_button("Save result", type="primary")
        if save:
            if not title.strip(): st.error("Assessment title is required.")
            elif score > maximum: st.error("Marks obtained cannot exceed maximum marks.")
            else:
                save_assessment(student_options[selected_student], title.strip(), score, maximum, assessment_date.isoformat(), notes.strip())
                st.success("Assessment saved.")
                st.rerun()
    records = get_assessments()
    if records:
        df = pd.DataFrame(records)
        df["score_percent"] = (df["score"] / df["max_score"] * 100).round(1)
        st.subheader("Recorded results")
        st.dataframe(df[["student_code","full_name","class_name","title","score","max_score","score_percent","assessment_date","notes"]].rename(columns={"student_code":"Student ID","full_name":"Student","class_name":"Class","title":"Assessment","score":"Marks","max_score":"Out of","score_percent":"Score %","assessment_date":"Date","notes":"Notes"}), use_container_width=True, hide_index=True)
        st.download_button("Download assessment CSV", df.to_csv(index=False).encode("utf-8"), "attendiq_assessments.csv", "text/csv")
    else: st.info("No assessment results recorded yet.")

elif page == "Reports":
    st.subheader("Reports & exports")
    sdf = students_df()
    if sdf.empty: st.info("Add students to generate reports."); st.stop()
    att = attendance_summary()
    perf = performance_summary()
    report = sdf[["student_code","full_name","class_name","email"]].copy()
    if not att.empty: report = report.merge(att[["student_code","attendance_rate","sessions","present_count","absent_count"]], on="student_code", how="left")
    if not perf.empty: report = report.merge(perf[["student_code","average_percent","assessments"]], on="student_code", how="left")
    for col in ["attendance_rate","average_percent"]: 
        if col not in report: report[col] = pd.NA
    report = report.rename(columns={"student_code":"Student ID","full_name":"Student","class_name":"Class","email":"Email","attendance_rate":"Attendance %","sessions":"Marked sessions","present_count":"Present/late","absent_count":"Absent","average_percent":"Average score %","assessments":"Assessments"})
    st.write("Use the report to review attendance and academic performance together.")
    class_list = ["All classes"] + sorted([x for x in report["Class"].dropna().unique().tolist() if x])
    selected = st.selectbox("Class", class_list)
    if selected != "All classes": report = report[report["Class"] == selected]
    st.dataframe(report, use_container_width=True, hide_index=True)
    st.download_button("⬇ Download report as CSV", report.to_csv(index=False).encode("utf-8-sig"), "attendiq_student_report.csv", "text/csv", type="primary")
    st.caption("CSV files open in Excel, LibreOffice, and Google Sheets.")

elif page == "Data tools":
    st.subheader("Data tools & backup")
    st.write("Download your records for backup or move them into another spreadsheet.")
    sdf = students_df()
    att = get_attendance()
    assessments = get_assessments()
    a,b,c = st.columns(3)
    with a:
        st.metric("Students", len(sdf))
        st.download_button("Export students CSV", sdf.to_csv(index=False).encode("utf-8-sig"), "attendiq_students.csv", "text/csv")
    with b:
        st.metric("Attendance records", len(att))
        adf = pd.DataFrame(att)
        st.download_button("Export attendance CSV", adf.to_csv(index=False).encode("utf-8-sig") if not adf.empty else b"", "attendiq_attendance.csv", "text/csv", disabled=adf.empty)
    with c:
        st.metric("Assessment records", len(assessments))
        pdf = pd.DataFrame(assessments)
        st.download_button("Export assessments CSV", pdf.to_csv(index=False).encode("utf-8-sig") if not pdf.empty else b"", "attendiq_assessments.csv", "text/csv", disabled=pdf.empty)
    st.divider()
    st.subheader("Attendance rules")
    st.markdown("- **Present** and **Late** count toward attendance.\n- **Absent** counts against attendance.\n- **Excused** is excluded from the attendance percentage denominator.\n- Attendance alert threshold: **below 75%**.\n- Assessment percentage = marks obtained ÷ maximum marks × 100.")
    st.info("For a multi-user or public deployment, add authentication, backups, and a production database before storing sensitive student data.")
