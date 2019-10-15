#!/usr/bin/env python

__author__ = "Bernd Zeimetz"
__copyright = "Copyright (C) 2019  Bernd Zeimetz"
__license__ = """
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
__email__ = "b.zeimetz@conova.com"
__status__ = "Production"

#import collectd
import glob
import json
import re
from subprocess import Popen, PIPE, CalledProcessError

USE_COLLECTD = True
PLUGIN_NAME = 'varnishstat'

def varnishstat(params):
    try:
        p = Popen(
                ['varnishstat'] + params,
                stdout = PIPE,
                stderr = PIPE
                )
        stdout, stderr = p.communicate()
        ret = p.returncode
        if ret > 0:
            return (ret, stdout + stderr)
        return (ret, stdout)
    except CalledProcessError as error:
        return(255, str(error))

def log(msg, severity='info'):
    msg = '{}:{}'.format(PLUGIN_NAME, msg)
    if USE_COLLECTD:
        sev = {
                'info' : collectd.info,
                'error' : collectd.error,
                }
        sev[severity](msg)
    else:
        print(msg)

def dispatch_value(collectd_type, value, plugin_instance, type_instance):
    if USE_COLLECTD:
        val = collectd.Values(plugin=PLUGIN_NAME, plugin_instance=plugin_instance)
        val.type = collectd_type
        val.type_instance = type_instance
        val.values = [value]
        val.dispatch()
    else:
        msg = '{}.{}.{}-{}.value = {}'.format(
                PLUGIN_NAME,
                plugin_instance,
                collectd_type,
                type_instance,
                value
                )
        print(msg)


def read_callback_instance(plugin_instance):
    params = ['-j', '-t 2', '-n{}'.format(plugin_instance)]
    ret, stat_raw = varnishstat(params)
    if ret > 0:
        log(str(stat_raw), 'error')
        raise Exception(stat_raw)

    try:
        stat = json.loads(str(stat_raw))
    except json.decoder.JSONDecodeError as error:
        log(str(error), 'error')
        raise

    for k,v in stat.items():
        if k == 'timestamp':
            continue
        if v['format'] == 'b':
            # bitmap format, ignore for now.
            continue
        collectd_type = {
                'c' : 'counter',
                'g' : 'gauge',
                }[v['flag']]
        type_instance = k
        value = v['value']

        dispatch_value(collectd_type, value, plugin_instance, type_instance)

def read_callback():
    vsms = glob.glob('/var/lib/varnish/*/_.vsm*')
    vsms = [ re.sub(r'^/var/lib/varnish/([^/]+)/_.*', r'\1', vsm) for vsm in vsms]
    vsms = list(set(vsms))
    for instance in vsms:
        read_callback_instance(instance)


if __name__ == "__main__":
    USE_COLLECTD = False
    read_callback()
else:
    import collectd
    collectd.register_read(read_callback)
