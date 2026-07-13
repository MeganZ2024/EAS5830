#!/usr/bin/env python3
from hexbytes import HexBytes

# Do you need an account? (True or False)
create_account = False

# If you have an account you want to use make sure 'create_account' is False,
# complete the following fields and 'run tests' again to verify the information
name = 'Menghan Zhou'  # Your name
e_mail = 'mhzhou@engineering.upenn.edu'  # this should be your e-mail in ed-stem
account = '0xf298fcEcd61B0Ca864325d1A228a9c267A9b5aD9'  # The account you want the funds in

# 使用 HexBytes 包装你的私钥字符串，彻底解决以 0b 开头导致的类型误判问题
secret_key = HexBytes('0b230bc657981618781e18fdea1bcfd998416cae18bf957630e7c78330a8979f')

# Networks you want funding from (True or False)
AVAX = True
BNB = True