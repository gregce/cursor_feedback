import streamlit as st
import json
import pandas as pd
from datetime import datetime

def load_chat_data(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
        return data['messages']  # Extract the messages array

def convert_to_df(data):
    df = pd.DataFrame(data)
    
    # Convert timestamps with error handling
    try:
        # Convert to datetime and handle timezones by converting to UTC
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601', errors='coerce', utc=True)
        # Drop any rows where timestamp conversion failed
        df = df.dropna(subset=['timestamp'])
    except Exception as e:
        st.error(f"Error converting timestamps: {e}")
        st.write("Sample of problematic timestamps:", df['timestamp'].head())
        return None
    
    df['type'] = df['type'].fillna('Default')
    return df

st.title("Chat Analysis Dashboard")

# Load data
data = load_chat_data('simplified_chat.json')
df = convert_to_df(data)

# Check if DataFrame was created successfully
if df is None:
    st.error("Failed to process the chat data. Please check the timestamps format.")
    st.stop()

# Sidebar filters
st.sidebar.header("Filters")

# Date range filters
st.sidebar.subheader("Date Range")

# Preset date ranges
preset = st.sidebar.selectbox(
    "Preset ranges",
    ["Custom", "Last 7 days", "Last 30 days", "Last 90 days", "All time"],
    index=4  # Default to "All time"
)

# Get min and max dates
min_date = df['timestamp'].min().date()
max_date = df['timestamp'].max().date()

# Calculate preset dates
if preset == "Last 7 days":
    start_date = max_date - pd.Timedelta(days=7)
    end_date = max_date
elif preset == "Last 30 days":
    start_date = max_date - pd.Timedelta(days=30)
    end_date = max_date
elif preset == "Last 90 days":
    start_date = max_date - pd.Timedelta(days=90)
    end_date = max_date
elif preset == "All time":
    start_date = min_date
    end_date = max_date
else:  # Custom
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Start date", min_date, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("End date", max_date, min_value=min_date, max_value=max_date)

# Show date range info
date_range = pd.date_range(start_date, end_date)
st.sidebar.caption(f"Selected range: {len(date_range)} days")

# Message type filter
message_types = ['All', 'Default', 'Reply']
selected_type = st.sidebar.selectbox('Message type:', message_types)

# Author filter
authors = ['All'] + sorted(df['author'].unique().tolist())
selected_author = st.sidebar.selectbox('Author:', authors)

# Search filter in sidebar
search_term = st.sidebar.text_input("Search in messages:", "")

# Apply all filters
mask = (df['timestamp'].dt.date >= start_date) & (df['timestamp'].dt.date <= end_date)
if selected_type != 'All':
    mask = mask & (df['type'] == selected_type)
if selected_author != 'All':
    mask = mask & (df['author'] == selected_author)
if search_term:
    mask = mask & df['content'].str.contains(search_term, case=False, na=False)
filtered_df = df[mask]

# Show number of filtered messages
st.sidebar.write(f"Showing {len(filtered_df):,} messages")

# Main Dashboard Content

# Top Stats Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Messages", len(filtered_df))
with col2:
    st.metric("Replies", len(filtered_df[filtered_df['type'] == 'Reply']))
with col3:
    avg_length = round(filtered_df['content'].str.len().mean(), 1)
    st.metric("Avg Message Length", avg_length)
with col4:
    messages_per_day = round(len(filtered_df) / len(filtered_df['timestamp'].dt.date.unique()), 1)
    st.metric("Messages/Day", messages_per_day)

# Message Timeline in expander
with st.expander("📈 Message Timeline", expanded=False):
    timeline_data = filtered_df.groupby(filtered_df['timestamp'].dt.date)['type'].value_counts().unstack().fillna(0)
    st.line_chart(timeline_data)

# Message Distribution Stats in expander
with st.expander("📊 Message Distribution", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        st.caption("Message Length by Type")
        type_lengths = filtered_df.groupby('type')['content'].apply(lambda x: x.str.len().mean())
        st.bar_chart(type_lengths)
    
    with col2:
        st.caption("Message Type Distribution")
        type_counts = filtered_df['type'].value_counts()
        st.bar_chart(type_counts)

# Author Statistics in expander
with st.expander("👥 Author Activity", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        # Top authors by message count
        st.caption("Most Active Authors")
        author_counts = filtered_df['author'].value_counts().head(10)
        st.bar_chart(author_counts)
        
        # Show exact numbers in a table
        author_stats = pd.DataFrame({
            'Author': author_counts.index,
            'Messages': author_counts.values,
            'Percentage': (author_counts.values / len(filtered_df) * 100).round(1)
        })
        st.dataframe(
            author_stats,
            hide_index=True,
            column_config={
                "Author": st.column_config.TextColumn("Author", width="medium"),
                "Messages": st.column_config.NumberColumn("Messages", format="%d"),
                "Percentage": st.column_config.NumberColumn("% of Total", format="%.1f%%")
            }
        )
    
    with col2:
        # Average message length by author (top 10)
        st.caption("Authors by Avg Message Length")
        author_lengths = filtered_df.groupby('author')['content'].apply(
            lambda x: x.str.len().mean()
        ).sort_values(ascending=False).head(10)
        st.bar_chart(author_lengths)
        
        # Show exact numbers in a table
        length_stats = pd.DataFrame({
            'Author': author_lengths.index,
            'Avg Length': author_lengths.values.round(1)
        })
        st.dataframe(
            length_stats,
            hide_index=True,
            column_config={
                "Author": st.column_config.TextColumn("Author", width="medium"),
                "Avg Length": st.column_config.NumberColumn("Avg Characters", format="%.1f")
            }
        )

# Activity Patterns in expander
with st.expander("⏰ Activity Patterns", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        hourly_activity = filtered_df['timestamp'].dt.hour.value_counts().sort_index()
        st.caption("Messages by Hour")
        st.bar_chart(hourly_activity)
    
    with col2:
        daily_activity = filtered_df['timestamp'].dt.day_name().value_counts()
        st.caption("Messages by Day")
        st.bar_chart(daily_activity)

# Data Viewer
st.subheader("Message Data")
total_messages = len(df)
filtered_messages = len(filtered_df)
st.caption(f"Showing {filtered_messages:,} messages out of {total_messages:,} total messages")

# Create the display dataframe with formatted columns
display_df = filtered_df[['timestamp', 'content', 'author', 'type']].sort_values('timestamp', ascending=False)

st.dataframe(
    display_df,
    use_container_width=True,
    height=500,  # Make the table taller
    hide_index=True,
    column_config={
        "timestamp": st.column_config.DatetimeColumn(
            "Time",
            format="MMM DD, YYYY, hh:mm a",
            width="medium"
        ),
        "content": st.column_config.TextColumn(
            "Message",
            width="large"
        ),
        "author": st.column_config.TextColumn(
            "Author",
            width="small"
        ),
        "type": st.column_config.TextColumn(
            "Type",
            width="small"
        ),
    }
) 