import time
import pyupbit
import os.path
import pandas as pd

from decimal import Decimal
from collections import deque

# from _plotly_future_ import v4_subplots
import plotly.graph_objs as go
# import plotly.graph_objects as go
from plotly.subplots import make_subplots


def get_ohlcv(ticker):
    # dfs = []
    dfs = deque()
    df = pyupbit.get_ohlcv(ticker, interval="minute1", to="20210423 11:00:00")  # pyupbit 함수는 기본적으로 200개의 데이터를 반환함
    dfs.append(df)

    # 처음에 데이터 200개 위에서 받았고, 이어서 더 받아오도록 첫 번째 인덱스를 사용
    for i in range(60):
        df = pyupbit.get_ohlcv(ticker, interval="minute1", to=df.index[0])      # 앞서 조회한 데이터 날짜의 첫 번째를 지정해주면 반복적으로 이어서 가져올 수 있음 -> from이 아닌 to니까 첫 번째가 맞음
        dfs.append(df)
        time.sleep(0.2)

    df = pd.concat(dfs)
    df = df.sort_index()                                                        # 해당 df의 인덱스가 날짜이므로 날짜 순으로 정렬

    return df


def short_trading_for_1percent(df):
    # 1) 매수 일자 판별 (고가가 시가 대비 1% 이상 상승하면 매수 & 2% 이상 상승하면 매도)
    cond_buy = df['high'] >= df['open'] * 1.01      # 결과는 True or False
    df.index[cond_buy]                              # 인덱스가 날짜이므로 조건이 참인 날짜만 가져옴

    principal = 1
    acc_ror = 1
    sell_date = None

    # 누적 수익률 그리기 (누적 수익률은 매도 시점에 업데이트됨)
    ax_ror = []
    ay_ror = []


    # 2) 매도 조건 탐색 및 수익률 계산
    for buy_date in df.index[cond_buy]:
        if sell_date != None and buy_date <= sell_date:                 # 이전에 조회했던 날짜 (sell_date) 보다 현재 날짜 (buy_date)가 작다면 조건 탐색이 아니고 지나가야함
            continue                                                    # 현재 날짜가 작으면 매수할 수 있었지만 기존에 매수했던 걸 아직 매도하지 못했을 수 있으므로 이 경우는 패스하는 것 -> 이 전략은 조건에 맞으면 또 매수하는게 아니라 매수했으면 매도를 해야 다시 매수할 수 있는 로직인듯

        target = df.loc[buy_date:]                                      # 얻어온 매수일을 기준으로 과거일자는 필요 없으므로 [매수일자~이후날짜]만 슬라이싱함

        cond_sell = target['high'] >= df.loc[buy_date, 'open'] * 1.02   # 매일의 시가가 아니라 매수한 날의 시가(*1.02)를 기준으로 비교해야함 (target['open'] * 1.02 -> 틀림)
        sell_candidate = target.index[cond_sell]

        if len(sell_candidate) == 0:                                    # 매도 조건에 맞는 경우가 없으면 종가 데이터에 매도하고 탐색을 끝내야함
            buy_price = df.loc[buy_date, 'open'] * 1.01
            sell_price =df.iloc[-1, 3]                                  # OHLCV라서 High의 인덱스는 3
            acc_ror *= (sell_price / buy_price)

            # 팔지 못하고 보유하고 있었다면 현재 데이터의 마지막 값을 그림
            ax_ror.append(df.index[-1])
            ay_ror.append(acc_ror)

            break
        else:
            sell_date = sell_candidate[0]
            # 수수료 고려 (누적 수익에서 수수료를 차감해서 계산)
            # 매수 0.05%, 매도 0.05% & 슬리피지 약 0.4% 발생한다고 가정 (총 0.5%)
            # acc_ror *= 1.005
            commission = Decimal('0.0005') + Decimal('0.0005') + Decimal('0.004')      

            acc_ror *= float(Decimal('1.01') - commission)          # 1% 상승시 매수 & 2% 상승시 매도이므로 누적수익률은 1%

            # (그림을 나타내기 위해) 수익 실현시 해당 날짜와 누적된 수익률을 append 
            ax_ror.append(sell_date)
            ay_ror.append(acc_ror)


    # 캔들스틱 그리기
    candle = go.Candlestick(
        x = df.index,
        open = df['open'],
        high = df['high'],
        low = df['low'],
        close = df['close']
    )     

    ror_chart = go.Scatter(
        x = ax_ror,
        y = ay_ror
    )

    fig = make_subplots(specs=[ [ { "secondary_y": True } ] ])   
    fig.add_trace(candle)
    fig.add_trace(ror_chart, secondary_y=True)

    # 매수 가능한 위치/날짜를 표시
    # for idx in df.index[cond_buy]:
    #     fig.add_annotation(                 # 해당 함수는 값을 하나씩 입력해야하므로 for문을 사용해 값을 하나씩 추가
    #         x = idx,
    #         y = df.loc[idx, 'open']
    #     )
    #     fig.update_annotations(dict(showarrow=True))

    annotations = []
    for idx in df.index[cond_buy]:
        annotations.append(dict(x=idx, y=df.loc[idx, 'open'], showarrow=True))
    
    fig.update_layout(annotations=annotations)

    title = "코인 차트"
    fig.write_html('{}.html'.format(title))
    fig.show()

    return acc_ror


# tickers = ("KRW-BTC", "KRW-LTC", "KRW-ETH", "KRW-ADA")

# for ticker in tickers:
#     # TODO get_ohlcv로 받아오는 데이터가 변경되어도, 파일 이름이 같기 때문에 변경된 내용을 받아오지 못함
#     # TODO 그렇다고 이 파일을 실행할 때마다 get_ohlcv 함수를 호출하여 엑셀 파일의 내용과 비교할 수는 없음 -> 그럴거면 뭐하러 엑셀파일을 따로 저장해
#     # TODO 지금으로써는 받아오는 데이터가 변경됐다면, 우선 기존의 엑셀 파일을 삭제해야함
#     if os.path.isfile(f"{ticker}.csv"):
#         pass
#     else:
#         df = get_ohlcv(ticker)
#         df.to_csv(f"{ticker}.csv")

# for ticker in tickers:
for ticker in ["KRW-LTC"]:
    df = pd.read_csv(f"{ticker}.csv", index_col=0)    # 엑셀 상의 첫 번째 컬럼을 인덱스로 지정 (날짜가 인덱스로 지정될 것)
    ror = short_trading_for_1percent(df)

    # 비교용 기간수익률 (첫 영업일에 매수 후 마지막 날짜의 종가에 매도한 경우)
    total_term_simple_return = df.iloc[-1, 3] / df.iloc[0, 0]   # 메도가격/매수가격 & OHLCV -> O:0, C:3

    # 수익률 형식 설정
    ror_percent = (ror-1)*100
    total_term_simple_return_percent = (total_term_simple_return-1)*100

    # if ticker == tickers[0]:
    #     print(f"투자 기간 {df.index[0]} ~ {df.index[-1]}\n\n")

    print(f"TICKER: {ticker}  //  ROR: {ror_percent:.2f}%  //  비교용 기간수익률: {total_term_simple_return_percent:.2f}%\n")





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
