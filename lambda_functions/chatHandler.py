'''
    Hieu Do
    Handle chatting operation, call Lex bot to handle NLP stuff
'''

import json
import boto3

def lambda_handler(event, context):
    # Call Lex and wait for a response to return back to the user
    client = boto3.client('lex-runtime')
    response = client.post_text(
        botName='DiningConciergeBot',
        botAlias='$LATEST',
        userId='LF0',
        sessionAttributes={},
        requestAttributes={},
        inputText=event['text']
    )

    return {
        'statusCode': 200,
        'body': response
    }