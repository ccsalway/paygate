"""
Visa/MasterCard payment example including the handling of 3D Secure
"""
import time
import urllib
import urlparse
import requests
from libs.crypt import *
from libs.cards import *
from config import *

# order params
params = urllib.urlencode({
    'MerchantID': MERCHANTID,
    'TransID': str(int(time.time())),
    'ReqID': str(int(time.time())),  # to avoid double submission
    'RefNr': 'FXC-DEMO',  # bank statement
    'OrderDesc': 'Test:0000',
    'Amount': 1000,
    'Currency': 'GBP',
    'Capture': 'MANUAL',  # MANUAL or AUTO (default)
    # Card details
    'CreditCardHolder': 'John Smith',
    'CCNr': 4900000000000003,
    'CCCVC': 123,
    'CCExpiry': 202007,
    'CCBrand': 'VISA',
    # Address Verification
    'AddrStreet': 'High Street',
    'AddrCity': 'London',
    'AddrZip': 'N1 2AB',
    # Language
    'Language': 'en',
    # 3D Secure
    'TermURL': 'https://www.example.com/notify3ds',
    'URLNotify': 'https://requestb.in/puwsb2pu'
})

# encrypt params
params_blowfish = blowfish_encrypt(CRYPTKEY, params)

# submit params to /direct.aspx
resp = requests.post(BASE_URL + DIRECT_PATH, {
    'MerchantID': MERCHANTID,
    'Len': len(params),
    'Data': params_blowfish,
    'Language': 'en'  # german by default
})
if resp.status_code != 200: exit(resp.content)

# split the response in key val
keyvals = urlparse.parse_qs(resp.content)

# check if 3dsecure
if 'acsurl' in keyvals:
    # redirect client to acsurl
    resp = requests.post(keyvals['acsurl'][0], {
        'MD': None,  # have to include for backwards compatability
        'PaReq': keyvals['pareq'][0],
        'TermUrl': keyvals['termurl'][0]
    })
    # pull out the PaRes value from the response
    pares = re.compile(ur'name="PaRes" value="(.*?)"').search(resp.content).groups(1)[0]
    # submit pares to /direct3d.aspx
    resp = requests.post(BASE_URL + DIRECT3D_PATH, {
        'PaRes': pares
    })
    print resp.status_code, resp.content  # 200 is returned but no content

# if not 3dsecure
else:
    length = int(keyvals['Len'][0])
    encrypted = keyvals['Data'][0]
    decrypted = blowfish_decrypt(CRYPTKEY, encrypted)[:length]
    keyvals = urlparse.parse_qs(decrypted)
    print keyvals

    # assign to variables
    pay_id = keyvals['PayID']               # ID assigned by FXC for the payment
    trans_id = keyvals['TransID']           # Merchant transaction ID
    status = keyvals['Status']              # Authorized/Ok or Failed
    description = keyvals['Description']    # Reason for Failure
