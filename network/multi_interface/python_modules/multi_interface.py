import re
import time
import sys
import os
import copy

PARAMS = {}

NAME_PREFIX = 'vm_'

METRICS = {
    'time' : 0,
    'data' : {}
}
LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_MAX = 5

INTERFACES = []
descriptors = []

stats_tab = {
    "rx_bytes"  : 0,
    "rx_pkts"   : 1,
    "rx_errs"   : 2,
    "rx_drops"  : 3,
    "tx_bytes" : 8,
    "tx_pkts"  : 9,
    "tx_errs"  : 10,
    "tx_drops" : 11,
}

# Where to get the stats from
net_stats_file = "/proc/net/dev"

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_init(params):
    global descriptors
    global INTERFACES
    
#    INTERFACES = params.get('interfaces')
    watch_interfaces = params.get('interfaces')
    excluded_interfaces = params.get('excluded_interfaces')
    get_interfaces(watch_interfaces,excluded_interfaces)

#    print INTERFACES
    time_max = 60

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_delta,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%.4f',
        'units'       : '/s',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'network',
        }


    for dev in INTERFACES:
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "rx_bytes_" + dev,
                    "units"       : "bytes/sec",
                    "description" : "received bytes per sec",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "rx_pkts_" + dev,
                    "units"       : "pkts/sec",
                    "description" : "received packets per sec",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "rx_errs_" + dev,
                    "units"       : "pkts/sec",
                    "description" : "received error packets per sec",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "rx_drops_" + dev,
                    "units"       : "pkts/sec",
                    "description" : "receive packets dropped per sec",
                    }))
    
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "tx_bytes_" + dev,
                    "units"       : "bytes/sec",
                    "description" : "transmitted bytes per sec",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "tx_pkts_" + dev,
                    "units"       : "pkts/sec",
                    "description" : "transmitted packets per sec",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "tx_errs_" + dev,
                    "units"       : "pkts/sec",
                    "description" : "transmitted error packets per sec",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "tx_drops_" + dev,
                    "units"       : "pkts/sec",
                    "description" : "transmitted dropped packets per sec",
                    }))

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass
    
def get_interfaces(watch_interfaces, excluded_interfaces):
   global INTERFACES
   if_excluded = 0
        
   # check if particular interfaces have been specifieid. Watch only those
   if watch_interfaces != "":
      INTERFACES = watch_interfaces.split(" ")      
   else:
      if excluded_interfaces != "":
         excluded_if_list = excluded_interfaces.split(" ")
      f = open(net_stats_file, "r")
      for line in f:
         # Find only lines with :
         if re.search(":", line):
            a = line.split(":")
            dev_name = a[0].lstrip()
                    
            # Determine if interface is excluded by name or regex
            for ex in excluded_if_list:
               if re.match(ex,dev_name):
                  if_excluded = 1

            if not if_excluded:
               INTERFACES.append(dev_name)
            if_excluded = 0
   return 0


def get_metrics():
    """Return all metrics"""

    global METRICS, LAST_METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

	try:
	    file = open(net_stats_file, 'r')
    
	except IOError:
	    return 0

        # convert to dict
        metrics = {}
        for line in file:
            if re.search(":", line):
                a = line.split(":")
                dev_name = a[0].lstrip()
                metrics[dev_name] = re.split("\s+", a[1].lstrip())

        # update cache
        LAST_METRICS = copy.deepcopy(METRICS)
        METRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [METRICS, LAST_METRICS]
    
def get_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    # Names will be in the format of tx/rx underscore metric_name underscore interface
    # e.g. tx_bytes_eth0
    parts = name.split("_")
    iface = parts[2]
    name = parts[0] + "_" + parts[1]

    index = stats_tab[name]

    try:
      delta = (float(curr_metrics['data'][iface][index]) - float(last_metrics['data'][iface][index])) /(curr_metrics['time'] - last_metrics['time'])
      if delta < 0:
	print name + " is less 0"
	delta = 0
    except KeyError:
      delta = 0.0      

    return delta


if __name__ == '__main__':
    try:
        params = {
            "interfaces": "",
            "excluded_interfaces": "dummy",
            "debug"        : True,
            }
        metric_init(params)
        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is '+d['format']) % (d['name'],  v)
            time.sleep(5)
    except StandardError:
        print sys.exc_info()[0]
        os._exit(1)
