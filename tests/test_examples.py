import os
import sys
import time
import errno
import subprocess
from threading import Thread
from utils import require_user
from utils import require_8021q
from utils import require_bridge
from utils import require_bond
from nose.plugins.skip import SkipTest
from pyroute2.netlink import NetlinkError

try:
    import imp
    from Queue import Queue

    def _import(symbol):
        return imp.load_module(symbol, *imp.find_module(symbol))

except ImportError:
    from queue import Queue
    from importlib import import_module

    def _import(symbol):
        return import_module(symbol)


def interface_event():
    with open(os.devnull, 'w') as fnull:
        subprocess.call('ip link add dev d0 type dummy'.split(),
                        stdout=fnull,
                        stderr=fnull)
        subprocess.call('ip link del dev d0'.split(),
                        stdout=fnull,
                        stderr=fnull)


class TestExamples(object):

    def setup(self):
        self.pwd = os.getcwd()
        os.chdir('../examples/')
        newdir = os.getcwd()
        if newdir not in sys.path:
            sys.path.append(newdir)
        self.client_feedback = Queue()
        self.server_feedback = Queue()
        self.pr, self.pw = os.pipe()
        __builtins__['pr2_sync'] = self.pr

    def teardown(self):
        os.chdir(self.pwd)
        os.close(self.pr)
        os.close(self.pw)

    def launcher(self, client, server=None):

        client_error = None
        server_error = None

        def wrapper(parent, symbol, feedback):
            try:
                if symbol in globals():
                    globals()[symbol]()
                else:
                    _import(symbol)
                feedback.put(None)
            except Exception as e:
                feedback.put(e)

        if server is not None:
            s = Thread(target=wrapper, args=(self,
                                             server,
                                             self.server_feedback))
            s.start()
            time.sleep(1)

        c = Thread(target=wrapper, args=(self,
                                         client,
                                         self.client_feedback))
        c.start()
        client_error = self.client_feedback.get()

        if server is not None:
            os.write(self.pw, b'q')
            server_error = self.server_feedback.get()
            s.join()

        c.join()

        if any((client_error, server_error)):
            print("client error:")
            print(client_error)
            print("server error:")
            print(server_error)
            raise RuntimeError

    def test_create_bond(self):
        require_user('root')
        require_bond()
        self.launcher('create_bond')

    def test_create_interface(self):
        require_user('root')
        self.launcher('create_interface')

    def test_create_vlan(self):
        require_user('root')
        require_8021q()
        self.launcher('create_vlan')

    def test_ip_monitor(self):
        require_user('root')
        self.launcher('interface_event', server='ip_monitor')

    def test_ipdb_autobr(self):
        require_user('root')
        require_bridge()
        self.launcher('ipdb_autobr')

    def test_ipdb_chain(self):
        require_user('root')
        require_bond()
        self.launcher('ipdb_chain')

    def test_ipdb_precb(self):
        require_user('root')
        self.launcher('ipdb_precb')

    def test_ipdb_routes(self):
        require_user('root')
        self.launcher('ipdb_routes')

    def test_nla_operators(self):
        require_user('root')
        self.launcher('nla_operators')

    def test_nla_operators2(self):
        require_user('root')
        self.launcher('nla_operators2')

    def test_wireless_intf(self):
        self.launcher('nl80211_interface_type')

    def test_taskstats(self):
        require_user('root')
        try:
            self.launcher('taskstats')
        except NetlinkError as x:
            if x.code == errno.ENOENT:
                raise SkipTest('missing taskstats support')
            else:
                raise

    def _test_pmonitor(self):
        require_user('root')
        try:
            self.launcher('pmonitor', server='server')
        except NetlinkError as x:
            if x.code == errno.ENOENT:
                raise SkipTest('missing taskstats support')
            else:
                raise
