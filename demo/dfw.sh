
. ./demo-magic.sh

clear 

DEMO_PROMPT="apidemo$"


pe "./nsxt.py -u admin -p 'CptWare12345!' 10.172.165.152 session create --filename session.txt"
# find VM and show that no tags are there
pe "./nsxt.py  --cookie session.txt 10.172.165.152 vm   find  --name Demo1VM1"
# tag the first set of VMs
pe 'for i in {1..5}; do ./nsxt.py  --cookie session.txt 10.172.165.152 vm   tag --vmname Demo1VM${i} --tags demo:firstset demo:demo1; done'
# find again to show tag
pe "./nsxt.py  --cookie session.txt 10.172.165.152 vm   find  --name Demo1VM1"
# tag demo2
pe 'for i in {1..5}; do ./nsxt.py  --cookie session.txt 10.172.165.152 vm   tag --vmname Demo2VM${i} --tags demo:secondset demo:demo2; done'

# Create group with all demo VMs
pe './nsxt.py  --cookie session.txt 10.172.165.152 group config --name DemoVMs --expression ":VirtualMachine:Tag:EQUALS:demo|demo1" ":VirtualMachine:Tag:EQUALS:demo|demo2"'
# Create Group with demo1
pe './nsxt.py  --cookie session.txt 10.172.165.152 group config --name Demo1VMs --expression ":VirtualMachine:Tag:EQUALS:demo|demo1"'
# Create Group with demo2 using name
pe './nsxt.py  --cookie session.txt 10.172.165.152 group config --name Demo2VMs --expression ":VirtualMachine:Name:STARTSWITH:Demo2VM"'

pe "./nsxt.py  --cookie session.txt 10.172.165.152  policy config  --name Demo --sequence 1"
pe "./nsxt.py  --cookie session.txt 10.172.165.152  policy config  --name Demo1 --sequence 2"
pe "./nsxt.py  --cookie session.txt 10.172.165.152  policy config  --name Demo2 --sequence 3"

# Position Demo1 and Demo2 above demo
pe "./nsxt.py --cookie session.txt 10.172.165.152 policy position --name Demo1 --operation insert_before --anchor Demo"
pe "./nsxt.py --cookie session.txt 10.172.165.152 policy position --name Demo2 --operation insert_before --anchor Demo"
# config deny all rule to all Demo VMs
pe "./nsxt.py  --cookie session.txt 10.172.165.152  rule --policyname Demo config --name denyToDemo --src ANY --dst DemoVMs --action REJECT --services ANY --log"
pe "./nsxt.py  --cookie session.txt 10.172.165.152  rule --policyname Demo config --name icmpToDemo --src ANY --dst DemoVMs --action ALLOW --services 'ICMP ALL'"
pe "./nsxt.py  --cookie session.txt 10.172.165.152  rule --policyname Demo config --name sshToDemo --src ANY --dst DemoVMs --action ALLOW --services 'SSH'"
pe "./nsxt.py  --cookie session.txt 10.172.165.152  rule --policyname Demo position --name denyToDemo --operation insert_bottom"
# 
pe "./nsxt.py  --cookie session.txt 10.172.165.152  rule --policyname Demo1 config --name https --src ANY --dst Demo1VMs --action ALLOW --services HTTPS"
