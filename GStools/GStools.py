from sopel import module
import json
import requests
import time
from urllib.parse import urlparse

gsdbase = json.load(open('/home/ubuntu/.sopel/modules/GSdbase.json', encoding='utf-8'))

class gsapi(): # Create a global class for ease of calling variables
    file = json.load(open('/home/ubuntu/.sopel/modules/GSwikis.json', encoding='utf-8')) # JSON file containing project apiurl and category associations
    users = json.load(open('/home/ubuntu/.sopel/modules/users.json', encoding='utf-8')) # File contiaining authorized users
    connect = requests.Session()
    greeting = "Hello friendly Global Sysop! Here is the information you requested..."
    intgreeting = "Hello Global Sysop! I'm delivering your requested daily update. Use <code>!daily del project</code> in {{irc|wikimedia-gs}} to stop these messages."
    intTitle = "Daily Global Sysop Update"
    secTitle = "Global Sysop Report for "
    site = "https://meta.wikimedia.org/w/api.php"
    csrf = ""
    gsEdit = ""
    title = "User:Bot873/GSRequest" # on-wiki output page (deprecated for now)
    login = {
    'action':"login",
    'lgname':"", # Add your bot's Special:BotPassword username here.
    'lgpassword':"", # Add your bot's Special:BotPassword password here.
    'lgtoken': "",
    'format':"json"
    }
    agent = {
        'User-Agent': 'Bot873 v0.1 using Python3.7 Sopel',
        'From': 'contact@873gear.com'
    }

def gsedit(project, actName, title): # function to edit on-wiki meta page
    if gsapi.csrf == "": # Check to see if we are currently logged in
        gslogin()
    editSummary = "Automated edit requested by editor via IRC."
    editPage = "User_talk:" + actName
    reqEdit = {
        'action':"edit",
        'format':"json",
        'title':editPage,
        'section':"new",
        'sectiontitle':title,
        'text':gsapi.gsEdit,
        'summary':editSummary,
        'minor':"true",
        'redirect':"true",
        'token':gsapi.csrf
    }
    # perform actual edit
    DATA = gsapi.connect.post(gsapi.site, headers=gsapi.agent, data=reqEdit).json()
    gsapi.gsEdit = "" # reset edit container

def gslogin(): # Simple login function. Obtains login token, logs in, and obtains csrf token
    loginQuery = {
        'action':"query",
        'meta':"tokens",
        'type':"login",
        'format':"json"
    }
    # Obtain login token
    DATA = gsapi.connect.get(gsapi.site, headers=gsapi.agent, params=loginQuery).json()
    gsapi.login['lgtoken'] = DATA['query']['tokens']['logintoken']
    # Login with login token
    DATA = gsapi.connect.post(gsapi.site, headers=gsapi.agent, data=gsapi.login).json()
    if DATA['login']['result'] == 'Success':
        reqtoken = {
            'action':"query",
            'meta':"tokens",
            'format':"json"
        }
        # if login was successful, obtain and store a csrf token
        DATA = gsapi.connect.get(gsapi.site, headers=gsapi.agent, params=reqtoken).json()
        gsapi.csrf = DATA['query']['tokens']['csrftoken']

def gsintRun(bot, gswikis, actName): # Alternate form of main function for silently doing the same work.
    gswikis = gswikis.split(',')
    for project in gswikis:
        gsLinks = ""
        wiki = gsapi.file[project]
        urlpre = urlparse(wiki['apiurl'])
        gsQuery = {
            'action':"query",
            'format':"json",
            'list':"categorymembers",
            'cmtitle':wiki['csdcat']
            } # Setup query for MediaWiki API
        while True: # 
            DATA = gsapi.connect.get(wiki['apiurl'], headers=gsapi.agent, params=gsQuery).json()
            for item in DATA['query']['categorymembers']: # iterate through results
                gshyper = str("#+https://" + urlpre.netloc + "/wiki/" + item['title'] + '+\n')
                gshyperlink = ''.join(gshyper).replace(" ", "_")
                gshyperlink = gshyperlink.replace("+", " ")
                if gsLinks == "":
                    gsLinks = "{{Hidden|header=" + project + "|content=" + '\n' + gshyperlink
                else:
                    gsLinks = gsLinks + gshyperlink
            if ('continue' not in DATA) or ('error' in DATA):
                break
            cont = DATA['continue']
            gsQuery.update(cont)
        if gsLinks != "": # conditionally format for page edit
            gsLinks = gsLinks + "}}" + '\n'
            gsapi.gsEdit = gsapi.gsEdit + gsLinks
    if gsapi.gsEdit is not "":
        gsapi.gsEdit = gsapi.intgreeting + gsapi.gsEdit + "~~~~" # finalize edit
        gsedit(gsapi.gsEdit, actName, gsapi.intTitle)

def gswork(bot, gswikis, actName): # Main function. Query requested wikis, store resuls
    gswikis = gswikis.split()
    for project in gswikis: # Begin working with each project, 1 by 1
        # Check to see if project is known
        if project not in gsapi.file:
            bot.say("I don't know " + project + "... You can add it by using !gsadd wikiabrev fullAPIurl Category:CSD category. Example: !gsadd enwiki https://en.wikipedia.org/w/api.php Category:Candidates for speedy deletion")
            continue
        else:
            # Begin processing for API call
            gsLinks = ""
            wiki = gsapi.file[project]
            urlpre = urlparse(wiki['apiurl'])
            gsQuery = {
                'action':"query",
                'format':"json",
                'list':"categorymembers",
                'cmtitle':wiki['csdcat']
            }
            while True: # iterate through results
                DATA = gsapi.connect.get(wiki['apiurl'], headers=gsapi.agent, params=gsQuery).json()
                for item in DATA['query']['categorymembers']:
                    gshyper = str("#+https://" + urlpre.netloc + "/wiki/" + item['title'] + '+\n')
                    gshyperlink = ''.join(gshyper).replace(" ", "_")
                    gshyperlink = gshyperlink.replace("+", " ")
                    if gsLinks == "":
                        gsLinks = "{{Hidden|header=" + project + "|content=" + '\n' + gshyperlink
                    else:
                        gsLinks = gsLinks + gshyperlink
                if ('continue' not in DATA) or ('error' in DATA):
                    break
                cont = DATA['continue']
                gsQuery.update(cont)
            if gsLinks != "": # conditionally format for page edit
                gsLinks = gsLinks + "}}" + '\n'
                gsapi.gsEdit = gsapi.gsEdit + gsLinks
            else:
                bot.say("No items found on " + project)
                gsLinks = ""
                continue
    if gsapi.gsEdit is not "":
        gsapi.gsEdit = gsapi.greeting + gsapi.gsEdit + "~~~~" # finalize edit
        editTitle = gsapi.secTitle + actName
        gsedit(gsapi.gsEdit, actName, editTitle)
        bot.say("Request complete! https://meta.wikimedia.org/wiki/User_talk:" + actName)
    else:
        bot.say("No items found so I didn't report to your talk page.")

def gsircwork(bot, trigger):
    wiki = trigger.group(3)
    if wiki in gsapi.file:
        response = ""
        project = gsapi.file[wiki]
        urlpre = urlparse(project['apiurl'])
        gsQuery = {
            'action':"query",
            'format':"json",
            'list':"categorymembers",
            'cmtitle':project['csdcat']
        }
        DATA = gsapi.connect.get(project['apiurl'], headers=gsapi.agent, params=gsQuery).json()
        for item in DATA['query']['categorymembers']:
            response = response + " https://" + urlpre.netloc + "/wiki/" + item['title'].replace(" ", "_")
        if response is not "":
            for each in response.split(' '):
                bot.say(each)
            if 'continue' in DATA:
                bot.say(trigger.nick + ", more items exist. Rerun !onirc " + wiki + " after deleting above articles.")
            else:
                bot.say("Request complete.")
        else:
            bot.say("There are no pages listed in the CSD category.")
    else:
        bot.say("I don't know " + wiki + "... You can add it by using !gsadd wikiabrev fullAPIurl Category:CSD category.")
        bot.say("Example: !gsadd enwiki https://en.wikipedia.org/w/api.php Category:Candidates for speedy deletion")

def gsnew(bot, addAbrev, addAPI, addCat): # permit users to add other projects to JSON file
    if addAbrev in gsapi.file:
        bot.say("I already know that wiki. If override is needed, contact Operator873")
    else:
        gsapi.file.update({addAbrev: {'apiurl': addAPI, 'csdcat': addCat}})
        with open('/home/ubuntu/.sopel/modules/GSwikis.json', 'w') as update:
            json.dump(gsapi.file, update)
        update.close()
        bot.say("Project " + addAbrev + " added successfully!")

def OperTest(bot, project): # debugging func. Returns stored values in keys
    if (project in gsapi.file):
        target = gsapi.file[project]
        bot.say(target['apiurl'] + " " + target['csdcat'])
    else:
        bot.say("I don't know that wiki.")

def gsre(bot, addAbrev, addAPI, addCat): # admin rewrite function. Replace key instead of adding
    gsapi.file.update({addAbrev: {'apiurl': addAPI, 'csdcat': addCat}})
    with open('/home/ubuntu/.sopel/modules/GSwikis.json', 'w') as update:
            json.dump(gsapi.file, update)
    update.close()
    bot.say(addAbrev + " updated API: " + gsapi.file[addAbrev]['apiurl'] + " CSD Cat: " + gsapi.file[addAbrev]['csdcat'])

def intRunAdd(bot, project, actName):
    now = str(time.time())
    gsdbase[actName][now] = project
    with open('/home/ubuntu/.sopel/modules/GSdbase.json', 'w') as update:
        json.dump(gsdbase, update)

def intRunDel(bot, project, actName):
    for item in gsdbase[actName]:
        if gsdbase[actName][item] is project:
            del gsdbase[actName][item]
            with open('/home/ubuntu/.sopel/modules/GSdbase.json', 'w') as update:
                json.dump(gsdbase, update)

@module.require_chanmsg(message="This message must be used in the channel")
@module.commands('update')
@module.nickname_commands('update')
def gsupdate(bot, trigger):
    if trigger.group(2) is None:
        bot.say("Please inlcude a project for me check. Example: !gsupdate enwikibooks arcwiki")
    else:
        if str(trigger.nick) in gsapi.users:
            if trigger.group(3) in gsapi.file:
                actName = gsapi.users[str(trigger.nick)]
                abrev = trigger.group(2)
                gswork(bot, abrev, actName)
            else:
                bot.say("I don't know " + trigger.group(3) + ".")
        else:
            bot.say("I'm sorry! You're not authorized to perform this action.")

@module.interval(86400)
def gsinterval(bot):
    for nick in gsdbase:
        project = None
        for item in gsdbase[nick]:
            if project is None:
                project = str(gsdbase[nick][item])
            else:
                project = str(gsdbase[nick][item]) + "," + project
            gsintRun(bot, project, nick)
    bot.say("Daily run complete. Check your talk pages!", "#wikimedia-gs")

@module.require_owner(message="This function is only available to the bot's owner.")
@module.require_chanmsg(message="This message must be used in the channel")
@module.commands('manint')
def gsintManual(bot, trigger):
    for nick in gsdbase:
        project = None
        for item in gsdbase[nick]:
            if project is None:
                project = str(gsdbase[nick][item])
            else:
                project = str(gsdbase[nick][item]) + "," + project
            gsintRun(bot, project, nick)
    bot.say("Daily run complete. Check your talk pages!")

@module.require_chanmsg(message="This message must be used in the channel")
@module.commands('add')
@module.nickname_commands('add')
def gsadd(bot, trigger):
    if str(trigger.nick) in gsapi.users:
        actName = gsapi.users[str(trigger.nick)]
        if trigger.group(2) is None:
            bot.say("Please include wiki abrev, api url, and CSD Category...")
            bot.say("Example: !gsadd test https://test.wikipedia.org/w/api.php Category:Candidates for speedy deletion")
        else:
            addWiki = trigger.group(2)
            addCat = ""
            try:
                addAbrev = addWiki.split(" ")[0]
                addAPI = addWiki.split(" ")[1]
                addWiki = addWiki.split(" ")[2::]
                addCat = ' '.join(addWiki)
            except:
                bot.say("Please include wiki abrev, api url, and CSD Category...")
                bot.say("Example: !gsadd test https://test.wikipedia.org/w/api.php Category:Candidates for speedy deletion")
        if addCat != "":
            gsnew(bot, addAbrev, addAPI, addCat)
    else:
        bot.say("I'm sorry! You're not authorized to perform this action.")

@module.require_chanmsg(message="This message must be used in the channel")
@module.commands('onirc')
@module.nickname_commands('onirc')
def gsirc(bot, trigger):
    if (str(trigger.nick) in gsapi.users):
        if trigger.group(3) is not None:
            if len(str(trigger.group(2)).split()) > 1:
                bot.say("For IRC responses, only one project is supported. Proceeding with " + trigger.group(3) + ":")
            gsircwork(bot, trigger)
        else:
            bot.say("I need a project to check!")
    else:
        bot.say("I'm sorry! You're not authorized to perform this action.")

@module.require_owner(message="This function is only available to the bot's owner.")
@module.commands('idwiki')
def gsid(bot, trigger):
    OperTest(bot, trigger.group(2))

@module.require_owner(message="This function is only available to the bot's owner.")
@module.commands('csrf')
def gscsrf(bot, trigger):
    gslogin()
    bot.say(gsapi.csrf)

@module.require_owner(message="This function is only available to the bot's owner.")
@module.commands('rewrite')
def gsrewrite(bot, trigger):
    addWiki = trigger.group(2)
    addAbrev = addWiki.split(" ")[0]
    addAPI = addWiki.split(" ")[1]
    addWiki = addWiki.split(" ")[2::]
    addCat = ' '.join(addWiki)
    gsre(bot, addAbrev, addAPI, addCat)

@module.require_owner(message="This function is only available to the bot's owner.")
@module.commands('authnick')
def authnick(bot, trigger):
    gsapi.users.update({trigger.group(3): trigger.group(4)})
    with open('/home/ubuntu/.sopel/modules/users.json', 'w') as update:
        json.dump(gsapi.users, update)
    update.close()
    bot.say("User " + trigger.group(3) + " added as " + trigger.group(4) + " successfully!")

@module.require_owner(message="This function is only available to the bot's owner.")
@module.commands('idnick')
def idnick(bot, trigger):
    ircnick = str(trigger.group(3))
    try:
        actName = gsapi.users[ircnick]
        bot.say("I know " + ircnick + " as " + actName + ".")
    except KeyError:
        bot.say("I don't know " + ircnick + " .")

@module.require_owner(message="This function is only available to the bot's owner.")
@module.commands('rmvnick')
def rmvnick(bot, trigger):
    test = gsapi.users.pop(trigger.group(3), "False")
    if test != "False":
        with open('/home/ubuntu/.sopel/modules/users.json', 'w') as update:
            json.dump(gsapi.users, update)
        update.close()
        bot.say("User " + trigger.group(3) + " removed from authorized users successfully!")
    else:
        bot.say("That nick is not in the authorized user list.")
