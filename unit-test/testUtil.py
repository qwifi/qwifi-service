#!/usr/bin/python
import unittest
import sys, os, ConfigParser

sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
import qwifi



class UtilTest(unittest.TestCase):
    def test_freeload_gen(self):
        test = (("name1", "mac_1", "date1"), ("name1", "mac_2", "date2"), ("name1", "mac_3", "date3"),
                ("name2", "mac_4", "date1"), ("name2", "mac_5", "date5"), ("name2", "mac_6", "date6"))
        actual_freeloaders = ["mac_2", "mac_3", "mac_5", "mac_6"]
        result = [fl for fl in qwifi.freeloader_gen(test)]
        self.assertEqual(actual_freeloaders, result,
                         "qwifi.freeloader_gen does not generate the correct values.\nGenerated Values:"
                         + str(actual_freeloaders) + "\ndoes not equal\nExpected:" + str(result))
    def test_parse_args(self):
        temp = sys.argv
        sys.argv = []
        sys.argv.append("")
        sys.argv.append("-n")
        args = qwifi.parse_args()
        self.assertEqual("Namespace(c='qwifi.conf', n=True)", str(args))
        sys.argv.pop()
        sys.argv.append("-c")
        sys.argv.append("test")
        args = qwifi.parse_args()
        self.assertEqual("Namespace(c='test', n=False)", str(args))
        sys.argv.append("-n")
        args = qwifi.parse_args()
        self.assertEqual("Namespace(c='test', n=True)", str(args))

    def test_config_section_map_exception(self):
        with self.assertRaises(ConfigParser.NoSectionError):
            qwifi.config_section_map("derp")

    def test_parse_config_file_exception(self):
        with self.assertRaises(ConfigParser.NoSectionError):
            qwifi.parse_config_file('bad.conf')

if __name__ == '__main__':
    unittest.main()
