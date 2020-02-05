# This is the live version
import json
from sopel import module
from sopel import tools
from sseclient import SSEClient as EventSource

watcherList = json.load(open('/home/ubuntu/.sopel/modules/WatcherDB.json', encoding='utf-8'))

class watcher():
    check = "off"
    url = "https://stream.wikimedia.org/v2/stream/recentchange"

def watcherRead(bot, change):
    if change['wiki'] in watcherList.keys():
        try:
            changeWiki = str(change['wiki'])
            changeTitle = str(change['title'])
            chRev = str(change['revision']['new'])
            chURL = str(change['server_url'])
            chDiff = chURL + "/w/index.php?diff=" + chRev
            chComment = change['comment']
            chEditAccount = str(change['user'])
            for item in watcherList[changeWiki][changeTitle]:
                chNick = str(item['actName'])
                chNotify = str(item['notify'])
                chChan = str(item['channel'])
                if watcherList['switch'][chNick] == "on":
                    if chNotify == "yes":
                        watchResponse = chNick + ": " + changeTitle + " was edited by " + chEditAccount + ". " + chDiff + " Summary: " + chComment
                    else:
                        watchResponse = changeTitle + " was edited by " + chEditAccount + ". " + chDiff + " Summary: " + chComment
                    bot.say(watchResponse, chChan)
        except KeyError:
            pass

def watcherAdd(nick, channel, wiki, page):
    newEntry = {"actName": nick, "notify": "no", "channel": channel}
    if wiki in watcherList.keys():
        if page in watcherList[wiki].keys():
            watcherList[wiki][page].append(newEntry)
        else:
            watcherList[wiki][page] = newEntry
            watcherList[wiki][page] = [watcherList[wiki][page]]
    else:
        watcherList[wiki] = {page: [newEntry]}
    with open('/home/ubuntu/.sopel/modules/WatcherDB.json', "w") as jsonFile:
        json.dump(watcherList, jsonFile)
    addResult = page + " on " + wiki + " added to alerts for " + nick + " in channel: " + channel
    return addResult

def watcherDel(nick, channel, wiki, page):
    try:
        for item in watcherList[wiki][page]:
            if item['actName'] == nick and item['channel'] == channel:
                findIndex = watcherList[wiki][page].index(item)
                watcherList[wiki][page].pop(findIndex)
                with open('/home/ubuntu/.sopel/modules/WatcherDB.json', "w") as jsonFile:
                    json.dump(watcherList, jsonFile)
                delResult = page + " removed from " + wiki + " for " + nick
                return delResult
    except KeyError:
        delResult = "Page not found for that user."
        return delResult

def watcherOff(nick, switchSet):
    watcherList['switch'][nick] = "off"
    offResponse = "Recent Change reports disabled for " + nick + "."
    with open('/home/ubuntu/.sopel/modules/WatcherDB.json', "w") as jsonFile:
        json.dump(watcherList, jsonFile)
    return offResponse

def watcherOn(nick, switchSet):
    watcherList['switch'][nick] = "on"
    onResponse = "Recent Change reports enable for " + nick + "."
    with open('/home/ubuntu/.sopel/modules/WatcherDB.json', "w") as jsonFile:
        json.dump(watcherList, jsonFile)
    return onResponse

@module.require_owner(message="This function is only available to the bot owner.")
@module.commands('watchstart')
def watchstart(bot, trigger):
    if watcher.check == "off":
        bot.say("Starting EventStream processing...", "##YourChannel")
        watcher.check = "on"
        while watcher.check is "on":
            for event in EventSource(watcher.url):
                if event.event == 'message':
                    try:
                        change = json.loads(event.data)
                        watcherRead(bot, change)
                    except ValueError:
                        continue
    else:
        bot.say("EventStream processing already running.", "##YourChannel")

@module.require_owner(message="This function is only available to the bot owner.")
@module.commands('watchstop')
def watchstop(bot, trigger):
    bot.say("Stopping EventStream processing...", "##YourChannel")
    watcher.check = "off"

@module.require_owner(message="This function currently being tested and is only available to the bot owner.")
@module.require_chanmsg(message="This message must be used in the channel")
@module.commands('watch')
def watch(bot, trigger):
    watchAction = trigger.group(3)  
    if watchAction == "add" or watchAction == "Add" or watchAction == "+":
        chan = trigger.sender
        if trigger.group(5) == "":
            bot.say("command seems misformed. Format: !watch add proj page")
        wiki = trigger.group(4)
        page = trigger.group(2).split(' ', 2)
        page = page.replace("_", " ")
        bot.say(watcherAdd(trigger.nick, chan, wiki, page[2]))
    elif watchAction == "del" or watchAction == "Del" or watchAction == "-":
        chan = trigger.sender
        if trigger.group(5) == "":
            bot.say("command seems misformed. Format: !watch del proj page")
        wiki = trigger.group(4)
        page = trigger.group(2).split(' ', 2)
        page = page.replace("_", " ")
        bot.say(watcherDel(trigger.nick, chan, wiki, page[2]))
    elif watchAction == "off" or watchAction == "Off":
        switch = trigger.group(3)
        bot.say(watcherOff(trigger.nick, switch))
    elif watchAction == "on" or watchAction == "On":
        switch = trigger.group(3)
        bot.say(watcherOn(trigger.nick, switch))
    else:
        bot.say("I don't recognize that command. Options are: Add, Del, On, Off.")

@module.require_chanmsg(message="This message must be used in the channel")
@module.commands('pingon')
def watchNotifier(bot, trigger):
    project = trigger.group(3)
    page = trigger.group(2).split(' ', 1)
    page = page[1].replace("_", " ")
    nick = trigger.nick
    try:
        for item in watcherList[project][page]:
            if item['actName'] == nick:
                item['notify'] = "yes"
                with open('/home/ubuntu/.sopel/modules/WatcherDB.json', "w") as jsonFile:
                    json.dump(watcherList, jsonFile)
                bot.say("I will notify " + nick + " of changes to " + page + " on " + project + ".")
    except KeyError:
        bot.say("It doesn't look like you're following that page.")

@module.require_chanmsg(message="This message must be used in the channel")
@module.commands('pingoff')
def watcherQuiet(bot, trigger):
    project = trigger.group(3)
    page = trigger.group(2).split(' ', 1)
    page = page[1].replace("_", " ")
    nick = trigger.nick
    try:
        for item in watcherList[project][page]:
            if item['actName'] == nick:
                item['notify'] = "no"
                with open('/home/ubuntu/.sopel/modules/WatcherDB.json', "w") as jsonFile:
                    json.dump(watcherList, jsonFile)
                bot.say("I will no longer notify " + nick + " of changes to " + page + " on " + project + ".")
    except KeyError:
        bot.say("It doesn't look like you're following that page.")
