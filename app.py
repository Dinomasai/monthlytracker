import calendar
from datetime import datetime


from pymongo import MongoClient
import streamlit as st
from streamlit_option_menu import option_menu  # pip install streamlit-option-menu
import plotly.graph_objects as go

# Load the environment variables
MONGODB_CONNECTION_STRING = "mongodb://localhost:27017/"

# Connect to MongoDB
client = MongoClient(MONGODB_CONNECTION_STRING)
db = client["monthly_reports"]

# Check if the database exists and create it if it doesn't
if "periods" not in db.list_collection_names():
    db.create_collection("periods")

def insert_period(period, incomes, expenses, comment):
    """Returns the report on a successful creation, otherwise raises an error"""
    collection = db["periods"]
    return collection.insert_one({"key": period, "inc": incomes, "expenses": expenses, "comment": comment})

def fetch_all_periods():
    """Returns a dict of all periods"""
    collection = db["periods"]
    periods = collection.find()
    return list(periods)

def get_period(period):
    """If not found, the function will return None"""
    collection = db["periods"]
    return collection.find_one({"key": period})

# --------------SETTINGS -----------
income = ["Salary", "Blog", "Other Income"]
expenses = ["Rent", "Utilities", "Groceries", "Cars", "Other Expenses", "Savings"]
currency = "USD"
page_title = "Income and Expense Tracker"
page_icon = ":money_with_wings:"
layout = "centered"
# ----------------------------------------

st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)
st.title(page_title + " " + page_icon)

# --- DROP DOWN VALUES FOR SELECTING THE PERIOD ----
years = [datetime.today().year, datetime.today().year + 1]
months = list(calendar.month_name[1:])

# --- HIDE STREAMLIT STYLE ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)


# --- NAVIGATION MENU ---
selected = option_menu(
    menu_title=None,
    options=["Data Entry", "Data Visualization"],
    icons=["pencil-fill", "bar-chart-fill"],  # https://icons.getbootstrap.com/
    orientation="horizontal",
)

# ---INPUT & SAVE PERIODS ---
if selected == "Data Entry":
    st.header(f"Data Entry in {currency}")
    with st.form("entry_form", clear_on_submit=True):
        col1,col2 = st.columns(2)
        col1.selectbox("Select Month:", months, key="month")
        col2.selectbox("Select Year:", years, key="year")

        "---"
        with st.expander("Income"):
            for inc in income:
                st.number_input(f"{inc}:", min_value=0, format="%i", step=10, key=inc)
        with st.expander("Expenses"):
            for expense in expenses:
                st.number_input(f"{expense}:", min_value=0, format="%i", step=10, key=expense)
        with st.expander("Comment"):
            comment = st.text_area("", placeholder="Enter a comment here...", key="comment")  # Initialize comment
            "---"
            submitted = st.form_submit_button("Save Data")
            if submitted:
                period = f"{st.session_state['year']}_{st.session_state['month']}"
                incomes = {inc: st.session_state[inc] for inc in income}
                expenses = {expense: st.session_state[expense] for expense in expenses}
                comment_value = st.session_state['comment']
                # Insert values into database
                result = insert_period(period, incomes, expenses, comment_value)
                if result.acknowledged:
                    st.success("Data saved successfully!")
                else:
                    st.error("Failed to save data.")


if selected == "Data Visualization":
    st.header("Data Visualization")
    with st.form("saved_periods"):
        saved_periods = fetch_all_periods()
        saved_period_names = [period["key"] for period in saved_periods]
        period = st.selectbox("Select Period:", saved_period_names)
        submitted = st.form_submit_button("Plot Period")
        if submitted:
            selected_period = next((p for p in saved_periods if p["key"] == period), None)
            if selected_period:
                incomes = selected_period["inc"]
                expenses = selected_period["expenses"]
                comment = selected_period["comment"]
                # Calculate total income and expenses
                total_income = sum(incomes.values())
                total_expense = sum(expenses.values())
                remaining_budget = total_income - total_expense
                
                # Display metrics
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Income", f"{total_income}{currency}")
                col2.metric("Total Expense", f"{total_expense}{currency}")
                col3.metric("Remaining Budget", f"{remaining_budget}{currency}")
                st.text(f"Comment: {comment}")

                # Create sankey chart
                label = list(incomes.keys()) + ["Total Income"] + list(expenses.keys())
                source = list(range(len(incomes))) + [len(incomes)] * len(expenses)
                target = [len(incomes)] * len(incomes) + [label.index(expense) for expense in expenses.keys()]
                value = list(incomes.values()) + list(expenses.values())

                # Data to dict, dict to sankey
                link = dict(source=source, target=target, value=value)
                node = dict(label=label, pad=20, thickness=30, color="#E694FF")
                data = go.Sankey(link=link, node=node)

                # Plot it!
                fig = go.Figure(data)
                fig.update_layout(margin=dict(l=0, r=0, t=5, b=5))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("Selected period not found in the database.")
