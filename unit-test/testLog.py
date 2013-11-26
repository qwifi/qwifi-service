#!/usr/bin/python
import unittest
import sys, os
from cStringIO import StringIO
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
import qwifi


class LogTest(unittest.TestCase):

        def test_log_debug(self):
            qwifi.log_level = qwifi.log_levels.DEBUG
            qwifi.log("DEBUG", "level=DEBUG", qwifi.log_levels.DEBUG)
            f = open("/var/log/syslog")
            lines = f.readlines()
            # this 'weird' indexing is because the beginning of each line is a timestamp + the device name
            # the only way I could get only the message was to index from the back of the line.
            self.assertEqual(lines[-1][-19:-1], "[DEBUG]level=DEBUG")
            f.close()

        def test_log_error(self):
            qwifi.log_level = qwifi.log_levels.DEBUG
            qwifi.log("ERROR", "level=ERROR", qwifi.log_levels.DEBUG)
            f = open("/var/log/syslog")
            lines = f.readlines()
            self.assertEqual(lines[-1][-19:-1], "[ERROR]level=ERROR")
            f.close()

        def test_log_greater(self):
            qwifi.log_level = qwifi.log_levels.ERROR
            qwifi.log("greater", "level=DEBUG log_level=ERROR", qwifi.log_levels.DEBUG)
            f = open("/var/log/syslog")
            lines = f.readlines()
            f.close()
            self.assertEqual(lines[-1][-43:-1], "[INVALID] Tried to log with invalid level.")

        def test_log_info(self):
            qwifi.log_level = qwifi.log_levels.DEBUG
            qwifi.log("info", "level=info", qwifi.log_levels.INFO)
            f = open("/var/log/syslog")
            lines = f.readlines()
            self.assertEqual(lines[-1][-17:-1], "[info]level=info")
            f.close()

        def test_log_none(self):
            qwifi.log("none", "level=none", qwifi.log_levels.NONE)
            f = open("/var/log/syslog")
            lines = f.readlines()
            self.assertEqual(lines[-1][-43:-1], "[INVALID] Tried to log with invalid level.")
            f.close()

        def test_log_unknown(self):
            qwifi.log("UNKNOWN", "level=UNKNOWN", -1)
            f = open("/var/log/syslog")
            lines = f.readlines()
            self.assertEqual(lines[-1][-28:-1], "[UNKNOWN MODE]level=UNKNOWN")
            f.close()

        def test_log_warning(self):
            qwifi.log_level = qwifi.log_levels.DEBUG
            qwifi.log("WARNING", "level=WARNING", qwifi.log_levels.DEBUG)
            f = open("/var/log/syslog")
            lines = f.readlines()
            self.assertEqual(lines[-1][-23:-1], "[WARNING]level=WARNING")
            f.close()

        def test_log_foreground(self):
            real_stdout = sys.stdout
            sys.stdout = myout = StringIO()
            qwifi.log_level = qwifi.log_levels.DEBUG
            qwifi.mode = qwifi.modes.FOREGROUND
            qwifi.log("FG", "level=DEBUG", qwifi.log_levels.DEBUG)
            sys.stdout = real_stdout
            self._baseAssertEqual(myout.getvalue(), "[FG]level=DEBUG\n")



if __name__ == '__main__':
    unittest.main()
