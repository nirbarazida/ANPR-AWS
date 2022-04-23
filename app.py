import json
import re
import boto3
from flask import Response, Flask, render_template, request, redirect
import yaml
import datetime
import math
import uuid

import io
from PIL import Image
from PIL.ExifTags import GPSTAGS

# TODO: how to use TICKET_NUM as global var?
# TODO: What if app fail? ticket id will restart and overwrite.
# global TICKET_NUM
# TICKET_NUM = 0
app = Flask(__name__)

with open('const.yaml') as f:
    # use safe_load instead load
    const = yaml.safe_load(f)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/entry', methods=['POST'])
def entry():
    if request.is_json:
        entry_json = request.get_json()
        dynamodb_dynamodb = boto3.client('dynamodb')
        ticket_num = uuid.uuid4().int
        dynamodb_dynamodb.put_item(TableName=const["TableName"],
                                   Item={const["LicensePlateKey"]: {'S': entry_json[const["LicensePlateKey"]]},
                                         const["ParkingLotKey"]: {'S': entry_json[const["ParkingLotKey"]]},
                                         const["TicketIdKey"]: {'S': ticket_num},
                                         const["EntryTimeKey"]: {
                                             'S': datetime.datetime.strptime(datetime.datetime.utcnow().isoformat(),
                                                                             '%Y-%m-%dT%H:%M:%S.%f')}
                                         }
                                   )
        # TICKET_NUM += 1
        return Response(mimetype='application/json',
                        response=json.dumps({const["TicketIdKey"]: ticket_num}),
                        status=200)


def calc_time_min(entry_time):
    now = datetime.datetime.strptime(datetime.datetime.utcnow().isoformat(), '%Y-%m-%dT%H:%M:%S.%f')
    delta = (now - entry_time)
    return math.ceil(delta.total_seconds() / 60)


def calc_cost(duration_min):
    return math.ceil(duration_min / 15) * 2.5


@app.route('/exit', methods=['POST'])
def exit_car():
    if request.is_json:
        exit_json = request.get_json()
        dynamodb_dynamodb = boto3.client('dynamodb')
        user = dynamodb_dynamodb.get_item(TableName=const["TableName"],
                                          Key={const["TicketIdKey"]: {'S': exit_json[const["TicketIdKey"]]
                                                                      }
                                               }
                                          )
        if user:
            return Response(mimetype='application/json',
                            response=json.dumps({"price": calc_cost(calc_time_min(user[const["EntryTimeKey"]]))}),
                            status=200)
        else:
            return Response(mimetype='application/json',
                            response="{'Error': 'No Ticket ID found'}",
                            status=404)


@app.route('/lpr', methods=['POST'])
def upload():
    image = request.files['image']
    rekognition_client = boto3.client('rekognition')

    buffer = image.read()

    rekognition_response = rekognition_client.detect_text(Image={'Bytes': buffer})

    for text in rekognition_response['TextDetections']:
        txt = text['DetectedText']
        s = ''.join(re.findall('\d', txt))
        if len(s) < 8 and len(s) > 9:
            continue  # not a license plate

        return entry(json.dumps({const["LicensePlateKey"]: s,
                                 const["ParkingLotKey"]: const["ParkingLot"]
                                 }
                                )
                     )

    return Response(mimetype='application/json',
                    response="{'Error': 'No license plate found'}",
                    status=404)
