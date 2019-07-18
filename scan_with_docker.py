#!/usr/bin/env python3

import re
import sys
import shlex
import socket
import ipaddress
import subprocess
from multiprocessing.dummy import Pool as ThreadPool

# Note, you don't have to enter an API key to simply scan a subnet.
SHODAN_API_KEY = "Insert your API key here if you want to use Shodan"

def port_scan(ip):
    try:
        socket.create_connection((str(ip), 3389), timeout=1)
        return str(ip)
    except:
        pass

    return None

def run_rdesktop_in_docker(ip):
    args = ['/usr/bin/docker'] + shlex.split("run cve-2019-0708:latest {}".format(str(ip)))
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)

    try:
        stdout, stderr = process.communicate(timeout=10)
    except:
        process.kill()
        stdout, stderr = process.communicate(timeout=1)

    returncode = process.returncode

    if returncode != 0:
        return None
    elif stdout is not None and re.search('Target is VULNERABLE', stdout.decode('UTF-8')):
        return str(ip)

    return None

def shodan_search(search_term):
    try:
        import shodan
    except:
        print('Please install shodan if you want to get hosts using the API.')
        sys.exit(1)

    api = shodan.Shodan(SHODAN_API_KEY)
    results = api.search(search_term)

    if results['total'] > 0:
        input("Shodan search returned {} hosts, press enter to start scan".format(results['total']))
        return [x['ip_str'] for x in results['matches']]

    return None

def main():
    if len(sys.argv) < 2:
        print('Usage with a subnet: scan_with_docker.py x.x.x.x/x')
        print('Usage with shodan: scan_with_docker.py \'hostname:"*.example.com" port:3389\'')
        sys.exit(1)

    try:
        hosts_to_scan = ipaddress.ip_network(sys.argv[1]).hosts()
    except:
        print("Not a valid subnet. Trying to use as Shodan search terms ...")
        hosts_to_scan = shodan_search(sys.argv[1])

    if hosts_to_scan is None:
        print('No available hosts to scan. Exiting.')
        sys.exit(1)

    port_scan_pool = ThreadPool(100)
    rdesktop_pool = ThreadPool(20)

    port_scan_result = port_scan_pool.map(port_scan, hosts_to_scan)
    try:
        port_scan_pool.join()
        port_scan_pool.close()
    except:
        pass

    # Filter the result to only include IP-addresses
    hosts_with_port_3389_open = [x for x in port_scan_result if x is not None]

    rdesktop_result = rdesktop_pool.map(run_rdesktop_in_docker, hosts_with_port_3389_open)
    try:
        rdesktop_pool.join()
        rdesktop_pool.close()
    except:
        pass

    # Filter the result to only include vulnerable hosts
    hosts_with_vuln = [x for x in rdesktop_result if x is not None]

    if len(hosts_with_vuln) > 0:
        print('Vulnerable hosts:')
        for host in hosts_with_vuln:
            print(host)
    else:
        print('No vulnerable hosts found')

if __name__ == '__main__':
    main()
