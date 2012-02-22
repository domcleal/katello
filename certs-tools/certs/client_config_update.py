#!/usr/bin/python -u
#
# Copyright (c) 2008--2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#
# key=value formatted "config file" mapping script
#
# NOT TO BE USED DIRECTLY
# This is called by a script generated by the katello-bootstrap utility.
#
# Specifically engineered with the RHN Update Agent configuration files
# in mind though it is relatively generic in nature.
#
# Author: Todd Warner <taw@redhat.com>
# FIXME: fix the docs

"""
Client configuration mapping script that writes to an RHN Update Agent-type
config file(s)

I.e., maps a file with RHN Update Agent-like key=value pairs e.g.,
serverURL=https://test-satellite.example.redhat.com/XMLRPC
noSSLServerURL=http://test-satellite.example.redhat.com/XMLRPC
enableProxy=0
sslCACert=/usr/share/rhn/RHN-ORG-TRUSTED-SSL-CERT

 (NOTE - older RHN Satellite's and Proxy's used:
  sslCACert=/usr/share/rhn/RHNS-CORP-CA-CERT)

And maps that to the client's configuration files.

-------------
To map new settings to a file that uses the format key=value, where
key[comment]=value is a comment line you do this (e.g., mapping
key=value pairs to /etc/sysconfig/rhn/up2date):

    1. edit a file (e.g., 'client-config-overrides.txt'), inputing new key=value pairs
       to replace in config file (e.g., /etc/sysconfig/rhn/up2date).
       Specifically:
serverURL=https://test-satellite.example.redhat.com/XMLRPC
noSSLServerURL=http://test-satellite.example.redhat.com/XMLRPC

    2. ./client_config_update.py /etc/sysconfig/rhn/up2date client-config-overrides.txt

That's all there is to it.

If you are running an older RHN Update Agent, the rhn_register file can be
mapped as well:

    ./client_config_update.py /etc/sysconfig/rhn/rhn_register client-config-overrides.txt
"""


import os
import sys
import string
import tempfile

DEFAULT_CLIENT_CONFIG_OVERRIDES = 'client-config-overrides.txt'

RHN_REGISTER = "/etc/sysconfig/rhn/rhn_register"
UP2DATE = "/etc/sysconfig/rhn/up2date"


def _parseConfigLine(line):
    """parse a line from a config file. Format can be either "key=value\n"
       or "whatever text\n"

    return either:
        (key, value)
    or
        None
    The '\n' is always stripped from the value.
    """

    kv = string.split(line, '=')
    if len(kv) < 2:
        # not a setting
        return None

    if len(kv) > 2:
        # '=' is part of the value, need to rejoin it.
        kv = kv[0], string.join(kv[1:], '=')

    if string.find(kv[0], '[comment]') > 0:
        # comment; not a setting
        return None

    # it's a setting, trim the '\n' and return the (key, value) pair.
    kv[0] = string.strip(kv[0])
    if kv[1][-1] == '\n':
        kv[1] = kv[1][:-1]
    return tuple(kv)

def readConfigFile(configFile):
    "read in config file, return dictionary of key/value pairs"

    fin = open(configFile, 'rb')

    d = {}

    for line in fin.readlines():
        kv = _parseConfigLine(line)
        if kv:
            d[kv[0]] = kv[1]
    return d


def dumpConfigFile(configFile):
    "print out dictionary of key/value pairs from configFile"

    import pprint
    pprint.pprint(readConfigFile(configFile))


def mapNewSettings(configFile, dnew):
    fo = tempfile.TemporaryFile(prefix = '/tmp/client-config-overrides-', mode = 'r+b')
    fin = open(configFile, 'rb')

    changedYN = 0

    # write to temp file
    for line in fin.readlines():
        kv = _parseConfigLine(line)
        if not kv:
            # not a setting, write the unaltered line
            fo.write(line)
        else:
            # it's a setting, populate from the dictionary
            if dnew.has_key(kv[0]):
                if dnew[kv[0]] != kv[1]:
                    fo.write('%s=%s\n' % (kv[0], dnew[kv[0]]))
                    changedYN = 1
                else:
                    fo.write(line)
            # it's a setting but not being mapped
            else:
                fo.write(line)
    fin.close()

    if changedYN:
        # write from temp file to configFile
        fout = open(configFile, 'wb')
        fo.seek(0)
        fout.write(fo.read())
        print '*', configFile, 'written'


def parseCommandline():
    """parse/process the commandline

    Commandline is dead simple for easiest portability.
    """

    # USAGE & HELP!
    if '--usage' in sys.argv or '-h' in sys.argv or '--help' in sys.argv:
        print """\
usage: python %s CONFIG_FILENAME NEW_MAPPINGS [options]
arguments:
  CONFIG_FILENAME       config file to alter
  NEW_MAPPINGS          file containing new settings that map onto the
                        config file
options:
  -h, --help            show this help message and exit
  --usage               show brief usage summary

examples:
  python %s %s %s
  python %s %s %s
""" % (sys.argv[0],
       sys.argv[0], RHN_REGISTER, DEFAULT_CLIENT_CONFIG_OVERRIDES,
       sys.argv[0], UP2DATE, DEFAULT_CLIENT_CONFIG_OVERRIDES)

        sys.exit(0)


    if len(sys.argv) != 3:
        msg = "ERROR: exactly two arguments are required, see --help"
        raise TypeError(msg)

    configFilename = os.path.abspath(sys.argv[1])
    newMappings = os.path.abspath(sys.argv[2])

    if not os.path.exists(configFilename):
        msg = ("ERROR: filename to alter (1st argument), does not exist:\n"
               "       %s"
               % configFilename)
        raise IOError(msg)

    if not os.path.exists(newMappings):
        msg = ("ERROR: filename that contains the mappings (2nd argument), "
               "does not exist:\n"
               "       %s" % newMappings)
        raise IOError(msg)

    return configFilename, newMappings


def main():
    "parse commandline, process config file key=value mappings"

    configFilename, newMappings = parseCommandline()
    #dumpConfigFile(configFilename)
    #mapNewSettings('test-up2date', readConfigFile(DEFAULT_CLIENT_CONFIG_OVERRIDES))

    mapNewSettings(configFilename, readConfigFile(newMappings))

if __name__ == '__main__':
    sys.exit(main() or 0)