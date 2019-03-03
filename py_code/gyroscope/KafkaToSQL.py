import sys
import math
import numpy as np
import pandas as pd
import mysql.connector
from datetime import datetime
from sklearn.externals import joblib
from kafka import KafkaConsumer

class CatchDataFrame(pd.DataFrame):
    def __init__(self, col_name, num):
        super().__init__(np.zeros(num * len(col_name)).reshape(num, len(col_name)), columns=col_name)
        self.num = num
        self.pointer = 0

    def pointer_add(self):
        self.pointer += 1

    def pointer_zero(self):
        self.pointer = 0

def dist(a,b):
    return math.sqrt((a*a)+(b*b))

def get_y_rotation(x,y,z):
    radians = math.atan2(x, dist(y, z))
    return -math.degrees(radians)

def get_x_rotation(x,y,z):
    radians = math.atan2(y, dist(x, z))
    return math.degrees(radians)

def datastd(df):
    dtdfstd = []
    for i in list(df.columns):
        dtstd = np.std(np.array(df[i]))
        dtdfstd.append(dtstd)
    return dtdfstd

def statusvote(df, clf):
    status = ["靜止", "走路", "慢跑", "快跑"]
    lis = list(clf.predict(df))
    statuscount = [lis.count(0), lis.count(1), lis.count(2), lis.count(3)]
    statusscale = list(map(lambda var: round(var / len(lis), 3), statuscount))
    statusmode = statusscale.index(max(statusscale))
    return status[statusmode]

def sendtoSQL(df):
    subset = df[:]
    records = [tuple(x) for x in subset.values]
    db = mysql.connector.connect(
        user='srh',
        password='srh',
        host='mysql',
        database='smart_running_helper',
    )
    table_name = 'user_sport_database'

    cursor = db.cursor()
    sql = 'INSERT INTO ' + table_name + ' VALUES'\
            '(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
    cursor.executemany(sql, records)
    db.commit()
    db.close()

if __name__ == "__main__":
    # 創建計算數據標準差的DataFrame (col_name, 計算標準差資料筆數)
    stddfcol_name = ['gyro_x', 'gyro_y', 'gyro_z', 'accel_x', 'accel_y', 'accel_z', 'rotation_x', 'rotation_y']
    stddf = CatchDataFrame(stddfcol_name, 10)

    # 創建評估狀態的DataFrame (col_name, 評估狀態資料筆數)
    svdfcol_name = ['gyro_x', 'gyro_y', 'gyro_z', 'accel_x', 'accel_y', 'accel_z', 'rotation_x', 'rotation_y',
                    'gyro_x_stdev', 'gyro_y_stdev', 'gyro_z_stdev', 'accel_x_stdev', 'accel_y_stdev', 'accel_z_stdev',
                    'rotation_x_stdev', 'rotation_y_stdev']
    svdf = CatchDataFrame(svdfcol_name, 50)

    # 創建暫存SQL的DataFrame (col_name, SQL_batch資料筆數)
    savedfcol_name = ['UserID', 'time', 'Tag', 'gyro_x', 'gyro_y', 'gyro_z', 'accel_x', 'accel_y', 'accel_z',
                      'rotation_x', 'rotation_y', 'gyro_x_stdev', 'gyro_y_stdev', 'gyro_z_stdev',
                      'accel_x_stdev', 'accel_y_stdev', 'accel_z_stdev', 'rotation_x_stdev', 'rotation_y_stdev']
    savedf = CatchDataFrame(savedfcol_name, 100)

    # 載入訓練模型 KNN_no_std KNN Tree XGBoost
    clf = joblib.load("../Ref/gyroscope/KNN_0217_exclude.pkl")
    # 設定要連線到Kafka集群的相關設定, 產生一個Kafka的Consumer的實例
    consumer = KafkaConsumer(
        # Kafka集群在那裡?
        bootstrap_servers=["kafka:9092"],
        # ConsumerGroup的名稱
        group_id="test_004",
        # 指定msgKey的反序列化器, 若Key為None, 無法反序列化
        # key_deserializer=bytes.decode,
        # 指定msgValue的反序列化器
        value_deserializer=bytes.decode,
        # 是否從這個ConsumerGroup尚未讀取的partition / offset開始讀
        auto_offset_reset="earliest",
    )
    # 指定想要訂閱訊息的topic名稱
    topic_name = "test0225"
    # 讓Consumer向Kafka集群訂閱指定的topic
    consumer.subscribe(topics=topic_name)
    # 持續的拉取Kafka有進來的訊息
    try:
        print("Start listen incoming messages ...")
        # 持續監控是否有新的record進來
        for record in consumer:
            # 資料儲存控制設定
            if stddf.pointer == stddf.num:
                stddf.pointer_zero()
            if svdf.pointer == svdf.num:
                # 評估狀態
                status = statusvote(svdf, clf)
                savedf.iloc[savedf.pointer - svdf.num:savedf.pointer, 2] = status
                svdf.pointer_zero()
            if savedf.pointer == savedf.num:
                # ToSQL
                sendtoSQL(savedf)
                savedf.pointer_zero()
            # 取出msgValue並切割數據
            msgValue = record.value
            Value = msgValue.split(',')
            # 轉換資料型態並計算相對數據
            datatime = datetime.fromtimestamp(record.timestamp / 1000)
            gyro_xyz = tuple(map(lambda var: float(var), Value[1:4]))
            accel_xyz = tuple(map(lambda var: float(var), Value[4::]))
            accel_scaled_xyz = tuple(map(lambda var: var / 16384.0, accel_xyz))
            x_rotation = round(get_x_rotation(accel_scaled_xyz[0], accel_scaled_xyz[1], accel_scaled_xyz[2]), 4)
            y_rotation = round(get_y_rotation(accel_scaled_xyz[0], accel_scaled_xyz[1], accel_scaled_xyz[2]), 4)
            # 合併Data(gyro_xyz, accel_xyz, x_rotation, y_rotation)
            Data = gyro_xyz + accel_xyz + (x_rotation, y_rotation)
            # 將資料加入計算數據標準差的DataFrame
            stddf.iloc[stddf.pointer, :] = Data
            stddf.pointer_add()
            # 將資料加入評估狀態的DataFrame
            svdf.iloc[svdf.pointer, :len(Data)] = Data
            svdf.iloc[svdf.pointer, len(Data):] = datastd(stddf)
            svdf.pointer_add()
            # 將資料加入暫存SQL的DataFrame
            savedf.iloc[savedf.pointer, 0] = "UserID"
            savedf.iloc[savedf.pointer, 1] = datatime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-4]
            savedf.iloc[savedf.pointer, 3:] = svdf.iloc[svdf.pointer-1, :]
            savedf.pointer_add()
    except:
        # 錯誤處理
        e_type, e_value, e_traceback = sys.exc_info()
        print("type ==> %s" % (e_type))
        print("value ==> %s" % (e_value))
        print("traceback ==> file name: %s" % (e_traceback.tb_frame.f_code.co_filename))
        print("traceback ==> line no: %s" % (e_traceback.tb_lineno))
        print("traceback ==> function name: %s" % (e_traceback.tb_frame.f_code.co_name))
    finally:
        consumer.close()
        print("close")