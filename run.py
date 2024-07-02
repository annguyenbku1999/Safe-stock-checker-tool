from datetime import datetime, timedelta
import os
import pandas as pd
import subprocess
import json


# Lấy các biến môi trường
DAYCHECK = 1
PERCENTAGE_HIGH_VOLUME = 1.5

def get_previous_weekday(date):
    """Lấy ngày trước đó mà không phải là thứ bảy (6) hoặc chủ nhật (0)"""
    while date.weekday() in [5, 6]:  # 5 là thứ bảy, 6 là chủ nhật
        date -= timedelta(days=1)
    return date

# Lấy thời điểm hiện tại và thời điểm 1 ngày trước, loại bỏ thứ bảy và chủ nhật
today = datetime.now()

dayStart = get_previous_weekday(today - timedelta(days=DAYCHECK))
dayEnd = get_previous_weekday(dayStart - timedelta(days=1))

# Chuyển đổi sang timestamp
today_timestamp = int(dayStart.timestamp())
yesterday_timestamp = int(dayEnd.timestamp())

def read_tickers(file_path):
    """Đọc danh sách mã chứng khoán từ file .txt"""
    with open(file_path, 'r') as file:
        tickers = file.read().splitlines()
    return tickers

def fetch_data_with_curl(ticker, from_timestamp, to_timestamp):
    """Sử dụng curl để lấy dữ liệu từ API"""
    url = f"https://dchart-api.vndirect.com.vn/dchart/history?symbol={ticker}&resolution=D&from={from_timestamp}&to={to_timestamp}"
    try:
        result = subprocess.run(['curl', '-s', url], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Failed to download {ticker}: {e}")
        return None

def parse_data(data):
    """Phân tích dữ liệu nhận được từ API"""
    try:
        data = json.loads(data)
    except ValueError:
        print("Invalid JSON response")
        return None

    if not data or 't' not in data:
        print("No data found, skipping.")
        return None

    df = pd.DataFrame({
        'timestamp': data['t'],
        'close': data['c'],
        'volume': data['v']
    })
    df['date'] = pd.to_datetime(df['timestamp'], unit='s')
    df.set_index('date', inplace=True)
    return df


def volumeHighChange(ticker):
    """Kiểm tra sự thay đổi lớn của khối lượng giao dịch giữa hai ngày"""
    # Lấy ngày hôm nay và ngày hôm qua không phải thứ 7 và Chủ nhật

    # Chuyển đổi sang timestamp
    todayStartTimestamp = int(datetime(dayStart.year, dayStart.month, dayStart.day, 9, 0, 0).timestamp())
    todayEndTimeStamp = int(datetime(dayStart.year, dayStart.month, dayStart.day, 15, 0, 0).timestamp())
    # Lấy dữ liệu ngày hôm nay
    today_data = fetch_data_with_curl(ticker, todayStartTimestamp, todayEndTimeStamp)
    if today_data is None:
        return False
    df_today = parse_data(today_data)

    # Lấy dữ liệu ngày hôm qua
    yesterdayStartTimestamp = int(datetime(dayEnd.year, dayEnd.month, dayEnd.day, 9, 0, 0).timestamp())
    yesterdayEndTimeStamp = int(datetime(dayEnd.year, dayEnd.month, dayEnd.day, 15, 0, 0).timestamp())
    yesterday_data = fetch_data_with_curl(ticker, yesterdayStartTimestamp, yesterdayEndTimeStamp)
    if yesterday_data is None:
        return False
    df_yesterday = parse_data(yesterday_data)

    # Tính toán sự thay đổi khối lượng giao dịch
    volume_change_today = df_today['volume'].sum()
    volume_change_yesterday = df_yesterday['volume'].sum()
    return volume_change_today > PERCENTAGE_HIGH_VOLUME * volume_change_yesterday
def percentage_change(df):
    """Tính phần trăm thay đổi của cột 'close' so với giá trị đầu tiên"""
    first_close = df.iloc[0]['close']
    df['percentage_change'] = (df['close'] - first_close) / first_close * 100
    return df

def analyze_stock(ticker):
    print('-------------- Analyzing', ticker, '--------------')
    """Phân tích một mã chứng khoán"""
    today_data = fetch_data_with_curl(ticker, yesterday_timestamp, today_timestamp)
    if today_data is None:
        return False

    df = parse_data(today_data)
    if df is None:
        return False

    meets_criteria_volume = volumeHighChange(ticker)

    if meets_criteria_volume:
        # Tính toán phần trăm thay đổi
        df = percentage_change(df)

        # Kiểm tra phần trăm thay đổi > 1%
        meets_criteria_percentage = df.iloc[-1]['percentage_change'] > 1

        if meets_criteria_percentage:
            print(f'{ticker} meets criteria.')
            return True
        else:
            print(f'{ticker} does not meet criteria (percentage change < {PERCENTAGE_HIGH_VOLUME}%).')
            return False
    else:
        print(f'{ticker} does not meet volume change criteria.')
        return False

def analyze_multiple_files(directory_path):
    """Phân tích mã chứng khoán từ nhiều file trong thư mục"""
    result = []

    for file_name in os.listdir(directory_path):
        exchangeResult = []
        print(f'####################### ANALYZING {file_name[:-4].upper()}  #######################')
        if file_name.endswith('.txt'):
            file_path = os.path.join(directory_path, file_name)
            tickers = read_tickers(file_path)
            for ticker in tickers:
                if analyze_stock(ticker):
                    exchangeResult.append(ticker)
        print(f'{file_name[:-4].upper()} Result: {exchangeResult}')
        if len(exchangeResult) > 0:
            result.append({file_name[:-4].upper(): exchangeResult})
    print('####################### RESULT #######################')
    return result

# Đường dẫn tới thư mục chứa các file .txt
directory_path = 'exchanges/'

# Phân tích và in kết quả
result = analyze_multiple_files(directory_path)
print(result)
