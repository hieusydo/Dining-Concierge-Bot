"""
    Hieu Do
    Handle Lex DiningConciergeBot
    Based on hotel booking bot template

"""

import json
import datetime
import time
import os
import dateutil.parser
import logging

from botocore.vendored import requests

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

'''
    Helper functions
'''
def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }

def close(session_attributes, fulfillment_state, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }

def build_validation_result(isvalid, violated_slot, message_content):
    return {
        'isValid': isvalid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }

# For safe slot extraction
def try_ex(func):
    try:
        return func()
    except KeyError:
        return None

# Validate input data
def validate_dining(slots):
    dining_date = try_ex(lambda: slots['diningDate'])
    dining_time = try_ex(lambda: slots['diningTime'])
    num_people = try_ex(lambda: slots['numPeople'])

    # Validate party size
    if num_people and not (0 < int(num_people) < 51):
        return build_validation_result(
            False,
            'numPeople',
            'Your party needs to be between 1 and 50 people. Can you try again?'
        )

    # Validate the date first
    if dining_date:
        intended_date = dateutil.parser.parse(dining_date)
        grace_period = datetime.datetime.today() - datetime.timedelta(days=1)
        if intended_date < grace_period:
            return build_validation_result(
                False,
                'diningDate',
                'You cannot go back in time!'
            )

    # Validate the time
    if dining_date and dining_time:
        intended_datetime = dateutil.parser.parse(dining_date + ' ' + dining_time)
        if intended_datetime < datetime.datetime.now():
            return build_validation_result(
                False,
                'diningTime',
                'You cannot go back in time!'
            )

    return {'isValid': True}

# Convert input datetime to Unix time for Yelp call
def convert_to_unixtime(thedate, thetime):
    if not thedate or not thetime:
        return 0

    dt = dateutil.parser.parse(thedate + ' ' + thetime)
    return int(time.mktime(dt.timetuple()))

# Call Yelp and parse result
def fetch_suggestions(num_result, cuisine, location, dining_date, dining_time):
    unix_datetime = convert_to_unixtime(dining_date, dining_time)
    payload = {
        'categories' : cuisine.lower(),
        'location'   : location.lower(),
        'open_at'    : unix_datetime,
        'limit'      : num_result
    }

    auth_key = ' '.join(['Bearer', os.environ['YELP_KEY']])
    headers = {"Authorization": auth_key}
    api_call = requests.get(os.environ['YELP_SEARCH_API'], params=payload, headers=headers)

    result = api_call.json()
    biz = try_ex(lambda: result['businesses'])
    result_str = []

    if not biz:
        return result_str

    for b in range(len(biz)):
        bb = biz[b]
        result_str.append(str(b+1) + '. ' + bb['name'] + ' (' + ' '.join(bb['location']['display_address']) + ')')
    return ' - '.join(result_str)


'''
    Fulfill intents
'''
def greet(intent_request):
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'Hi there, how can I help?'
        }
    )

def suggest_dining(intent_request):
    slots = intent_request['currentIntent']['slots']
    location = try_ex(lambda: slots['location'])
    cuisine = try_ex(lambda: slots['cuisine'])
    dining_date = try_ex(lambda: slots['diningDate'])
    dining_time = try_ex(lambda: slots['diningTime'])
    num_people = try_ex(lambda: slots['numPeople']) # not supported by Yelp API

    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    # Load confirmation history and track the current reservation.
    reservation = json.dumps({
        'location': location,
        'cuisine': cuisine,
        'diningDate': dining_date,
        'diningTime': dining_time,
        'numPeople': num_people
    })

    session_attributes['currentReservation'] = reservation

    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Validate any slots which have been specified.  If any are invalid, re-elicit for their value
        validation_result = validate_dining(intent_request['currentIntent']['slots'])
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )

        session_attributes['currentReservation'] = reservation
        return delegate(session_attributes, intent_request['currentIntent']['slots'])

    # Make call to Yelp API to get suggestions
    num_result = 3
    logger.debug('dining at={}'.format(reservation))
    result_str = fetch_suggestions(num_result, cuisine, location, dining_date, dining_time)

    del session_attributes['currentReservation']
    session_attributes['lastConfirmedReservation'] = reservation

    if not result_str:
        reply = "Sorry, I can't find the restaurants that fit your criteria. Please try again."
    else:
        reply = "Here are my suggestions for {cuisine} food in {location} on {diningDate} at {diningTime} for {numPeople} people: ".format(
                cuisine=cuisine.title(),
                location=location.title(),
                diningDate=dining_date,
                diningTime=dining_time,
                numPeople=num_people
            )
        reply += result_str

    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': reply
        }
    )

def thank(intent_request):
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'Sure thing, enjoy your meal!'
        }
    )

def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'Greet':
        return greet(intent_request)
    elif intent_name == 'SuggestDining':
        return suggest_dining(intent_request)
    elif intent_name == 'ThankYou':
        return thank(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')

# Entry point
def lambda_handler(event, context):
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    return dispatch(event)