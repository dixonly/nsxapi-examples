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
                 user='admin', password=None, access_token=None, cookie=None, 
                 content='application/json', accept='application/json',
                 global_infra=False, global_gm=False, org='default',
                 site='default', enforcement='default', domain='default',
                 cert=None, verify=False, timeout=None, project=None, isNsx=True):
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
        self.access_token = access_token
        self.verify = verify
        self.timeout = timeout
        self.cert = cert
        self.timeout = timeout
        self.cookie=cookie
        self.verify = verify
        self.global_infra = global_infra
        self.global_gm = global_gm
        self.site=site
        self.enforcement=enforcement
        self.domain=domain
        self.org=org
        self.project=project
        

        self.session = requests.Session()
        
        if self.access_token:
              self.requestAttr = {
            'headers': {'Content-Type': content, 'Accept':accept, 'Authorization':'Bearer %s' %(self.access_token)},
            'verify': self.verify
        }
        # Default auth is Basic Auth
        else: 
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
            self.session.cert = self.cert.split(',')
            self.session.headers.update(self.requestAttr['headers'])
            self.session.verify=verify
            
        # revert to using auth if header is still there.  VIDM auth if @ in username          
        if 'auth' in self.requestAttr:
            if '@!!!' in self.username:
                self.requestAttr.pop('auth')
                creds = "%s:%s" %(self.username, self.password)
                creds = creds.encode()
                self.requestAttr['headers']['Authorization'] = 'Remote %s' % base64.b64encode(creds)
        if isNsx:
            self.version = self.getVersion()

    def getVersion(self):
        # for API compatibility purposes, only get major and minor
        v = self.get(api='/api/v1/node/version', verbose=False, codes=[200])
        versionStr = v['product_version'].split('.')
        version=int("%s%s" % (versionStr[0],versionStr[1]))
        return version

    def getGlobalInfra(self):
        return self.global_infra
    def getGlobalGm(self):
        return self.global_gm
    def setHeader(header, app):
        if header in self.headers:
            self.headers.pop(header)
            self.headers[header] = app

    def amILM(self):
        d = self.get(api='/policy/api/v1/infra/federation-config', verbose=False, codes=[200,404])
        if 'error_code' in d:
            return False
        return True
        
        
    def normalizeGmLmApi(self, api):
        newApi=api
        if self.global_infra or self.global_gm:
            if api.startswith('/policy/api/v1/infra'):
                if not self.global_gm:
                    newApi = api.replace('/policy/api/v1/infra',
                                         '/policy/api/v1/global-infra')
                else:
                    newApi = api.replace('/policy/api/v1/infra',
                                         '/global-manager/api/v1/global-infra')
            elif api.startswith('/policy/api/v1/global-infra') and self.global_gm:
                newApi = api.replace('/policy/api/v1/global-infra',
                                     '/global-manager/api/v1/global-infra')
            elif api.startswith('/policy/api/v1') and self.global_gm:
                newApi = api.replace('/policy/api/v1',
                                     '/global-manager/api/v1')
            elif api.startswith('/api/v1')  and self.global_gm:
                newApi = api.replace('/api/v1', '/global-manager/api/v1')

        if self.project:
            if 'search/query' in api:
                pass
            elif api.startswith('/policy/api/v1'):
                newApi = newApi.replace("/policy/api/v1",
                                        "/policy/api/v1/orgs/%s/projects/%s" %(self.org,
                                                                               self.project))
            elif api.startswith('/global-manager/api/v1'):
                newApi=newApi.replace("/global-manager/api/v1",
                                      "/global-manager/api/v1/orgs/%s/projects/%s" %(self.org,
                                                                                     self.project))
        return newApi
            
    def jsonPrint(self, data, header=None, indent=4, brief=False):
        '''
        Takes dictionary and print output to stdout
        '''
        if data and not isinstance(data,dict):
            print("Data not a valid dictionary")
            return
        if header and not brief:
            print(header)
        if data:
            if 'results' not in data.keys() or not brief:
                print(json.dumps(data,indent=indent))
            else:
                if header:
                    print("%30s %30s %-s" %("name","id","path"))
                    print("%30s %30s %-s" %("----------","----------", "----------"))
                for i in data['results']:
                    print("%30s %30s %-s" %(i['display_name'],
                                            i['id'],
                                            i['path'] if 'path' in i.keys() else "-"))
                    
    def __checkReturnCode(self, result, codes):
        '''
        Checks HTTP requests result.status_code against a list of accepted codes
        '''
        if codes:
            if result.status_code not in codes:
                raise ValueError("Return code '%d' not in list of expected codes: %s\n %s"
                      %(result.status_code,codes, result.text))

            
    def get(self, api, verbose=True, trial=False, codes=None, display=False):
        '''
        REST API get request
        api - REST API, this will be appended to self.server
        verbose - if True, will print info about API and results
        trial - if True, will not execute the specified called.
                combine with verbose=true to see what'll be submitted
                NSX
        codes - List of HTTP request status codes for success
        '''
        api=self.normalizeGmLmApi(api)
        url = self.server+api
        if verbose:
            print("API: GET %s" %api)
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
        if display:
            self.jsonPrint(json.loads(r.text))

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
        api=self.normalizeGmLmApi(api=api)
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
                    return json.loads(r.text)
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
        codes - List of HTTP request status codes for success
        '''
        api=self.normalizeGmLmApi(api)
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

    def delete(self, api, data=None, verbose=True,trial=False,codes=None):
        '''
        REST API delete requests
        api - REST API, this will be appended to self.server
        verbose - if True, will print info about API and result
        trial - if true, will not execute the request
        codes - List of HTTP request status codes for success
        '''
        api=self.normalizeGmLmApi(api)
        url = self.server+api
        if verbose:
            print("API: DELETE %s" %url)
        if not trial:
            r = self.session.delete(url,timeout=self.timeout,
                                    data=json.dumps(data), 
                                    **self.requestAttr)
            self.__checkReturnCode(r,codes)
            if verbose:
                print('result code: %d' %r.status_code)
                return r.text
        else:
            if verbose:
                print("API not alled - in safe mode")
            return None
            
            
    def post(self, api, data=None,verbose=True,trial=False, codes=None, display=False):
        '''
        REST API post requests
        api - REST API, this will be appended to self.server
        data - dictionary (not json string) to be submiited
        verbose - if True, will print info about API and results
        trial - if True, will not execute the specified called.
                combine with verbose=true to see what'll be submitted
                NSX
        codes - List of HTTP request status codes for success
        '''
        api=self.normalizeGmLmApi(api)
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
                if display:
                    self.jsonPrint(json.loads(r.text))
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
        if '@ddd' in self.username:
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



