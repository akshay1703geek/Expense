import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
from io import BytesIO
import os

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Smart Expense Tracker", layout="wide")
st.title("💼 Smart Expense Tracker & Analytics Dashboard")

DATA_FILE = "expenses.csv"

# ---------------- LOAD DATA ----------------
@st.cache_data(show_spinner=False)
def load_data():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(
            columns=["Date", "Category", "Amount", "Description"]
        )
        df.to_csv(DATA_FILE, index=False)
        return df

    df = pd.read_csv(DATA_FILE)

    # 🔴 CRITICAL TYPE FIX
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")

    return df

# ---------------- SESSION STATE ----------------
if "df" not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df.copy()

# ---------------- SIDEBAR ----------------
st.sidebar.header("⚙ Controls")
monthly_budget = st.sidebar.number_input(
    "Set Monthly Budget (₹)", min_value=0.0, step=500.0
)

# ---------------- ADD EXPENSE ----------------
st.subheader("➕ Add New Expense")

with st.form("expense_form", clear_on_submit=True):
    c1, c2 = st.columns(2)

    with c1:
        expense_date = st.date_input("Date", date.today())
        category = st.selectbox(
            "Category",
            ["Food", "Travel", "Shopping", "Bills", "Entertainment", "Education", "Other"]
        )

    with c2:
        amount = st.number_input("Amount (₹)", min_value=0.0, step=50.0)
        description = st.text_input("Description")

    submitted = st.form_submit_button("Add Expense")

if submitted:
    new_row = {
        "Date": pd.to_datetime(expense_date),   # 🔴 FIX
        "Category": category,
        "Amount": float(amount),                # 🔴 FIX
        "Description": description
    }

    st.session_state.df = pd.concat(
        [st.session_state.df, pd.DataFrame([new_row])],
        ignore_index=True
    )

    st.session_state.df.to_csv(DATA_FILE, index=False)
    st.success("✅ Expense Added")

# ---------------- CSV UPLOAD ----------------
st.subheader("📂 Upload Expense CSV")

uploaded = st.file_uploader("Upload CSV File", type="csv")

if uploaded:
    temp_df = pd.read_csv(uploaded)

    required_cols = {"Date", "Category", "Amount"}
    if not required_cols.issubset(temp_df.columns):
        st.error("CSV must contain Date, Category, Amount columns")
        st.stop()

    if "Description" not in temp_df.columns:
        temp_df["Description"] = ""

    # 🔴 CRITICAL TYPE FIX
    temp_df["Date"] = pd.to_datetime(temp_df["Date"], errors="coerce")
    temp_df["Amount"] = pd.to_numeric(temp_df["Amount"], errors="coerce")

    temp_df = temp_df.dropna(subset=["Date", "Amount"])

    st.session_state.df = temp_df
    temp_df.to_csv(DATA_FILE, index=False)

    st.success("✅ CSV Uploaded & Dashboard Updated")

# ---------------- DATA CLEANING (FINAL SAFETY NET) ----------------
df = st.session_state.df.copy()

if df.empty:
    st.info("No data available yet.")
    st.stop()

# 🔴 ABSOLUTE GUARANTEE AGAINST .dt ERROR
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
df = df.dropna(subset=["Date", "Amount"])

df["Month"] = df["Date"].dt.to_period("M").astype(str)

# ---------------- FILTERS ----------------
st.subheader("🔍 Filters")

f1, f2 = st.columns(2)

with f1:
    selected_month = st.selectbox(
        "Select Month",
        ["All"] + sorted(df["Month"].unique())
    )

with f2:
    selected_category = st.selectbox(
        "Select Category",
        ["All"] + sorted(df["Category"].unique())
    )

filtered_df = df.copy()

if selected_month != "All":
    filtered_df = filtered_df[filtered_df["Month"] == selected_month]

if selected_category != "All":
    filtered_df = filtered_df[filtered_df["Category"] == selected_category]

# ---------------- METRICS ----------------
st.subheader("📌 Key Insights")

total_expense = filtered_df["Amount"].sum()

top_category = (
    filtered_df.groupby("Category")["Amount"].sum().idxmax()
    if not filtered_df.empty else "N/A"
)

m1, m2, m3 = st.columns(3)
m1.metric("Total Expense", f"₹{total_expense:.2f}")
m2.metric("Transactions", len(filtered_df))
m3.metric("Top Category", top_category)

# ---------------- BUDGET ALERT ----------------
if monthly_budget > 0:
    usage = (total_expense / monthly_budget) * 100

    if usage >= 100:
        st.error("🚨 Budget Exceeded!")
    elif usage >= 80:
        st.warning("⚠ Approaching Budget Limit")
    else:
        st.success("✅ Budget Under Control")

# ---------------- VISUAL ANALYTICS ----------------
st.subheader("📊 Visual Analytics")

if not filtered_df.empty:
    c1, c2 = st.columns(2)

    category_summary = filtered_df.groupby("Category")["Amount"].sum()

    with c1:
        fig1, ax1 = plt.subplots()
        ax1.pie(
            category_summary,
            labels=category_summary.index,
            autopct="%1.1f%%",
            startangle=90
        )
        ax1.set_title("Expense Distribution")
        st.pyplot(fig1)

    with c2:
        fig2, ax2 = plt.subplots()
        ax2.bar(category_summary.index, category_summary.values)
        ax2.set_ylabel("Amount (₹)")
        ax2.set_title("Expenses by Category")
        plt.xticks(rotation=30)
        st.pyplot(fig2)

# ---------------- TREND ----------------
st.subheader("📈 Spending Trend")

trend = (
    filtered_df
    .groupby("Date", as_index=False)["Amount"]
    .sum()
    .sort_values("Date")
)

if not trend.empty:
    fig3, ax3 = plt.subplots(figsize=(10, 4))
    ax3.plot(trend["Date"], trend["Amount"], marker="o")
    ax3.set_xlabel("Date")
    ax3.set_ylabel("Amount (₹)")
    ax3.set_title("Daily Expense Trend")
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig3)

# ---------------- DATA VIEW ----------------
st.subheader("📋 Expense Table")
st.dataframe(filtered_df, use_container_width=True)

# ---------------- EXPORT ----------------
st.subheader("📤 Export Report")

if not filtered_df.empty:
    buffer = BytesIO()
    filtered_df.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        "⬇ Download Excel Report",
        buffer,
        file_name="Expense_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
