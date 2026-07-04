import binascii
import hashlib
import rc4
import struct

class non_fips():

    def __init__(self, server_ran, client_ran):

        # PreMasterSecret = First192Bits(ClientRandom) + First192Bits(ServerRandom)
        self.server_ran = server_ran
        self.client_ran = client_ran

        # PreMasterSecret
        self.pms = self.client_ran[:24] + self.server_ran[:24]
        # MasterSecret
        self.ms = self.__get_master_secret()
        # SessionKeyBlob
        self.sess_key_blob = self.__get_sess_key_blob() 

        # MACKey128 = First128Bits(SessionKeyBlob)
        # InitialClientDecryptKey128 = FinalHash(Second128Bits(SessionKeyBlob))
        # InitialClientEncryptKey128 = FinalHash(Third128Bits(SessionKeyBlob))

    def get_dec_key(self):
        return rc4.RC4Key(self.__get_final_hash(self.sess_key_blob[16:32]))

    def get_enc_key(self):
        key = self.__get_final_hash(self.sess_key_blob[32:48])
        return rc4.RC4Key(key), key

    def get_mac_key(self):
        #print('mac key')
        #print(binascii.hexlify(self.sess_key_blob[:16]))
        return self.sess_key_blob[:16]

    # MasterSecret = PreMasterHash(0x41) + PreMasterHash(0x4242) + PreMasterHash(0x434343)
    def __get_master_secret(self):
        return self.__get_pm_hash(b'\x41') + self.__get_pm_hash(b'\x42'*2) + self.__get_pm_hash(b'\x43'*3)

    # SessionKeyBlob = MasterHash(0x58) + MasterHash(0x5959) + MasterHash(0x5A5A5A)
    def __get_sess_key_blob(self):
        return self.__get_m_hash(b'\x58') + self.__get_m_hash(b'\x59'*2) + self.__get_m_hash(b'\x5a'*3)

    # PreMasterHash(I) = SaltedHash(MasterSecret, I)
    def __get_m_hash(self, I):
        return self.__get_salted_hash(self.ms, I)

    # PreMasterHash(I) = SaltedHash(PremasterSecret, I)
    def __get_pm_hash(self, I):
        return self.__get_salted_hash(self.pms, I)

    # SaltedHash(S, I) = MD5(S + SHA(I + S + ClientRandom + ServerRandom))
    def __get_salted_hash(self, S, I):

        sha1Digest = hashlib.sha1()
        md5Digest = hashlib.md5()

        sha1Digest.update(I)
        sha1Digest.update(S)
        sha1Digest.update(self.client_ran)
        sha1Digest.update(self.server_ran)
        sha1Sig = sha1Digest.digest()
        
        md5Digest.update(S)
        md5Digest.update(sha1Sig) 

        return md5Digest.digest()

    # FinalHash(K) = MD5(K + ClientRandom + ServerRandom)
    def __get_final_hash(self, K):

        md5Digest = hashlib.md5()

        md5Digest.update(K)
        md5Digest.update(self.client_ran)
        md5Digest.update(self.server_ran)

        md5Sig = md5Digest.digest()

        #print('encrypt/decrypt key')
        #print(binascii.hexlify(md5Sig))

        return md5Sig

class rc4_crypter():

    def __init__(self, non_fips):

        # we are sploiting no need for decrypt as far as i've seen
        self.enc_key, self.initial_key = non_fips.get_enc_key()
        self.current_key = self.initial_key

        self.dec_key = non_fips.get_dec_key()
        self.mac_key = non_fips.get_mac_key()

        self.enc_count = 0

    def encrypt(self, data):
        enc = rc4.crypt(self.enc_key, data)
        self.increment()
        return enc

    def decrypt(self, data):
        return rc4.crypt(self.dec_key, data)

    # Pad1 = 0x36 repeated 40 times to give 320 bits
    # Pad2 = 0x5C repeated 48 times to give 384 bits
    #  
    # SHAComponent = SHA(MACKeyN + Pad1 + DataLength + Data)
    # MACSignature = First64Bits(MD5(MACKeyN + Pad2 + SHAComponent))

    def sign(self, data):

        sha1Digest = hashlib.sha1()
        md5Digest = hashlib.md5()

        len_data = len(data)
        len_data = struct.pack('<I', len_data)

        sha1Digest.update(self.mac_key)        
        sha1Digest.update(b'\x36'*40)        
        sha1Digest.update(len_data)
        sha1Digest.update(data)
   
        sha1Sig = sha1Digest.digest() 

        md5Digest.update(self.mac_key)
        md5Digest.update(b'\x5c'*48) 
        md5Digest.update(sha1Sig)

        md5Sig = md5Digest.digest()

        return md5Sig[:8]


    def increment(self):

        self.enc_count += 1

        if self.enc_count == 4096:
            self.update_enc_key()
            self.enc_count = 0


    def update_enc_key(self):

        sha1Digest = hashlib.sha1()
        md5Digest = hashlib.md5()

        sha1Digest.update(self.initial_key)
        sha1Digest.update(b"\x36" * 40)
        sha1Digest.update(self.current_key)

        sha1Sig = sha1Digest.digest()

        md5Digest.update(self.initial_key)
        md5Digest.update(b"\x5c" * 48)
        md5Digest.update(sha1Sig)

        tempKey128 = md5Digest.digest()

        # If the key strength is 128 bits, then the temporary key (TempKey128) is used to 
        # reinitialize the associated RC4 substitution table. (For more information on RC4 
        # substitution table initialization, see [[SCHNEIER]] section 17.1.)

        # S-TableEncrypt = InitRC4(TempKey128)
        # RC4 is then used to encrypt TempKey128 to obtain the new 128-bit encryption key.

        S_TableEncrypt = rc4.RC4Key(tempKey128)

        # NewEncryptKey128 = RC4(TempKey128, S-TableEncrypt)

        self.current_key = rc4.crypt(S_TableEncrypt, tempKey128)

        # Finally, the associated RC4 substitution table is reinitialized with the new 
        # encryption key (NewEncryptKey128), which can then be used to encrypt a further 4,096 packets.

        # S-Table = InitRC4(NewEncryptKey128)

        self.enc_key = rc4.RC4Key(self.current_key)



