'''
    LF2
'''

import boto3
import json
import logging

from botocore.vendored import requests
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def poll_from_queue():
    cuisine = None
    phone_num = None

    location = None
    dining_date = None
    dining_time = None
    num_people = None

    sqs = boto3.client('sqs')
    queue_url = 'https://sqs.us-east-1.amazonaws.com/307836514159/diningSuggestion'
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=0,
        WaitTimeSeconds=0
    )

    message = None
    try:
        message = response['Messages'][0]
        receipt_handle = message['ReceiptHandle']
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        logger.debug('Received and deleted message: %s' % message)
    except KeyError:
        logger.debug("Empty queue")
        return (cuisine, phone_num, location, dining_date, dining_time, num_people)

    if message is None:
        logger.debug("Empty message")
        return (cuisine, phone_num, location, dining_date, dining_time, num_people)

    try:
        cuisine = message["MessageAttributes"]["Cuisine"]["StringValue"]
        phone_num = message["MessageAttributes"]["PhoneNum"]["StringValue"]

        location = message["MessageAttributes"]["Location"]["StringValue"]
        dining_date = message["MessageAttributes"]["DiningDate"]["StringValue"]
        dining_time = message["MessageAttributes"]["DiningTime"]["StringValue"]
        num_people = message["MessageAttributes"]["NumPeople"]["StringValue"]
    except KeyError:
        logger.debug("No Cuisine or PhoneNum key found in message")
        return (cuisine, phone_num, location, dining_date, dining_time, num_people)

    return (cuisine, phone_num, location, dining_date, dining_time, num_people)


def lambda_handler(event, context):
    # 1. Poll from queue to see if there is any suggestion
    cuisine, phone_num, location, dining_date, dining_time, num_people = poll_from_queue()
    if not cuisine or not phone_num:
        return

    # 2. If there is, make 2 queries to get restaurant suggestions
    size_limit = 3
    es_query = "https://search-nyu-cloud-public-cqsfv756f4dttcuafzhri3jtqq.us-east-1.es.amazonaws.com/restaurants/_search?q={cuisine}&size={limit}".format(
        cuisine=cuisine,
        limit=size_limit
        )
    r = requests.get(es_query)
    data = json.loads(r.content.decode('utf-8'))
    try:
        raw_result = data["hits"]["hits"]
    except KeyError:
        logger.debug("Error extracting hits from ES response")

    all_rest_ids = []
    for rest in raw_result:
        all_rest_ids.append(rest["_id"])

    response_sns_text = 'Here are my suggestions for {cuisine} food in {location} on {diningDate} at {diningTime} for {numPeople} people: '.format(
            cuisine=cuisine,
            location=location,
            diningDate=dining_date,
            diningTime=dining_time,
            numPeople=num_people
        )
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('yelp-restaurants')
    for i, rid in enumerate(all_rest_ids):
        result = table.scan(FilterExpression=Attr('id').eq(rid))
        # Keep scanning until the result is found
        while 'LastEvaluatedKey' in result and len(result['Items']) == 0:
            result = table.scan(
                FilterExpression=Attr('id').eq(rid),
                ExclusiveStartKey=result['LastEvaluatedKey']
                )

        rest_obj = None
        item = result['Items']
        try:
            rest_obj = item[0]
        except IndexError:
            logger.debug("No restaurant with id %s found" % rid)

        if rest_obj is not None:
            address = rest_obj["location"]["display_address"][0]
            name = rest_obj["name"]
            rest_str = '%d. %s (%s). ' % (i+1, name, address)
            response_sns_text += rest_str


    # 3. Format the suggestion and send a text to the user
    messagingClient = boto3.client('sns')
    response = messagingClient.publish(
        PhoneNumber=phone_num,
        Message=response_sns_text,
        MessageStructure='string',
    )

    logger.debug("Message '%s' sent to %s" % (response_sns_text, phone_num))

    return response_sns_text