# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Course Builder test suite.

This script runs all functional and units test in the Course Builder project.

Here is how to use the script:
    - download WebTest Python package from a URL below and put
      the files in a folder of your choice, for example: tmp/webtest:
          http://pypi.python.org/packages/source/W/WebTest/WebTest-1.4.2.zip
    - update your Python path:
          PYTHONPATH=$PYTHONPATH:/tmp/webtest
    - run this command from a command line:
          python tests/suite.py
    - review the output to make sure there are no errors or warnings

Good luck!
"""

__author__ = 'Sean Lip'

import base64
import os
import sys
import unittest

# The following import is needed in order to add third-party libraries.
import appengine_config  # pylint: disable-msg=unused-import
import webtest

from google.appengine.datastore import datastore_stub_util
from google.appengine.ext import deferred
from google.appengine.ext import testbed


EXPECTED_TEST_COUNT = 67


def empty_environ():
    os.environ['AUTH_DOMAIN'] = 'example.com'
    os.environ['SERVER_NAME'] = 'localhost'
    os.environ['HTTP_HOST'] = 'localhost'
    os.environ['SERVER_PORT'] = '8080'
    os.environ['USER_EMAIL'] = ''
    os.environ['USER_ID'] = ''


class BaseTestClass(unittest.TestCase):
    """Base class for setting up and tearing down test cases."""

    def getApp(self):  # pylint: disable-msg=g-bad-name
        """Returns the main application to be tested."""
        raise Exception('Not implemented.')

    def setUp(self):  # pylint: disable-msg=g-bad-name
        empty_environ()

        # setup an app to be tested
        self.testapp = webtest.TestApp(self.getApp())
        self.testbed = testbed.Testbed()
        self.testbed.activate()

        # configure datastore policy to emulate instantaneously and globally
        # consistent HRD; we also patch dev_appserver in main.py to run under
        # the same policy
        policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(
            probability=1)

        # declare any relevant App Engine service stubs here
        self.testbed.init_user_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_datastore_v3_stub(consistency_policy=policy)
        self.testbed.init_taskqueue_stub()
        self.taskq = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)

    def tearDown(self):  # pylint: disable-msg=g-bad-name
        self.testbed.deactivate()

    def execute_all_deferred_tasks(self, queue_name='default'):
        """Executes all pending deferred tasks."""
        for task in self.taskq.GetTasks(queue_name):
            deferred.run(base64.b64decode(task['body']))


def create_test_suite():
    """Loads all test classes from appropriate modules."""
    import tests.functional.tests as functional_tests  # pylint: disable=C6204
    import tests.unit.tests as unit_tests  # pylint: disable=C6204

    tests = []
    for item in [unit_tests, functional_tests]:
        tests += unittest.TestLoader().loadTestsFromModule(item)

    # Here is how to test just one test case:
    #    tests = unittest.TestLoader().loadTestsFromTestCase(
    #        functional_tests.MultipleCoursesTest)

    return unittest.TestLoader().suiteClass(tests)


def fix_sys_path():
    """Fix the sys.path to include GAE extra paths."""
    import dev_appserver  # pylint: disable=C6204

    # dev_appserver.fix_sys_path() prepends GAE paths to sys.path and hides
    # our classes like 'tests' behind other modules that have 'tests'.
    # Here, unlike dev_appserver, we append the path instead of prepending it,
    # so that our classes come first.
    sys.path += dev_appserver.EXTRA_PATHS[:]


def main():
    """Starts in-process server and runs all test cases in this module."""
    fix_sys_path()
    result = unittest.TextTestRunner(verbosity=2).run(create_test_suite())

    if result.testsRun != EXPECTED_TEST_COUNT:
        raise Exception('Expected %s tests to be run, not %s.' %
                        (EXPECTED_TEST_COUNT, result.testsRun))

    if result.errors or result.failures:
        raise Exception(
            'Functional test suite failed: %s errors, %s failures of '
            ' %s tests run.' % (
                len(result.errors), len(result.failures), result.testsRun))

    import tests.functional.actions as actions  # pylint: disable-msg=g-import-not-at-top

    count = len(actions.UNIQUE_URLS_FOUND.keys())
    result.stream.writeln('INFO: Unique URLs found: %s' % count)
    result.stream.writeln('INFO: All %s tests PASSED!' % EXPECTED_TEST_COUNT)


if __name__ == '__main__':
    appengine_config.gcb_force_default_encoding('ascii')
    main()
