
import time
import pyupbit
import pandas as pd
from decimal import Decimal
import matplotlib.pyplot as plt

from collections import deque

def short_trading_for_1percent(ticker):
    # dfs = []
    dfs = deque()
    df = pyupbit.get_ohlcv(ticker, interval="minute1", to="20210414 23:00:00")  # pyupbit 함수는 기본적으로 200개의 데이터를 반환함
    dfs.append(df)

    # 처음에 데이터 200개 위에서 받았고, 이어서 더 받아오도록 첫 번째 인덱스를 사용
    for i in range(60):
        df = pyupbit.get_ohlcv(ticker, interval="minute1", to=df.index[0])   # 앞서 조회한 데이터 날짜의 첫 번째를 지정해주면 반복적으로 이어서 가져올 수 있음 -> from이 아닌 to니까 첫 번째가 맞음
        dfs.append(df)
        time.sleep(0.2)

    df = pd.concat(dfs)
    df = df.sort_index()                        # 해당 df의 인덱스가 날짜이므로 날짜 순으로 정렬

    # 1) 매수 일자 판별 (고가가 시가 대비 1% 이상 상승하면 매수 & 2% 이상 상승하면 매도)
    cond = df['high'] >= df['open'] * 1.01      # 결과는 True or False
    df.index[cond]                              # 인덱스가 날짜이므로 조건이 참인 날짜만 가져옴

    principal = 1
    acc_ror = 1
    sell_date = None

    # 2) 매도 조건 탐색 및 수익률 계산
    for buy_date in df.index[cond]:
        if sell_date != None and buy_date <= sell_date:             # 이전에 조회했던 날짜 (sell_date) 보다 현재 날짜 (buy_date)가 작다면 조건 탐색이 아니고 지나가야함
            continue                                                # 현재 날짜가 작으면 매수할 수 있었지만 기존에 매수했던 걸 아직 매도하지 못했을 수 있으므로 이 경우는 패스하는 것 -> 이 전략은 조건에 맞으면 또 매수하는게 아니라 매수했으면 매도를 해야 다시 매수할 수 있는 로직인듯

        target = df.loc[ buy_date : ]                               # 얻어온 매수일을 기준으로 과거일자는 필요 없으므로 [매수일자~이후날짜]만 슬라이싱함

        cond = target['high'] >= target['open'] * 1.02
        sell_candidate = target.index[cond]

        if len(sell_candidate) == 0:                                # 매도 조건에 맞는 경우가 없으면 종가 데이터에 매도하고 탐색을 끝내야함
            buy_price = df.loc[buy_date, 'open'] * 1.01
            sell_price =df.iloc[-1, 3]                              # OHLCV라서 High의 인덱스는 3
            acc_ror *= (sell_price / buy_price)

            break
        else:
            sell_date = sell_candidate[0]
            # acc_ror *= 1.005
            # 수수료 고려 (누적 수익에서 수수료를 차감해서 계산)
            # 매수 0.05%, 매도 0.05% & 슬리피지 약 0.4% 발생한다고 가정 (총 0.5%)
            commission = Decimal('0.0005') + Decimal('0.0005') + Decimal('0.004')      

            acc_ror *= float(Decimal('1.01') - commission)          # 1% 상승시 매수 & 2% 상승시 매도이므로 누적수익률은 1%

    return acc_ror

tickers = ("KRW-BTC", "KRW-LTC", "KRW-ETH", "KRW-ADA")
for ticker in tickers:
    ror = short_trading_for_1percent(ticker)
    print(f"TICKER: {ticker} & ROR: {ror}")




# # 우선 순위 큐를 위한 최적화 모듈 heapq
# import heapq

# data = [
#     (12.23, "강보람"),
#     (12.31, "김지원"),
#     (11.98, "박시우"),
#     (11.99, "장준혁"),
#     (11.67, "차정웅"),
#     (12.02, "박중수"),
#     (11.57, "차동현"),
#     (12.04, "고미숙"),
#     (11.92, "한시우"),
#     (12.22, "이민석"),
# ]

# print(heapq.nsmallest(3, data))
