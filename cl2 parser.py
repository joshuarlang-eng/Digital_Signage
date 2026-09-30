# -*- coding: utf-8 -*-
"""
Spyder Editor

An attempt to parse a .cl2 file and save it as a .csv file
"""

import os

path = 'cl2 files'

team_code = input('What is the team code for the team you want to export?')

def parse_file(file):

    file_1 = open(file,'r')
    lines_1 = file_1.readlines()
    file_1.close()
    
    def get_meet_info():
        """  
        Returns
        -------
        meet_name : str
            The name of the meet.
        meet_start : str
            The start date of the meet.
        meet_end : str
            The end date of the meet.
            
        Example
        -------
        Team_name,Meet_start,Meet_end = get_meet_info()
        """
        for line in lines_1:
            if line[:2]=='B1':
                meet_name = line[11:41]
                meet_start = line[121:129]
                meet_start = meet_start[:2]+'/'+ meet_start[2:4] + '/' + meet_start[4:8]
                meet_end = line[129:137]
                meet_end = meet_end[:2]+'/'+ meet_end[2:4] + '/' + meet_end[4:8]
                
        return meet_name,meet_start,meet_end
    
    
    def get_team_range(team):
        """
        Parameters
        ----------
        team : str
            the call letters for the team desired.
    
        Returns
        -------
        team_start : int
            the index of the list of records that begins the data for team.
        team_end : int
            the index of the list of records that begins the data for the next team (end of team).
    
        Example
        -------
        team,team_start,team_end = get_team_range()
        """
        try:
            for line in lines_1:
                if line[:2]=='C1' and line[13:13+len(team)]==team:
                    team_start = (lines_1.index(line))
                
            for line in lines_1:    
                if line[:2]=='C1' and lines_1.index(line)>team_start or line[:2]=='Z0':
                    team_end = (lines_1.index(line))
                    
                    break
                
            return team_start,team_end
        
        except TypeError:
            print("\n\nTeam not found\n\n")
            
        except UnboundLocalError:
            print('\n\nTeam not found\n\n')
    
    event_table = {1:'Free', 2:'Back', 3:'Breast', 4:"Fly", 5:'IM', 6:'Free Relay', 7:'Medley Relay'}
    
    

    meet_name,meet_start,meet_end = get_meet_info()
    meet_name = meet_name.strip()
    start,end = get_team_range(team_code)
    
    file_name = 'csv files/'+team_code+' '+meet_name+'.csv'
    
    f=open(file_name,'w')
    f.write('Last,First,Age,Gender,Distance,Stroke,Entry,Time,Place,Points,Meet,Date\n')
    f.close()
    
    def get_swims():
        for line in lines_1[start:end]:
            if line[:2]=='D0':
                swimmer_name = line[11:39].strip()
                swimmer_name = swimmer_name.replace(', Jr','')
                swimmer_last, swimmer_first = swimmer_name.split(', ')
                swimmer_age = line[63:65].strip()
                swimmer_gender = line[66]
                event_dist = line[67:71].strip()
                event_stroke = event_table[int(line[71])]
                entry_time = line[88:96].strip()
                prelims_time = line[97:105].strip()
                finals_time = line[115:123].strip()
                event_place = line[135:138].strip()
                event_points = line[139:142].strip()
                #print(swimmer_first, swimmer_last,swimmer_age,swimmer_gender,event_dist,event_stroke,entry_time,event_time,event_place,event_points)
    
                if prelims_time == '':
                    event_time = finals_time
                    
                else:
                    event_time = prelims_time
    
                f=open(file_name,'a')
                f.write(swimmer_last+','+swimmer_first+','+swimmer_age+','+swimmer_gender+','+event_dist+','+event_stroke+','+entry_time+','+event_time+','+event_place+','+event_points+','+meet_name+','+meet_start+'\n')
                f.close()
    
    
    
    
    
    get_swims()

try:    

    for stuff in os.listdir(path):
        parse_file(path+'/'+stuff)
        print('{} has been processed for team {}.'.format(stuff,team_code))

except:
    pass