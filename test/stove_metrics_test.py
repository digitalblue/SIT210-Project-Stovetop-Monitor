#####################################################
# SIT210 Project - Stovetop Monitor
# SID: 215279167
#
# stove_metrics_test.py
#
#####################################################

import unittest
from datetime import datetime

from stovetop_monitor.stove_metrics import StoveMetrics

class TestStoveMetrics(unittest.TestCase):

    stovemetrics = None

    def setUp(self):
        self.stovemetrics = StoveMetrics()

    def test_stove_metrics_object_created_with_defaults(self):

        self.assertEqual(self.stovemetrics.rolling_metrics_count, 5)
        self.assertEqual(self.stovemetrics.temp_list, [])
        self.assertEqual(self.stovemetrics.hum_list, [])
        self.assertEqual(self.stovemetrics.dist_list, [])
        self.assertEqual(self.stovemetrics.event_time_list, [])
        self.assertEqual(self.stovemetrics.rolling_metrics_list, [])
        self.assertEqual(self.stovemetrics.temp_avg, 0.0)
        self.assertEqual(self.stovemetrics.hum_avg, 0.0)
        self.assertEqual(self.stovemetrics.dist_avg, 0.0)
        self.assertEqual(self.stovemetrics.health_status, 0)

    def test_set_metrics_appends_values_to_list(self):
        # given
        date = datetime.strptime('Jun 1 2021  12:00AM', '%b %d %Y %I:%M%p')
        
        # when
        self.stovemetrics.set_metrics(20.00, 30.00, 40.00, date )
        
        # then
        self.assertTrue(len(self.stovemetrics.temp_list) == 1)
        self.assertTrue(len(self.stovemetrics.hum_list) == 1)
        self.assertTrue(len(self.stovemetrics.dist_list) == 1)

        self.assertEqual(self.stovemetrics.temp_list[0], 20.00)
        self.assertEqual(self.stovemetrics.hum_list[0], 30.00)
        self.assertEqual(self.stovemetrics.dist_list[0], 40.00)
        self.assertEqual(self.stovemetrics.event_time_list[0], datetime(2021, 6, 1, 0, 0))

    def test_get_rolling_metrics(self):

        # given - create and set rolling event data
        date0 = datetime.strptime('Jun 1 2021  12:00AM', '%b %d %Y %I:%M%p')
        date1 = datetime.strptime('Jun 1 2021  12:01AM', '%b %d %Y %I:%M%p')
        date2 = datetime.strptime('Jun 1 2021  12:02AM', '%b %d %Y %I:%M%p')
        date3 = datetime.strptime('Jun 1 2021  12:03AM', '%b %d %Y %I:%M%p')
        date4 = datetime.strptime('Jun 1 2021  12:04AM', '%b %d %Y %I:%M%p')
        self.stovemetrics.set_metrics(10.00, 10.00, 10.00, date0 )
        self.stovemetrics.set_metrics(20.00, 20.00, 20.00, date1 )
        self.stovemetrics.set_metrics(30.00, 30.00, 30.00, date2 )
        self.stovemetrics.set_metrics(40.00, 40.00, 40.00, date3 )
        self.stovemetrics.set_metrics(50.00, 50.00, 50.00, date4 )
        
        # assert first element of list popped after creating rolling metrics
        self.assertTrue(len(self.stovemetrics.temp_list) == 4)
        self.assertTrue(len(self.stovemetrics.hum_list) == 4)
        self.assertTrue(len(self.stovemetrics.dist_list) == 4)

        self.assertEqual(self.stovemetrics.temp_list[0], 20.00)
        self.assertEqual(self.stovemetrics.hum_list[0], 20.00)
        self.assertEqual(self.stovemetrics.dist_list[0], 20.00)
        self.assertEqual(self.stovemetrics.event_time_list[0], datetime(2021, 6, 1, 0, 1))

        # when
        rolling_metrics = self.stovemetrics.get_rolling_metrics()

        # then
        self.assertTrue(len(rolling_metrics) == 6)
        self.assertEqual(rolling_metrics[1].get('temp'), 10.00)
        self.assertEqual(rolling_metrics[1].get('hum'), 10.00)
        self.assertEqual(rolling_metrics[1].get('dist'), 10.00)
        self.assertEqual(rolling_metrics[1].get('time'), "Tue 1 Jun 2021, 00:00:00")
        self.assertEqual(rolling_metrics[5].get('temp'), 50.00)
        self.assertEqual(rolling_metrics[5].get('hum'), 50.00)
        self.assertEqual(rolling_metrics[5].get('dist'), 50.00)
        self.assertEqual(rolling_metrics[5].get('time'), "Tue 1 Jun 2021, 00:04:00")

    def test_get_avg_metrics(self):

        # given - create and set rolling event data
        date0 = datetime.strptime('Jun 1 2021  12:00AM', '%b %d %Y %I:%M%p')
        date1 = datetime.strptime('Jun 1 2021  12:01AM', '%b %d %Y %I:%M%p')
        date2 = datetime.strptime('Jun 1 2021  12:02AM', '%b %d %Y %I:%M%p')
        date3 = datetime.strptime('Jun 1 2021  12:03AM', '%b %d %Y %I:%M%p')
        date4 = datetime.strptime('Jun 1 2021  12:04AM', '%b %d %Y %I:%M%p')
        self.stovemetrics.set_metrics(10.00, 10.00, 10.00, date0 )
        self.stovemetrics.set_metrics(20.00, 20.00, 20.00, date1 )
        self.stovemetrics.set_metrics(30.00, 30.00, 30.00, date2 )
        self.stovemetrics.set_metrics(40.00, 40.00, 40.00, date3 )
        self.stovemetrics.set_metrics(50.00, 50.00, 50.00, date4 )
        
        # when
        avg_metrics = self.stovemetrics.get_avg_metrics()
        
        # then - average of 10, 20, 30, 40 , 50 = 30
        self.assertEqual(avg_metrics[0], 30.00)
        self.assertEqual(avg_metrics[1], 30.00)
        self.assertEqual(avg_metrics[2], 30.00)
        self.assertEqual(avg_metrics[3], datetime(2021, 6, 1, 0, 1))

    def test_health_status(self):

        # when
        self.stovemetrics.set_health_status(2)

        # given
        date = datetime.strptime('Jun 1 2021  12:00AM', '%b %d %Y %I:%M%p')
        self.stovemetrics.set_metrics(20.00, 30.00, 40.00, date )
        
        # then
        rolling_metrics = self.stovemetrics.get_rolling_metrics()
        self.assertEqual(rolling_metrics[0].get('status'), 2)


if __name__ == '__main__':
    unittest.main()
