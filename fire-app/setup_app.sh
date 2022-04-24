# debug
# set -o xtrace

KEY_NAME="NAPR-AWS"
KEY_PEM="$KEY_NAME.pem"

echo "create key pair $KEY_PEM to connect to instances and save locally"
aws ec2 create-key-pair --key-name $KEY_NAME --query "KeyMaterial" --output text > $KEY_PEM

# secure the key pair
chmod 400 $KEY_PEM

SEC_GRP="NAPR-AWS-sg"

echo "setup firewall $SEC_GRP"
aws ec2 create-security-group   \
    --group-name $SEC_GRP       \
    --description "Access my instances"

# figure out my ip
MY_IP=$(curl ipinfo.io/ip)
echo "My IP: $MY_IP"


echo "setup rule allowing SSH access to $MY_IP only"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 22 --protocol tcp \
    --cidr $MY_IP/32

echo "setup rule allowing HTTP (port 5000) access to $MY_IP only"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 5000 --protocol tcp \
    --cidr $MY_IP/32

UBUNTU_20_04_AMI="ami-0d527b8c289b4af7f"

echo "Creating Ubuntu 20.04 instance..."
RUN_INSTANCES=$(aws ec2 run-instances   \
    --image-id $UBUNTU_20_04_AMI        \
    --instance-type t2.micro            \
    --key-name $KEY_NAME                \
    --security-groups $SEC_GRP)

INSTANCE_ID=$(echo $RUN_INSTANCES | jq -r '.Instances[0].InstanceId')

echo "Waiting for instance creation..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

PUBLIC_IP=$(aws ec2 describe-instances  --instance-ids $INSTANCE_ID |
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

echo "New instance $INSTANCE_ID @ $PUBLIC_IP"

echo "Create table"
aws dynamodb create-table \
    --table-name ParkingLot \
    --attribute-definitions AttributeName=ticketId,AttributeType=S \
    --key-schema AttributeName=ticketId,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1

echo "Deploy and run app"
ssh -tt -i $KEY_PEM -o "IdentitiesOnly=yes" -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$PUBLIC_IP <<EOF
    sudo apt-get update -y
    sudo apt-get upgrade -y
    echo "install pip"
    sudo -H pip3 install pip==8.1.1
    sudo pip3 install --upgrade pip
    echo "Clone repo"
    sudo git clone https://github.com/nirbarazida/ANPR-AWS.git
    cd ANPR-AWS
    echo "Install requirements"
    sudo pip install -r requirements.txt
    export FLASK_APP=app/app.py
    # run app
    echo "Run app"
    python3 -m flask run --host=0.0.0.0
EOF


echo "test that it all worked"
curl  --retry-connrefused --retry 10 --retry-delay 1  http://$PUBLIC_IP:5000