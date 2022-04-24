import json
import re
import boto3
from flask import Response, Flask, render_template, request, redirect
import yaml
import datetime
import math
import uuid

# TODO: how to use TICKET_NUM as global var?
# TODO: What if app fail? ticket id will restart and overwrite.
# global TICKET_NUM
# TICKET_NUM = 0
app = Flask(__name__)

with open('./const.yaml') as f:
    # use safe_load instead load
    const = yaml.safe_load(f)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/entry', methods=['POST', 'GET'])
def entry():
    user_license_plate = str(request.args.get(const["LicensePlateKey"]))
    user_parking_lot = str(request.args.get(const["ParkingLotKey"]))
    print(user_license_plate, user_parking_lot)

    dynamodb_dynamodb = boto3.client('dynamodb')
    ticket_num = uuid.uuid4().int
    dynamodb_dynamodb.put_item(TableName=const["TableName"],
                               Item={const["TicketIdKey"]: {'S': str(ticket_num)},
                                     const["ParkingLotKey"]: {'S': user_parking_lot},
                                     const["LicensePlateKey"]: {'S': user_license_plate},
                                     const["EntryTimeKey"]: {
                                         'S': str(datetime.datetime.strptime(datetime.datetime.utcnow().isoformat(),
                                                                             '%Y-%m-%dT%H:%M:%S.%f'))}
                                     }
                               )
    return Response(mimetype='application/json',
                    response=json.dumps({const["TicketIdKey"]: ticket_num}),
                    status=200)


def calc_parking_time_min(entry_time):
    now = datetime.datetime.strptime(datetime.datetime.utcnow().isoformat(), '%Y-%m-%dT%H:%M:%S.%f')
    delta = (now - entry_time)
    return math.ceil(delta.total_seconds() / 60)


def calc_cost(duration_min):
    return math.ceil(duration_min / 15) * 2.5


@app.route('/exit', methods=['POST', 'GET'])
def exit_car():
    user_ticket_id = str(request.args.get(const["TicketIdKey"]))
    dynamodb_dynamodb = boto3.client('dynamodb')
    user = dynamodb_dynamodb.get_item(TableName=const["TableName"],
                                      Key={const["TicketIdKey"]: {'S': user_ticket_id
                                                                  }
                                           }
                                      )
    try:
        user_entry_string = user["Item"][const["EntryTimeKey"]]["S"]
        entry_datetime = datetime.datetime.strptime(user_entry_string, '%Y-%m-%d %H:%M:%S.%f')
        user_park_time = calc_parking_time_min(entry_datetime)
        user_parking_cost = calc_cost(user_park_time)
        user_plate = user["Item"][const["LicensePlateKey"]]["S"]
        user_parking_lot_id = user["Item"][const["ParkingLotKey"]]["S"]

        return Response(mimetype='application/json',
                        response=json.dumps({"LicensePlate": user_plate,
                                             "TotalParkedTime": user_park_time,
                                             "ParkingLotID": user_parking_lot_id,
                                             "PriceDollar": user_parking_cost}),
                        status=200)
    except KeyError:
        return Response(mimetype='application/json',
                        response="{'Error': 'No Ticket ID found'}",
                        status=404)


@app.route('/home', methods=['POST'])
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

        # TODO: How to call to a different HTTP request?
        return entry(json.dumps({const["LicensePlateKey"]: s,
                                 const["ParkingLotKey"]: const["ParkingLot"]
                                 }
                                )
                     )

    return Response(mimetype='application/json',
                    response="{'Error': 'No license plate found'}",
                    status=404)
