import requests
import pandas as pd
from datetime import datetime
from pushsafer import init, Client
import urllib3


urllib3.disable_warnings()

# getting data from yahoo finance 
def get_data(symbol, data_range='60d', data_interval='30m'):
    res = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={data_range}&interval={data_interval}'.format(**locals()))
    data = res.json()
    body = data['chart']['result'][0]
    df = pd.DataFrame(body['indicators']['quote'][0], index=body['timestamp'])
    df = df.loc[:, ('open', 'high', 'low', 'close')]
    df.dropna(inplace=True)
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'Time', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
    df['RSI'] = 0.0
    df['200EMA'] = df['Close'].ewm(span=200).mean()
    return df


# creating Relative Strenght Indicator with period of 20
def RSI(df, period=20):
    delta = df["Close"].diff()
    up, down = delta.copy(), delta.copy()
    up[up < 0] = 0
    down[down > 0] = 0
    gain = up.ewm(com=(period - 1), min_periods=period).mean()
    loss = down.abs().ewm(com=(period - 1), min_periods=period).mean()
    RS = gain / loss
    df['RSI'] = pd.Series(100 - (100 / (1 + RS)))
    return df


# main buy sell decision function based on Relative Strength Index and Exponential Moving Average
def buy_sell_function(df):
    buy = False
    weeks = 48 * 10
    atime = None
    for i in range(200 + weeks, len(df)-2):

        # Buy signal
        if df.iat[i, 5] < 30 and df.iat[i-weeks, 6] < df.iat[i, 6] and not buy:
            buy = True
            atime = df.iat[i+1, 0]

        # Close signal
        elif df.iat[i, 5] > 70 and buy:
            buy = False
            atime = df.iat[i+1, 0]

    return df, buy, atime

#   Structure of dataframe:
#
#   Time    Open    High    Low     Close   RSI     EMA200
#   0       1       2       3       4       5       6

recievers = [
    '35542', # Adam Kukucka
    '35715', # Adam Letko
    '36535', # Lukas Balogh
]

# EUR, AUD, CAD, CHF, GBP, JPY, USD
symbols = [
    ('EUR/AUD', 'EURAUD=X'),
    ('EUR/CAD', 'EURCAD=X'),
    ('EUR/CHF', 'EURCHF=X'),
    ('EUR/GBP', 'EURGBP=X'),
    ('EUR/JPY', 'EURJPY=X'),
    ('EUR/USD', 'EURUSD=X'),
    ('AUD/CAD', 'AUDCAD=X'),
    ('AUD/CHF', 'AUDCHF=X'),
    ('AUD/JPY', 'AUDJPY=X'),
    ('AUD/USD', 'AUDUSD=X'),
    ('CAD/CHF', 'CADCHF=X'),
    ('CAD/JPY', 'CADJPY=X'),
    ('CHF/JPY', 'CHFJPY=X'),
    ('GBP/AUD', 'GBPAUD=X'),
    ('GBP/CAD', 'GBPCAD=X'),
    ('GBP/CHF', 'GBPCHF=X'),
    ('GBP/JPY', 'GBPJPY=X'),
    ('GBP/USD', 'GBPUSD=X'),
    ('USD/CAD', 'CAD=X'),
    ('USD/CHF', 'CHF=X'),
    ('USD/JPY', 'JPY=X'),
]

# alternating ring tone 
ring = "26"
if datetime.now().hour > 7 - 2 and datetime.now().hour < 23 - 2:
    ring = "11"

ring_on = True
if datetime.now().weekday() == 6 and datetime.now().hour < 22:
    ring_on = False

units = {
    'EUR': 1,
}

# reading opened forex pairs from txt file 
with open('app.txt') as f:
    opened = list(map(lambda x: x.strip(), list(f.readlines())))

# current trade value
eur = 5540

# looping through all 21 forex pairs and sending notifications to recievers
init("S9PxnHJuMr0AHPX82LGS")
for key, symbol in symbols:
    df = get_data(symbol)
    df = RSI(df)
    df, buy, atime = buy_sell_function(df)
    
    if key[:3] == 'EUR':
        units[key[4:]] = df.iat[-3, 4]

    if atime:
        timestamp = datetime.fromtimestamp(atime)
        message = timestamp.strftime('%H:%M %d.%m.%Y') + ' \t' + key

    if buy and not key in opened:
        message += ' \t' + str(int(eur * units[key[:3]]))

        # notification for buy signals 
        for reciever in recievers:
            Client("").send_message(message, "BUY", reciever, "48", ring, "", "", "", "0", "2", "0", "0", "0", "", "", "")

        opened.append(key)

    elif not buy and key in opened:

        # notifications for sell singals
        for reciever in recievers:
            Client("").send_message(message, "CLOSE", reciever, "49", ring, "", "", "", "0", "2", "0", "0", "0", "", "", "")

        opened.remove(key)

# creating txt file with openned forex pairs
with open('app.txt', 'w') as f:
    for open_key in opened:
        f.write(open_key + '\n')
