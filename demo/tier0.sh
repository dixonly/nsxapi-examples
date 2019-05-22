. ./demo-magic.sh

clear 

DEMO_PROMPT="apidemo$"

pe "./nsxt.py -u admin -p 'CptWare12345!' 10.172.165.152 session create --filename session.txt"
pe "./nsxt.py --cookie session.txt 10.172.165.152 tier0  locale edgecluster --name DemoT0 --cluster ec1"
pe "./nsxt.py --cookie session.txt 10.172.165.152 tier0   locale redist --name DemoT0 --types TIER0_STATIC TIER0_CONNECTED TIER0_EXTERNAL_INTERFACE TIER0_SEGMENT"
pe "./nsxt.py --cookie session.txt 10.172.165.152 tier0   locale  get --name DemoT0"
pe "./nsxt.py --cookie session.txt 10.172.165.152 tier0    interface config  --name DemoT0 --int uplink1 --cidr 71.218.34.51/24 --edge sfe9 --type EXTERNAL --segment  Edge2034"
pe "./nsxt.py --cookie session.txt 10.172.165.152 tier0    interface config  --name DemoT0 --int uplink2 --cidr 71.218.35.51/24 --edge sfe9 --type EXTERNAL --segment  Edge2035"
pe "./nsxt.py --cookie session.txt 10.172.165.152 tier0    interface config  --name DemoT0 --int uplink3 --cidr 71.218.34.52/24 --edge sfe10 --type EXTERNAL --segment  Edge2034"
pe "./nsxt.py --cookie session.txt 10.172.165.152 tier0    interface config  --name DemoT0 --int uplink4 --cidr 71.218.35.52/24 --edge sfe10 --type EXTERNAL --segment  Edge2035"
pe "./nsxt.py --cookie session.txt 10.172.165.152 tier0      bgp  config --name DemoT0 --local_as 65334 --enable_intersr --enable_ecmp"
pe "./nsxt.py --cookie session.txt 10.172.165.152 tier0      bgp   neighbor  config --name DemoT0 --peer N9K-d18-1 --remoteAs 4000 --address 71.218.34.252 --keepalive 2 --holdtime 8 --password 'Vmware123!'"
pe "./nsxt.py --cookie session.txt 10.172.165.152 tier0      bgp   neighbor  config --name DemoT0 --peer N9K-d18-2 --remoteAs 4000 --address 71.218.35.253 --keepalive 2 --holdtime 8 --password 'Vmware123!'"
pe "ping -c 3 71.218.34.51"
pe "ping -c 3 71.218.35.51"

