import streamlit as st
import pandas as pd
import requests
from io import StringIO
from io import BytesIO
import json
import streamlit as st
import base64
import numpy as np


@st.cache_data
def read_onedrive_csv (onedrive_link):
    data_bytes64 = base64.b64encode(bytes(onedrive_link, 'utf-8'))
    data_bytes64_String = data_bytes64.decode('utf-8').replace('/','_').replace('+','-').rstrip("=")
    resultUrl = f"https://api.onedrive.com/v1.0/shares/u!{data_bytes64_String}/root/content"
    df=pd.read_csv(resultUrl)
    return df

@st.cache_data
def read_onedrive_excel (onedrive_link,sheet_name=None):
    data_bytes64 = base64.b64encode(bytes(onedrive_link, 'utf-8'))
    data_bytes64_String = data_bytes64.decode('utf-8').replace('/','_').replace('+','-').rstrip("=")
    resultUrl = f"https://api.onedrive.com/v1.0/shares/u!{data_bytes64_String}/root/content"
    if sheet_name == None:
        st.write(pd.read_excel(resultUrl).keys())
        df=pd.read_excel(resultUrl,sheet_name=sheet_name)
    else:
        df=pd.read_excel(resultUrl,sheet_name=sheet_name)
    return df

input_data_cpm,processing,current_portfolio,planner_portfolio, summary_portfolio=st.tabs(['Input','Processing','Current Portfolio','Planner Portfolio','Summary Portfolio'])


company_finance_df = read_onedrive_csv('https://1drv.ms/u/s!Agfa0F4-51TwgYEkqnTC-DIdP79KlA?e=lHLNjv')
input_link='https://1drv.ms/x/s!Agfa0F4-51TwhvBWnj0HgUq1Eiti_A?e=T5hVf8'
latest_price_df = read_onedrive_csv("https://1drv.ms/u/s!Agfa0F4-51TwhvBoOkPKo2Ni8xCwyQ?e=jgPw56")
company_industry_df=read_onedrive_excel('https://1drv.ms/x/s!Agfa0F4-51TwhvBYN69gaO7iPbqPjg?e=aMP8BI',sheet_name="Sheet1")


#LEVEL 1
stock_action_df=read_onedrive_excel(input_link,'Stock Action')
# Function to convert Excel-style dates
def convert_excel_date(excel_date):
    if isinstance(excel_date, int) or isinstance(excel_date, float):
        return pd.to_datetime('1899-12-30') + pd.to_timedelta(excel_date, 'D')
    return pd.to_datetime(excel_date, format='%d/%m/%Y')

# Applying the conversion function to the Change_Date column
stock_action_df['Change_Date'] = stock_action_df['Change_Date'].apply(convert_excel_date)
stock_action_df['Asset'] = stock_action_df['Asset'].astype(str)
stock_action_df['Action'] = stock_action_df['Action'].astype('int64')
stock_action_df['Change_Quantity'] = stock_action_df['Change_Quantity'].astype('int64')
stock_action_df['Change_Price'] = stock_action_df['Change_Price'].astype('int64')
stock_action_df['Total Change'] = stock_action_df['Total Change'].astype('int64')
# Add 'Q_Change' column
stock_action_df['Q_Change'] = stock_action_df.apply(lambda row: row['Change_Quantity'] if row['Action'] > 0 else -row['Change_Quantity'], axis=1)
# Add 'Action_Cash' column
stock_action_df['Action_Cash'] = stock_action_df.apply(lambda row: -row['Total Change'] if row['Action'] == 1 else (row['Total Change'] if row['Action'] == -1 else 0), axis=1)


# CASH ACTION DATA
cash_action_df=read_onedrive_excel(input_link,"Cash Action")
cash_action_df['Change Date'] = pd.to_datetime(cash_action_df['Change Date'], format ='%d/%m/%Y')
cash_action_df['Net Change (2)'] = cash_action_df['Action'] * cash_action_df['Net Change']


#PLANNER DATA
planner_df=read_onedrive_excel(input_link,"Planner")
# Convert the Change_Date column to datetime
planner_df["Change_Date"] = pd.to_datetime(planner_df["Change_Date"], format ='%d/%m/%Y')
#planner_df["Change_Date"]= planner_df["Change_Date"].dt.strftime('%d/%m/%Y')
# Add Q_Change column
planner_df["Q_Change"] = planner_df.apply(lambda row: -row["Action"] * row["Change_Quantity"] if row["Action"] == -1 else row["Action"] * row["Change_Quantity"], axis=1)
# Add Action_Cash column
planner_df["Action_Cash"] = planner_df.apply(lambda row: -row["Total Change"] if row["Action"] == 1 else row["Total Change"], axis=1)
# Uppercase the Asset column
planner_df["Asset"] = planner_df["Asset"].str.upper()





#LEVEL 2

#CURRENT CASH FROM STOCK ACTION
current_cash_from_stock_action = stock_action_df.groupby('Change_Date')['Action_Cash'].sum().reset_index()
#current_cash_from_stock_action['Change_Date'] = pd.to_datetime(current_cash_from_stock_action['Change_Date'], errors='coerce')
# Rename the column to 'Cash_Change' for clarity
current_cash_from_stock_action.rename(columns={'Action_Cash': 'Cash_Change'}, inplace=True)
current_cash_from_stock_action = current_cash_from_stock_action.sort_values(by='Change_Date')

#PLANNER TO STOCK ACTION
planner_to_stock_action = pd.concat([planner_df, stock_action_df], ignore_index=True)




#LEVEL 3

#CURRENT CASH HISTORY
cash_action_df['Change Date'] = pd.to_datetime(cash_action_df['Change Date'])
current_cash_from_stock_action['Change_Date'] = pd.to_datetime(current_cash_from_stock_action['Change_Date'])
# Merge the dataframes
merged_df = pd.merge(cash_action_df, current_cash_from_stock_action, how='outer', left_on='Change Date', right_on='Change_Date')
# Replace null values in 'Asset' column with 'Trading'
merged_df['Asset'].fillna('Trading', inplace=True)
# Create 'Cash_Change_Date' column
merged_df['Cash_Change_Date'] = merged_df['Change Date'].combine_first(merged_df['Change_Date'])
# Replace null values in 'Net Change' and 'Cash_Change' columns with 0
merged_df['Net Change'].fillna(0, inplace=True)
merged_df['Cash_Change'].fillna(0, inplace=True)
# Create 'Portfolio Change' column
merged_df['Portfolio Change'] = merged_df['Net Change'] + merged_df['Cash_Change']
# Group by 'Cash_Change_Date' and sum 'Portfolio Change'
grouped_df = merged_df.groupby('Cash_Change_Date')['Portfolio Change'].sum().reset_index()
# Rename columns for clarity
grouped_df.rename(columns={'Cash_Change_Date': 'Date_Change', 'Portfolio Change': 'Cash_Change'}, inplace=True)
# Add 'Asset' column with value 'Cash'
grouped_df['Asset'] = 'Cash'
# Reorder columns
current_cash_history = grouped_df[['Asset', 'Date_Change', 'Cash_Change']].sort_values('Date_Change').reset_index(drop=True)

# Planner_Cash_from_Stock_Action
# Grouping the rows by "Change_Date" and summing the "Action_Cash" values
Planner_Cash_from_Stock_Action = planner_to_stock_action.groupby('Change_Date', as_index=False).agg({'Action_Cash': 'sum'})

# Renaming the column to match the desired output
Planner_Cash_from_Stock_Action.rename(columns={'Action_Cash': 'Cash_from_StockAction'}, inplace=True)



#LEVEL 4:

#CURRENT CASH BALANCE
# Grouping by 'Asset' and summing 'Cash_Change'
grouped_df = current_cash_history.groupby('Asset')['Cash_Change'].sum().reset_index()

# Dividing 'Cash_Change' column values by 10000
grouped_df['C_Quantity'] = grouped_df['Cash_Change'] / 10000

# Adding 'C_CapitalCost' column
grouped_df['C_CapitalCost'] = grouped_df['C_Quantity'] * 10000

# Adding 'C_Price' column
grouped_df['C_Price'] = 10000

# Adding 'C_Target' column
grouped_df['C_Target'] = 10000

# Reordering columns
current_cash_balance_df = grouped_df[['Asset', 'C_Quantity', 'C_CapitalCost', 'C_Target', 'C_Price']]

#PLANNER CASH BALANCE
#Merging the DataFrames
merged_df = pd.merge(cash_action_df, 
                    Planner_Cash_from_Stock_Action, 
                    left_on='Change Date', 
                    right_on='Change_Date', 
                    how='outer')
# Creating the 'Date_Change' column
merged_df['Date_Change'] = merged_df.apply(
    lambda row: row['Change Date'] if pd.notnull(row['Change Date']) else row['Change_Date'], 
    axis=1
)
# Replacing NaN values with 0 in 'Net Change' and 'Cash_from_StockAction' columns
merged_df['Net Change'].fillna(0, inplace=True)
merged_df['Cash_from_StockAction'].fillna(0, inplace=True)
# Creating the 'Cash_Change' column
merged_df['Cash_Change'] = merged_df['Net Change'] + merged_df['Cash_from_StockAction']
# Grouping by 'Date_Change' and summing the 'Cash_Change' values
grouped_df = merged_df.groupby('Date_Change')['Cash_Change'].sum().reset_index()
# Adding the 'Asset' column
grouped_df['Asset'] = 'Cash'
# Grouping by 'Asset' and summing the 'Cash_Change' values
final_grouped_df = grouped_df.groupby('Asset')['Cash_Change'].sum().reset_index()
# Dividing 'Cash_Change' by 10000 to get 'P_Quantity'
final_grouped_df['P_Quantity'] = final_grouped_df['Cash_Change'] / 10000
# Creating the 'P_CapitalCost' column
final_grouped_df['P_CapitalCost'] = final_grouped_df['P_Quantity'] * 10000
# Adding the 'P_Target' column
final_grouped_df['P_Target'] = 10000
# Changing the data types
final_grouped_df = final_grouped_df.astype({
    'P_Quantity': 'int64',
    'P_CapitalCost': 'int64',
    'P_Target': 'int64'
})
# Reordering the columns
current_planner_cash_balance_df = final_grouped_df[['Asset', 'P_Quantity', 'P_CapitalCost', 'P_Target']]

#LEVEL 5

#PLANNER_CASH_HISTORY
# Merging the tables
Merged_Queries = pd.merge(cash_action_df, Planner_Cash_from_Stock_Action, left_on='Change Date', right_on='Change_Date', how='outer')
# Adding 'Date_Change' column
Merged_Queries['Date_Change'] = Merged_Queries['Change Date'].combine_first(Merged_Queries['Change_Date'])
# Reordering columns
Merged_Queries = Merged_Queries[['Date_Change', 'Asset', 'Change Date', 'Action', 'Quantity Change', 'Price', 'Gross Change', 'T&F', 'Net Change', 'Notes', 'Net Change (2)', 'Change_Date', 'Cash_from_StockAction']]
# Replacing null values
Merged_Queries['Net Change'].fillna(0, inplace=True)
Merged_Queries['Cash_from_StockAction'].fillna(0, inplace=True)
# Adding 'Cash_Change' column
Merged_Queries['Cash_Change'] = Merged_Queries['Net Change'] + Merged_Queries['Cash_from_StockAction']
# Reordering columns again
Merged_Queries = Merged_Queries[['Date_Change', 'Cash_Change', 'Asset', 'Change Date', 'Action', 'Quantity Change', 'Price', 'Gross Change', 'T&F', 'Net Change', 'Notes', 'Net Change (2)', 'Change_Date', 'Cash_from_StockAction']]
# Grouping by 'Date_Change' and summing 'Cash_Change'
Grouped_Rows = Merged_Queries.groupby('Date_Change', as_index=False).agg({'Cash_Change': 'sum'})
# Changing type of 'Date_Change' to date
Grouped_Rows['Date_Change'] = pd.to_datetime(Grouped_Rows['Date_Change'])
# Adding 'Asset' column with a constant value 'Cash'
Grouped_Rows['Asset'] = 'Cash'
# Reordering columns again
Grouped_Rows = Grouped_Rows[['Asset', 'Date_Change', 'Cash_Change']]
# Grouping by 'Asset' and summing 'Cash_Change'
Grouped_Rows1 = Grouped_Rows.groupby('Asset', as_index=False).agg({'Cash_Change': 'sum'}).rename(columns={'Cash_Change': 'P_Quantity'})
# Dividing 'P_Quantity' by 10000
Grouped_Rows1['P_Quantity'] = Grouped_Rows1['P_Quantity'] / 10000
# Adding 'P_CapitalCost' column
Grouped_Rows1['P_CapitalCost'] = Grouped_Rows1['P_Quantity'] * 10000
# Changing types
Grouped_Rows1['P_Quantity'] = Grouped_Rows1['P_Quantity'].astype(np.int64)
Grouped_Rows1['P_CapitalCost'] = Grouped_Rows1['P_CapitalCost'].astype(np.int64)

# Adding 'P_Target' column
Grouped_Rows1['P_Target'] = 10000
# Changing type of 'P_Target'
Grouped_Rows1['P_Target'] = Grouped_Rows1['P_Target'].astype(np.int64)



# CURRENT STOCK VIEW
# Change type of "Target Price" to int64
stock_action_df["Target Price"] = stock_action_df["Target Price"].astype("int64")

# Group by "Asset" and aggregate
grouped_df = stock_action_df.groupby("Asset").agg(
    P_Quantity=pd.NamedAgg(column="Q_Change", aggfunc="sum"),
    P_CapitalCost=pd.NamedAgg(column="Action_Cash", aggfunc=lambda x: -sum(x)),
    P_Target=pd.NamedAgg(column="Target Price", aggfunc="mean")
).reset_index()

# Merge with latest price data
merged_df = pd.merge(grouped_df, latest_price_df, left_on="Asset", right_on="ticker", how="left")

# Rename columns
merged_df = merged_df.rename(columns={"close": "C_Price", "P_Target": "C_Target", "P_CapitalCost": "C_CapitalCost", "P_Quantity": "C_Quantity"})

# Adding custom columns
merged_df["UnitCost"] = merged_df.apply(lambda row: row["C_CapitalCost"] / row["C_Quantity"] if row["C_Quantity"] > 0 else 0, axis=1)
merged_df["C_Amount"] = merged_df["C_Quantity"] * merged_df["C_Price"]

# Change types
merged_df = merged_df.astype({"C_Amount": "int64", "C_Price": "int64", "C_Quantity": "int64", "UnitCost": "int64"})

# Merge with company industry data
merged_df = pd.merge(merged_df, company_industry_df, left_on="Asset", right_on='Stock', how="left")

# Adding more custom columns
merged_df["C_PL"] = merged_df.apply(lambda row: row["C_Price"] / row["UnitCost"] - 1 if row["C_Quantity"] > 0 else 0, axis=1)
merged_df["C_Upside"] = merged_df.apply(lambda row: row["C_Target"] / row["C_Price"] - 1 if row["C_Quantity"] > 0 else 0, axis=1)

# Change types
merged_df = merged_df.astype({"C_PL": "float64", "C_Upside": "float64"})

# Reorder columns
columns_order = ["Asset", "C_Quantity", "C_CapitalCost", "C_Target", "C_Price", "UnitCost", "C_Amount", "C_PL", "C_Upside", "L4N", "L3N", "L2N", "L1N"]
current_stock_view_df = merged_df[columns_order]




#PLANNER STOCKVIEW
# Group by "Asset" and aggregate
grouped_df = planner_to_stock_action.groupby("Asset").agg(
    P_Quantity=pd.NamedAgg(column="Q_Change", aggfunc="sum"),
    P_CapitalCost=pd.NamedAgg(column="Total Change", aggfunc="sum"),
    P_Target=pd.NamedAgg(column="Target Price", aggfunc="mean")
).reset_index()

# Append planner cash balance (assuming planner_cash_balance_df is your dataframe)
# planner_cash_balance_df should be defined or replace it with the correct dataframe
# Append current planner cash balance
appended_df = pd.concat([grouped_df, current_planner_cash_balance_df], ignore_index=True)

# Merge with latest price data
merged_df = pd.merge(appended_df, latest_price_df, left_on="Asset", right_on="ticker", how="left")

# Replace null values in "Price_Current" with 10000
merged_df["close"].fillna(10000, inplace=True)

# Rename columns
merged_df = merged_df.rename(columns={"close": "P_Price"})

# Adding custom columns
merged_df["UnitCost"] = merged_df.apply(lambda row: row["P_CapitalCost"] / row["P_Quantity"] if row["P_Quantity"] != 0 else 0, axis=1)
merged_df["P_Amount"] = merged_df["P_Quantity"] * merged_df["P_Price"]

# Change types
merged_df = merged_df.astype({"UnitCost": "int64", "P_Amount": "int64"})

# Adding custom columns
merged_df["P_Upside"] = merged_df.apply(lambda row: row["P_Target"] / row["P_Price"] - 1 if row["P_Quantity"] > 0 else 0, axis=1)

# Merge with company industry data
merged_df = pd.merge(merged_df, company_industry_df, left_on="Asset", right_on="Stock", how="left")

# Reorder columns
columns_order = ["Asset", "P_Quantity", "P_CapitalCost", "P_Target", "P_Price", "P_Upside", "L4N", "L3N", "L2N", "L1N", "UnitCost", "P_Amount"]
planner_stock_view_df = merged_df[columns_order]














with input_data_cpm:
    st.header("Latest Price Data")
    st.dataframe(latest_price_df)

    st.header("Stock Action Data")
    st.dataframe(stock_action_df)

    st.header("Cash Action Data")
    st.dataframe(cash_action_df)

    st.header('Planner')
    st.dataframe(planner_df)

    st.header("Reference")
    st.dataframe(company_industry_df)



with current_portfolio:


    st.header("Current Cash from Stock Action")
    st.dataframe(current_cash_from_stock_action)

    st.header("Current Stock View")
    st.dataframe(current_stock_view_df)
    
    st.header("Current Cash History")
    st.dataframe(current_cash_history)

with planner_portfolio:
    st.header("Planner to Stock Action")
    st.dataframe(Planner_Cash_from_Stock_Action)
    
    st.header("Planner Cash from Stock Action")
    st.dataframe(planner_to_stock_action)

    st.header("Planner Stock View")
    try:
        st.dataframe(planner_stock_view_df)
    except:
        pass
    
    st.header("Planner Cash History")
    st.dataframe(Grouped_Rows1)

with summary_portfolio:
    st.header("Portfolio Changes")
    st.header("Industry Level Allocation")
    st.header("Portfolio Details")
    st.header("Trading History")


with processing:
    st.header("Current Cash Balance")
    st.dataframe(current_cash_balance_df)

    st.header("Planner Cash Balance")
    st.dataframe(current_planner_cash_balance_df)

