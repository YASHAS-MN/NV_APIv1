import json
import urllib.request

RPC_URL = 'http://127.0.0.1:8545'

def rpc_call(method, params=[]):
    data = json.dumps({"jsonrpc":"2.0","method":method,"params":params,"id":1}).encode('utf-8')
    req = urllib.request.Request(RPC_URL, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as response:
        return json.load(response)['result']

chain_id = int(rpc_call('eth_chainId'), 16)
print(f"Chain ID: {chain_id}")

with open(r'C:\NebulaVerse\Smart_Contract_V1\deployments\anvil\deployment.json', 'r') as f:
    deployment = json.load(f)

for name, address in deployment['contracts'].items():
    code = rpc_call('eth_getCode', [address, 'latest'])
    if code == '0x':
        print(f"Contract {name} at {address} is MISSING code.")
    else:
        print(f"Contract {name} at {address} has code.")
