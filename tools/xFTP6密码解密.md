### xFTP6密码解密

```python
from base64 import b64encode, b64decode
from Crypto.Hash import MD5, SHA256
from Crypto.Cipher import ARC4

UserSid = "RcoIlS-1-5-21-3990929841-153547143-3340509336-1001"
rawPass = "klSqckgTSU0TfhYxu6MB1ayrbnu3qnTOEYXUVlZe9R1zdney"
data = b64decode(rawPass)
Cipher = ARC4.new(SHA256.new((UserSid).encode()).digest())
ciphertext, checksum = data[:-SHA256.digest_size], data[-SHA256.digest_size:]
plaintext = Cipher.decrypt(ciphertext)
print plaintext.decode()
```

上面就是解密代码,需要自行安装需要的库，使用python2运行或者修改print()在python3环境下使用.