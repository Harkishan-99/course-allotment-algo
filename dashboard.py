import streamlit as st
import pandas as pd

from algo import run_allotment

def preprocess_history(file):
    df_hist= pd.read_csv(file)
    df_hist = df_hist[["Instructor Name",	"Email",	"Courses",	"current_sem_ug",	"current_sem_pg",	"ug_left", "Courses_left"]]
    df_hist["Courses"] = df_hist["Courses"].apply(
        lambda x: ','.join([course.strip().split('_')[0] for course in x.split(',')])
    )
    df_hist["Email"] = df_hist["Email"].apply(lambda x: x.strip(";"))
    return df_hist

def preprocess_preference(file):
    df_pref = pd.read_csv(file)
    cols=["UG First Preference", "UG Second Preference", "UG Third Preference",	"PG First Preference",	"PG Second Preference",	"PG Third Preference"]
    df_pref[cols]= df_pref[cols].map(lambda x: x.split(" ")[0]).map(lambda x: x.split("/")[0])
    df_pref = df_pref.drop(["Faculty Name",	"Courses taught by you in last three semesters (including Current Semester) "], axis=1)
    df_pref.rename(columns={"Email Address": "Email"}, inplace=True)
    return df_pref


def preprocess_course_details(file):
    courses_df = pd.read_csv(file)
    courses_df['code'] = courses_df['code'].apply(lambda x: x.split("/")[0])
    return courses_df[["code", "type", "sections"]].to_dict('records')


def combine_data(history, preference):
    merged_dfp = pd.merge(history, preference, on='Email', how='outer')
    merged_dfp.dropna(inplace=True)
    merged_dfp.drop_duplicates(inplace=True,keep='first',subset='Email')
    all_cols = [
    'UG First Preference', 'UG Second Preference', 'UG Third Preference',
    'PG First Preference', 'PG Second Preference', 'PG Third Preference'
    ]

    merged_dfp['preferences'] = merged_dfp.apply(
        lambda row: {row[col]: i + 1 for i, col in enumerate(all_cols) if pd.notnull(row[col])},
        axis=1
    )

    def calculate_history(preferences, courses_str):
        # preferences is already a dictionary, no need for eval()
        courses = courses_str.split(',')
        history = {}
        for course in preferences:
            history[course] = courses.count(course)
        return history

    merged_dfp['history'] = merged_dfp.apply(lambda row: calculate_history(row['preferences'], row['Courses']), axis=1)

    # Convert the Timestamp column to datetime
    merged_dfp['Timestamp'] = pd.to_datetime(merged_dfp['Timestamp'])

    # Normalize timestamps to a [0, 1] range
    min_time = merged_dfp['Timestamp'].min()
    max_time = merged_dfp['Timestamp'].max()
    total_range = (max_time - min_time).total_seconds()
    if total_range == 0:
        merged_dfp['timestamp_norm'] = 0.0
    else:
        merged_dfp['timestamp_norm'] = merged_dfp['Timestamp'].apply(lambda x: (x - min_time).total_seconds() / total_range)
    merged_dfp = merged_dfp[["Courses_left", "current_sem_pg", "current_sem_ug",	"history",	
                       "Instructor Name", "preferences",	"timestamp_norm",	"ug_left"]]
    merged_dfp.rename(columns={"timestamp_norm": "timestamp", "Courses_left":'courses_left',"current_sem_pg":'current_semester_pg',  
                    "current_sem_ug":'current_semester_ug',"Instructor Name":'name' }, inplace=True)
    return merged_dfp.to_dict('records')



# Streamlit App
st.title("Faculty Course Allocation")

st.header("Upload Required CSV Files")
teaching_history_file = st.file_uploader("Upload Teaching History CSV", type=["csv"])
teaching_preference_file = st.file_uploader("Upload Teaching Preference CSV", type=["csv"])
course_requirements_file = st.file_uploader("Upload Course Requirements CSV", type=["csv"])

if teaching_history_file and teaching_preference_file and course_requirements_file:
    teaching_history = preprocess_history(teaching_history_file)
    teaching_preference = preprocess_preference(teaching_preference_file)
    courses = preprocess_course_details(course_requirements_file)
    faculties = combine_data(teaching_history, teaching_preference)
    
    allocations, unallotted_sections = run_allotment(faculties, courses)
    
    st.header("Allocation Results")
    allocation_df = pd.DataFrame(list(allocations.items()), columns=["Faculty Name", "Assigned Course"])
    st.table(allocation_df)
    
    st.header("Unallotted Sections")
    unallotted_df = pd.DataFrame(unallotted_sections, columns=["Unallotted Course Sections"])
    st.table(unallotted_df)
