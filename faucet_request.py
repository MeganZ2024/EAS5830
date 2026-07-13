#!/usr/bin/env python3
import os

# Do you need an account? (True or False)
create_account = False

# If you have an account you want to use make sure 'create_account' is False,
# complete the following fields and 'run tests' again to verify the information
name = 'Menghan Zhou'  # Your name
e_mail = 'mhzhou@engineering.upenn.edu'  # this should be your e-mail in ed-stem

# 1. 动态且安全地从同路径下的 secret_key.txt 读取私钥
with open("secret_key.txt", "r") as f:
    raw_key = f.read().strip()

# 2. 核心兼容逻辑：如果文件里包含 '0x'，切片删掉它，因为评测脚本自己会强行拼上 '0x'
if raw_key.startswith("0x"):
    secret_key = str(raw_key[2:])
else:
    secret_key = str(raw_key)

# 3. 动态通过私钥推导出钱包地址，确保 100% 绝对匹配，杜绝人工复制粘贴的错误
from eth_account import Account
account = Account.from_key(raw_key).address

# Networks you want funding from (True or False)
AVAX = True
BNB = True