# -----------------------------------------------------------------------------
# 
# This file is the copyrighted property of Tableau Software and is protected 
# by registered patents and other applicable U.S. and international laws and 
# regulations.
# 
# Unlicensed use of the contents of this file is prohibited. Please refer to 
# the NOTICES.txt file for further details.
# 
# -----------------------------------------------------------------------------

"""
    Tableau Datasource Verification Tool Tester - TDVTT
    Test the TDVT.

    You can run these like:
    All tests:
        py -3 test_tdvt.py
    A Class:
        py -3 test_tdvt.py ReRunFailedTestsTest
    One specific test:
        py -3 test_tdvt.py ReRunFailedTestsTest.test_logical_rerun_fail
"""

import configparser
import os
import unittest
import xml.etree.ElementTree
import pkg_resources
from tdvt import tdvt
from tdvt.config_gen import datasource_list
from tdvt.config_gen.test_config import TestConfig,TestSet
from tdvt.resources import get_path

class DiffTest(unittest.TestCase):
    def test_diff(self):
        LOG.log("Starting diff tests:\n")
        subdir = 'diff_tests'
        #Go through the 'expected' files as the driver.
        test_files = []
        for item in os.listdir(os.path.join(TEST_DIRECTORY, subdir)):
            if 'expected.' in item:
                test_files.append(item)

        failed_tests = []
        for test in test_files:
            actual_file = test.replace('expected', 'actual')
            
            actual_file = os.path.join(os.path.join(TEST_DIRECTORY, subdir), actual_file)
            expected_file = os.path.join(os.path.join(TEST_DIRECTORY, subdir), test)

            LOG.log("Testing: " + test)
            actual_xml = xml.etree.ElementTree.parse(actual_file).getroot()
            expected_xml = xml.etree.ElementTree.parse(expected_file).getroot()
            compare_sql = False
            compare_tuples = False
            if 'expected.sql' in test:
                compare_sql = True
            if 'expected.tuples' in test:
                compare_tuples = True
            if 'expected.both' in test:
                compare_tuples = True
                compare_sql = True
            results = tdvt.TestResult()
            test_config = tdvt.TestConfig(compare_sql, compare_tuples)
            results.add_actual_output(tdvt.TestOutput(actual_xml, test_config), actual_file)
            expected_output = tdvt.TestOutput(expected_xml, test_config)

            num_diffs, diff_string = tdvt.diff_test_results(results, expected_output)
            results.set_best_matching_expected_output(expected_output, expected_file, 0, [0])

            if results.all_passed() and 'shouldfail' not in test:
                LOG.log("Test passed: " + test)
                self.assertTrue(True)
            elif not results.all_passed() and 'shouldfail' in test:
                LOG.log("Test passed: " + test)
                self.assertTrue(True)
            else:
                LOG.log("Test failed: " + test)
                failed_tests.append(test)
                self.assertTrue(False)
            LOG.log("\n")

        if failed_tests:
            LOG.log("All failed tests:\n")
            for item in failed_tests:
                LOG.log("Failed -- " + item)

        LOG.log("Ending diff tests:\n")
        return len(test_files), len(failed_tests)

class BaseTDVTTest(unittest.TestCase):
    def check_results(self, test_results, total_test_count, should_pass=True):
        test_status_expected = "passed" if should_pass else "failed"
        #Make sure we ran the right number of tests and that they all passed.
        self.assertTrue(len(test_results) == total_test_count, "Did not run the right number of tests.")
        for path, test_result in test_results.items():
            passed = test_result is not None
            passed = passed and test_result.all_passed()
            test_status = "passed" if passed else "failed"
            self.assertTrue(passed == should_pass, "Test [{0}] {1} but should have {2}.".format(path, test_status, test_status_expected))

class ExpressionTest(BaseTDVTTest):
    def setUp(self):
        self.config_file = 'tool_test/config/expression.tde.cfg'
        self.tds_file = tdvt.get_tds_full_path(ROOT_DIRECTORY, 'tool_test/tds/cast_calcs.tde.tds')
        self.test_config = tdvt.TestConfig()

    def test_expression_tests(self):
        all_test_results = {}
        all_test_results = tdvt.run_tests_parallel(tdvt.generate_test_file_list(ROOT_DIRECTORY, '', self.config_file, ''), self.tds_file, self.test_config)

        self.check_results(all_test_results, 2)

class LogicalTest(BaseTDVTTest):
    def setUp(self):
        self.config_file = 'tool_test/config/logical.tde.cfg'
        self.tds_file = tdvt.get_tds_full_path(ROOT_DIRECTORY, 'tool_test/tds/cast_calcs.tde.tds')
        self.test_config = tdvt.TestConfig()
        self.test_config.logical = True

    def test_logical_tests(self):
        all_test_results = {}
        all_test_results = tdvt.run_tests_parallel(tdvt.generate_test_file_list(ROOT_DIRECTORY, '', self.config_file, ''), self.tds_file, self.test_config)

        self.check_results(all_test_results, 1)

class ReRunFailedTestsTest(BaseTDVTTest):
    def setUp(self):
        self.test_dir = TEST_DIRECTORY
        self.config_file = 'tool_test/config/logical.tde.cfg'
        self.tds_file = tdvt.get_tds_full_path(ROOT_DIRECTORY, 'tool_test/tds/cast_calcs.tde.tds')
        self.test_config = tdvt.TestConfig()
        self.test_config.logical = True

    def test_failed_test_output(self):
        """Make sure TDVT writes the correct output file for rerunning failed tests."""
        all_test_results = {}
        #This will cause the test to fail as expected.
        self.test_config.tested_sql = True
        self.test_config.invocation_extra_args = '--compare-sql'
        all_test_results = tdvt.run_tests_parallel(tdvt.generate_test_file_list(ROOT_DIRECTORY, '', self.config_file, ''), self.tds_file, self.test_config)
        tdvt.write_standard_test_output(all_test_results, self.test_dir)

        self.check_results(all_test_results, 1, False)

        #Now rerun the failed tests which should fail again, indicating that the 'tested_sql' option was persisted correctly.
        all_test_results = tdvt.run_failed_tests_impl(get_path('tool_test', 'tdvt_output.json', __name__), ROOT_DIRECTORY, tdvt.init_arg_parser())

        self.check_results(all_test_results, 1, False)

    def test_logical_rerun(self):
        all_test_results = tdvt.run_failed_tests_impl(get_path('tool_test/rerun_failed_tests', 'logical.json', __name__), ROOT_DIRECTORY, tdvt.init_arg_parser())
        self.check_results(all_test_results, 1)

    def test_expression_rerun(self):
        all_test_results = tdvt.run_failed_tests_impl(get_path('tool_test/rerun_failed_tests','exprtests.json', __name__), ROOT_DIRECTORY, tdvt.init_arg_parser())
        self.check_results(all_test_results, 2)

    def test_combined_rerun(self):
        all_test_results = tdvt.run_failed_tests_impl(get_path('tool_test/rerun_failed_tests', 'combined.json', __name__), get_path(ROOT_DIRECTORY, module_name=__name__), tdvt.init_arg_parser())
        self.check_results(all_test_results, 3)

    def test_logical_rerun_fail(self):
        all_test_results = tdvt.run_failed_tests_impl(get_path('tool_test/rerun_failed_tests', 'logical_compare_sql.json', __name__), ROOT_DIRECTORY, tdvt.init_arg_parser())
        self.check_results(all_test_results, 1, False)

class PathTest(unittest.TestCase):
    def test_config_file_path(self):
        cfg_path = tdvt.get_config_file_full_path(ROOT_DIRECTORY, 'tool_test/config/logical.tde.cfg')
        self.assertTrue(os.path.isfile(cfg_path))

    def test_config_file_default_path(self):
        cfg_path = tdvt.get_config_file_full_path(os.path.join(ROOT_DIRECTORY, 'tool_test'), 'logical.tde.cfg')
        self.assertTrue(os.path.isfile(cfg_path))

        #        self.tds_file = tdvt.get_tds_full_path(ROOT_DIRECTORY, 'tool_test/tds/cast_calcs.tde.tds')

class ConfigTest(unittest.TestCase):
    def test_load_ini(self):
        config = configparser.ConfigParser()
        config.read(get_path('tool_test/ini', 'aurora.ini', __name__))
        test_config = datasource_list.LoadTest(config)
        x = test_config.get_logical_tests() + test_config.get_expression_tests()

        test1 = TestSet('logical.calcs.aurora.cfg', 'cast_calcs.aurora.tds', '', 'logicaltests/setup/calcs/setup.*.bool_.xml')

        test2 = TestSet('logical.staples.aurora.cfg', 'Staples.aurora.tds', 'Filter.Trademark', 'logicaltests/setup/staples/setup.*.bool_.xml')

        test3 = TestSet('logical.lod.aurora.cfg', 'Staples.aurora.tds', '', 'logicaltests/setup/lod/setup.*.bool_.xml')

        test4 = TestSet('expression_test.aurora.cfg', 'cast_calcs.aurora.tds', 'string.char,dateparse', 'exprtests/standard/')

        test5 = TestSet('expression.lod.aurora.cfg', 'cast_calcs.aurora.tds', '', 'exprtests/lodcalcs/setup.*.txt')

        tests = [test1, test2, test3, test4, test5]
        
        for test in tests:
            found = [y for y in x if y == test] 
            self.assertTrue(found, "[Did not find expected value of [{0}]".format(test))


    def test_load_ini_missing(self):
        config = configparser.ConfigParser()
        config.read(get_path('tool_test/ini', 'aurora_missing.ini', __name__))
        test_config = datasource_list.LoadTest(config)
        x = test_config.get_logical_tests() + test_config.get_expression_tests()

        test1 = TestSet('logical.calcs.aurora.cfg', 'cast_calcs.aurora.tds', '', 'logicaltests/setup/calcs/setup.*.bool_.xml')

        test2 = TestSet('logical.staples.aurora.cfg', 'Staples.aurora.tds', 'Filter.Trademark', 'logicaltests/setup/staples/setup.*.bool_.xml')

        test3 = TestSet('expression_test.aurora.cfg', 'cast_calcs.aurora.tds', 'string.char,dateparse', 'exprtests/standard/')

        tests = [test1, test2, test3]
        
        for test in tests:
            found = [y for y in x if y == test] 
            self.assertTrue(found, "[Did not find expected value of [{0}]".format(test))
        
    def test_load_ini_missing2(self):
        config = configparser.ConfigParser()
        config.read(get_path('tool_test/ini', 'aurora_missing2.ini', __name__))
        test_config = datasource_list.LoadTest(config)
        x = test_config.get_logical_tests() + test_config.get_expression_tests()

        test1 = TestSet('logical.calcs.aurora.cfg', 'cast_calcs.aurora.tds', '', 'logicaltests/setup/calcs/setup.*.bool_.xml')

        test2 = TestSet('logical.staples.aurora.cfg', 'Staples.aurora.tds', '', 'logicaltests/setup/staples/setup.*.bool_.xml')

        test3 = TestSet('expression_test.aurora.cfg', 'cast_calcs.aurora.tds', '', 'exprtests/standard/')

        tests = [test1, test2, test3]
        
        for test in tests:
            found = [y for y in x if y == test] 
            self.assertTrue(found, "[Did not find expected value of [{0}]".format(test))

    def test_load_ini_bigquery(self):
        config = configparser.ConfigParser()
        config.read(get_path('tool_test/ini', 'bigquery.ini', __name__))
        test_config = datasource_list.LoadTest(config)
        x = test_config.get_logical_tests() + test_config.get_expression_tests()

        test1 = TestSet('logical.calcs.bigquery.cfg', 'cast_calcs.bigquery.tds', '', 'logicaltests/setup/calcs/setup.*.bigquery.xml')

        test2 = TestSet('logical.staples.bigquery.cfg', 'Staples.bigquery.tds', '', 'logicaltests/setup/staples/setup.*.bigquery.xml')

        test3 = TestSet('expression_test.bigquery.cfg', 'cast_calcs.bigquery.tds', 'string.ascii,string.char,string.bind_trim,string.left.real,string.right.real,dateparse', 'exprtests/standard/')

        tests = [test1, test2, test3]
        
        for test in tests:
            found = [y for y in x if y == test] 
            self.assertTrue(found, "[Did not find expected value of [{0}]".format(test))

    def test_load_override(self):
        config = configparser.ConfigParser()
        config.read(get_path('tool_test/ini', 'override.ini', __name__))
        test_config = datasource_list.LoadTest(config)
        x = test_config.get_logical_tests() + test_config.get_expression_tests()

        test1 = TestSet('logical.calcs.bigquery.cfg', 'cast_calcs.bigquery.tds', '', 'logicaltests/setup/calcs/setup.*.bigquery.xml')

        test2 = TestSet('logical.staples.bigquery.cfg', 'Staples.bigquery.tds', '', 'logicaltests/setup/staples/setup.*.bigquery.xml')

        test3 = TestSet('expression_test.bigquery.cfg', 'cast_calcs.bigquery.tds', '', 'exprtests/standard/')

        tests = [test1, test2, test3]
        
        self.assertTrue(test_config.d_override == 'DWorkFaster=True', 'Override did not match.')

        for test in tests:
            found = [y for y in x if y == test] 
            self.assertTrue(found, "[Did not find expected value of [{0}]".format(test))

    def test_load_ini_bigquery_sql(self):
        config = configparser.ConfigParser()
        config.read(get_path('tool_test/ini', 'bigquery_sql.ini', __name__))
        test_config = datasource_list.LoadTest(config)
        x = test_config.get_logical_tests() + test_config.get_expression_tests()

        test1 = TestSet('logical.calcs.bigquery_sql.cfg', 'cast_calcs.bigquery_sql.tds', '', 'logicaltests/setup/calcs/setup.*.bigquery_sql.xml')

        test2 = TestSet('logical.staples.bigquery_sql.cfg', 'Staples.bigquery_sql.tds', 'Filter.Trademark', 'logicaltests/setup/staples/setup.*.bigquery_sql.xml')

        test3 = TestSet('logical.lod.bigquery_sql.cfg', 'Staples.bigquery_sql.tds', '', 'logicaltests/setup/lod/setup.*.bigquery_sql.xml')

        test4 = TestSet('expression_test.bigquery_sql.cfg', 'cast_calcs.bigquery_sql.tds', 'string.ascii,string.char,string.bind_trim,string.left.real,string.right.real,dateparse,math.degree,math.radians,cast.str,cast.int.nulls,logical', 'exprtests/standard/')

        test5 = TestSet('expression_test_dates.bigquery_sql.cfg', 'cast_calcs.bigquery_sql_dates.tds', 'string.ascii,string.char,string.bind_trim,string.left.real,string.right.real,dateparse,math.degree,math.radians,cast.str,cast.int.nulls', 'exprtests/standard/')

        test6 = TestSet('expression_test_dates2.bigquery_sql.cfg', 'cast_calcs.bigquery_sql_dates2.tds', 'string.ascii,string.char,string.bind_trim,string.left.real,string.right.real,dateparse,math.degree,math.radians,cast.str,cast.int.nulls', 'exprtests/standard/')

        test7 = TestSet('expression.lod.bigquery_sql.cfg', 'cast_calcs.bigquery_sql.tds', '', 'exprtests/lodcalcs/setup.*.txt')

        test8 = TestSet('logical_test_dates.bigquery_sql.cfg', 'cast_calcs.bigquery_sql.tds', '', 'exprtests/standard/setup.*.bigquery_dates.xml')

        tests = [test1, test2, test3, test4, test5, test6, test7, test8]

        for test in tests:
            found = [y for y in x if y == test] 
            self.assertTrue(found, "[Did not find expected value of [{0}]".format(test))

    def test_load_ini_staplesdata_on(self):
        config = configparser.ConfigParser()
        config.read(get_path('tool_test/ini', 'staples_data.ini', __name__))
        test_config = datasource_list.LoadTest(config)
        x = test_config.get_logical_tests() + test_config.get_expression_tests()

        test1 = TestSet('expression.staples.bigquery.cfg', 'Staples.bigquery.tds', '', 'exprtests/staples/setup.*.txt')

        tests = [test1]
        
        for test in tests:
            found = [y for y in x if y == test] 
            self.assertTrue(found, "[Did not find expected value of [{0}]".format(test))

    def test_load_ini_staplesdata_off(self):
        config = configparser.ConfigParser()
        config.read(get_path('tool_test/ini', 'staples_data_off.ini', __name__))
        test_config = datasource_list.LoadTest(config)
        x = test_config.get_logical_tests() + test_config.get_expression_tests()

        self.assertTrue(not x)

ROOT_DIRECTORY = pkg_resources.resource_filename(__name__, '') 
TEST_DIRECTORY = pkg_resources.resource_filename(__name__, 'tool_test')
print ("Using root dir " + str(ROOT_DIRECTORY))
print ("Using test dir " + str(TEST_DIRECTORY))
LOG = tdvt.init_logging(TEST_DIRECTORY, True)
tdvt.configure_tabquery_path()
if __name__ == '__main__':

    LOG.log("Starting TDVT tests\n")

    unittest.main()

    LOG.log("Ending TDVT tests\n")
