from datetime import datetime, timedelta
import os
from dateutil.tz import gettz
import json
import boto3
import urllib.request

diff_hours = int(os.environ["DIFF_HOURS"])

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')

    now = datetime.utcnow()
    target_time = now + timedelta(hours=-diff_hours)

    ec2_instances = []
    ec2_data = ec2.describe_instances()
    for ec2_reservation in ec2_data['Reservations']:
        for ec2_instance in ec2_reservation['Instances']:
            if ec2_instance["State"]["Code"] != 80 and ec2_instance["LaunchTime"].astimezone() < target_time.astimezone():
                ec2_instances.append(ec2_instance)

    notify_targets = []
    for ec2_instance in ec2_instances:
        name = "-"
        ignore = False
        for tag in ec2_instance["Tags"]:
            if tag["Key"] == "Name":
                name = tag["Value"]
            if tag["Key"] == "ec2-checker":
                ignore = tag["Value"] == "0"

        if ignore:
            continue

        notify_targets.append([{
            "title": "インスタンス",
            "value": name,
            "short": True
        }, {
            "title": "起動時刻",
            "value": ec2_instance["LaunchTime"].astimezone(gettz('Asia/Tokyo')).strftime('%Y/%m/%d %H:%M:%S'),
            "short": True
        }])

    if len(notify_targets) > 0:
        body = {
            "text": f"起動時間が{diff_hours}時間を超えているEC2インスタンスがあります",
            "attachments": []
        }
        for notify_target in notify_targets:
            body["attachments"].append({
                "color": "danger",
                "fields": notify_target
            })

        req = urllib.request.Request(os.environ["SLACK_WEBHOOK_URL"],
                                    data=json.dumps(body).encode('utf-8'),
                                    method='POST')
        res = urllib.request.urlopen(req)

    return notify_targets
