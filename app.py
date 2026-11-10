
import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import date, timedelta

# ---------------- DATABASE ----------------

conn = sqlite3.connect("food_pantry.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS foods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT,
    quantity INTEGER,
    purchase_date TEXT,
    expiry_date TEXT,
    location TEXT
)
""")
conn.commit()


# ---------------- PAGE SETTINGS ----------------

st.set_page_config(
    page_title="Food Pantry Tracker",
    page_icon="🥗",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background-color: #f5f8f2;
}
h1, h2, h3 {
    color: #245c3a;
}
div[data-testid="stMetric"] {
    background-color: white;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #dce9dc;
}
</style>
""", unsafe_allow_html=True)


# ---------------- HELPER FUNCTIONS ----------------

def get_foods():
    return pd.read_sql_query(
        "SELECT * FROM foods ORDER BY expiry_date",
        conn
    )


def get_status(expiry):
    days = (date.fromisoformat(expiry) - date.today()).days

    if days < 0:
        return "Expired"
    elif days <= 3:
        return "Critical"
    elif days <= 7:
        return "Expiring Soon"
    else:
        return "Fresh"


def save_food(name, category, quantity, purchase, expiry, location):
    cursor.execute("""
        INSERT INTO foods
        (name, category, quantity, purchase_date, expiry_date, location)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, category, quantity, str(purchase),
          str(expiry), location))
    conn.commit()


# ---------------- SIDEBAR ----------------

st.sidebar.title("🥗 Food Pantry")
st.sidebar.caption("Expiry Management System")

page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Add Food", "Inventory",
     "Expiry Alerts", "Reports"]
)

st.sidebar.markdown("---")
st.sidebar.info("Manage food smartly. Reduce food waste!")


# ---------------- DASHBOARD ----------------

if page == "Dashboard":

    st.title("🥗 Food Pantry Dashboard")
    st.write("Welcome! Manage your food inventory in one place.")

    df = get_foods()

    if not df.empty:
        df["Status"] = df["expiry_date"].apply(get_status)

    total = len(df)
    expired = (df["Status"] == "Expired").sum() if total else 0
    critical = (df["Status"] == "Critical").sum() if total else 0
    soon = (df["Status"] == "Expiring Soon").sum() if total else 0
    fresh = (df["Status"] == "Fresh").sum() if total else 0

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Items", total)
    c2.metric("Fresh Items", fresh)
    c3.metric("Expiring Soon", soon + critical)
    c4.metric("Expired Items", expired)

    st.markdown("---")
    st.subheader("📋 Recent Food Inventory")

    if total:
        st.dataframe(
            df[["name", "category", "quantity",
                "expiry_date", "Status"]],
            use_container_width=True,
            hide_index=True
        )

        fig = px.pie(
            df,
            names="Status",
            title="Food Expiry Status",
            color="Status",
            color_discrete_map={
                "Fresh": "#38a169",
                "Expiring Soon": "#ecc94b",
                "Critical": "#ed8936",
                "Expired": "#e53e3e"
            }
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No food items added yet. Go to Add Food to get started.")


# ---------------- ADD FOOD ----------------

elif page == "Add Food":

    st.title("➕ Add Food Items")
    st.write("Enter the details of your food products.")

    with st.form("add_food_form"):

        name = st.text_input("Food Item Name")

        category = st.selectbox(
            "Food Category",
            ["Fruits", "Vegetables", "Dairy",
             "Grains", "Snacks", "Canned Food",
             "Meat", "Beverages", "Other"]
        )

        quantity = st.number_input(
            "Quantity", min_value=1, step=1
        )

        purchase = st.date_input(
            "Purchase Date", value=date.today()
        )

        expiry = st.date_input(
            "Expiry Date", value=date.today() + timedelta(days=7)
        )

        location = st.selectbox(
            "Storage Location",
            ["Refrigerator", "Freezer", "Kitchen Shelf",
             "Pantry Cabinet", "Other"]
        )

        submit = st.form_submit_button(
            "➕ Add Food Item",
            use_container_width=True
        )

        if submit:
            if not name.strip():
                st.error("Please enter the food item name.")
            elif expiry < purchase:
                st.error("Expiry date cannot be before purchase date.")
            else:
                save_food(
                    name.strip(), category, quantity,
                    purchase, expiry, location
                )
                st.success(f"{name} added successfully!")
                st.rerun()


# ---------------- INVENTORY ----------------

elif page == "Inventory":

    st.title("📦 Food Inventory Management")

    df = get_foods()

    if df.empty:
        st.info("Your inventory is empty. Add some food items first.")

    else:
        df["Status"] = df["expiry_date"].apply(get_status)

        search = st.text_input("🔍 Search Food Item")

        categories = ["All"] + sorted(df["category"].dropna().unique().tolist())
        selected_category = st.selectbox("Filter by Category", categories)

        statuses = ["All", "Fresh", "Expiring Soon", "Critical", "Expired"]
        selected_status = st.selectbox("Filter by Status", statuses)

        filtered = df.copy()

        if search:
            filtered = filtered[
                filtered["name"].str.contains(search, case=False, na=False)
            ]

        if selected_category != "All":
            filtered = filtered[
                filtered["category"] == selected_category
            ]

        if selected_status != "All":
            filtered = filtered[
                filtered["Status"] == selected_status
            ]

        st.dataframe(
            filtered,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")
        st.subheader("✏️ Edit or Delete Food Items")

        ids = df["id"].tolist()

        selected_id = st.selectbox(
            "Select Food Item ID",
            ids,
            format_func=lambda x: (
                f"{x} - {df.loc[df['id'] == x, 'name'].iloc[0]}"
            )
        )

        item = df[df["id"] == selected_id].iloc[0]

        with st.form("edit_food_form"):

            edit_name = st.text_input("Food Name", value=item["name"])

            edit_category = st.selectbox(
                "Category",
                ["Fruits", "Vegetables", "Dairy", "Grains",
                 "Snacks", "Canned Food", "Meat",
                 "Beverages", "Other"],
                index=["Fruits", "Vegetables", "Dairy", "Grains",
                       "Snacks", "Canned Food", "Meat",
                       "Beverages", "Other"].index(item["category"])
                if item["category"] in
                   ["Fruits", "Vegetables", "Dairy", "Grains",
                    "Snacks", "Canned Food", "Meat",
                    "Beverages", "Other"] else 0
            )

            edit_quantity = st.number_input(
                "Quantity", min_value=1,
                value=int(item["quantity"])
            )

            edit_purchase = st.date_input(
                "Purchase Date",
                value=date.fromisoformat(item["purchase_date"])
            )

            edit_expiry = st.date_input(
                "Expiry Date",
                value=date.fromisoformat(item["expiry_date"])
            )

            edit_location = st.text_input(
                "Storage Location", value=item["location"]
            )

            update = st.form_submit_button("Update Item")

            if update:
                if not edit_name.strip():
                    st.error("Food name cannot be empty.")
                elif edit_expiry < edit_purchase:
                    st.error("Expiry date cannot be before purchase date.")
                else:
                    cursor.execute("""
                        UPDATE foods SET
                        name=?, category=?, quantity=?,
                        purchase_date=?, expiry_date=?, location=?
                        WHERE id=?
                    """, (
                        edit_name.strip(), edit_category, edit_quantity,
                        str(edit_purchase), str(edit_expiry),
                        edit_location, selected_id
                    ))
                    conn.commit()
                    st.success("Food item updated!")
                    st.rerun()

        if st.button("🗑️ Delete Selected Item", type="primary"):
            cursor.execute(
                "DELETE FROM foods WHERE id=?", (selected_id,)
            )
            conn.commit()
            st.success("Food item deleted!")
            st.rerun()


# ---------------- EXPIRY ALERTS ----------------

elif page == "Expiry Alerts":

    st.title("⚠️ Food Expiry Alerts")

    df = get_foods()

    if df.empty:
        st.info("No food items available.")

    else:
        df["Status"] = df["expiry_date"].apply(get_status)

        expired_items = df[df["Status"] == "Expired"]
        critical_items = df[df["Status"] == "Critical"]
        soon_items = df[df["Status"] == "Expiring Soon"]

        st.subheader("🔴 Expired Items")
        if not expired_items.empty:
            st.error("These food items have passed their expiry dates.")
            st.dataframe(expired_items, use_container_width=True)
        else:
            st.success("No expired food items!")

        st.subheader("🟠 Expiring Within 3 Days")
        if not critical_items.empty:
            st.warning("Use these items immediately, if still safe.")
            st.dataframe(critical_items, use_container_width=True)
        else:
            st.success("No critical expiry alerts!")

        st.subheader("🟡 Expiring Within 7 Days")
        if not soon_items.empty:
            st.warning("These food items are expiring soon.")
            st.dataframe(soon_items, use_container_width=True)
        else:
            st.success("No upcoming expiry alerts!")


# ---------------- REPORTS ----------------

elif page == "Reports":

    st.title("📊 Food Pantry Reports")

    df = get_foods()

    if df.empty:
        st.info("Add food items to generate reports.")

    else:
        df["Status"] = df["expiry_date"].apply(get_status)

        st.subheader("Inventory Summary")

        report = df.groupby("Status").size().reset_index(name="Count")

        fig = px.bar(
            report,
            x="Status",
            y="Count",
            color="Status",
            title="Food Inventory Analysis",
            color_discrete_map={
                "Fresh": "#38a169",
                "Expiring Soon": "#ecc94b",
                "Critical": "#ed8936",
                "Expired": "#e53e3e"
            }
        )

        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Download Inventory Report")

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="⬇️ Download CSV Report",
            data=csv,
            file_name="food_pantry_report.csv",
            mime="text/csv"
        )

        st.success("Your inventory report is ready!")


# ---------------- FOOTER ----------------

st.sidebar.markdown("---")
st.sidebar.caption("Food Pantry Expiry Tracker | Python Project")
st.sidebar.caption("Developed for Food Waste Management")
