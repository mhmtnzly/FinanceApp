import os
import pandas as pd
from flask import make_response


class Extract:
    def __init__(self) -> None:
        pass

    def csv_file_name(self, file):
        file = file.split('.')[0]
        return file

    def reading_csv_files(self, file):
        read = pd.read_csv(file)
        return read

    def reading_json_files(self, file):
        data = pd.read_json(file)
        df = pd.DataFrame()
        df['date'] = data['chart']['result'][0]['timestamp']
        df['date'] = pd.to_datetime(df['date'], unit='s')
        df['low'] = data['chart']['result'][0]['indicators']['quote'][0]['low']
        df['open'] = data['chart']['result'][0]['indicators']['quote'][0]['open']
        df['volume'] = data['chart']['result'][0]['indicators']['quote'][0]['volume']
        df['high'] = data['chart']['result'][0]['indicators']['quote'][0]['high']
        df['close'] = data['chart']['result'][0]['indicators']['quote'][0]['close']
        df['adjustedClose'] = data['chart']['result'][0]['indicators']['adjclose'][0]['adjclose']
        return df

    def df_arrange(self, df, filename):
        df['name'] = self.csv_file_name(filename)
        df.columns = ['date', 'low', 'open', 'volume',
                      'high', 'close', 'adjustedClose', 'name']
        df = df[['name', 'date', 'low', 'open',
                 'volume', 'high', 'close', 'adjustedClose']]
        df['date'] = pd.to_datetime(df['date'], dayfirst=True)
        df['date'] = [d.strftime(
            '%m-%d-%Y') if not pd.isnull(d) else '' for d in df['date']]
        return df



    def download_csv_nasdaq(self, data):
        cols = ['date', 'low', 'open', 'volume',
                'high', 'close', 'adjustedClose']
        result = [{col: getattr(d, col) for col in cols} for d in data]
        result = pd.DataFrame.from_dict(
            pd.json_normalize(result)).to_csv(index=False)
        return result

    def download_json_nasdaq(self, data):
        cols = ['date', 'low', 'open', 'volume',
                'high', 'close', 'adjustedClose']
        result = [{col: getattr(d, col) for col in cols} for d in data]
        result = {'results': result}

        return result

    def get_nasdaq_data(self, data):
        cols = ['id', 'date', 'low', 'open', 'volume',
                'high', 'close', 'adjustedClose']
        result = [{col: getattr(d, col) for col in cols} for d in data]
        return result

    def file_download(self, fileName, data, fileType):
        response = make_response(data)
        cd = 'attachment; filename='+fileName+'.' + fileType
        response.headers['Content-Disposition'] = cd
        response.mimetype = 'text/'+fileType
        return response

    def file_type(self, filename):
        fileType = filename.split('.')[1]
        return fileType