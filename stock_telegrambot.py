# coding=UTF-8
__author__ = 'fernandolourenco'
import version

import datetime
import time
import dateutil.parser

import telepot
import codecs
import sys
import os

import sqlite3

import monitorstock

from ConfigParser import SafeConfigParser

#Constants
# ##########################################################################
SETTINGSFILE = 'tom_files/stocks.ini'
##########################################################################

#Globals
##########################################################################
global bot
global uid

global DATABASE
##########################################################################


##########################################################################
def handle(msg):
    global DATABASE

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    #pprint.pprint(msg)
    message = msg['text'].upper()
    commands = message.split(" ")

    if commands[0] == '/SELL':
        try:
            qty = float(commands[1])
            stock = commands[2]
            price = float(commands[3])
        except:
            bot.sendMessage(uid, text=u"Error. Correct syntax /sell quantity google_code price [date]" )
            return

        try:
            date = commands[4]
        except:
            date = None

        c = conn.cursor()

        try:
            if monitorstock.sellstock(stock, qty, price, date, conn):
                c.execute("select portfolio.qty,portfolio.cost from portfolio, stocks where stocks.symbolgoogle=:symbol and portfolio.stockid=stocks.id", {'symbol':stock})
                row = c.fetchone()
                try:
                    qtyonhand = float(row['qty'])
                    bot.sendMessage(uid, text=u"Success. Sold %.2f. New quantity on hand %.2f." % (qty, qtyonhand) )
                except:
                    bot.sendMessage(uid, text=u"Success. Sold %.2f. Closed position." % (qty) )
            else:
                bot.sendMessage(uid, text=u"Error. Unknown stock; or not available; or not enough quantity to sell %s" % stock )
        except Exception,e:
            #print str(e)
            bot.sendMessage(uid, text=u"Error. Unknown stock or not available to sell %s" % stock )
            return

        conn.close()
    elif commands[0] == '/BUY':
        try:
            qty = float(commands[1])
            stock = commands[2]
            price = float(commands[3])
        except:
            bot.sendMessage(uid, text=u"Error. Correct syntax /buy quantity google_code price [date]" )
            return

        try:
            date = commands[4]
        except:
            date = None

        try:
            monitorstock.buystock(stock, qty, price, date, conn)

            c = conn.cursor()
            c.execute("select portfolio.qty,portfolio.cost from portfolio, stocks where stocks.symbolgoogle=:symbol and portfolio.stockid=stocks.id", {'symbol':stock})
            row = c.fetchone()
            avgprice = float(row['cost'])
            bot.sendMessage(uid, text=u"Success. Bought %.2f %s @ %.3f. New quantity on hand %.2f. New averageprice %.3f" % (qty, stock, price, float(row['qty']), avgprice) )

        except Exception,e:
            #print str(e)
            bot.sendMessage(uid, text=u"Error. Unknown stock or not available to buy %s" % stock )
            return

        conn.close()
    elif commands[0] == '/DIVIDEND':
        try:
            stock = commands[1]
            dividend = float(commands[2])
            date = commands[3]
        except:
            bot.sendMessage(uid, text=u"Error. Correct syntax /dividend google_code value date" )
            return

        try:
            c = conn.cursor()
            c.execute("select id from stocks where symbolgoogle=:symbol", {'symbol':stock})
            row = c.fetchone()

            c.execute("""
            insert into dividends(stockid,date,value)
            values(?,?,?)
            """, (int(row['id']), date, float(dividend)))

            conn.commit()

            bot.sendMessage(uid, text=u"Ok. Dividend set for %s" % stock)
        except:
            bot.sendMessage(uid, text=u"Error setting dividend for %s" % stock)

    elif commands[0] == '/STATUS':
        bot.sendMessage(uid, text=u"Ok. Running\n%s" % version.__version__)
    elif commands[0] == '/START':
        bot.sendMessage(uid, text=u"Started. Time now\n%s" % datetime.datetime.now())
    elif commands[0] == '/PORTFOLIO':
        bot.sendMessage(uid, text=u"QTY\tSTOCK\tPRICE")

        c = conn.cursor()
        for row in c.execute("select portfolio.qty,portfolio.cost, stocks.name, stocks.symbolgoogle from portfolio, stocks where portfolio.stockid=stocks.id"):
            bot.sendMessage(uid, text=u"%.2f\t%s (%s)\t%.3f" % (float(row['qty']), row['name'], row['symbolgoogle'], float(row['cost']) ))
    elif commands[0] == '/RETURNS':
        bot.sendMessage(uid, text=u"QTY\tSTOCK\tRETURN %")

        c = conn.cursor()
        for row in c.execute("select portfolio.qty,portfolio.cost, portfolio.stockid, stocks.name, stocks.symbolgoogle from portfolio, stocks where portfolio.stockid=stocks.id"):
            ireturn = monitorstock.getstockreturn(row['stockid'], conn)

            bot.sendMessage(uid, text=u"%.2f\t%s\t%.1f" % (float(row['qty']), row['name'], ireturn))
    elif commands[0] == '/MOVEMENTS':
        c = conn.cursor()
        try:
            bot.sendMessage(uid, text=u"DATE\tQTY\tVALUE\tTYPE")
            stock = commands[1].upper()
            query = "select movements.*, stocks.symbolgoogle from movements, stocks where movements.stockid=stocks.id and stocks.symbolgoogle='%s'" % stock
        except:
            bot.sendMessage(uid, text=u"DATE\tSTOCK\tQTY\tVALUE\tTYPE")
            stock = None
            query = "select movements.*, stocks.symbolgoogle from movements, stocks where movements.stockid=stocks.id"

        for row in c.execute(query):
            stockdate = dateutil.parser.parse(row['date'])
            if stock is None:
                bot.sendMessage(uid, text=u"%s\t%s\t%.3f\t%.3f\t%s" % (stockdate.date(), row['symbolgoogle'].upper(), row['qty'], row['value'], row['action'].upper()))
            else:
                bot.sendMessage(uid, text=u"%s\t%.3f\t%.3f\t%s" % (stockdate.date(), row['qty'], row['value'], row['action'].upper()))
    elif commands[0] == '/SPLIT':
        try:
            stock = str(commands[1]).upper()
            split = eval("1.0*"+commands[2])
            splitdate = str(commands[3])
        except:
            bot.sendMessage(uid, text=u"Error. Correct syntax /split google_code ratio date" )
            return

        try:
            c = conn.cursor()
            c.execute("insert into splits(stockid,date,value) select stocks.id, ?, ? from stocks where symbolgoogle=?", (splitdate, float(split), stock))
            conn.commit()
            bot.sendMessage(uid, text=u"Ok. Split set for %s" % stock)
        except:
            print sys.exc_info()[0]
            bot.sendMessage(uid, text=u"Error setting split for %s" % stock)

    elif commands[0] == '/HELP':
        bot.sendMessage(uid, text=u"Available commands for %s:\n /buy, /sell, /dividend, /status, /portfolio, /returns, /movements, /split" % os.path.basename(sys.argv[0]))
    else:
        bot.sendMessage(uid, text=u"Unknown command" )
##########################################################################

##########################################################################
def main():
    global bot
    global uid

    # Read config file
    parser = SafeConfigParser()

    # Open the file with the correct encoding
    with codecs.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), SETTINGSFILE), 'r', encoding='utf-8') as f:
        parser.readfp(f)

    try:
        # Create access to bot
        bot = telepot.Bot(parser.get('Telegram', 'token'))
        bot.message_loop(handle)
        uid = parser.get('Telegram', 'uid')
        bot.sendMessage(uid, text=u"Start %s\n%s\n%s" % (os.path.basename(sys.argv[0]), version.__version__, datetime.datetime.now()))
    except:
        print u'Cannot access Telegram. Please do /start'
        sys.exit(1)

    global DATABASE
    DATABASE = parser.get('Database', 'File')

    # Keep the program running.
    while 1:
        time.sleep(10)
##########################################################################


if __name__ == "__main__":
    main()