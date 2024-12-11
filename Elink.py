import streamlit as st
import collections
from datetime import datetime, timedelta
import os
import pickle
import pytz
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import calendar

# Initialize session state for saved_materials and event categories
if "saved_materials" not in st.session_state:
    st.session_state.saved_materials = {}
if "event_categories" not in st.session_state:
    st.session_state.event_categories = {}
if "events_with_materials" not in st.session_state:
    st.session_state.events_with_materials = set()  # Track events with materials

# Set page layout to wide mode
st.set_page_config(
    layout="wide",
    page_title="Google Calendar Event Manager 🎉",
    page_icon="📅"
)

# Add cartoonish styling with custom CSS
st.markdown("""
    <style>
    body {
        background-color: #f9f6ff;
        font-family: 'Comic Sans MS', cursive, sans-serif;
        color: #333;
    }
    .main-header {
        text-align: center;
        font-size: 3em;
        color: #ff4081;
        font-weight: bold;
        text-shadow: 2px 2px 4px #aaa;
        margin-bottom: 20px;
    }
    .sub-header {
        font-size: 1.5em;
        color: #ff7043;
        margin-bottom: 15px;
    }
    .event-card {
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 10px;
        background-color: #e8f5e9;
        box-shadow: 3px 3px 8px rgba(0, 0, 0, 0.2);
        text-align: center;
        font-size: 1.2em;
    }
    .event-card.super-important {
        background-color: #D5006D;  /* Dark Pink */
        color: white;
    }
    .event-card.important {
        background-color: #FF4081;  /* Slightly Dark Pink */
        color: white;
    }
    .event-card.not-so-important {
        background-color: #FF79B0;  /* Pink */
        color: white;
    }
    .event-card.less-important {
        background-color: #FFB3D9;  /* Light Pink */
        color: white;
    }
    .event-card.default {
        background-color: #FFFFFF;
        color: black;
    }
    .event-card.with-material {
        border: 3px solid purple;  /* Bold purple outline */
        font-weight: bold;         /* Make the text bold */
    }
    .button {
        background-color: #ff4081;
        color: white;
        padding: 10px 20px;
        border-radius: 10px;
        border: none;
        font-size: 1em;
        cursor: pointer;
        text-shadow: 1px 1px 2px #aaa;
    }
    .footer {
        text-align: center;
        font-size: 1.2em;
        font-family: 'Comic Sans MS', cursive, sans-serif;
        color: #ff4081;
        margin-top: 20px;
    }
    .footer img {
        width: 100%;
        max-width: 400px;
        height: auto;
    }
    </style>
""", unsafe_allow_html=True)


# Google Calendar API Configuration
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CLIENT_SECRET_FILE = 'client_secretDesktop.json'
CREDENTIALS_FILE = 'credentials.pkl'  # File to store credentials

# Function to authenticate Google Account
def authenticate_google_account():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'rb') as token:
            credentials = pickle.load(token)
        if credentials.valid:
            return build('calendar', 'v3', credentials=credentials)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        credentials = flow.run_local_server(port=0)
        with open(CREDENTIALS_FILE, 'wb') as token:
            pickle.dump(credentials, token)  # Save credentials for future use
        return build('calendar', 'v3', credentials=credentials)

# Function to get events from Google Calendar
def get_google_calendar_events():
    service = authenticate_google_account()
    if service is None:
        st.error("Authentication failed. Please re-authenticate.")
        return {}

    tz = pytz.timezone('Asia/Jakarta')
    now = datetime.now(tz).isoformat()
    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])
    grouped_events = collections.defaultdict(list)
    seen_events = set()

    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        title = event.get('summary', 'No Title')
        event_datetime = datetime.fromisoformat(start[:-6]).astimezone(tz)
        formatted_time = event_datetime.strftime("%H:%M:%S")
        day_of_week = event_datetime.strftime("%A")
        date_str = event_datetime.strftime("(%d %b)")

        event_str = f"{title} at {formatted_time}"

        if event_str not in seen_events:
            grouped_events[day_of_week].append((date_str, event_str, 'default'))
            seen_events.add(event_str)

    sorted_grouped_events = collections.OrderedDict(sorted(grouped_events.items(), key=lambda x: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].index(x[0])))
    return sorted_grouped_events

# Color map for importance categories
importance_colors = {
    'super important': 'super-important',  # Class for dark pink
    'important': 'important',  # Class for slightly dark pink
    'not so important': 'not-so-important',  # Class for pink
    'less important': 'less-important',  # Class for light pink
    'default': 'default',  # Default class
}

# Streamlit App Header
st.markdown("<div class='main-header'>📅 Google Calendar Event Manager 📅</div>", unsafe_allow_html=True)

search_query = st.text_input("🔍 Search events by title, date, or time...")

# Get events from Google Calendar
events = get_google_calendar_events()

# Filter events based on search query
if search_query:
    filtered_events = collections.defaultdict(list)
    for day, day_events in events.items():
        for event in day_events:
            if search_query.lower() in event[1].lower() or search_query.lower() in event[0].lower():
                filtered_events[day].append(event)
    events = filtered_events

# Days of the week
days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# Create 7 columns for the days of the week (vertical panel layout)
columns = st.columns(7)

# Display events based on category
for idx, day in enumerate(days_of_week):
    event_list = events.get(day, [("No events today", "No upcoming events", 'default')])

    with columns[idx]:
        st.markdown(f"<div class='sub-header'>{day}</div>", unsafe_allow_html=True)

        for event in event_list:
            # If the event is already categorized, use the stored category from session state
            selected_category = st.session_state.event_categories.get(event[1], 'default')
            category = st.selectbox(
                f"Category for {event[1]}",
                options=['super important', 'important', 'not so important', 'less important', 'default'],
                key=f"{event[1]}_{day}",
                index=['super important', 'important', 'not so important', 'less important', 'default'].index(selected_category)
            )
            st.session_state.event_categories[event[1]] = category  # Store the selected category
            
            # Apply the correct CSS class based on category
            css_class = importance_colors.get(category, 'default')  # Dynamically get the right class

            # Check if the event has attachments and apply the purple bold outline if it does
            if event[1] in st.session_state.events_with_materials:
                css_class += ' with-material'  # Add the class for purple bold outline

            # Display the event with or without the purple bold outline
            st.markdown(f"<div class='event-card {css_class}'>{event[1]}</div>", unsafe_allow_html=True)

# Panel for file upload and material entry
col1, col2 = st.columns(2)  # Creating two columns for layout

with col1:
    # To-Do List Panel (left)
    st.markdown("<div class='sub-header'>📋 To-Do List</div>", unsafe_allow_html=True)
    day = st.selectbox("Select a day to view events", options=days_of_week)

    if day in events:
        event_list = events[day]
        for event in event_list:
            # Use the stored category to get the color automatically
            selected_category = st.session_state.event_categories.get(event[1], 'default')
            css_class = importance_colors.get(selected_category, 'default')  # Use stored category color
            st.markdown(f"<div class='event-card {css_class}'>{event[1]}</div>", unsafe_allow_html=True)

# Panel for Add Material (right)
with col2:
    st.markdown("<div class='sub-header'>📝 Add Material for Event</div>", unsafe_allow_html=True)

    # Select a day
    day = st.selectbox("Select event day to add material", options=days_of_week)

    if day in events:
        # Get the list of events for the selected day
        event_list = events[day]

        # Create a select box to choose a specific event
        event_titles = [event[1] for event in event_list]
        selected_event = st.selectbox("Select an event", event_titles)

        # Get the selected event details
        selected_event_details = next(event for event in event_list if event[1] == selected_event)

        uploaded_file = st.file_uploader("Upload a file", type=["pdf", "docx", "txt", "jpg", "png"], key="file_uploader")
        link_or_material = st.text_area("Or enter a link or other material information", "")

    if st.button("Save Material"):
        if uploaded_file or link_or_material:
            if day not in st.session_state.saved_materials:
                st.session_state.saved_materials[day] = []
            st.session_state.saved_materials[day].append({
                "event": selected_event,  # Track event name
                "file": uploaded_file,
                "link": link_or_material
            })
            # Track events with materials
            st.session_state.events_with_materials.add(selected_event)  # Mark event as having material
            st.success("Material saved successfully!")
            # Clear inputs after saving
            st.session_state.uploaded_file = None
            st.session_state.link_or_material = ""

    if day in st.session_state.saved_materials:
        st.subheader(f"Saved Materials for {day}")
        for material in st.session_state.saved_materials[day]:
            # Display uploaded file as a downloadable link if available
            if material["file"]:
                st.write(f"File: {material['file'].name}")
                st.download_button(
                    label="Download File",
                    data=material["file"].getvalue(),
                    file_name=material["file"].name,
                    mime=material["file"].type
                )

            if material["link"]:
                st.write(f"Link: {material['link']}")

# Function to calculate reminder times based on event category
def calculate_reminders(event_datetime, category):
    reminder_offsets = {
        'super important': [timedelta(days=3), timedelta(days=1), timedelta(hours=12), timedelta(hours=1), timedelta(minutes=5)],
        'important': [timedelta(days=1), timedelta(hours=12), timedelta(hours=1), timedelta(minutes=5)],
        'not so important': [timedelta(hours=12), timedelta(hours=1), timedelta(minutes=5)],
        'less important': [timedelta(hours=1), timedelta(minutes=5)],
        'default': [timedelta(minutes=5)],
    }
    return [(event_datetime - offset).strftime("%Y-%m-%d %H:%M:%S") for offset in reminder_offsets.get(category, [])]

# Panel for reminders
st.markdown("<div style='font-size:24px; color:#FF79B0; font-weight:bold;'>✨ Event Reminders</div>", unsafe_allow_html=True)

for day, day_events in events.items():
    for event in day_events:
        event_title = event[1]
        selected_category = st.session_state.event_categories.get(event_title, 'default')
        # Remove parentheses from the date string
        event_datetime_str = event[0].replace("(", "").replace(")", "") + " " + event_title.split(" at ")[-1]
        event_datetime = datetime.strptime(event_datetime_str, "%d %b %H:%M:%S").replace(year=datetime.now().year)

        # Calculate reminders
        reminders = calculate_reminders(event_datetime, selected_category)
        if reminders:
            # Stylish reminder header with a cute emoji and event category color
            if selected_category == 'super important':
                reminder_header_color = "#D5006D"
            elif selected_category == 'important':
                reminder_header_color = "#FF4081"
            elif selected_category == 'not so important':
                reminder_header_color = "#FF79B0"
            else:
                reminder_header_color = None  # No background for 'default' or if no category is chosen

            # If no specific category is chosen, the text is plain with no background color
            if reminder_header_color:
                st.markdown(f"<div style='background-color:{reminder_header_color}; color:white; padding:10px; border-radius:8px;'>🔔 <b>{event_title}</b></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color:black; padding:10px; border-radius:8px;'>🔔 <b>{event_title}</b></div>", unsafe_allow_html=True)

            # Display reminders with the format: "Reminder scheduled at: [time]"
            for reminder in reminders:
                st.markdown(f"<div style='background-color:#FEE2E2; padding:8px; margin-top:6px; border-radius:8px; border:2px solid #FF79B0;'>💡 <b>Reminder scheduled at:</b> {reminder}</div>", unsafe_allow_html=True)

import json
import os

# File paths to store the session data
MATERIALS_FILE = 'saved_materials.json'
CATEGORIES_FILE = 'event_categories.json'

# Load saved materials from a file
def load_saved_materials():
    if os.path.exists(MATERIALS_FILE):
        with open(MATERIALS_FILE, 'r') as f:
            return json.load(f)
    return {}

# Load event categories from a file
def load_event_categories():
    if os.path.exists(CATEGORIES_FILE):
        with open(CATEGORIES_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save saved materials to a file
def save_saved_materials():
    with open(MATERIALS_FILE, 'w') as f:
        json.dump(st.session_state.saved_materials, f)

# Save event categories to a file
def save_event_categories():
    with open(CATEGORIES_FILE, 'w') as f:
        json.dump(st.session_state.event_categories, f)

# Initialize session state on app load
if "saved_materials" not in st.session_state:
    st.session_state.saved_materials = load_saved_materials()

if "event_categories" not in st.session_state:
    st.session_state.event_categories = load_event_categories()

# Save data when event categories or materials are modified
if st.session_state.saved_materials != load_saved_materials():
    save_saved_materials()

if st.session_state.event_categories != load_event_categories():
    save_event_categories()

# Footer with image and text
st.markdown("""
    <div class='footer'>
        <img src="https://th.bing.com/th/id/OIP.2317bJV_1s3uaRGs0vjhdgHaE8?rs=1&pid=ImgDetMain" alt="Footer Image">
        <p>Time Is Gold, Manage It Correctly ;) </p>
    </div>
""", unsafe_allow_html=True)