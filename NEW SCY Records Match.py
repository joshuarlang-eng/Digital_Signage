# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Enhanced script to compare meet results with team records,
handling prelims and finals times.
"""

import pandas as pd

# Load team records
records = pd.read_csv('SCY-Records.csv', parse_dates=['Date'])
records = records.filter(['Agegroup', 'Gender', 'Event', 'Time', 'Name', 'Date'])

# Convert times to seconds for easy comparison
def convert_to_seconds(time):
    if pd.isna(time):
        return float('inf')  # Treat missing times as infinitely large
    return time.minute * 60 + time.second + time.microsecond / 1e6

# Load meet results
meet = pd.read_csv('csv files/MCSC 2026 SE Southeastern Winter SC.csv', parse_dates=['Date'])

# Convert Prelims and Finals times to seconds
meet.Prelims = pd.to_datetime(meet.Prelims, format='%S.%f', errors='coerce').fillna(
    pd.to_datetime(meet.Prelims, format='%M:%S.%f', errors='coerce')
)
meet.Finals = pd.to_datetime(meet.Finals, format='%S.%f', errors='coerce').fillna(
    pd.to_datetime(meet.Finals, format='%M:%S.%f', errors='coerce')
)
# Convert Entry times to datetime and then to seconds
meet.Entry = pd.to_datetime(meet.Entry, format='%S.%f', errors='coerce').fillna(
    pd.to_datetime(meet['Entry'], format='%M:%S.%f', errors='coerce')
)

meet['Prelims'] = meet.Prelims.apply(convert_to_seconds)
meet['Finals'] = meet.Finals.apply(convert_to_seconds)
meet['Entry'] = meet.Entry.apply(convert_to_seconds)

meet.replace([float('inf'), -float('inf')], pd.NA, inplace=True)

# Determine the fastest time (prelims or finals)
meet['Fastest'] = meet[['Prelims', 'Finals']].min(axis=1)

# Define Agegroup bins
bins = [0, 7, 9, 11, 13, 15, 110]
labels = ['6U', '8U', '9-10', '11-12', '13-14', 'Senior']
meet['Agegroup'] = pd.cut(meet.Age, bins=bins, labels=labels, right=False)

# Add unique identifiers
meet['Name'] = meet.First + ' ' + meet.Last
meet['Event'] = meet.Distance.astype(str) + ' ' + meet.Stroke
meet['Swim'] = meet.Agegroup.astype(str) + ' ' + meet.Gender + ' ' + meet.Event
records['Swim'] = records.Agegroup.astype(str) + ' ' + records.Gender + ' ' + records.Event

# Condense the Rows of Prelims and Finals
df = meet.groupby(['Name','Swim']).agg('min')
df['Fastest'] = df[['Prelims','Finals']].min(axis=1)

meet = df
meet = meet.reset_index()
meet = meet.dropna(subset = ['Fastest'])

# Create a PR report for the meet
meetName = input("Enter a Name for this Meet: ")
PR = meet[meet.Entry > meet.Fastest]
PR = PR.filter(['Name', 'Agegroup', 'Gender', 'Event', 'Entry', 'Fastest','Prelims', 'Finals']).sort_values(by="Name")

# Create a New Swim Report for the meet
NewSwim = meet[meet.Entry.isnull()&meet.Fastest.notnull()]
NewSwim = NewSwim.filter(['Name', 'Agegroup', 'Gender', 'Event', 'Fastest','Prelims', 'Finals']).sort_values(by="Name")

# Export Times Reports to Excel
def times_report():
    with pd.ExcelWriter(meetName + ' Times Report.xlsx') as writer:
        PR.to_excel(writer, sheet_name="PRs", index=False)
        NewSwim.to_excel(writer, sheet_name="New Swims", index=False)


swims = meet.Swim.unique()

# Match and Update Records
def record_match():
    # Initialize lists to store records data
    records_data = []

    # Iterate over swims
    for swim in swims:
        if swim in records.Swim.unique():
            for time in meet[meet.Swim==swim].Fastest:
                if time < records[records.Swim==swim].Time.values[0]:
                    record_holder = records[records.Swim==swim]['Name'].values[0]
                    swimmer = meet.Name[(meet.Swim == swim) & (meet.Fastest == time)].values[0]
                    records_data.append([swimmer, swim, time, record_holder])
        else:
            time = meet.Fastest[meet.Swim == swim].min()
            name = meet.Name[(meet.Swim == swim) & (meet.Fastest == time)].values[0]
            records_data.append([name, swim, time, 'New Record'])

    # Create DataFrame
    records_df = pd.DataFrame(records_data, columns=['Swimmer', 'Event', 'Time', 'Previous Record Holder'])

    # Export to Excel
    with pd.ExcelWriter(meetName + '_Records_Report.xlsx') as writer:
        records_df.to_excel(writer, sheet_name="Records", index=False)

def record_update(records):
    for swim in swims:
        if swim in records.Swim.unique():
            for time in meet[meet.Swim==swim].Fastest:
                if time < records[records.Swim==swim].Time.values[0]:
                    records.loc[records.Swim==swim,'Name']=meet.Name[(meet.Swim ==swim)&(meet.Fastest == time)].values[0]
                    records.loc[records.Swim==swim,'Time']=time
                    records.loc[records.Swim==swim,'Date']=meet.Date[(meet.Swim ==swim)&(meet.Fastest == time)].values[0]
    
        else:
            time = meet.Fastest[meet.Swim == swim].min()
            name = meet.Name[(meet.Swim ==swim)&(meet.Fastest == time)].values[0]
            agegroup = meet.Agegroup[(meet.Swim ==swim)&(meet.Fastest == time)].values[0]
            gender = meet.Gender[(meet.Swim ==swim)&(meet.Fastest == time)].values[0]
            event = meet.Event[(meet.Swim ==swim)&(meet.Fastest == time)].values[0]
            date = meet.Date[(meet.Swim ==swim)&(meet.Fastest == time)].values[0]
            records.loc[len(records.index)] = [agegroup,gender,event,time,name,date,swim]
            
            
    updated = records.filter(['Agegroup','Gender','Event','Time','Name','Date'])
    
    updated.to_csv('SCY-Records.csv',index = False)

