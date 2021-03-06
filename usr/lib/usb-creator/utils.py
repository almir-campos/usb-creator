#! /usr/bin/env python3

import subprocess
import urllib.request
import urllib.error
import re
import threading
from os.path import exists


def shell_exec_popen(command, kwargs={}):
    print(('Executing:', command))
    return subprocess.Popen(command, shell=True,
                            stdout=subprocess.PIPE, **kwargs)


def shell_exec(command):
    print(('Executing:', command))
    return subprocess.call(command, shell=True)


def getoutput(command):
    #return shell_exec(command).stdout.read().strip()
    try:
        output = subprocess.check_output(command, shell=True).decode('utf-8').strip().split('\n')
    except:
        output = []
    return output


def chroot_exec(command):
    command = command.replace('"', "'").strip()  # FIXME
    return shell_exec('chroot /target/ /bin/sh -c "%s"' % command)


def memoize(func):
    """ Caches expensive function calls.

    Use as:

        c = Cache(lambda arg: function_to_call_if_yet_uncached(arg))
        c('some_arg')  # returns evaluated result
        c('some_arg')  # returns *same* (non-evaluated) result

    or as a decorator:

        @memoize
        def some_expensive_function(args [, ...]):
            [...]

    See also: http://en.wikipedia.org/wiki/Memoization
    """
    class memodict(dict):
        def __call__(self, *args):
            return self[args]

        def __missing__(self, key):
            ret = self[key] = func(*key)
            return ret
    return memodict()


def get_config_dict(file, key_value=re.compile(r'^\s*(\w+)\s*=\s*["\']?(.*?)["\']?\s*(#.*)?$')):
    """Returns POSIX config file (key=value, no sections) as dict.
    Assumptions: no multiline values, no value contains '#'. """
    d = {}
    with open(file) as f:
        for line in f:
            try:
                key, value, _ = key_value.match(line).groups()
            except AttributeError:
                continue
            d[key] = value
    return d


# Check for internet connection
def has_internet_connection(test_url=None):
    if test_url is None:
        test_url == ''
        src_lst = '/etc/apt/sources.list'
        if exists(src_lst):
            with open(src_lst, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line.startswith('#'):
                        matchObj = re.search('http[a-z0-9:\/\.]+', line)
                        if matchObj:
                            test_url = matchObj.group(0)
                            break
    if test_url == '':
        test_url = 'http://google.com'
    #print(("test_url = {}".format(test_url)))
    try:
        urllib.request.urlopen(test_url, timeout=1)
        return True
    except urllib.error.URLError:
        pass
    return False


# Check if running in VB
def runningInVirtualBox():
    dmiBIOSVersion = getoutput("dmidecode -t0 | grep 'Version:' | awk -F ': ' '{print $2}'")
    dmiSystemProduct = getoutput("dmidecode -t1 | grep 'Product Name:' | awk -F ': ' '{print $2}'")
    dmiBoardProduct = getoutput("dmidecode -t2 | grep 'Product Name:' | awk -F ': ' '{print $2}'")
    if dmiBIOSVersion != "VirtualBox" and dmiSystemProduct != "VirtualBox" and dmiBoardProduct != "VirtualBox":
        return False
    return True


# Check if is 64-bit system
def isAmd64():
    machine = getoutput("uname -m")[0]
    if machine == "x86_64":
        return True
    return False


# Check for backports
def has_backports():
    try:
        bp = getoutput("grep backports /etc/apt/sources.list | grep -v ^#")[0]
    except:
        bp = ''
    if bp.strip() == "":
        try:
            bp = getoutput("grep backports /etc/apt/sources.list.d/*.list | grep -v ^#")[0]
        except:
            bp = ''
    if bp.strip() != "":
        return True
    return False


def getPackageVersion(package, candidate=False):
    cmd = "env LANG=C bash -c 'apt-cache policy %s | grep \"Installed:\"'" % package
    if candidate:
        cmd = "env LANG=C bash -c 'apt-cache policy %s | grep \"Candidate:\"'" % package
    lst = getoutput(cmd)[0].strip().split(' ')
    version = lst[-1]
    if 'none' in version:
        version = ''
    return version


# Class to run commands in a thread and return the output in a queue
class ExecuteThreadedCommands(threading.Thread):

    def __init__(self, commandList, theQueue=None, returnOutput=False):
        super(ExecuteThreadedCommands, self).__init__()
        self.commands = commandList
        self.queue = theQueue
        self.returnOutput = returnOutput

    def run(self):
        if isinstance(self.commands, (list, tuple)):
            for cmd in self.commands:
                self.exec_cmd(cmd)
        else:
            self.exec_cmd(self.commands)

    def exec_cmd(self, cmd):
        if self.returnOutput:
            ret = getoutput(cmd)
        else:
            ret = shell_exec(cmd)
        if self.queue is not None:
            self.queue.put(ret)
