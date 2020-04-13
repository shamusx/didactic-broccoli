#!/usr/bin/env python3

import requests
import urllib3
import json, subprocess
import re, docker
from dateutil.parser import parse
urllib3.disable_warnings()

#Pull from private daily build registry
def pull_priv_registry(docker_pull):
    run_docker = subprocess.Popen(docker_pull, shell=True, stdout=subprocess.PIPE)
    pull_result = {}
    for line in run_docker.stdout:
        translate_str = line.decode("utf-8").strip()
        split_str = translate_str.split(':', 1)
        pull_result[split_str[0]] = split_str[1]
    return(pull_result)

remote_registry = "192.168.10.20:443/app_test"  #Remote registry for local environment with new repo name
registry = "100.50.20.15:443"  #Registry that hosts daily builds
repo_name = "night-build/app_serv" #Repo name of remote registry

#obtain list of all versions of daily builds
r = requests.get('https://' + registry + '/v2/' + repo_name + '/tags/list', verify=False)

build_versions = r.json()
nt = ''
build_tag = ''

#Loop through versions obtained and check the created date stamp to determine the newest version
for tag in build_versions['tags']:
  r = requests.get('https://' + registry + '/v2/' + repo_name + '/manifests/' + tag, verify=False)
  manifest = r.json()
  ft = parse(json.loads(manifest['history'][0]['v1Compatibility'])['created'], ignoretz=True)
  if not nt:
      nt = ft
  if ft > nt:
      nt = ft
      print('Current ', nt,build_tag,' Check Against  ', ft,tag)
      build_tag = tag
print(build_tag)

#Pull command from private nightly build registry
docker_pull = 'docker pull --disable-content-trust ' + registry + '/' + repo_name + ':' + build_tag
pull_logs = pull_priv_registry(docker_pull)

#Check for "Status" key value returned from pull_priv_registry function 
#if status returns as New image was downloaded, tag the registry 
#with properties for new registry
if 'Status' in pull_logs:
    if re.match(r'(^.*Downloaded newer image)',pull_logs['Status']):
        print(pull_logs['Status'])
        client = docker.APIClient(base_url='unix://var/run/docker.sock')
        client.tag(registry + '/' + repo_name + ':' + build_tag, remote_registry)
        client.push(remote_registry)