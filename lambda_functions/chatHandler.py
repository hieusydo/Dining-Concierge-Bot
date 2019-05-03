'''
    LF0
'''

import json
import boto3

def lambda_handler(event, context):
    print(event['text'])

    client = boto3.client('lex-runtime')
    response = client.post_text(
        botName='DiningConciergeBot',
        botAlias='$LATEST',
        userId='LF0',
        sessionAttributes={},
        requestAttributes={},
        inputText=event['text']
    )
    print(response['message'])
    return {
        'statusCode': 200,
        'body': response
    }