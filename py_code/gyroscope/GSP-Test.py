import sys
import math
import numpy as np
import pandas as pd
import mysql.connector
from datetime import datetime
from sklearn.externals import joblib
from kafka import KafkaConsumer
from elasticsearch import Elasticsearch
from redis import Redis


class GyroscopeConsumerProcess:
    def __init__(self, userid, clf):
        self.userid = userid
        self.clf = clf
        self.col_name_list = ['UserID', 'time', 'Tag', 'gyro_x', 'gyro_y', 'gyro_z', 'accel_x', 'accel_y', 'accel_z',
                              'rotation_x', 'rotation_y', 'gyro_x_stdev', 'gyro_y_stdev', 'gyro_z_stdev',
                              'accel_x_stdev', 'accel_y_stdev', 'accel_z_stdev', 'rotation_x_stdev', 'rotation_y_stdev']
        # 創建計算數據標準差的DataFrame (col_name, 計算標準差資料筆數)
        self.stddf = CatchDataFrame(self.col_name_list[3:11], 10)
        # 創建評估狀態的DataFrame (col_name, 評估狀態資料筆數)
        self.svdf = CatchDataFrame(self.col_name_list[3:], 50)
        # 創建暫存SQL的DataFrame (col_name, SQL_batch資料筆數)
        self.savedf = CatchDataFrame(self.col_name_list, 500)
        # 創建判斷狀態持續或改變的變數
        self.statuslist = []
        self.oldstatus = -1
        self.newstatus = -1

    def connect(self, kafka_group_id="process1"):
        # 設定要連線到Kafka集群的相關設定, 產生一個Kafka的Consumer的實例
        self.consumer = KafkaConsumer(bootstrap_servers=["kafka:9092"], group_id=kafka_group_id,
                                      value_deserializer=bytes.decode, auto_offset_reset="earliest")
        # 讓Consumer向Kafka集群訂閱指定的topic
        self.consumer.subscribe(topics=self.userid)
        # 建立Elasticsearch連線 (預設9200)
        self.es = Elasticsearch('elasticsearch')
        # ES => 設定schema
        mappings = {
            "mappings": {
                self.userid: {  # user00 是doc_type(table)
                    "properties": {
                        "userID": {"type": "string"},  # text
                        "time": {"type": "date"},
                        "status": {"type": "integer"}
                    }
                }
            }
        }
        # 創建一個index(database)
        self.es.indices.create(index=self.userid, ignore=400, body=mappings)
        self.rs = Redis(host='redis', port=6379, db=0)

    def datastd(self):
        dtdfstd = []
        for i in list(self.stddf.columns):
            dtstd = np.std(np.array(self.stddf[i]))
            dtdfstd.append(dtstd)
        return dtdfstd

    def statusvote(self):
        status = ["0", "1", "2", "3"]
        lis = list(self.clf.predict(self.svdf))
        statuscount = [lis.count(0), lis.count(1), lis.count(2), lis.count(3)]
        statusscale = list(map(lambda var: round(var / len(lis), 3), statuscount))
        statusmode = statusscale.index(max(statusscale))
        self.newstatus = int(status[statusmode])
        return status[statusmode]

    def sendtosql(self, table_name):
        subset = self.savedf[:]
        if self.savedf.pointer != self.savedf.num:
            subset = self.savedf.iloc[:self.savedf.pointer, :]
        column_num = len(subset.columns)
        records = [tuple(x) for x in subset.values]
        db = mysql.connector.connect(
            user='srh',
            password='srh',
            host='mysql',
            database='smart_running_helper',
        )
        cursor = db.cursor()
        sql = 'INSERT INTO ' + table_name + ' VALUES(%s' + ', %s' * (column_num - 1) + ')'
        cursor.executemany(sql, records)
        db.commit()
        db.close()

    def sendtoredis(self):
        self.statuslist.append(self.newstatus)
        if len(self.statuslist) > 3:
            del self.statuslist[0]
            if self.newstatus != self.oldstatus and max(self.statuslist) == min(self.statuslist):
                self.rs.set(self.userid, self.newstatus)
                self.oldstatus = self.newstatus

    def main(self):
        print("Start listen incoming messages ...")
        # 持續監控是否有新的record進來
        for record in self.consumer:
            # 取出msgValue並切割數據
            msgvalue = record.value
            value = msgvalue.split(',')
            # 轉換資料型態並計算相對數據
            datatime = datetime.fromtimestamp(record.timestamp / 1000)
            gyro_xyz = tuple(map(lambda var: float(var), value[1:4]))
            accel_xyz = tuple(map(lambda var: float(var), value[4:]))
            accel_scaled_xyz = tuple(map(lambda var: var / 16384.0, accel_xyz))
            get_y_rotation = lambda x, y, z: round(-math.degrees(math.atan2(x, math.sqrt((y * y) + (z * z)))), 4)
            get_x_rotation = lambda x, y, z: round(math.degrees(math.atan2(y, math.sqrt((x * x) + (z * z)))), 4)
            x_rotation = get_x_rotation(accel_scaled_xyz[0], accel_scaled_xyz[1], accel_scaled_xyz[2])
            y_rotation = get_y_rotation(accel_scaled_xyz[0], accel_scaled_xyz[1], accel_scaled_xyz[2])
            # 合併Data(gyro_xyz, accel_xyz, x_rotation, y_rotation)
            Data = gyro_xyz + accel_xyz + (x_rotation, y_rotation)
            # 將資料加入計算數據標準差的DataFrame
            self.stddf.iloc[self.stddf.pointer, :] = Data
            self.stddf.pointer_add()
            # 將資料加入評估狀態的DataFrame
            self.svdf.iloc[self.svdf.pointer, :len(Data)] = Data
            self.svdf.iloc[self.svdf.pointer, len(Data):] = self.datastd()
            self.svdf.pointer_add()
            # 將資料加入暫存SQL的DataFrame
            self.savedf.iloc[self.savedf.pointer, 0] = self.userid
            self.savedf.iloc[self.savedf.pointer, 1] = datatime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-4]
            self.savedf.iloc[self.savedf.pointer, 3:] = self.svdf.iloc[self.svdf.pointer - 1, :]
            self.savedf.pointer_add()
            # 資料儲存控制設定
            if self.stddf.pointer == self.stddf.num:
                self.stddf.pointer_zero()
            if self.svdf.pointer == self.svdf.num:
                # 評估狀態
                self.savedf.iloc[self.savedf.pointer - self.svdf.num:self.savedf.pointer, 2] = self.statusvote()
                self.svdf.pointer_zero()
                # ToELK
                elkdata = {"userID": self.userid,
                           "time": datatime.strftime("%Y-%m-%dT%H:%M:%S.000+0800"),
                           "status": self.newstatus}
                self.es.index(index=self.userid, doc_type='gyroscope', body=elkdata)
                # ToRedis
                self.sendtoredis()
            if self.savedf.pointer == self.savedf.num:
                # ToSQL
                self.sendtosql('user_sport_database')
                self.savedf.pointer_zero()

    def close(self):
        self.consumer.close()
        self.sendtosql('user_sport_database')
        print('Closed Process')


class CatchDataFrame(pd.DataFrame):
    def __init__(self, col_name, num):
        super().__init__(np.zeros(num * len(col_name)).reshape(num, len(col_name)), columns=col_name)
        self.num = num
        self.pointer = 0

    def pointer_add(self):
        self.pointer += 1

    def pointer_zero(self):
        self.pointer = 0


if __name__ == "__main__":
    try:
        # 載入訓練模型 KNN_no_std KNN Tree XGBoost
        clf = joblib.load("./model/KNN_16.pkl")
        # 創建屬於UserID的實例
        user = GyroscopeConsumerProcess("user1", clf)
        # 設定相關連線作業
        user.connect()
        # 開始進行處理
        user.main()
    except (Exception,):
        # 錯誤處理
        e_type, e_value, e_traceback = sys.exc_info()
        print("type ==> %s" % (e_type))
        print("value ==> %s" % (e_value))
        print("traceback ==> file name: %s" % (e_traceback.tb_frame.f_code.co_filename))
        print("traceback ==> line no: %s" % (e_traceback.tb_lineno))
        print("traceback ==> function name: %s" % (e_traceback.tb_frame.f_code.co_name))
    except (SystemExit, KeyboardInterrupt):
        user.close()
        print("SystemExit")