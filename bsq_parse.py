#!/usr/bin/python

###########################################
#                                         #
#  Copyright Grazcoin 2017                #
#  https://github.com/grazcoin/bisq-tools #
#                                         #                                         
###########################################

import logging
from bsq_utils_general import *
from bsq_utils_parse import *
import sys
from pprint import pprint

# debug and last_block:
import bsq_globals

bsq_globals.init()

genesis_txids_list=['10085081b3c7eb3d15bc45eab9f8c4bd17a043f92928ea321f2705370bd44865','9249e46293eac9b43d43468035ca41d48bf92ff07871e07e7f9bb4aecdfc2d8c','6d39423c64952b9d62b945f2496055d292fe10d7531d7069e84e2e76a7b8b836']

#genesis_txids_list=['10085081b3c7eb3d15bc45eab9f8c4bd17a043f92928ea321f2705370bd44865','c3f5892c6e0c23818fc593f364acc2a0a0938463c8b203690b7db2a2ca9d63e2','a95c0953fc8c855ff3f950624d49bd37f44af11959b76d96fa751c669a5549ca']

#genesis_txids_list=['10085081b3c7eb3d15bc45eab9f8c4bd17a043f92928ea321f2705370bd44865','c3f5892c6e0c23818fc593f364acc2a0a0938463c8b203690b7db2a2ca9d63e2','a95c0953fc8c855ff3f950624d49bd37f44af11959b76d96fa751c669a5549ca','cc3807e818980efcc6989fe98b4c2273dee4bf43427e078509f131395ddcf1ce']
#genesis_txids_list=['10085081b3c7eb3d15bc45eab9f8c4bd17a043f92928ea321f2705370bd44865','9d897294bc60ccbdc79bee4feb5afc88e3845686252ea121a76b9c72e948b200']
#genesis_txids_list=['10085081b3c7eb3d15bc45eab9f8c4bd17a043f92928ea321f2705370bd44865']
#genesis_txids_list=['7200f9530a1a4fb7ceacd00de1c32bd2dd720ce51d82b78d5a164e0791055ab6']

#max_height=443660
#max_height=444444
#max_height=444000
#max_height=443500
#max_height=455555
max_height=get_height()

blocks_chunk_size=1000


# preparing initial bsqutxo from genesis (and compensation requests)
for genesis_txid in genesis_txids_list:
    update_outputs_for_tx(genesis_txid, True)


print "running ..."

chunk_num=1
# get the starting height (look for minimal height among all outputs)
parse_height=max_height
for k in bsq_globals.bsqutxo_dict.keys():
    if bsq_globals.bsqutxo_dict[k][u'height'] != 0:
        parse_height=min(parse_height,bsq_globals.bsqutxo_dict[k][u'height'])

print "Starting height is:",parse_height, "and chunk size is:", blocks_chunk_size


# run in height chunks generate:
# 1. updated bsqutxo set until each height chunk, based on existing bsqutxo set
# 2. validate bsqutxo set, and drop invalid bsqutxo
# repeat for next chunk until max_height

while parse_height <= max_height:

    # the closest next "round" chunk
    parse_height=parse_height+blocks_chunk_size-parse_height%blocks_chunk_size

    keys=bsq_globals.bsqutxo_dict.keys()
    keys.sort()

    print
    print "#######################"
    print "##### upto",parse_height,"#####"
    print "#######################"

    for k in keys:

        # run recursively from each genesis output
        current={}
        txid,index=k.split(':')
        if bsq_globals.bsqutxo_dict[k].has_key(u'height'):
            height=bsq_globals.bsqutxo_dict[k][u'height']
        else:
            height=0
        recursive_get_spent_tx({u'txid': txid, u'index': int(index), u'height':height}, parse_height)

    # validate (drop invalid bsqutxo)
    outputs_list=bsq_globals.bsqutxo_dict.keys()
    outputs_list.sort()
    print "--------------------------------------------------------------------------------"
    print "starting with output set:",outputs_list
    print "--------------------------------------------------------------------------------"
    for current_key in outputs_list:
        #print current_key
        # skip calculation/validation of bsq_amount input if already exists
        if bsq_globals.bsqutxo_dict[current_key].has_key(u'bsq_amount'):
            #print "already bsq_amount there:",bsq_globals.bsqutxo_dict[current_key][u'bsq_amount'],"from:",current_key
            bsq_input=bsq_globals.bsqutxo_dict[current_key][u'bsq_amount']
        else:
            txid,index=current_key.split(':')
            sj=get_tx_json(txid)
            outputs_len=len(sj[u'vout'])
            inputs_len=len(sj[u'vin'])
            print "#####"
            print txid, "inputs:", inputs_len, "outputs:", outputs_len
            # sum bsq from all inputs
            bsq_input=0
            for i in range(inputs_len):
                input_txid=sj[u'vin'][i][u'txid']
                input_index=sj[u'vin'][i][u'vout']
                input_key=unicode(input_txid+':'+str(input_index))
                print "Calculating inputs from:",input_key
                if bsq_globals.bsqutxo_dict.has_key(input_key):
                    try:
                        print "Added SQU to input:",bsq_globals.bsqutxo_dict[input_key][u'bsq_amount']
                        bsq_input+=bsq_globals.bsqutxo_dict[input_key][u'bsq_amount']
                    except KeyError:
                        print "No SQU field on input key:",input_key
                        pass
                else:
                    print "No SQU on:",input_key
                    pass

            print "total bsq_input for",txid,"is",bsq_input
            #print "-----"

            bsq_input_left=int(bsq_input)
            for o in range(outputs_len):
                #print o
                output_key=unicode(txid+':'+str(o))
                requested_bsq_output=int(sj[u'vout'][o][u'valueSat'])
                if requested_bsq_output <= bsq_input_left: # enough SQU to fund new output
                    try:
                        bsq_globals.bsqo_dict[output_key][u'bsq_amount']=requested_bsq_output
                        bsq_globals.bsqo_dict[output_key][u'validated']=True
                        bsq_globals.bsqutxo_dict[output_key][u'bsq_amount']=requested_bsq_output
                        bsq_globals.bsqutxo_dict[output_key][u'validated']=True
                        bsq_input_left-=requested_bsq_output
                        print "just used",requested_bsq_output,"granted to",output_key
                    except KeyError as e:
                        print "!!!!!!!!!!!!!!!!! KeyError",e
                    #print bsq_globals.bsqutxo_dict[output_key]
                else:
                    print "Out of SQU. Ignore request:",requested_bsq_output,"left:",bsq_input_left
                    #print bsq_globals.bsqutxo_dict[output_key]
                    try:
                        bsq_globals.bsqo_dict[output_key][u'bsq_amount']=0
                        bsq_globals.bsqo_dict[output_key][u'validated']=True
                        bsq_globals.bsqutxo_dict[output_key][u'bsq_amount']=0
                        bsq_globals.bsqutxo_dict[output_key][u'validated']=True
                    except KeyError as e:
                        print "!!!!!!!!!!!!!!111 KeyError",e
                    bsq_input_left=0 # first failure means the rest SQU are lost

    chunk_num+=1



atomic_json_dump(bsq_globals.bsqo_dict,'www/general/bsq_txos.json', add_brackets=False)

sys.exit(0)

bsq_globals.bsqo_dict=load_json_file('www/general/bsq_txos.json')

for k in bsq_globals.bsqo_dict.keys():
    if bsq_globals.bsqo_dict[k][u'bsq_amount']==0:
        bsq_globals.bsqo_dict.pop(k)
        bsq_globals.bsqutxo_dict.pop(k)
        print "drop:",k
        continue
    if not bsq_globals.bsqo_dict[k].has_key(u'scriptPubKey'):
        txid=k.split(':')[0]
        update_outputs_for_tx(txid)

    # that's for address on the sending side
    is_spent=(bsq_globals.bsqo_dict[k][u'spent_info']!=None)
    dest_addrs=bsq_globals.bsqo_dict[k][u'scriptPubKey']['addresses']
    for a in dest_addrs:
        if bsq_globals.addr_dict.has_key(a):
            if is_spent == False:
                bsq_globals.addr_dict[a][u'utxo'].update({k:bsq_globals.bsqo_dict[k]})
            else:
                bsq_globals.addr_dict[a][u'stxo'].update({k:bsq_globals.bsqo_dict[k]})
        else:
            bsq_globals.addr_dict[a]={u'utxo':{},u'stxo':{}} # for 
            if is_spent == False:
                bsq_globals.addr_dict[a][u'utxo']={k:bsq_globals.bsqo_dict[k]}
            else:
                bsq_globals.addr_dict[a][u'stxo']={k:bsq_globals.bsqo_dict[k]}

    atomic_json_dump(bsq_globals.bsqo_dict[k],'www/txo/'+k+'.json')

for k in bsq_globals.tx_dict.keys():
     print "################"

     bsq_received=0
     bsq_sent=0
     bsq_burnt=0

     txtxo={}
     tx_data=bsq_globals.tx_dict[k]
     vin_amount=len(tx_data[u'vin'])
     vin_keys_list=[]
     for i in range(vin_amount):
         txo_id=str(tx_data[u'vin'][i][u'txid'])+':'+str(tx_data[u'vin'][i][u'vout'])
         print i,k,txo_id
         # are there bsq on that txo?
         if bsq_globals.bsqo_dict.has_key(txo_id) and bsq_globals.bsqo_dict[txo_id].has_key(u'bsq_amount') and bsq_globals.bsqo_dict[txo_id][u'bsq_amount'] > 0:
             vin_keys_list.append(txo_id)
             # that's for addresses on the receiving side
#             src_addrs=bsq_globals.bsqo_dict[txo_id][u'scriptPubKey']['addresses']
#             for a in src_addrs:
#                 if bsq_globals.addr_dict.has_key(a):
#                     bsq_globals.addr_dict[a][u'vin'].update({txo_id:bsq_globals.bsqo_dict[txo_id]})
#                 else:
#                     bsq_globals.addr_dict[a]={u'vin':{},u'vout':{}} # for 
#                     bsq_globals.addr_dict[a][u'vin']={txo_id:bsq_globals.bsqo_dict[txo_id]}


#
     vin_keys_list.sort()

     vin_list=[]
     try:
         for vik in vin_keys_list:
             vin_list.append(bsq_globals.bsqo_dict[vik])
             bsq_received+=bsq_globals.bsqo_dict[vik][u'bsq_amount']
     except KeyError:
         print "KeyError:",vik

     vout_list=[]
     for i in range(len(tx_data[u'vout'])):
         vok=k+':'+str(i)
         try:
             if bsq_globals.bsqo_dict[vok].has_key(u'bsq_amount') and bsq_globals.bsqo_dict[vok][u'bsq_amount'] > 0:
                 vout_list.append(bsq_globals.bsqo_dict[vok])
                 bsq_sent+=bsq_globals.bsqo_dict[vok][u'bsq_amount']
         except KeyError:
             print "No bsq in:",vok
             pass

     bsq_burnt=bsq_received-bsq_sent

     bsq_globals.tx_dict[k][u'bsq_received']=bsq_received
     bsq_globals.tx_dict[k][u'bsq_sent']=bsq_sent
     bsq_globals.tx_dict[k][u'bsq_burnt']=bsq_burnt

     atomic_json_dump([vin_list,vout_list],"www/txtxos/txtxos-"+k+'.json', add_brackets=False)
     atomic_json_dump(bsq_globals.tx_dict[k],'www/tx/'+k+'.json')



sorted_tx_list=get_sorted_tx_list(reverse=True)
summary_list=[]

for t in sorted_tx_list:
    try:
        summary_list.append({u'txid':t[u'txid'], u'tx_time':str(t[u'time'])+'000', u'bsq_amount':t[u'bsq_sent'], u'to_address':t[u'vout'][0][u'scriptPubKey'][u'addresses'][0], u'icon':t[u'vout'][0][u'icon'], u'color':t[u'vout'][0][u'color'], u'icon_text':t[u'vout'][0][u'icon_text']})
    except KeyError:
        print "BOOOOOOOOOOOOOOOOOOO!"
        print t


for i in range(int(len(summary_list)/10)+1):
    strnum=str(i+1).zfill(4)
    atomic_json_dump(summary_list[i*10:i*10+9],'www/general/BSQ_'+strnum+'.json', add_brackets=False)

# generate addresses json
for a in bsq_globals.addr_dict.keys():
    utxo_list=[]
    stxo_list=[]
    balance=0
    received_num=0
    spent=0
    spent_num=0
    burnt=0
    burnt_num=0
    genesis=0
    genesis_tx=0
    for u in bsq_globals.addr_dict[a][u'utxo'].items():
        utxo=u[1]
        txid,output_index=u[0].split(':')
        utxo[u'txid']=txid
        utxo[u'output_index']=output_index
        utxo_list.append(utxo)
        balance+=utxo[u'bsq_amount']
        if utxo[u'icon']=='exodus':
            genesis+=utxo[u'bsq_amount']
            genesis_tx+=1
        received_num+=1
    for s in bsq_globals.addr_dict[a][u'stxo'].items():
        stxo=s[1]
        txid,output_index=s[0].split(':')
        stxo[u'txid']=txid
        stxo[u'output_index']=output_index
        stxo_list.append(stxo)
        spent+=stxo[u'bsq_amount']
        if stxo[u'icon']=='exodus':
            genesis+=stxo[u'bsq_amount']
            genesis_tx+=1
        spent_num+=1

    # get burnt from all spent transactions
    stxos=bsq_globals.addr_dict[a][u'stxo'].keys()
    txs=set()
    for s in stxos:
        txs.add(s.split(':')[0])
    for tx in txs:
        if bsq_globals.tx_dict[tx][u'bsq_burnt']>0:
            burnt+=bsq_globals.tx_dict[tx][u'bsq_burnt']
            burnt_num+=1

    addr_json={u'address':a}
    addr_json.update({u'utxos':utxo_list})
    addr_json.update({u'stxos':stxo_list})
    addr_json.update({u'reserved':0})

    addr_json.update({u'balance':balance})
    addr_json.update({u'total_exodus':genesis})
    addr_json.update({u'total_received':balance+spent})
    addr_json.update({u'total_spent':spent})
    addr_json.update({u'total_burnt':burnt})

    addr_json.update({u'total_reserved':0})
    addr_json.update({u'exodus_tx_num':genesis_tx})
    addr_json.update({u'received_outputs_num':received_num+spent_num})
    addr_json.update({u'spent_outputs_num':spent_num})
    addr_json.update({u'burnt_num':burnt_num})
 
    atomic_json_dump(addr_json,'www/addr/'+a+'.json', add_brackets=False)


for tx in bsq_globals.tx_dict.keys():
    if bsq_globals.tx_dict[tx][u'vout'][0][u'icon_text']=="Genesis":
        bsq_globals.stats_dict['Minted amount']+=bsq_globals.tx_dict[tx][u'bsq_sent']
    if bsq_globals.tx_dict[tx][u'bsq_burnt']>0:
        bsq_globals.stats_dict['Burnt amount']+=bsq_globals.tx_dict[tx][u'bsq_burnt']

bsq_globals.stats_dict['Existing amount']=bsq_globals.stats_dict['Minted amount']-bsq_globals.stats_dict['Burnt amount']

for txo in bsq_globals.bsqo_dict.keys():
    try:
        if bsq_globals.bsqo_dict[txo][u'spent_info']==None:
            bsq_globals.stats_dict['Unspent TXOs']+=1
        else:
            bsq_globals.stats_dict['Spent TXOs']+=1
    except KeyError:
        print "Missing spent_info field! ",txo

bsq_globals.stats_dict['Addresses']=len(bsq_globals.addr_dict.keys())
bsq_globals.stats_dict['Price']=0.00001234
bsq_globals.stats_dict['Marketcap']=bsq_globals.stats_dict['Price']*bsq_globals.stats_dict['Existing amount']


stats_json=[]
for k in ["Existing amount", "Minted amount", "Burnt amount", "Addresses", "Unspent TXOs", "Spent TXOs", "Price", "Marketcap"]:
    stats_json.append({"name":k, "value":bsq_globals.stats_dict[k]})

atomic_json_dump(stats_json,'www/general/stats.json', add_brackets=False)

#for k in bsq_globals.bsqutxo_dict.keys():
#    if bsq_globals.bsqutxo_dict[k][u'spent_info']==None:
#        print k


#print '#######################################'
#pprint(bsq_globals.bsqutxo_dict)
#print bsq_globals.bsqo_dict.keys()
