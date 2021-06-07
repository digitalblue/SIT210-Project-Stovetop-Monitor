#####################################################
# SIT210 Project - Stovetop Monitor
# SID: 215279167
#
# stove_metrics.py
#
#####################################################

from datetime import datetime

class StoveMetrics:
    def __init__(self):
        self.rolling_metrics_count = 5
        self.temp_list = []
        self.hum_list = []
        self.dist_list = []
        self.event_time_list = []
        self.rolling_metrics_list = []
        self.temp_avg = 0.0
        self.hum_avg = 0.0
        self.dist_avg = 0.0
        self.health_status = 0
    
    def set_metrics(self, temp, hum, dist, event_time):
        self.temp_list.append(temp)
        self.hum_list.append(hum)
        self.dist_list.append(dist)
        self.event_time_list.append(event_time)
        
        # calculate and set averages of rolling count
        self.temp_avg = round(sum(self.temp_list) / self.rolling_metrics_count, 2)
        self.hum_avg = round(sum(self.hum_list) / self.rolling_metrics_count, 2)
        self.dist_avg = round(sum(self.dist_list) / self.rolling_metrics_count, 2)
        self.create_rolling_metrics()
        
        if len(self.temp_list) >= self.rolling_metrics_count:
            # pop first entry to keep rolling
            self.temp_list.pop(0)
            self.hum_list.pop(0)
            self.dist_list.pop(0)
            self.event_time_list.pop(0)
    
    def create_rolling_metrics(self):
        # create rolling metrics list as dictionary objects for conversion to json
        rolling_metrics = []
        if len(self.event_time_list) > 0:
            metrics_dict = {"temp": self.temp_avg, "hum": self.hum_avg, "dist": self.dist_avg, "time": self.event_time_list[0].strftime("%a %-d %b %Y, %H:%M:%S"), "status": self.health_status}
            rolling_metrics.append(metrics_dict)
            for i in range(len(self.temp_list)):
                metrics_dict = {"temp": self.temp_list[i], "hum": self.hum_list[i], "dist": self.dist_list[i], "time": self.event_time_list[i].strftime("%a %-d %b %Y, %H:%M:%S")}
                rolling_metrics.append(metrics_dict)
        self.rolling_metrics_list = rolling_metrics
        
    def get_rolling_metrics(self):
        return self.rolling_metrics_list
    
    def get_avg_metrics(self):
        if len(self.event_time_list) > 0:        
            return [self.temp_avg, self.hum_avg, self.dist_avg, self.event_time_list[0]]
        return [self.temp_avg, self.hum_avg, self.dist_avg, datetime.now()]
    
    def set_health_status(self, status):
        self.health_status = status