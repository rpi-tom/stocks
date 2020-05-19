#Test strategy
__author__ = 'fernandolourenco'
import version

from ystockquote import get_historical_prices
import operator

import sqlite3

import codecs
from ConfigParser import SafeConfigParser
import argparse

import datetime

import sys
import os

#Constants
##########################################################################
SETTINGSFILE = '/tom_files/'
VERBOSE = True

#Strategy
LOWCOUNT = 5
MINRETURN = 0.05

#Constants
TAXONDIVIDENDS = 0.26
COMISSION = 14.95* 1.04
##########################################################################

def main():
    # Read config file
    parser = SafeConfigParser()

    # Open the file with the correct encoding
    with codecs.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), SETTINGSFILE), 'r', encoding='utf-8') as f:
        parser.readfp(f)

    global DATABASE
    DATABASE = parser.get('Database', 'File')


    cloptions = argparse.ArgumentParser(description='Backtest vs. %s' % version.__version__, prog='Backtest %s' % version.__version__)
    cloptions.add_argument('-s', '--stock', help='Yahoo finance symbol(s) of stock to backtest (comma separated)', nargs = 1, default = ['QLIK'],required=True)
    cloptions.add_argument('-t', '--sdate', help='Start date to backtest (format yyyy-mm-dd)', nargs = 1, default = ['2012-01-01'],required=False)
    cloptions.add_argument('-f', '--fdate', help='Finish date to backtest (format yyyy-mm-dd)', nargs = 1,required=False)
    cloptions.add_argument('-l', '--lowcount', help='Strategy low count', nargs = 1, default = 5, required=False)
    cloptions.add_argument('-m', '--minreturn', help='Strategy Minimum return (%)', nargs = 1, default = 5, required=False)

    cloptions.add_argument('-v', '--version', action='version', version='%(prog)s')

    args = cloptions.parse_args()

    try:
        stocksymbol = args.stock[0]
    except:
        sys.exit(1)

    try:
        startdate = args.sdate[0]
    except:
        startdate = "2012-01-01"

    try:
        finishdate = args.fdate[0]
    except:
        finishdate = (datetime.datetime.utcnow() + datetime.timedelta( days=-1 )).strftime("%Y-%m-%d")

    try:
        LOWCOUNT = args.lowcount
    except:
        pass

    try:
        MINRETURN = float(args.minreturn)/100
    except:
        pass

    if VERBOSE:
        print "Start %s\n%s\n%s\n\n" % (os.path.basename(sys.argv[0]), version.__version__, datetime.datetime.now())

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    c = conn.cursor()
    c.execute("select symbolyahoo from stocks where type='stock' and symbolyahoo=:symbol;", {'symbol':stocksymbol})
    stocks = c.fetchall()

    for STOCK in stocks:

        CAPITAL = 10000

        try:
            quotes = get_historical_prices(STOCK[0], startdate, finishdate)
        except:
            print "Error geting quotes for %s from %s to %s" % (stocksymbol, startdate, finishdate)
            sys.exit(1)

        sortedquotes = sorted(quotes.items(), key=operator.itemgetter(0))

        # get stock id
        c.execute("select id from stocks where symbolyahoo='%s';" % STOCK[0])
        stockid = c.fetchone()[0]

        # get dividends
        c.execute("select * from dividends where stockid=%d;" % stockid)
        dividends = c.fetchall()
        datesdividends=[o['date'] for o in dividends]

        quoteant = 0.0
        finalquote="0.0"
        countlow = 0

        buy = False
        qty = 0
        buyprice = 0.0
        cash = CAPITAL

        buys = 0
        sells = 0

        for day in sortedquotes:
            #calculate day return
            if quoteant != 0:
                dayreturn = (float(day[1]["Close"])-quoteant)/quoteant
            else:
                dayreturn = 0

            if buy == False:
                #check number of consecutive days lowering exceeded, and opening low again
                if countlow>= LOWCOUNT:
                    if float(day[1]["Open"])<quoteant:
                        buy = True
                        buyprice = float(day[1]["Open"])
                        qty = int((cash-COMISSION)/buyprice)
                        cash = cash - qty * buyprice - COMISSION
                        if VERBOSE:
                            print("BOUGHT %8.0f @ %8.3f" % (qty, buyprice))

                        buys += 1
            else:
                # Check if minimum return acheived, so sell
                if (float(day[1]["Open"])-buyprice)/buyprice>=MINRETURN:
                    buy = False
                    cash = cash + qty * float(day[1]["Open"]) - COMISSION
                    qty = 0
                    if VERBOSE:
                        print("SOLD! Cash now:%6.0f" % cash)

                    sells += 1

            if buy == True:
                # check to see if dividend paid
                if day[0] in datesdividends:
                    i = datesdividends.index(day[0])
                    cash = cash + qty * dividends[i]['value'] * (1-TAXONDIVIDENDS)
                    if VERBOSE:
                        print "Dividend pay %s * %d" % (dividends[i]['value'],qty)

            #increase number of consecutive days lowering
            if dayreturn<0.0:
                countlow = countlow+1
            else:
                countlow = 0

            quoteant = float(day[1]["Close"])
            if VERBOSE:
                print("Date: %s Close Price:%s Adj Close:%s Change:%5.2f%%" % (day[0], day[1]["Close"], day[1]["Adj Close"], dayreturn*100) )
            finalquote = day[1]["Close"]

        print("\nStock %s" % STOCK[0])
        if buy == False:
            print("Final Cash:%6.0f" % cash)
        else:
            print("Final Position %8.0f stock valued %6.0f" % (qty, qty*float(finalquote)))

        print ("Total Buys:%d Total Sells:%d" % (buys, sells))

##########################################################################
if __name__ == "__main__":
    main()