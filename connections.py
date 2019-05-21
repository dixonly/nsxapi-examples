#!/usr/bin/env python
import socket
import requests
from requests.structures import CaseInsensitiveDict
import base64
import json
import copy
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class NsxConnect(requests.Request):
    def __init__(self, server, port = 443,
                 user='admin', password=None, cookie=None, 
                 content='application/json', accept='application/json',
                 cert=None, verify=False, timeout=None):
        '''
        server - The NSX Manager IP or FQDN
        port - TCP port for server
        user - The NSX User name with role to perform required API requests
        password - Password for the user, not required when re-using session
                   or cert auth
        cookie - Session cookiefile
        
        
        '''


        self.port = port
        self.server = 'https://'+server + ':'+str(self.port)
        self.headers = {'Content-Type': content, 'Accept':accept}
        self.username = user
        self.password = password
        self.verify = verify
        self.timeout = timeout
        self.cert = cert
        self.timeout = timeout
        self.cookie=cookie
        self.verify = verify

        self.session = requests.Session()

        # Default auth is Basic Auth
        self.requestAttr = {
            'auth': (self.username, self.password),
            'headers': self.headers,
            'verify': self.verify
        }

        # if session cookie file present
        if self.cookie:
            with open(self.cookie) as f:
                headers = CaseInsensitiveDict(json.loads(f.read()))
                self.requestAttr.pop('auth')
                self.requestAttr['headers']['Cookie'] = headers['set-cookie'].split()[0].strip(';')
                self.requestAttr['headers']['X-xsrf-token'] = headers['x-xsrf-token']


        # if certificate given
        if self.cert:
            self.requestAttr.pop('auth')
            self.session.cert = self.cert
            self.session.headers.update(self.requestAttr['headers'])
            self.session.verify=verify
            
        # revert to using auth if header is still there.  VIDM auth if @ in username          
        if 'auth' in self.requestAttr:
            if '@' in self.username:
                self.requestAttr.pop('auth')
                self.requestAttr['headers']['Authorization'] = 'Remote %s' % base64.b64encode('%s:%s' %(self.username, self.password))

    def __checkReturnCode(self, result, codes):
        if codes:
            if result.status_code not in codes:
                raise ValueError("Return code '%d' not in list of expected codes: %s\n %s"
                      %(result.status_code,codes, result.text))

            
    def get(self, api, verbose=True, trial=False, codes=None):
        '''
        REST API get request
        api - REST API, this will be appended to self.server
        verbose - if True, will print info about API and results
        trial - if True, will not execute the specified called.
                combine with verbose=true to see what'll be submitted
                NSX
        '''

        url = self.server+api
        if verbose:
            print("API: GET %s" %url)
        if not trial:
            r = self.session.get(url, timeout=self.timeout,
                                 **self.requestAttr)
            self.__checkReturnCode(r, codes)
            if verbose:
                print("result code: %d" % r.status_code)
                #print(json.dumps(json.loads(r.text), indent=4))
        else:
            if verbose:
                print("API not called - in safe mode")
            return None
        return json.loads(r.text)

    def patch(self, api, data=None, verbose=True,trial=False, codes=None):
        '''
        REST API patch request.  Note that this does not
             check entity revision
        api - REST API, this will be appended to self.server
        data - dictionary (not json string) to be submiited
        verbose - if True, will print info about API and results
        trial - if True, will not execute the specified called.
                combine with verbose=true to see what'll be submitted
                NSX
        '''
        url=self.server+api
        if verbose:
            print("API: PATCH %s with data:" %url)
            print(json.dumps(data, indent=4))
        if not trial:
            r = self.session.patch(url,data=json.dumps(data),
                                   timeout=self.timeout,
                                   **self.requestAttr)
            if verbose:
                print('result code: %d' %r.status_code)
                if r.text:
                    print(r.text)
        else:
            if verbose:
                print("API not called - in safe mode")
            return None
        self.__checkReturnCode(r, codes)
        return  r

    def put(self, api, data=None,verbose=True,trial=False, codes=None):
        '''
        REST API put requests.  Note that any put request must submit data
            contain a revision version that matches current version in NSX
        api - REST API, this will be appended to self.server
        data - dictionary (not json string) to be submiited
        verbose - if True, will print info about API and results
        trial - if True, will not execute the specified called.
                combine with verbose=true to see what'll be submitted
                NSX
        '''
        url=self.server+api
        if verbose:
            print("API: PUT %s with data:" %url)
            print(json.dumps(data, indent=4))

        if not trial:
            r = self.session.put(url, data=json.dumps(data),
                                 timeout=self.timeout,
                                 **self.requestAttr)
            self.__checkReturnCode(r, codes)
            if verbose:
                print('result code: %d' %r.status_code)
                return json.loads(r.text)
        else:
            if verbose:
                print("API not called - in safe mode")
            return None

    def delete(self, api, verbose=True,trial=False,codes=None):
        url = self.server+api
        if verbose:
            print("API: DELETE %s" %url)
        if not trial:
            r = self.session.delete(url,timeout=self.timeout,
                                    **self.requestAttr)
            self.__checkReturnCode(r,codes)
            if verbose:
                print('result code: %d' %r.status_code)
        else:
            if verbose:
                print("API not alled - in safe mode")
            return None
            
            
    def post(self, api, data=None,verbose=True,trial=False, codes=None):
        '''
        REST API post requests
        api - REST API, this will be appended to self.server
        data - dictionary (not json string) to be submiited
        verbose - if True, will print info about API and results
        trial - if True, will not execute the specified called.
                combine with verbose=true to see what'll be submitted
                NSX
        '''
        url = self.server+api
        if verbose:
            print("API: POST %s with data" %url)
            print(json.dumps(data, indent=4)) 
        if not trial:
            r = self.session.post(url, data=json.dumps(data),
                                  timeout=self.timeout,
                                  **self.requestAttr)
            self.__checkReturnCode(r, codes)
            if verbose:
                print('result code: %d' %r.status_code)
            if r.text:
                return json.loads(r.text)
            else:
                return None
        else:
            if verbose:
                print("API not called - in safe mode")
            return None

    def createSessionCookie(self, filename):
        '''
        Retrieve a remote session cookie that can be used for API requests
          and store in @filename.
        if the username has format of user@fqdn, then it's considered
          to be a remote auth request to VIDM
        '''
        if '@' in self.username:
            api=self.server + '/api/v1/eula/acceptance'
            r = self.session.get(api, **self.requestAttr)
        else:
            self.headers['Content-Type']= 'application/x-www-form-urlencoded'
            self.headers['Accept'] = '*/*'
            data='j_username=%s&j_password=%s' %(self.username,
                                                 self.password)
            api=self.server+'/api/session/create'
            r = self.session.post(api, data=data, **self.requestAttr)
        
        if 'set-cookie' not in  (k.lower() for k in r.headers.keys()):
            print("set-cookie not found in header, failure to create session")
            return
            
        fp = open(filename, 'w')
        fp.write(json.dumps({k:v for k,v in r.headers.items()
                             if k.lower() in ['set-cookie',
                                              'x-xsrf-token', 'date']}))

if __name__ == '__main__':
    #nsx=NsxConnect('10.172.165.165', verify=False, user='sfadmin@ad.cptroot.com', password='Vmware123!')
    nsx=NsxConnect('10.172.165.165', verify=False, user='admin', password='CptWare12345!')
    nsx.createSessionCookie(filename="abc.txt")
    nsx=NsxConnect('10.172.165.165', verify=False, cookie='abc.txt')
    
    r,h = nsx.get(api='/api/v1/logical-routers')
    if r:
        print(r)

    data={}
    data['prefixes'] = [{'action': 'PERMIT', 'network': "ANY"}]
    data['display_name'] = 'test_prefix4'

    r = nsx.patch(api='/policy/api/v1/infra/tier-0s/t0_1/prefix-lists/test_prefix4', data=json.dumps(data),verbose=True,trial=False)


    if r:
        print(r)

