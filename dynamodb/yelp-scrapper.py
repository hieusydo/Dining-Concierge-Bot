'''
    Hieu Do (hsd258)
    Scrap 5000+ random restaurants in Manhattan
    Get restaurants by your self-defined cuisine types
    Each cuisine type should have 1,000 restaurants or so.
'''

import config
import os
import requests
import time
import boto3
import datetime
import json
import decimal

CUISINE_TYPES = ["vietnamese", "indian", "italian", "mediterranean", "french", "japanese", "chinese", "korean", "ukrainian", "spanish", "southern", "russian", "hungarian", "german", "caribbean", "american", "armenian", "bangladeshi", "belgian", "british"]
LOCATION_DEFAULT = "manhattan"
LIMIT_DEFAULT = 50 # max set by Yelp

# Goal: 5000+ unique restaurants in Manhattan
def crawl_from_yelp():
    payload = {
        "location" : LOCATION_DEFAULT,
        "limit" : LIMIT_DEFAULT
    }
    auth_key = ' '.join(["Bearer", config.YELP_KEY])
    headers = {"Authorization": auth_key}

    biz_ids = {}
    total_biz = 0
    for c in CUISINE_TYPES_MORE:
        payload["categories"] = c
        rest_cnt = 0
        offset = 0
        all_biz = {}
        all_biz["businesses"] = []
        # need 1000 unique res per cuisine
        while True:
            # Yelp requirement: limit + offset <= 1000
            if rest_cnt == 1000 or (LIMIT_DEFAULT + offset) > 1000:
                total_biz += rest_cnt
                break

            payload["offset"] = offset
            # Fetch result from Yelp
            api_res = requests.get(config.YELP_SEARCH_API, params=payload, headers=headers)

            # Check result for duplicates
            data = api_res.json()
            for biz in data["businesses"]:
                if biz["id"] not in biz_ids:
                    biz_ids[biz["id"]] = 1
                    rest_cnt += 1
                    all_biz["businesses"].append(biz)
            print("%d restaurants so far at offset %d" % (rest_cnt, offset))
            offset += 50

        fn = "json_data/restaurants_{0}.json".format(c)
        with open(fn, "w+") as f:
            f.write(json.dumps(all_biz))
        print("%d items written to %s. Total: %d" % (len(all_biz["businesses"]), fn, total_biz))

# Credit: https://stackoverflow.com/a/27974027/3975668
def _clean_empty(d):
    if not isinstance(d, (dict, list)):
        return d
    if isinstance(d, list):
        return [v for v in (_clean_empty(v) for v in d) if v]
    return {k: v for k, v in ((k, _clean_empty(v)) for k, v in d.items()) if v}

def insert_into_dynamo():
    # Assume credentials were already set up (ie, via AWS CLI: $ aws configure)
    # Do not need endpoint_url unless using local DB
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table("yelp-restaurants")

    for c in CUISINE_TYPES:
        # Re-read crawled data
        fn = "json_data/restaurants_{0}.json".format(c)
        with open(fn, "r") as f:
            rawjson = json.load(f, parse_float=decimal.Decimal)

        for biz in rawjson["businesses"]:
            current_timestamp = datetime.datetime.now().isoformat()
            biz["insertedAtTimestamp"] = current_timestamp

            # Filter out keys with empty vals to match put_item requirement
            biz_nonull = _clean_empty(biz)
            # print(biz_nonull)

            response = table.put_item(Item=biz_nonull)
            print("PutItem succeeded:")
            print(response)

def main():
    crawl_from_yelp()
    insert_into_dynamo()

    ## Sanity check for duplicates
    # dups = {}
    # dupscnt = 0
    # cnt = 0
    # for c in CUISINE_TYPES:
    #     # Re-read crawled data
    #     fn = "json_data/restaurants_{0}.json".format(c)
    #     with open(fn, "r") as f:
    #         rawjson = json.load(f)

    #     for biz in rawjson["businesses"]:
    #         if biz["id"] in dups:
    #             dupscnt += 1
    #         else:
    #             dups[biz["id"]] = 0
    #             cnt += 1
    # print(cnt)
    # print(dupscnt)


if __name__ == "__main__":
    main()