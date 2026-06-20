import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px

st.set_page_config(
    page_title="AI Project Orchestrator",
    layout="wide"
)

st.title("AI Project Orchestrator")
st.caption("Predict timelines, recommend owners, and simulate project delivery scenarios using dummy data.")

# -----------------------------
# Load Data
# -----------------------------
# -----------------------------
# File Upload Section
# -----------------------------
# -----------------------------
# File Upload Section
# -----------------------------
st.sidebar.header("Upload Project Data")

uploaded_tasks_file = st.sidebar.file_uploader(
    "Upload Project Tasks File",
    type=["csv", "xlsx"],
    help="Upload a project task tracker with planned dates, owners, status, blockers, and dependencies.",
    key="project_tasks_uploader"
)

uploaded_team_file = st.sidebar.file_uploader(
    "Upload Team Capacity File",
    type=["csv", "xlsx"],
    help="Upload team capacity, skills, workload, and availability data.",
    key="team_capacity_uploader"
)

def read_uploaded_file(uploaded_file, default_csv_path):
    """
    Reads uploaded CSV/XLSX file.
    If no file is uploaded, falls back to default dummy CSV.
    """
    if uploaded_file is not None:
        file_name = uploaded_file.name.lower()

        if file_name.endswith(".csv"):
            return pd.read_csv(uploaded_file)

        elif file_name.endswith(".xlsx"):
            return pd.read_excel(uploaded_file)

        else:
            st.error("Unsupported file type. Please upload CSV or Excel file.")
            st.stop()

    return pd.read_csv(default_csv_path)


def validate_columns(df, required_columns, file_label):
    """
    Validates required columns for uploaded files.
    """
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        st.error(
            f"{file_label} is missing required columns: {', '.join(missing_columns)}"
        )
        st.stop()


# -----------------------------
# Required Columns
# -----------------------------
required_task_columns = [
    "Task_ID",
    "Workstream",
    "Task_Name",
    "Planned_Start",
    "Planned_End",
    "Current_Owner",
    "Skill_Required",
    "Complexity",
    "Effort_Days",
    "Progress_Percent",
    "Status",
    "Dependency_Type",
    "Blocker_Flag",
    "Priority"
]

required_team_columns = [
    "Owner",
    "Primary_Skill",
    "Secondary_Skill",
    "Capacity_Percent",
    "Current_Load",
    "Availability",
    "Location"
]


# -----------------------------
# Load Data
# -----------------------------
tasks = read_uploaded_file(uploaded_tasks_file, "project_tasks.csv")
team = read_uploaded_file(uploaded_team_file, "team_capacity.csv")

validate_columns(tasks, required_task_columns, "Project Tasks File")
validate_columns(team, required_team_columns, "Team Capacity File")

# Convert date columns
tasks["Planned_Start"] = pd.to_datetime(tasks["Planned_Start"], errors="coerce")
tasks["Planned_End"] = pd.to_datetime(tasks["Planned_End"], errors="coerce")

# Validate date conversion
if tasks["Planned_Start"].isna().any() or tasks["Planned_End"].isna().any():
    st.error("Planned_Start or Planned_End contains invalid date values. Use format YYYY-MM-DD.")
    st.stop()

# Clean numeric columns
tasks["Effort_Days"] = pd.to_numeric(tasks["Effort_Days"], errors="coerce").fillna(0)
tasks["Progress_Percent"] = pd.to_numeric(tasks["Progress_Percent"], errors="coerce").fillna(0)
team["Capacity_Percent"] = pd.to_numeric(team["Capacity_Percent"], errors="coerce").fillna(0)
team["Current_Load"] = pd.to_numeric(team["Current_Load"], errors="coerce").fillna(0)

st.sidebar.success("Data loaded successfully")

# -----------------------------
# Data Preview
# -----------------------------
with st.expander("Preview Uploaded / Default Project Tasks"):
    st.dataframe(tasks, use_container_width=True)

with st.expander("Preview Uploaded / Default Team Capacity"):
    st.dataframe(team, use_container_width=True)

# -----------------------------
# Sidebar Scenario Controls
# -----------------------------
st.sidebar.header("Scenario Simulator")

vendor_delay_days = st.sidebar.slider(
    "Vendor dependency delay days",
    min_value=0,
    max_value=20,
    value=5
)

scope_increase_percent = st.sidebar.slider(
    "Scope increase %",
    min_value=0,
    max_value=50,
    value=10
)

resource_capacity_reduction = st.sidebar.slider(
    "Resource capacity reduction %",
    min_value=0,
    max_value=50,
    value=10
)

testing_compression = st.sidebar.slider(
    "Testing compression %",
    min_value=0,
    max_value=30,
    value=0
)# -----------------------------
# AI-style Timeline Prediction
# -----------------------------
def calculate_delay(row):
    delay = 0

    if row["Status"] == "Delayed":
        delay += 5
    elif row["Status"] == "Not Started":
        today = pd.Timestamp.today().normalize()
        if today > row["Planned_Start"]:
            delay += 3

    if row["Blocker_Flag"] == "Yes":
        delay += 5

    if row["Complexity"] == "High":
        delay += 4
    elif row["Complexity"] == "Medium":
        delay += 2

    if row["Progress_Percent"] < 30:
        delay += 3
    elif row["Progress_Percent"] < 60:
        delay += 2

    if row["Dependency_Type"] == "Vendor":
        delay += vendor_delay_days
    elif row["Dependency_Type"] == "Business":
        delay += 2

    delay += int(row["Effort_Days"] * scope_increase_percent / 100)

    if row["Workstream"] == "UAT":
        delay -= int(row["Effort_Days"] * testing_compression / 100)

    return max(delay, 0)

tasks["Predicted_Delay_Days"] = tasks.apply(calculate_delay, axis=1)
tasks["Predicted_End"] = tasks["Planned_End"] + pd.to_timedelta(tasks["Predicted_Delay_Days"], unit="D")

# -----------------------------
# Risk Classification
# -----------------------------
def risk_level(delay):
    if delay >= 10:
        return "Red"
    elif delay >= 5:
        return "Amber"
    else:
        return "Green"

tasks["Risk_Level"] = tasks["Predicted_Delay_Days"].apply(risk_level)

# -----------------------------
# Owner Recommendation
# -----------------------------
def recommend_owner(task_row, team_df):
    skill = task_row["Skill_Required"]

    matching_team = team_df[
        (team_df["Primary_Skill"] == skill) |
        (team_df["Secondary_Skill"] == skill)
    ].copy()

    if matching_team.empty:
        return task_row["Current_Owner"], "No better match found"

    matching_team["Adjusted_Load"] = matching_team["Current_Load"] + resource_capacity_reduction
    matching_team = matching_team.sort_values(by=["Adjusted_Load", "Capacity_Percent"], ascending=[True, False])

    recommended = matching_team.iloc[0]

    reason = (
        f"Best skill match for {skill}, current load {recommended['Current_Load']}%, "
        f"capacity {recommended['Capacity_Percent']}%, availability {recommended['Availability']}."
    )

    return recommended["Owner"], reason

recommendations = tasks.apply(
    lambda row: recommend_owner(row, team),
    axis=1
)

tasks["Recommended_Owner"] = [r[0] for r in recommendations]
tasks["Owner_Recommendation_Reason"] = [r[1] for r in recommendations]

# -----------------------------
# Executive Metrics
# -----------------------------
planned_finish = tasks["Planned_End"].max()
predicted_finish = tasks["Predicted_End"].max()
forecast_delay = (predicted_finish - planned_finish).days

red_count = len(tasks[tasks["Risk_Level"] == "Red"])
amber_count = len(tasks[tasks["Risk_Level"] == "Amber"])
green_count = len(tasks[tasks["Risk_Level"] == "Green"])

if red_count > 0:
    overall_health = "Red"
elif amber_count > 2:
    overall_health = "Amber"
else:
    overall_health = "Green"

# -----------------------------
# Dashboard
# -----------------------------
st.header("1. Executive Dashboard")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Overall Health", overall_health)
col2.metric("Planned Finish", planned_finish.strftime("%d-%b-%Y"))
col3.metric("Predicted Finish", predicted_finish.strftime("%d-%b-%Y"))
col4.metric("Forecast Delay", f"{forecast_delay} days")

st.subheader("Executive Summary")

summary_points = []

if overall_health == "Red":
    summary_points.append("Project health is Red due to high-risk delayed activities and unresolved blockers.")
elif overall_health == "Amber":
    summary_points.append("Project health is Amber due to moderate forecast slippage and dependency risk.")
else:
    summary_points.append("Project health is Green with limited forecast slippage.")

summary_points.append(f"The current forecast completion date is {predicted_finish.strftime('%d-%b-%Y')}, compared to the planned finish date of {planned_finish.strftime('%d-%b-%Y')}.")
summary_points.append(f"{red_count} task(s) are Red, {amber_count} are Amber, and {green_count} are Green.")
summary_points.append("Highest delivery risk is concentrated around vendor dependencies, blockers, and low-progress tasks.")
summary_points.append("Management attention is required on blocked critical tasks and overloaded owners.")

for point in summary_points:
    st.markdown(f"- {point}")

# -----------------------------
# Risk Chart
# -----------------------------
st.header("2. Timeline Prediction")

risk_summary = tasks.groupby(["Workstream", "Risk_Level"]).size().reset_index(name="Count")

fig = px.bar(
    risk_summary,
    x="Workstream",
    y="Count",
    color="Risk_Level",
    title="Risk by Workstream"
)

st.plotly_chart(fig, use_container_width=True)

timeline_view = tasks[
    [
        "Task_ID",
        "Workstream",
        "Task_Name",
        "Planned_End",
        "Predicted_End",
        "Predicted_Delay_Days",
        "Risk_Level",
        "Blocker_Flag",
        "Dependency_Type"
    ]
].sort_values(by="Predicted_Delay_Days", ascending=False)

st.dataframe(timeline_view, use_container_width=True)

# -----------------------------
# Gantt Chart
# -----------------------------
st.subheader("Predicted Delivery Timeline")

gantt_df = tasks.copy()
gantt_df["Timeline_Label"] = gantt_df["Task_ID"] + " - " + gantt_df["Task_Name"]

fig_gantt = px.timeline(
    gantt_df,
    x_start="Planned_Start",
    x_end="Predicted_End",
    y="Timeline_Label",
    color="Risk_Level",
    title="Planned Start to Predicted Finish"
)

fig_gantt.update_yaxes(autorange="reversed")
st.plotly_chart(fig_gantt, use_container_width=True)

# -----------------------------
# Owner Assignment
# -----------------------------
st.header("3. AI Owner Recommendation")

owner_view = tasks[
    [
        "Task_ID",
        "Task_Name",
        "Skill_Required",
        "Current_Owner",
        "Recommended_Owner",
        "Owner_Recommendation_Reason"
    ]
]

st.dataframe(owner_view, use_container_width=True)

# -----------------------------
# Scenario Output
# -----------------------------
st.header("4. Scenario Simulation Result")

st.markdown(
    f"""
    **Scenario Applied:**

    - Vendor delay: **{vendor_delay_days} days**
    - Scope increase: **{scope_increase_percent}%**
    - Resource capacity reduction: **{resource_capacity_reduction}%**
    - Testing compression: **{testing_compression}%**

    **Result:** The project is forecast to finish on **{predicted_finish.strftime('%d-%b-%Y')}**, with a total forecast delay of **{forecast_delay} days**.
    """
)

# -----------------------------
# Recommended Management Actions
# -----------------------------
st.header("5. Recommended Management Actions")

actions = []

blocked = tasks[tasks["Blocker_Flag"] == "Yes"]
vendor_tasks = tasks[tasks["Dependency_Type"] == "Vendor"]
red_tasks = tasks[tasks["Risk_Level"] == "Red"]

if not blocked.empty:
    actions.append("Resolve blockers on critical tasks before adding more scope.")
if not vendor_tasks.empty:
    actions.append("Escalate vendor dependencies and agree revised delivery dates.")
if not red_tasks.empty:
    actions.append("Reassign Red tasks to owners with better capacity or stronger skill match.")
if forecast_delay > 7:
    actions.append("Re-baseline the project plan or increase capacity for critical path activities.")
if testing_compression > 0:
    actions.append("Testing compression should be controlled carefully to avoid quality risk.")

for action in actions:
    st.markdown(f"- {action}")

st.success("Demo complete: AI Project Orchestrator has predicted delivery delay, recommended owners, and simulated delivery scenarios.")