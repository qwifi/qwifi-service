import unittest
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
import qwifi



class UtilTest(unittest.TestCase):
    def test_freeload_gen(self):
        test = (("name1", "mac_1", "date1"),("name1", "mac_2", "date2"),("name1", "mac_3", "date3"),
                ("name2", "mac_4", "date1"),("name2", "mac_5", "date5"),("name2", "mac_6", "date6"))
        actual_freeloaders = ["mac_2", "mac_3", "mac_5", "mac_6"]
        result = [fl for fl in qwifi.freeloader_gen(test)]
        self.assertEqual(actual_freeloaders, result, "qwifi.freeloader_gen does not generate the correct values.\nGenerated Values:"
                                                + str(actual_freeloaders) + "\ndoes not equal\nExpected:" + str(result))




if __name__ == '__main__':
    unittest.main()
