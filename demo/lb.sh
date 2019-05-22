
. ./demo-magic.sh

clear 

DEMO_PROMPT="apidemo$"


pe "./nsxt.py -u admin -p 'CptWare12345!' 10.172.165.152 session create --filename session.txt"

pe "./nsxt.py --cookie session.txt 10.172.165.152 lb config --name DemoLB --size MEDIUM --tier1 DemoT1"
pe "./nsxt.py  --cookie session.txt 10.172.165.152  lb serverSslProfile config --name DemoServerSslProfile --cipher_group BALANCED --protocols TLS_V1_1 TLS_V1_2 --cache"
pe "./nsxt.py  --cookie session.txt 10.172.165.152  lb monitor  configHttp --name DemoHttpsMonitor --type https --fallCount 3 --riseCount 3 --interval 2 --timeout 10 --response_codes 200 201 204 --request_version HTTP_VERSION_1_1 --port 443"
pe "./nsxt.py  --cookie session.txt 10.172.165.152  lb monitor serverSslBinding --name DemoHttpsMonitor --sslProfile DemoServerSslProfile --serverCA cpt-linux cpt-linux2"
pe "./nsxt.py  --cookie session.txt 10.172.165.152  lb  clientSslProfile config --name DemoClientSslProfile --cipher_group BALANCED  --protocols TLS_V1_1 TLS_V1_2 --cache"
pe "./nsxt.py  --cookie session.txt 10.172.165.152  lb   persistence  configSourcePersistence --name DemoSourcePersistenceProfile --purge FULL --sync"
pe "./nsxt.py  --cookie session.txt 10.172.165.152  lb   persistence  configCookiePersistence --name DemoCookiePersistenceProfile --mode INSERT  --cookie_name DEMO"
pe "./nsxt.py  --cookie session.txt 10.172.165.152  lb pool config --name Demo1Pool --member_group Demo1VMs --algorithm ROUND_ROBIN --snat_translation LBSnatAutoMap --active_monitor DemoHttpsMonitor"
pe "./nsxt.py --cookie session.txt 10.172.165.152 lb appProfile config --name DemoHttpAppProfile --type HTTP  --idleTimeout 10"
pe "./nsxt.py  --cookie session.txt 10.172.165.152   lb  vip  config --name DemoVip --appProfile DemoHttpAppProfile --persistProfile DemoSourcePersistenceProfile --lb_service DemoLB --pool Demo1Pool --ip 74.12.1.1 --ports 443"
pe "ping -c 10 74.12.1.1"
pe "curl -s -v https://74.12.1.1 > /dev/null"
pe "./nsxt.py --cookie session.txt 10.172.165.152 lb   vip clientSslBinding --name DemoVip --cert lb1 --sslProfile DemoClientSslProfile"
pe "curl -s -v https://74.12.1.1 > /dev/null"


