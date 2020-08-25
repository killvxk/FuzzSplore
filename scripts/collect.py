#!/usr/bin/python3

import subprocess
import argparse
import json
import sys
import os

import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

DESCR=''''''

script_dir = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))

opt = argparse.ArgumentParser(description=DESCR, formatter_class=argparse.RawTextHelpFormatter)
opt.add_argument("--conf", help="Configuration json", action='store', required=True)
opt.add_argument("--output", help="Output prefix", action='store', required=True)

args = opt.parse_args()

AFL_SHOWMAP = os.path.join(script_dir, "../AFLplusplus/afl-showmap")
OUT_FILE = "virgin_map.bin"

'''
[
  {
    "name": "ngram3",
    "corpus": "libpng/out/queue",
    "cmd": ["libpng/harness-ngram3", "@@"]
  }
]
'''
conf = json.load(open(args.conf))
print(conf)

# id:000213,src:000003,time:9769,op:havoc,rep:16,+cov
def parse_filename(name):
    name = name.split("/")[-1]
    src = None
    time = None
    id = int(name[3: name.find(",")])
    i = name.find("src:")
    if i >= 0:
        src = name[i+4: name.find(",", i)]
        src = list(map(int, src.split("+")))
    i = name.find("time:")
    if i >= 0:
        time = int(name[i+5: name.find(",", i)])
    return id, src, time

def iterate_files(path):
    for subdir, dirs, files in os.walk(path):
        for file in files:
            yield os.path.join(subdir, file)
        break

def run_showmap(f, cmd):
    cmd = cmd[:]
    os.system("rm %s" % OUT_FILE)
    for i in range(len(cmd)):
        if cmd[i] == "@@":
            cmd[i] = f
    showmap_args = [AFL_SHOWMAP, "-b", "-o", OUT_FILE, "--"] + cmd
    subprocess.check_call(showmap_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def merge_showmap(virgin_bits):
    new_bits = 0
    interesting = False
    f = open(OUT_FILE, "rb")
    bytes_data = f.read()
    i = 0
    for b in bytes_data:
        if b != 0:
            if virgin_bits[i] == 0:
                new_bits += 1
            if b > virgin_bits[i]:
                interesting = True
                virgin_bits[i] = b
        i += 1
    f.close()
    return bytes_data, new_bits, interesting


testcases = {}
graph = {}
timeline = {}
inputs_for_seconds = {}
coverage_over_time = {}

vects = open(args.output + '_vectors.csv', 'w')
vects.write('NAME,ID,X,Y\n')


for fuzzer in conf:
    queue_dir = fuzzer["corpus"]
    cmd = fuzzer["cmd"]
    name = fuzzer['name']

    bitmaps = []
    virgin_bits = [0] * (2 ** 16)
    cov_virgin_bits = [0] * (2 ** 16)

    i = 0
    idx_to_id = {}
    prev_cov = 0
    for f in sorted(iterate_files(queue_dir)):
        print(name, f)
        id, src, time = parse_filename(f)
        idx_to_id[i] = id
        i += 1
        sec = time // 1000
        run_showmap(f, cmd)
        bitmap, new_bits, interesting = merge_showmap(virgin_bits)
        if interesting:
            graph[name] = graph.get(name, {})
            graph[name][id] = graph[name].get(id, [])
            timeline[name] = timeline.get(name, {})
            timeline[name][sec] = timeline.get(sec, [])
            timeline[name][sec] += [id]
            inputs_for_seconds[sec] = inputs_for_seconds.get(sec, {})
            inputs_for_seconds[sec][name] = inputs_for_seconds[sec].get(name, 0)
            inputs_for_seconds[sec][name] += 1
            if src is not None:
                for sec in src:
                    graph[name] = graph.get(name, {})
                    graph[name][sec] = graph[name].get(sec, [])
                    graph[name][sec] += [id]
        cov_new_bits = new_bits
        if conf[0]['name'] != name:
            print(conf[0]['name'], f)
            run_showmap(f, conf[0]['cmd'])
            bitmap, cov_new_bits, _ = merge_showmap(cov_virgin_bits)
        if cov_new_bits:
            coverage_over_time[sec] = coverage_over_time.get(sec, {})
            coverage_over_time[sec][name] = coverage_over_time[sec].get(name, prev_cov)
            coverage_over_time[sec][name] += new_bits
            prev_cov += new_bits
        bitmaps.append(list(bitmap))
        testcases[name] = testcases.get(name, {})
        testcases[name][id] = testcases[name].get(id, {})
        testcases[name][id]['time'] = time
        testcases[name][id]['interesting'] = interesting
        testcases[name][id]['new_bits'] = new_bits
        testcases[name][id]['cross'] = testcases[name][id].get('cross', [])

    for fuzzer2 in conf:
        if name == fuzzer2['name']: continue
        
        queue_dir = fuzzer2["corpus"]
        virgin_bits = [0] * (2 ** 16)

        for f in sorted(iterate_files(queue_dir)):
            print(name, f)
            id, src, time = parse_filename(f)
            run_showmap(f, cmd)
            _, new_bits, interesting = merge_showmap(virgin_bits)
            if interesting:
                testcases[fuzzer2['name']] = testcases.get(fuzzer2['name'], {})
                testcases[fuzzer2['name']][id] = testcases[fuzzer2['name']].get(id, {})
                testcases[fuzzer2['name']][id]['cross'] = testcases[fuzzer2['name']][id].get('cross', [])
                testcases[fuzzer2['name']][id]['cross'].append(name)

    X = np.array(bitmaps)

    #pca = PCA(n_components=2)
    #pca.fit(X)

    print("TSNE...")
    X_embedded = TSNE(n_components=2).fit_transform(X)
    #np.savetxt(args.output + '_' + name + '_vectors.csv', X_embedded, delimiter=",", header='X,Y', comments='')

    for i in range(len(bitmaps)):
        vects.write('%s,%d,%f,%f\n' % (name, idx_to_id[i], X_embedded[i][0], X_embedded[i][1]))

print("Saving to %s_vectors.csv..." % args.output)
vects.close()

print("Saving to %s_coverage.csv..." % args.output)
covf = open(args.output + '_coverage.csv', 'w')
covf.write('NAME,TIME,VAL\n')
for sec in coverage_over_time:
    for name in coverage_over_time[sec]:
        covf.write('%s,%d,%d\n' % (name, sec, coverage_over_time[sec][name]))
covf.close()

print("Saving to %s_timeline.csv..." % args.output)
timef = open(args.output + '_timeline.csv', 'w')
timef.write('NAME,TIME,IDS\n')
for name in timeline:
    for sec in timeline[name]:
        timef.write('%s,%d,%d\n' % (name, sec, ':'.join(map(str, timeline[name][sec]))))
timef.close()


print("Saving to %s..." % args.output)
with open(args.output + '_data.json', 'w') as f:
    json.dump({
      'testcases': testcases,
      'inputs_for_seconds': inputs_for_seconds,
      'coverage_over_time': coverage_over_time,
      'timeline': timeline,
      'graph': graph,
    }, f)

print("Done.")
