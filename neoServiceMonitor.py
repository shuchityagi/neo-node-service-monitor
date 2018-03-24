#! /usr/bin/env python
'''Script to monitor server's tcp sockets and node's jsonrpc calls
to check if the NEO node is properly syncing. The script will reboot
the node if there is a difference of 5000 blocks between the test
network and the node's highest block or if the node fails to send
for any other reason.

Python:
    - 3.6
Usage:
    - $python3 neoServiceMonitor.py
''' 

from os import system
import sys, config, requests, subprocess
from socket import socket
from time import asctime


def tcp_test(server_info):
    cpos = server_info.find(':')
    if cpos < 1 or cpos == len(server_info) - 1:
        print('You need to give server info as hostname:port.')
        usage()
        return True
    try:
        sock = socket()
        sock.connect((server_info[:cpos], int(server_info[cpos+1:])))
        sock.close
        return True
    except:
        return False


def jsonrpc_test():
    ''' This function makes a JSON-RPC call to the Neo node and checks the block height.
    @Args:
    --
    config.rpc['url'] : URL of NEO node, along with the port
    config.neoscan['url'] : Neoscan's API to get block height
    @returns:
    --
    Boolean
    '''
    try:
        payload = "{\n  \"jsonrpc\": \"2.0\",\n  \"method\": \"getblockcount\",\n  \"params\": [],\n  \"id\": 1\n}"
        headers = {'content-type': "application/json"}
        jsonrpc = requests.request("POST", config.rpc['url'], data=payload, headers=headers)
        jsonrpc.raise_for_status()
        jsonrpc_response = jsonrpc.json()
        
    except requests.exceptions.RequestException as err:
        print ("OOps: Something Else",err)
        return False
    except requests.exceptions.HTTPError as errh:
        print ("Http Error:",errh)
        return False
    except requests.exceptions.ConnectionError as errc:
        print ("Error Connecting:",errc)
        return False
    except requests.exceptions.Timeout as errt:
        print ("Timeout Error:",errt)     
        return False

    headers = {'cache-control': "no-cache"}
    neoscan = requests.request("GET", config.neoscan['url'], headers=headers)
    neoscan.raise_for_status()
    neoscan_response = neoscan.json()

    if neoscan_response['index'] - jsonrpc_response['result'] > 5000 :
        return False
    else :
        return True


def server_test():
    # is_tcp_ok = tcp_test(config.rpc['url'])
    is_tcp_ok = True
    is_jsonrpc_okay = jsonrpc_test()
    if not is_tcp_ok :
        send_error("TCP",config.rpc['url'],config.admin['email'])
    if not is_jsonrpc_okay :
        send_error("JSON RPC",config.rpc['url'],config.admin['email'])
        subprocess.call(['supervisorctl','reload']) #Reload the supervisor to restart the node
    else :
        print("Everything looks good..")    

def send_error(test_type, server_info, email_address):
    ''' Send an email to the admin if the tests do not pass.
    @Args:
    --
    test_type : Can be either TCP or JSONRPC
    server_info : The server's host and port
    email_address : Email address of the admin
    '''
    subject = '%s: %s %s error' % (asctime(), test_type.upper(), server_info)
    message = 'There was an error while executing a %s test against %s.' % (test_type.upper(), server_info)
    system('echo "%s" | mail -s "%s" %s' % (message, subject, email_address))

if __name__ == '__main__':
    print("Initiating...")
    server_test()