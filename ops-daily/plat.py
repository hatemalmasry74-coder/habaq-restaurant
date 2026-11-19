# Firestore helpers (login with creds.json each run)
import json,os,urllib.request,urllib.parse
H=os.path.dirname(os.path.abspath(__file__));C=json.load(open(os.path.join(H,'creds.json')))
B=f"https://firestore.googleapis.com/v1/projects/{C['project']}/databases/(default)/documents"
def login():
    r=urllib.request.Request('https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key='+C['firebase_key'],data=json.dumps({'email':C['platform_email'],'password':C['platform_password'],'returnSecureToken':True}).encode(),headers={'Content-Type':'application/json'})
    d=json.load(urllib.request.urlopen(r));return d['idToken'],d['localId']
T,UID=login()
def val(v):
    k=list(v)[0];x=v[k]
    if k=='mapValue': return {a:val(b) for a,b in x.get('fields',{}).items()}
    if k=='arrayValue': return [val(i) for i in x.get('values',[])]
    if k=='integerValue': return int(x)
    if k=='doubleValue': return float(x)
    if k=='nullValue': return None
    return x
def enc(x):
    if x is None: return {'nullValue':None}
    if isinstance(x,bool): return {'booleanValue':x}
    if isinstance(x,int): return {'integerValue':str(x)}
    if isinstance(x,float): return {'doubleValue':x}
    if isinstance(x,str): return {'stringValue':x}
    if isinstance(x,list): return {'arrayValue':{'values':[enc(i) for i in x]}}
    if isinstance(x,dict): return {'mapValue':{'fields':{k:enc(v) for k,v in x.items()}}}
    raise Exception(type(x))
def req(url,data=None,method=None):
    r=urllib.request.Request(url,data=json.dumps(data).encode() if data is not None else None,method=method,headers={'Authorization':'Bearer '+T,'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(r,timeout=60))
def coll(name):
    out={};tok=None
    while True:
        d=req(f'{B}/{name}?pageSize=300'+(f'&pageToken={tok}' if tok else ''))
        for doc in d.get('documents',[]): out[doc['name'].split('/')[-1]]={a:val(b) for a,b in doc.get('fields',{}).items()}
        tok=d.get('nextPageToken')
        if not tok: return out
def fp(k): return k if k.replace('_','').isalnum() and k.isascii() and not k[0].isdigit() else '`'+k+'`'
def patch(path,fields):
    q='&'.join('updateMask.fieldPaths='+urllib.parse.quote(fp(k)) for k in fields)+'&currentDocument.exists=true'
    try: req(f'{B}/{path}?{q}',{'fields':{k:enc(v) for k,v in fields.items()}},'PATCH');return 'ok'
    except urllib.error.HTTPError as e: return f'ERR {e.code}'
def create(path,fields,created=None):
    body={'fields':{k:enc(v) for k,v in fields.items()}}
    if created: body['fields']['createdAt']={'timestampValue':created}
    try: req(f'{B}/{path}?currentDocument.exists=false',body,'PATCH');return 'ok'
    except urllib.error.HTTPError as e: return f'ERR {e.code}'
def getdoc(path):
    d=req(f'{B}/{path}');return {a:val(b) for a,b in d.get('fields',{}).items()}
