from bs4 import BeautifulSoup
import urllib2
from urllib2 import urlopen
import cookielib
from cookielib import CookieJar
from datetime import datetime, timedelta
#  import sqlite3
from time import sleep   #tells your program to run and then pause (for updated data)
import sys
import csv
import mechanize
import os

# CONSTANTS
ESPN_URL = "http://scores.espn.go.com"  ##global var
conferences = {'2': 'ACC', '7': 'Big Ten', '23': 'SEC', '3': 'A 10', '21': 'Pac-12', '8': 'Big 12', '4': 'Big East'} #conferences of interest
cj = CookieJar() # Not absolutely necessary but recommended
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
opener.addheaders = [('User-agent', 'Mozilla/5.0')] # To be able to crawl on websites that blocks Robots

#print ("hello")
def make_soup(url):
    soup = BeautifulSoup(opener.open(url).read(), "html.parser")
    soup.prettify()
    #print soup
    return soup


def get_games(date, confid):
    """
    Gets all the play-by-play URLs for a given date (YYYYMMDD).
    Fair warning: ESPN doesn't have play-by-play data for all games.
    """
    #print date

    try:
        soup = make_soup(ESPN_URL + "/ncb/scoreboard?date={0}&confId={1}".format(date, confid))   #all {ACC} games
    except Exception, e:
        pass
    

    #"get's all conferences?  /ncb/scoreboard?date=""
    #array of span tags that start with, start with id and end with "-gamelinks-expand", 
    #eg <span id="400589301-gameLinks-expand"><a href="/ncb/boxscore?gameId=400589301">Box&nbsp;Score</a>&nbsp;&#187;&nbsp;  <a href="/ncb/playbyplay?gameId=400589301">Play&#8209;By&#8209;Play</a>&nbsp;&#187;&nbsp;  <a href="/ncb/video?gameId=400589301">Videos</a>&nbsp;&#187;&nbsp;  <a href="/ncb/photos?gameId=400589301">Photos</a>&nbsp;&#187;&nbsp;  <a href="/ncb/conversation?gameId=400589301">Conversation</a>&nbsp;&#187;&nbsp;  </span>
    #x.lower changes everything to all lower case 
    games = soup.find_all("span",
        {"id": lambda x: x and x.lower().endswith("-gamelinks-expand")})   #gets game ID "from gameLinks-expand
    
    #print games[0]

    #this gets all href game ID urls pieces, eg <a href="/ncb/playbyplay?gameId=400589301">            
    link_sets = [game.find_all("a") for game in games]  #looking for everything inside games array with "a" tag 
    
    #print link_sets[0]

    play_by_plays = []
    #looks for all href tags and if there's a play by play tag, append to the array 
    ##array of links eg /ncb/playbyplay?gameId=400589301
    #Sprint "hello"
    for link_set in link_sets:
        for link in link_set:
            href = link.get("href")
            if "playbyplay" in href:
                play_by_plays.append(href)
                #print href
    return play_by_plays


def get_play_by_play(pbp_path, current_date):
    "Returns the play-by-play data for a given game id."
    #print (ESPN_URL + pbp_path)
    soup = make_soup(ESPN_URL + pbp_path)  #make_soup opens the url and returns the source code
#<<<<<<< HEAD
    table = soup.find("table", class_ = "mod-data mod-pbp")   #find the only table tag and returns string (find_all returns array)
    ##table has table row and table data (tr, td), but table var is a string**
    #print "------------------------------"
    #print soup
    #print "------------------------------"
    '''table = soup.find_all("div", "story-container")   #find the only table tag and returns string (find_all returns array)
    '''##table has table row and table data (tr, td), but table var is a string**
#>>>>>>> 8c94b1874697e0be2b50ddaf102d215faf710eb4
    #table rows has class for odd or even (probly why the table on espn is switched colors)
    #rows is an matrix of tr tags with even or odd 
    #eg <tr class="even"><td valign=top width=50>19:53</td><td valign=top>&nbsp;</td><td valign=top style="text-align:center;" NOWRAP>0-0</td><td valign=top>Karl-Anthony Towns missed Three Point Jumper.</td></tr>
    #each row in rows is an array of td's
    #print table
    #find_all splits table string into array by tr 

    #rows = []
    #print tbl

    rows = [row.find_all("td") for row in soup.find_all("tr",
        lambda x: x in ("odd", "even"))]

    data = []
    for row in rows:
        values = []
        for value in row:
            #if td is empty, append nothing/empty string; u might be unicode?
            #each string must be converted to unicode so you can process it
            ##some emoji's show up as boxes vs a emoji --> convert to unicode
            if value.string is None:    
                values.append(u"")
            else:
            #unicode has u"\xa0" as whitespace?, get rid of it and replace w/blank space
                values.append(value.string.replace(u"\xa0", u" "))   #u"\xa0" is unicode stuff -- read this 
        # handle timeouts being colspan=3
        # repeat the timeout or note in the other columns
        #</tr><tr class="odd"><td valign=top width=50>17:28</td><td colspan=3 style="text-align:center;"><b>Kentucky  Timeout</b></td></tr>
        #kentucky timeout spanned 3 colms


        if len(values) != 4:
            #print values
            values = [values[0], values[1], values[1], values[1]]  #timeout replaced multiple times 

        data.append(values)

    '''Find Home and Away Team infos for the game'''
    game_data = []
    team_data = []
    game_data = [current_date, pbp_path.lower().split("gameid=")[1]]
    for team in ["team home", "team away"]:
        matchup = soup.find("div", "matchup")
        the_team = soup.find("div", team)
        team_Name = the_team.find("a").text  #away team name 
        team_Rank = ""   #away team rank 
        rank = the_team.find("span", "rank")
        if rank:
            team_Rank = rank.text
        team_Record = the_team.find("p").text   #away team record 
        
        team_data.extend([team_Name, team_Rank, team_Record])
        team_data = [x.replace(u"\xa0", u" ") for x in team_data]
        #print "Name: %s, Rank %s, Record %s\n"%(team_Name, team_Rank, team_Record)
    #print game_data + team_data
    game_data = game_data + team_data

    #print game_data
    return data, game_data

def execute(START_DATE, END_DATE, confid):
    d = START_DATE
    delta = timedelta(days=1)

    game_details = []

    while d <= END_DATE:
        print "Getting data for: {0}".format(d.strftime("%Y-%m-%d"))
        
        #games is array with /ncb/playbyplay?gameId=400589301
        try:
            games = get_games(d.strftime("%Y%m%d"), confid)  #string format for date time 
            for game in games:
                game_id = game.lower().split("gameid=")[1]

                # I didn't feel like dealing with unicode characters
                try:
                    print "Writing data for game: {0}".format(game_id)
                    #save the data 
                    #cbb-play-data/ is a directory/folder and will write separate file for each game
                    pbp, game_data = get_play_by_play(game, d.strftime("%Y-%m-%d"))

                    game_details.append(game_data)
                    
                    if pbp:
                        filename = "PLAY_DATA/{0}/{1}/".format(conferences[confid], d.strftime("%Y-%m-%d")) + game_id + ".csv"
                        if not os.path.exists(os.path.dirname(filename)):
                            os.makedirs(os.path.dirname(filename))
                        with open(filename, "w") as f:
                            writer = csv.writer(f, delimiter="\t")
                            #header of the data 
                            writer.writerow(["time", "away", "score", "home"])
                            writer.writerows(pbp)
                        
                except UnicodeEncodeError:
                    print "Unable to write data for game: {0}".format(game_id)
                    print "Moving on ..."
                    continue
        except Exception, e:
            print "Error encountered....... Skipped!"
        d += delta
        sleep(.5) # be nice

    #print game_details
    with open("gameIDs/{0}_Team_GameIDs.csv".format(conferences[confid]), "w") as f:
                        writer = csv.writer(f, delimiter="\t")
                        #header of the data 
                        writer.writerow(["Date", "GameID", "HomeTeam", "HomeRank", "HomeRecord", "AwayTeam", "AwayRank", "AwayRecord"])
                        writer.writerows(game_details)

if __name__ == '__main__':
    try:
        START_DATE = datetime.strptime(sys.argv[1], "%Y-%m-%d")
        END_DATE = datetime.strptime(sys.argv[2], "%Y-%m-%d")
    except IndexError:
        print "I need a start and end date ('YYYY-MM-DD')."
        sys.exit()
    for confid in conferences.keys():

        print "..::Executing for conference: " + conferences[confid] + "::.."
        execute(START_DATE, END_DATE, confid)

    print "Done!"