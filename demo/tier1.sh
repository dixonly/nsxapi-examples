
. ./demo-magic.sh

clear 

DEMO_PROMPT="apidemo$"


pe "./nsxt.py -u admin -p 'CptWare12345!' 10.172.165.152 session create --filename session.txt"
pe "./nsxt.py --cookie session.txt 10.172.165.152 tier1  config  --name DemoT1 --tier0 DemoT0 --advertisements TIER1_STATIC_ROUTES TIER1_CONNECTED TIER1_NAT TIER1_LB_VIP TIER1_LB_SNAT"
pe "./nsxt.py --cookie session.txt 10.172.165.152 tier1  edgecluster --name DemoT1 --cluster ec1"

pe "./nsxt.py --cookie session.txt 10.172.165.152  segment config --name Demo-74.10.1.0 --tz TZ-OVERLAY --lr DemoT1 --gw 74.10.1.254/24"
pe "./nsxt.py --cookie session.txt 10.172.165.152  segment config --name Demo-74.10.2.0 --tz TZ-OVERLAY --lr DemoT1 --gw 74.10.2.254/24"

pe "ping -c 5 74.10.1.254"

pe "./nsxt.py --cookie session.txt 10.172.165.152 tier0 locale redist --types TIER0_SEGMENT TIER0_EXTERNAL_INTERFACE TIER0_CONNECTED TIER0_STATIC TIER1_STATIC TIER1_LB_VIP TIER1_LB_SNAT TIER1_CONNECTED  --name DemoT0"

pe "ping -c 5 74.10.1.254"

pe 'for i in {1..5}; do ./clone.py -s 10.172.165.149 -u sfadmin -p \'Vmware123!\' -d SF1 -c Cluster103 -m sc2_nfs1 -v demo -t ubuntu-template-tools --linked --snapshot base --vm_name Demo1VM${i} --vm_gw 74.10.1.254 --vm_cidr 74.10.1.${i}/24 --vm_dnsservers 10.172.106.1 --vm_dnssubfixes cptroot.com --vm_domain cptroot.com --network Demo-74.10.1.0 --poweron; done'
pe 'for i in {1..5}; do ./clone.py -s 10.172.165.149 -u sfadmin -p \'Vmware123!\' -d SF1 -c Cluster103 -m sc2_nfs1 -v demo -t ubuntu-template-tools --linked --snapshot base --vm_name Demo2VM${i} --vm_gw 74.10.2.254 --vm_cidr 74.10.2.${i}/24 --vm_dnsservers 10.172.106.1 --vm_dnssubfixes cptroot.com --vm_domain cptroot.com --network Demo-74.10.2.0 --poweron; done'

pe "fping -g 74.10.1.1 74.10.1.5"
pe "fping -g 74.10.2.1 74.10.2.5"

