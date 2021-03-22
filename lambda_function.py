import boto3
import base64
import datetime
import time
import json

from botocore.exceptions import ClientError
from binance_f import SubscriptionClient
from binance_f.constant.test import *
from binance_f.model import *
from binance_f.exception.binanceapiexception import BinanceApiException
from binance_f.base.printobject import *


original_price = 0.0
last_price = 0.0
running = True

def get_secret():

    secret_name = "BinanceBot"
    region_name = "us-east-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            secret = base64.b64decode(get_secret_value_response['SecretBinary'])
        
        return json.loads(secret)

def callback(data_type: 'SubscribeMessageType', event: 'any'):

    global original_price
    global last_price
    global running

    if data_type == SubscribeMessageType.RESPONSE:
        print("Event ID: ", event)
    elif  data_type == SubscribeMessageType.PAYLOAD:
        
        if original_price == 0.0:
            original_price = event.markPrice
            last_price = original_price
            print("Sending buy order @"+ str(event.markPrice))
        else:
            print(str(event.markPrice))
            if event.markPrice >= last_price:
                last_price = event.markPrice
            elif event.markPrice < (last_price - (last_price/1000)) :
                print("Sending sell order @"+ str(event.markPrice))
                running = False
                
        # sub_client.unsubscribe_all()
    else:
        print("Unknown Data:")
    print()

def error(e: 'BinanceApiException'):
    print(e.error_code + e.error_message)

def lambda_handler(event, handler):
    binance_api_keys = get_secret()

    curr_date = datetime.date.today().strftime('%Y-%m-%d')
    curr_hour = datetime.datetime.now().strftime('%H')
    TRADE_HOUR = ""
    if curr_hour == "01" or curr_hour == "08" or curr_hour == "16":
        TRADE_HOUR = curr_date + " " + curr_hour + ":17:15"
    elif curr_hour == "23" or curr_hour == "07" or curr_hour == "15":
        curr_hour = str(int(curr_hour) + 1) 
        if len(curr_hour) == 1:
            curr_hour = "0" + curr_hour
        TRADE_HOUR = curr_date + " " + curr_hour + ":00:15"
    else:
        print("Error")

    # time.sleep((datetime.datetime.strptime(TRADE_HOUR, '%Y-%m-%d %H:%M:%S') - datetime.datetime.now()).seconds)

    sub_client = SubscriptionClient(api_key=binance_api_keys["key"], secret_key=binance_api_keys["secret"])

    sub_client.subscribe_mark_price_event("vetusdt", callback, error)

    while running:
        pass

    return "OK"
