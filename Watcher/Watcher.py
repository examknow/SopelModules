# This is the live version
import time
import json
import threading
import sqlite3
from sopel import module
from sopel import tools
from sseclient import SSEClient as EventSource

class watcher():
    reports = []
    logReports = []

class wiki():
    
    db = sqlite3.connect("/home/ubuntu/.sopel/modules/wiki.db", check_same_thread=False)
    c = db.cursor()
    data = c.execute('SELECT * from config;').fetchall()[0]
    stream, botAct, botPass, csrf, botNick = data
    hushList = ["simplewiki", "ptwiki", "enwiki", "wikidata", "metawiki"]
    
    def checkTable(project):
        # Checks for tables existence. Returns 1 for True and 0 for False and NoneType for error
        try:
            data = wiki.c.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="%s";' % project).fetchone()
            return data
        except:
            return None
    
    def createTable(project):
        # Creates a new table... Used after checking with checkTable(project)
        try:
            wiki.c.execute('CREATE TABLE ' + project + '(page TEXT, nick TEXT, channel TEXT, notify TEXT);')
            wiki.db.commit()
            return True
        except:
            return None
    
    def checkPage(project, title):
        # Check and see if EventStream item needs to be processed
        try:
            check = wiki.c.execute('SELECT * from %s where page="%s";' % (project, title)).fetchone()
            return check
        except:
            return None
    
    def getPage(project, title):
        # If checkPage(project, title) returned an existing page, get the info to process
        try:
            data = wiki.c.execute('SELECT * from %s where page="%s";' % (project, title)).fetchall()
            return data
        except:
            return None
    
    def getPageNicks(project, page, chan):
        # While processing getPage(project, title), get the specific nicks we need to notify per channel
        try:
            data = wiki.c.execute('SELECT nick from %s where page="%s" and channel="%s" and notify="yes";' % (project, page, chan)).fetchall()
            return data
        except:
            return None
    
    def checkNewPage(project, page, nick, channel):
        try:
            check = wiki.c.execute('SELECT * from %s where page="%s" and nick="%s" and channel="%s";' % (project, page, nick, channel)).fetchone()
            return check
        except:
            return None
        
    def createPage(project, page, nick, channel):
        # Add a page to be watched by a nick. Should be used after checking for already watched page
        try:
            notify = "no"
            schema = "INSERT INTO " + project + "(page, nick, channel, notify) VALUES(?,?,?,?);"
            wiki.c.execute(schema, (page, nick, channel, notify))
            wiki.db.commit()
            return True
        except:
            return None
    
    def setNotify(project, page, nick, channel, notify):
        # Change the notify settings of an entry
        try:
            work = wiki.c.execute('UPDATE %s set notify="%s" where page="%s" and nick="%s" and channel="%s";' % (project, notify, page, nick, channel))
            wiki.db.commit()
            return True
        except:
            return None
    
    def deletePage(project, page, nick, channel):
        try:
            wiki.c.execute('DELETE FROM ' + project + 'WHERE page="%s" AND channel="%s" AND nick="%s";' % (page, channel, nick))
            wiki.db.commit()
            return True
        except:
            return None

    def checkSysop(actName):
        # Check to see if a username is in the Global Sysops table. Returns 1 for yes, 0 for no, None for error
        try:
            response = wiki.c.execute('SELECT account from globalsysops where account="%s";' % actName).fetchall()
            return response
        except:
            return None
    
    # Need addSysop(nick, actName)
    
    # Need delSysop(nick, actName)
    
def logSend(change):
    action = str(change['log_type']).upper()
    pageLink = change['meta']['uri']
    editor = change['user']
    title = change['title']
    comment = str(change['comment']).replace('\n','')
    report = None
    if action == "NEWUSERS":
        report = "Account created: " + editor + " " + pageLink
    elif action == "BLOCK":
        report = "Log action: " + action + " || " + editor + " blocked " + pageLink + " " + comment[:200]
    elif action == "ABUSEFILTER":
        report = action + " activated by " + editor + " " + pageLink
    elif action == "MOVE":
        report = "Log action: " + action + " || " + editor + " moved " + pageLink + " " + comment[:200]
    elif action == "PATROL" or action == "REVIEW" or action == "THANKS" or action == "UPLOAD":
        pass
    else:
        report = "Log action: " + action + " || " + editor + " " + pageLink + " " + comment[:200]
    if report is not None:
        watcher.logReports.append(report)

def editSend(change):
    changeWiki = change['wiki']
    if wiki.checkTable(changeWiki) is not None:
        changeTitle = change['title']
        chRev = str(change['revision']['new'])
        chURL = change['server_url']
        chDiff = chURL + "/w/index.php?diff=" + chRev
        chComment = change['comment']
        if wiki.checkPage(changeWiki, changeTitle):
            data = wiki.getPage(changeWiki, changeTitle)
            channels = []
            for record in data:
                if record[3] == "yes":
                    channels.append(record[2])
            channels = list(dict.fromkeys(channels)) # Collapse duplicate channels
            for chan in channels:
                nicks = ""
                data = wiki.getPageNicks(changeWiki, changeTitle, chan)
                for nick in data:
                    if nicks == "":
                        nicks = nick[0]
                    else:
                        nicks = nick[0] + " " + nicks
                newReport = chan + " " + nicks + ": " + changeTitle + " was edited. " + chDiff + " Summary: " + chComment
                watcher.reports.append(newReport)

def dispatcher(change):
    if change['type'] == "log":
        if wiki.checkSysop(change['user']) and change['wiki'] not in wiki.hushList:
            logSend(change)
        else:
            pass
    elif change['type'] == "edit":
        editSend(change)
    else:
        pass

def listener(url):
    for event in EventSource(url):
        if event.event == 'message':
            try:
                change = json.loads(event.data)
                dispatcher(change)
            except ValueError:
                pass

def watcherAdd(msg, nick, chan):
    action, project, page = msg.split(' ', 2)
    if wiki.checkTable(project) is None:
        if wiki.createTable(project) is None:
            response = "Error creating table! Help me Operator873..."
            return response
    if wiki.checkNewPage(project, page, nick, chan) is None:
        if wiki.createPage(project, page, nick, chan) is not None:
            response = "%s: I will report changes to %s on %s in this channel with no ping." % (nick, page, project)
        else:
            response = "Ugh. Something blew up. Operator873 help me..."
    else:
        response = "%s: I'm already reporting changes to %s for you here." % (nick, page)
    return response

def watcherDel(msg, nick, chan):
    action, project, page = msg.split(' ', 2)
    if wiki.checkNewPage(project, page, nick, chan) is not None:
        if wiki.deletePage(project, page, nick, chan) is True:
            response = "%s: I won't report changes to %s on %s anymore." % (nick, page, project)
        else:
            response = "Ugh. Something blew up. Operator873 help me..."
    else:
        response = "%s: It doesn't look like you're watching %s on %s." % (nick, page, project)
    return response

def watcherPing(msg, nick, chan):
    action, switch, project, page = msg.split(' ', 3)
    if wiki.setNotify(project, page, nick, chan, switch) is not None:
        response = nick + ": pings are now " + switch + " for " + page + " on " + project + " in this channel."
    else:
        response = "Ugh. Something blew up. Operator873 help me..."
    return response

listen = threading.Thread(target=listener, args=(wiki.stream,))

@module.require_owner(message="This function is only available to Operator873")
@module.commands('watchstart')
def watchstart(bot, trigger):
    listen.start()
    bot.say("Listening to EventStream...", "##Operator873")

@module.interval(2)
def readlogReports(bot):
    if len(watcher.logReports) > 0:
        for report in watcher.logReports:
            bot.say(report, "##873bots")
            watcher.logReports.remove(report)

@module.interval(3)
def readEditReports(bot):
    if len(watcher.reports) > 0:
        for report in watcher.reports:
            channel, msg = report.split(' ', 1)
            bot.say(msg, channel)
            watcher.reports.remove(report)

@module.require_chanmsg(message="This message must be used in the channel")
@module.commands('watch')
def watch(bot, trigger):
    watchAction = trigger.group(3)  
    if watchAction == "add" or watchAction == "Add" or watchAction == "+":
        if trigger.group(5) == "":
            bot.say("Command seems misformed. Syntax: !watch add proj page")
        else:
            bot.say(watcherAdd(trigger.group(2), trigger.nick, trigger.sender))
    elif watchAction == "del" or watchAction == "Del" or watchAction == "-":
        if trigger.group(5) == "":
            bot.say("Command seems misformed. Syntax: !watch del proj page")
        else:
            bot.say(watcherDel(trigger.group(2), trigger.nick, trigger.sender))
    elif watchAction == "ping" or watchAction == "Ping":
        if trigger.group(6) == "":
            bot.say("Command seems misformed. Syntax: !watch del proj page")
        else:
            bot.say(watcherPing(trigger.group(2), trigger.nick, trigger.sender))
    else:
        bot.say("I don't recognzie that command. Options are: Add & Del")
