from sopel import module
import sqlite3

@module.require_admin("Permission Denied")
@module.commands('gsadd')
def insertUser(bot, trigger):
    target, account = trigger.group(2).split(' ', 1)
    try:
        sqliteConnection = sqlite3.connect("/home/ubuntu/.sopel/modules/wiki.db")
        cursor = sqliteConnection.cursor()
        sqlite_select_query = "SELECT * from globalsysops where Nick='" + target + "'"
        cursor.execute(sqlite_select_query)
        records = cursor.fetchall()
        if len(records) > 0:
            bot.say(target + ' is already registered for another account.')
            cursor.close()
            return
    except sqlite3.Error as error:
        bot.say("An error occured")
        print("Failed to read data from sqlite table", error)
    finally:
        if (sqliteConnection):
            sqliteConnection.close()
    try:
        sqliteConnection = sqlite3.connect('/home/ubuntu/.sopel/modules/wiki.db')
        cursor = sqliteConnection.cursor()
        sqlite_insert_query = "INSERT INTO globalsysops(Nick, Account) VALUES ('" + target + "','" + account + "')"
        count = cursor.execute(sqlite_insert_query)
        sqliteConnection.commit()
        bot.say("User inserted successfully")
        cursor.close
    except sqlite3.Error as error:
        bot.say("An error occured")
        print("Failed to insert data into sqlite table", error)
    finally:
        if (sqliteConnection):
            sqliteConnection.close()

@module.require_admin("Permission Denied")
@module.commands('gsdel')
def delUser(bot, trigger):
    target = trigger.group(3)
    try:
        sqliteConnection = sqlite3.connect('/home/ubuntu/.sopel/modules/wiki.db')
        cursor = sqliteConnection.cursor()
        sqlite_select_query = "SELECT * from globalsysops where Nick='" + target + "'"
        cursor.execute(sqlite_select_query)
        records = cursor.fetchall()
        if len(records) == 0:
            bot.say(target + ' is not registered to a wiki account.')
            cursor.close()
            return
    except sqlite3.Error as error:
        print("Failed to read data from sqlite table", error)
    finally:
        if (sqliteConnection):
            sqliteConnection.close()
    try:
        sqliteConnection = sqlite3.connect('/home/ubuntu/.sopel/modules/wiki.db')
        cursor = sqliteConnection.cursor()
        sqlite_insert_query = "DELETE FROM globalsysops WHERE nickserv='" + target + "'"
        count = cursor.execute(sqlite_insert_query)
        sqliteConnection.commit()
        bot.say("User has been deleted")
        cursor.close
    except sqlite3.Error as error:
        bot.say("An error occured")
        print("Failed to insert data into sqlite table", error)
    finally:
        if (sqliteConnection):
            sqliteConnection.close()

@module.require_admin("Permission Denied")
@module.commands('gsinfo')
def getUser(bot, trigger):
    args = trigger.group(3)
    try:
        sqliteConnection = sqlite3.connect('/home/ubuntu/.sopel/modules/wiki.db')
        cursor = sqliteConnection.cursor()
        sqlite_select_query = "SELECT Account from globalsysops where Nick='" + target + "'"
        cursor.execute(sqlite_select_query)
        records = cursor.fetchall()
        if len(records) == 0:
            bot.say(target + ' is not registered to a wiki account. To do this use !gsadd <nick> <account>.')
            cursor.close()
            return
        else:
            for row in records:
                bot.say(target + " is registered to '" + row[0])
    except sqlite3.Error as error:
        bot.say("An error occured")
        print("Failed to read data from sqlite table", error)
    finally:
        if (sqliteConnection):
            sqliteConnection.close()
