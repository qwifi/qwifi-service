#!/usr/bin/python
import unittest
import sys, os, ConfigParser, threading, time
from subprocess import call

sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
sys.path.append('/usr/local/wsgi/resources/python/')
sys.path.append(os.path.join(os.path.dirname(__file__), '../../ui/resources/python/usr/local/wsgi/resources/python/'))
import qwifi

class UtilTest(unittest.TestCase):
    def setUp(self):
        global server
        global user
        global password
        global database
        global stdout_log

        qwifi.parse_config_file("qwifi.conf")
        server = qwifi.config.get('database', 'server')
        user = qwifi.config.get('database', 'username')
        password = qwifi.config.get('database', 'password')
        database = qwifi.config.get('database', 'database')
        os.system("mysqldump -u " + user + " -p" + password + " " + database + " > " + "backup.sql")

    def tearDown(self):
        os.system("mysql -u " + user + " -p" + password + " -h " + server + " " + database + " < " + "backup.sql")


    def test_freeload_gen(self):
        test = (("name1", "mac_1", "date1"), ("name1", "mac_2", "date2"), ("name1", "mac_3", "date3"),
                ("name2", "mac_4", "date1"), ("name2", "mac_5", "date5"), ("name2", "mac_6", "date6"))
        actual_freeloaders = ["mac_2", "mac_3", "mac_5", "mac_6"]
        result = [fl for fl in qwifi.freeloader_gen(test)]
        self.assertEqual(actual_freeloaders, result,
                         "qwifi.freeloader_gen does not generate the correct values.\nGenerated Values:"
                         + str(actual_freeloaders) + "\ndoes not equal\nExpected:" + str(result))

    def test_parse_args(self):
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

    def test_main(self):
        #setup
        call(["sudo", "service", "hostapd", "start"])
        os.system("mysql -u " + user + " -p" + password + " -h " + server + " " + database + " < " + "test.sql")
        r = open("qwifi.conf", "r")
        lines = r.readlines()
        r.close()
        sys.argv = []
        sys.argv.append("")
        sys.argv.append("-c")
        sys.argv.append("qwifi.conf")
        qwifi.args = qwifi.parse_args()
        qwifi.parse_config_file("qwifi.conf")
        #launch main
        t = threading.Thread(target=qwifi.main)
        t.start()
        self.assertTrue(t.is_alive())
        time.sleep(5)
        #change config file
        w = open("qwifi.conf", "w+")
        w.writelines([item for item in lines[0:-1]])
        w.write("mode = AP")
        w.close()
        #continue test
        self.assertTrue(t.is_alive())
        time.sleep(5)
        self.assertTrue(t.is_alive())
        qwifi.terminate_service()
        time.sleep(5)#this has to be before assertFalse. Otherwise main may be sleeping while assertFalse is called.
        self.assertFalse(t.is_alive())
        #reset config file
        w = open("qwifi.conf", "w+")
        w.writelines(item for item in lines)
        w.close()


if __name__ == '__main__':
    unittest.main()
