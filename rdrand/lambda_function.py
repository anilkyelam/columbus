import json
import rdrand

def lambda_handler(event, context):
    # TODO implement

    r = rdrand.RdRandom()
    key = r.getrandbytes(16)
    print(key)

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }