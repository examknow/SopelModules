# This is the live version
import time
import json
import threading
import sqlite3
import requests
from sopel import module
from sopel import tools
from sseclient import SSEClient as EventSource

reports = []

with open('/home/ubuntu/.sopel/modules/wikiList2.txt', 'r') as f:
    wikiList = f.read().splitlines()

class wiki():
    
    db = sqlite3.connect("/home/ubuntu/.sopel/modules/wiki.db", check_same_thread=False)
    c = db.cursor()
    data = c.execute('SELECT * from config;').fetchall()[0]
    stream, botAct, botPass, csrf, botNick = data
    wikiList = open('/home/ubuntu/.sopel/modules/wikiList.txt', 'r')
    
    def checkTable(project):
        # Checks for tables existence. Returns 1 for True and 0 for False and NoneType for error
        try:
            data = wiki.c.execute('''SELECT count(*) FROM sqlite_master WHERE type="table" AND name="%s";''' % project).fetchone()
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
            check = wiki.c.execute('''SELECT * FROM %s WHERE page="%s";''' % (project, title)).fetchone()
            return check
        except:
            return None
    
    def getPage(project, title):
        # If checkPage(project, title) returned an existing page, get the info to process
        try:
            data = wiki.c.execute('''SELECT * FROM %s WHERE page="%s";''' % (project, title)).fetchall()
            return data
        except:
            return None
    
    def getPageNicks(project, page, chan):
        # While processing getPage(project, title), get the specific nicks we need to notify per channel
        try:
            data = wiki.c.execute('''SELECT nick from %s where page="%s" and channel="%s" and notify="yes";''' % (project, page, chan)).fetchall()
            return data
        except:
            return None
    
    def checkNewPage(project, page, nick, channel):
        try:
            check = wiki.c.execute('''SELECT * from %s where page="%s" and nick="%s" and channel="%s";''' % (project, page, nick, channel)).fetchone()
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
            work = wiki.c.execute('''UPDATE %s set notify="%s" where page="%s" and nick="%s" and channel="%s";''' % (project, notify, page, nick, channel))
            wiki.db.commit()
            return True
        except:
            return None
    
    def deletePage(project, page, nick, channel):
        try:
            work = wiki.c.execute('''DELETE FROM %s WHERE page="%s" AND channel="%s" AND nick="%s";''' % (project, page, channel, nick))
            wiki.db.commit()
            return True
        except:
            return None
    
    def listPages(project):
        try:
            data = wiki.c.execute('''SELECT page from %s;''' % project).fetchall()
            return data
        except:
            return None

    def checkSysop(actName):
        # Check to see if a username is in the Global Sysops table. Returns 1 for yes, 0 for no, None for error
        try:
            response = wiki.c.execute('''SELECT account from globalsysops where account="%s";''' % actName).fetchall()
            return response
        except:
            return None

def logSend(change):
    db = sqlite3.connect("/home/ubuntu/.sopel/modules/wiki.db", check_same_thread=False)
    c = db.cursor()
    editor = change['user']
    GSes = None
    try:
        GSes = c.execute('''SELECT account from globalsysops where account="%s";''' % editor).fetchall()
    except:
        pass
    if len(GSes) > 0:
        action = str(change['log_type']).upper()
        pageLink = change['meta']['uri']
        project = change['wiki']
        space = u'\u200B'
        editor = editor[:2] + space + editor[2:]
        title = change['title']
        comment = str(change['comment']).replace('\n','')
        report = None
        if action == "NEWUSERS":
            pass
            #report = "Account created: " + editor + " " + pageLink
        elif action == "BLOCK":
            flags = change['log_params']['flags']
            duration = change['log_params']['duration']
            actionType = change['log_action']
            report = "Log action: " + action + " || " + editor + " " + actionType + "ed " + pageLink + " Flags: " + flags + " Duration: " + duration + " Comment: " + comment[:200]
        elif action == "ABUSEFILTER":
            report = action + " activated by " + editor + " " + pageLink
        elif action == "MOVE":
            report = "Log action: " + action + " || " + editor + " moved " + pageLink + " " + comment[:200]
        elif action == "PATROL" or action == "REVIEW" or action == "THANKS" or action == "UPLOAD" or action == "ABUSEFILTER" or action == "MASSMESSAGE":
            pass
        else:
            report = "Log action: " + action + " || " + editor + " " + pageLink + " " + comment[:200]
        if report is not None:
            channel = "##873bots"
            report = channel + " " + report
            reports.append(report)

def editSend(change):
    db = sqlite3.connect("/home/ubuntu/.sopel/modules/wiki.db", check_same_thread=False)
    c = db.cursor()
    proj = change['wiki']
    title = str(change['title'])
    chRev = str(change['revision']['new'])
    chURL = change['server_url']
    chDiff = chURL + "/w/index.php?diff=" + chRev
    chComment = change['comment']
    editor = change['user']
    check = None
    channel = "##OperTestBed"
    try:
        check = c.execute('''SELECT * FROM %s where page="%s";''' % (proj, title)).fetchall()
    except:
        pass
    if check is not None:
        channels = []
        for record in check:
            dbPage, dbNick, dbChan, notify = record
            channels.append(dbChan)
        channels = list(dict.fromkeys(channels)) # Collapse duplicate channels
        for chan in channels:
            nicks = ""
            pgNicks = c.execute('SELECT nick from %s where page="%s" and channel="%s" and notify="on";' % (proj, title, chan)).fetchall()
            if len(pgNicks) > 0:
                for nick in pgNicks:
                    if nicks == "":
                        nicks = nick[0]
                    else:
                        nicks = nick[0] + " " + nicks
                newReport = chan + " " + nicks + ": \x02" + title + "\x02 on " + proj + " was edited by \x02" + editor + "\x02 " + chDiff + " " + chComment
            else:
                newReport = chan + " \x02" + title + "\x02 on " + proj + " was edited by \x02" + editor + "\x02 " + chDiff + " " + chComment
            reports.append(newReport)

def dispatcher(change):
    if change['type'] == "log":
        if change['wiki'] in wikiList:
            logSend(change)
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
    if wiki.checkNewPage(project, page, nick, chan):
        if wiki.deletePage(project, page, nick, chan) is not None:
            response = "%s: I won't report changes to %s on %s anymore." % (nick, page, project)
        else:
            response = "Ugh. Something blew up. Operator873 help me..."
    else:
        response = "%s: It doesn't look like you're watching %s on %s." % (nick, page, project)
    return response

def watcherPing(msg, nick, chan):
    db = sqlite3.connect("/home/ubuntu/.sopel/modules/wiki.db", check_same_thread=False)
    c = db.cursor()
    action, switch, project, page = msg.split(' ', 3)
    readChange = None
    if switch == "on" or switch == "On" or switch == "off" or switch == "Off":
        readChange = c.execute('''UPDATE %s set notify="%s" where page="%s" and nick="%s" and channel="%s";''' % (project, switch, page, nick, chan))
        db.commit()
        response = "Ping set to " + switch + " for " + page + " on " + project + " in this channel."
    else:
        response = "Malformed command! Try: !watch ping {on/off} project The page you want"
    return response

def updateGSwikis():
    with open('/home/ubuntu/.sopel/modules/wikiList.txt', 'w') as repo:
        repo.write("")
    connect = requests.Session()
    checkurl = 'https://meta.wikimedia.org/w/api.php'
    myParams = {
        'format':"json",
        'action':"query",
        'list':"wikisets",
        'wsprop':"wikisincluded",
        'wsfrom':"Opted-out of global sysop wikis"
    }

    agent = {
        'User-Agent': 'Bot873 v0.1 using Python3.7 Sopel',
        'From': 'operator873@873gear.com'
    }
    DATA = connect.get(checkurl, headers=agent, params=myParams).json()
    wikis = DATA['query']['wikisets'][0]
    check = wikis['wikisincluded']
    with open('/home/ubuntu/.sopel/modules/wikiList.txt', 'w') as repo:
        for x in check:
            repo.write('%s\n' % check[x])

def readWikiList():
    count = len(open('/home/ubuntu/.sopel/modules/wikiList.txt', 'r').read().splitlines())
    response = "I am monitoring " + str(count) + " wikis for GS edits."
    return response
        
def checkReporter(bot):
    if len(reports) > 0:
        for item in reversed(reports):
            channel, msg = item.split(' ', 1)
            bot.say(msg, channel)
            reports.remove(item)

listen = threading.Thread(target=listener, args=(wiki.stream,))

@module.require_owner(message="This function is only available to Operator873")
@module.commands('watchstart')
def watchstart(bot, trigger):
    listen.start()
    bot.say("Listening to EventStream...", "##Operator873")

@module.require_owner(message="This function is only available to Operator873")
@module.commands('readGSwikis')
def readGSwikis(bot, trigger):
    updateGSwikis()
    bot.say("GS wikis have been updated.")

@module.require_owner(message="This function is only available to Operator873")
@module.commands('readdbrows')
def readdb(bot, trigger):
    proj, page = trigger.group(2).split(' ', 1)
    data = wiki.getPage(proj, page)
    for item in data:
        bot.say(str(item), trigger.sender)

@module.require_owner(message="This function is only available to Operator873")
@module.commands('readdbtables')
def readdbtable(bot, trigger):
    if wiki.checkTable(trigger.group(3))[0] > 0:
        pages = wiki.listPages(trigger.group(3))
        bot.say("I have a table called " + trigger.group(3) + ". The rows are called: " + str(pages))
    else:
        bot.say("I do not have a table called " + trigger.group(3))

@module.require_owner(message="This function is only available to Operator873")
@module.commands('getdbpage')
def getdbpage(bot, trigger):
    project, page = trigger.group(2).split(' ', 1)
    if wiki.getPage(project, page):
        bot.say("Yes.")

@module.priority("high")
@module.interval(5)
def checkReports(bot):
    checkReporter(bot)

@module.interval(3600)
def checkListener(bot):
    if listen.is_alive() is not True:
        listen.start()
        bot.say("Restarted listener", "Operator873")
    else:
        pass

@module.require_owner(message="This function is only available to Operator873")
@module.commands('countwikis')
def cmdreadWikilist(bot, trigger):
    bot.say(readWikiList())

@module.require_owner(message="This function is only available to Operator873")
@module.commands('watchstatus')
def watchStatus(bot, trigger):
    msg = trigger.sender + " Reader is functioning."
    if listen.is_alive() is True:
        msg = msg + " Listener is alive."
    reports.append(msg)

@module.require_owner(message="This function is only available to Operator873")
@module.commands('watchstop')
def watchStop(bot, trigger):
    listen.join()
    reports = []
    bot.say("Listener stopped. Reports container dumped.")
    
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
