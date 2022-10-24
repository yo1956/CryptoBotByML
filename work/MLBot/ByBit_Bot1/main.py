import pickle
import joblib
from datetime import datetime, timedelta
import time
import requests
import pandas as pd
import numpy as np
import os
import ccxt
import traceback
#from rich import print
import pprint
from features import features,calc_features
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError

#BybitのOHLCV情報を取得
#from_timeからのinterval分足のローソクをlimit本取得
def get_bybit_ohlcv(from_time,interval,limit):
    ohlcv_list = ccxt.bybit().publicLinearGetKline({
        'symbol': "BTCUSDT",
        'from': from_time,
        'interval': interval,
        'limit': limit
    })["result"]

    df = pd.DataFrame(ohlcv_list,columns=['open_time', 'open', 'high','low','close','volume']) 
    df.rename(columns={'open_time':'timestamp','open':'op','high':'hi','low':'lo','close':'cl'},inplace=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'] , unit='s')
    df.set_index("timestamp",inplace=True)
    df["op"]        = df["op"].astype(float)
    df["hi"]        = df["hi"].astype(float)
    df["lo"]        = df["lo"].astype(float)
    df["cl"]        = df["cl"].astype(float)
    df["volume"]    = df["volume"].astype(float)
    df.sort_index(inplace=True)
    return df

#ポジション情報を取得
def get_bybit_position(bybit):
    poss = bybit.privateLinearGetPositionList({"symbol": 'BTCUSDT'})['result']
    size= pnl = 0.0
    pprint.pprint(poss)
    for p in poss:
        if p['side'] == 'Buy':
            size += float(p['size'])
            pnl  += float(p['unrealised_pnl'])
        if p['side'] == 'Sell':
            size -= float(p['size'])
            pnl  -= float(p['unrealised_pnl'])
    if size == 0: 
        side = 'NONE'
    elif size > 0:
        side = 'BUY'
    else:
        side = 'SELL'
    return {'side':side, 'size':size, 'pnl':pnl}

#Bybitへ注文
def order_bybit(exchange,order_side,order_price,order_size):
    order = exchange.private_linear_post_order_create(
        {
            "side": order_side,
            "symbol": "BTCUSDT",
            "order_type": "Limit",
            "qty": order_size,
            "price":order_price,
            "time_in_force": "PostOnly",
            "reduce_only": False,
            "close_on_trigger": False,
            "position_idx":0
        }
    )
    pprint.pprint(order)

#ボット起動
def start(exchange,max_lot,lot,interval,line_bot_api):

    line_message = ""

    temp_str     = "paibot for bybit is started!\nmax_lot:{0}btc\nlot:{1}btc\ninterval:{2}min\n".format(max_lot,lot,interval)
    line_message = temp_str
    print(temp_str)
    #print("paibot for bybit is started!\nmax_lot:{0}btc lot:{1}btc interval:{2}min".format(max_lot,lot,interval))

    #モデル読み込み
    model_y_buy  = joblib.load('./model/model_y_buy_bybit_extra.xz')
    model_y_sell = joblib.load('./model/model_y_sell_bybit_extra.xz')
    temp_str = "paibot for bybit loaded MachineLearning Model.\n"
    line_message += "paibot for bybit loaded MachineLearning Model."
    print(temp_str)

    line_my_user_id = os.getenv("LINE_MY_USER_ID")
    
    try:
        line_bot_api.push_message(line_my_user_id, messages=TextSendMessage(text=line_message))
    except LineBotApiError as e:
        pprint.pprint(e)
    
    pips = 0.5
    
    line_notify_interval = 12
    line_notify_counter  = line_notify_interval

    while True:

        dt_now = datetime.now()

        # 稼働が続いていることをline_notify_time_interval時間おきにLINE通知
        if dt_now.minute % 60 == 0:
            if line_notify_counter % line_notify_interval == 0:
                line_bot_api.push_message(line_my_user_id, messages=TextSendMessage(text="Bybit MLbot is running..."))

            line_notify_counter-=1
            if line_notify_counter == 0:
                line_notify_counter = line_notify_interval
        
        #指定した時間間隔ごとに実行
        if dt_now.minute % interval == 0:

            try:

                #全注文をキャンセル
                exchange.cancelAllOrders("BTC/USDT")

                #OHLCV情報を取得
                time_now  = datetime.now()
                limit     = 200
                from_time = int((time_now + timedelta(minutes= - limit * interval)).timestamp())
                df        = get_bybit_ohlcv(from_time,interval,limit)

                #特徴量計算
                df_features = calc_features(df)

                #推論
                df_features["y_predict_buy"]  = model_y_buy.predict(df_features[features])
                df_features["y_predict_sell"] = model_y_sell.predict(df_features[features])

                limit_price_dist = df_features['ATR'] * 0.5
                limit_price_dist = np.maximum(1, (limit_price_dist / pips).round().fillna(1)) * pips
                df_features["buy_price"]  = df_features["cl"] - limit_price_dist 
                df_features["sell_price"] = df_features["cl"] + limit_price_dist 

                #売買判定のための情報取得
                predict_buy  = df_features["y_predict_buy"].iloc[-1]
                predict_sell = df_features["y_predict_sell"].iloc[-1]

                buy_price  =  df_features["buy_price"].iloc[-1]
                sell_price = df_features["sell_price"].iloc[-1]

                position = get_bybit_position(exchange)

                pprint.pprint("predict_buy:{0} predict_sell:{1}".format(str(predict_buy),str(predict_sell)))
                pprint.pprint("buy price:{0} sell price:{1}".format(str(buy_price),str(sell_price)))
                pprint.pprint("position side:{0} size:{1}".format(str(position["side"]),str(position["size"])))

                #注文処理

                order_side = "NONE"

                #エグジット
                if position["side"] == "BUY":
                    order_side  = "Sell"
                    order_price = sell_price
                    order_size  = abs(position["size"])
                    order_bybit(exchange,order_side,order_price,order_size)
                if position["side"] == "SELL":
                    order_side  = "Buy"
                    order_price = buy_price
                    order_size  = abs(position["size"])
                    order_bybit(exchange,order_side,order_price,order_size)
                #エントリー
                if predict_buy > 0 and position["size"] < max_lot:
                    order_side  = "Buy"
                    order_price = buy_price
                    order_size  = lot
                    order_bybit(exchange,order_side,order_price,order_size)
                if predict_sell > 0 and position["size"] > -max_lot:
                    order_side  = "Sell"
                    order_price = sell_price
                    order_size  = lot                    
                    order_bybit(exchange,order_side,order_price,order_size)

            except Exception as e:
                pprint.pprint(traceback.format_exc())
                line_bot_api.push_message(line_my_user_id, messages=TextSendMessage(text="Bybit MLbot detected an exception.\n"+traceback.format_exc()))
                pass

        time.sleep(60)

if __name__  == '__main__':

    apiKey    = os.getenv("API_KEY")
    secretKey = os.getenv("SECRET_KEY")
    lot       = float(os.getenv("LOT"))
    max_lot   = float(os.getenv("MAX_LOT"))
    interval  = int(os.getenv("INTERVAL"))
    testnet   = bool(os.getenv("TESTNET"))
    line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    line_bot_api              = LineBotApi(line_channel_access_token)

    exchange  = ccxt.bybit({"apiKey":apiKey, "secret":secretKey})
    exchange.set_sandbox_mode(testnet)
    start(exchange, max_lot, lot, interval,line_bot_api)


