"""Same SQLite rows/mutations and real HTTP for live/frozen pagination controls.

Controls are disclosed mechanisms, not competitors. A held read transaction is
correct while its process survives; restart loses that connection's frozen view.
"""
import argparse
from contextlib import closing
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import sysconfig
import time
from cursorsnapshot import Client, initialize

KEY=b'public-cursorsnapshot-pilot-key-32bytes'
ORDER='priority ASC NULLS FIRST,order_id ASC'


def raw(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')


def seed(source):
    initialize(source,'source')
    with closing(sqlite3.connect(source)) as connection,connection:
        connection.execute('PRAGMA journal_mode=WAL')
        for number in range(1,21):
            connection.execute('INSERT INTO orders VALUES(?,?,?,?,?,?)',('lab',number,[None,2,2,-1,0,None][number%6],
                ['\u00e9','e\u0301','\u4e2d','', 'a','z'][number%6],number*100,'open'))


def full_truth(source):
    with closing(sqlite3.connect(source)) as connection:
        connection.row_factory=sqlite3.Row
        return [dict(row) for row in connection.execute('SELECT * FROM orders WHERE tenant=? ORDER BY '+ORDER,('lab',))]


def mutation(source, first_id):
    with closing(sqlite3.connect(source)) as connection,connection:
        connection.execute('DELETE FROM orders WHERE tenant=? AND order_id=?',('lab',2))
        connection.execute('UPDATE orders SET priority=99999,title=? WHERE tenant=? AND order_id=?',('PUBLIC LAB moved after first page','lab',first_id))
        connection.execute('INSERT INTO orders VALUES(?,?,?,?,?,?)',('lab',999,-100,'PUBLIC LAB newly inserted',777,'open'))


def serve_control(source, mode, port):
    held=None
    if mode=='read-transaction':
        held=sqlite3.connect(source,check_same_thread=False);held.row_factory=sqlite3.Row
        held.execute('BEGIN');held.execute('SELECT count(*) FROM orders').fetchone()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            with closing(sqlite3.connect(source)) as live:
                live.row_factory=sqlite3.Row;connection=held or live
                values=['lab'];predicate='tenant=?'
                if mode!='offset' and body.get('last') is not None:
                    priority,order_id=body['last']
                    predicate+=' AND (priority IS NOT NULL,coalesce(priority,0),order_id)>(?,?,?)'
                    values += [int(priority is not None),0 if priority is None else priority,order_id]
                statement='SELECT * FROM orders WHERE '+predicate+' ORDER BY '+ORDER+' LIMIT ?'
                values.append(body['size'])
                if mode=='offset':statement+=' OFFSET ?';values.append(body.get('offset',0))
                rows=[dict(row) for row in connection.execute(statement,values)]
            response=raw({'records':rows});self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(response)));self.end_headers();self.wfile.write(response)
    server=HTTPServer(('127.0.0.1',port),Handler)
    print(json.dumps({'ready':True,'port':server.server_port}),flush=True)
    try:server.serve_forever()
    finally:
        server.server_close()
        if held is not None:held.close()


def launch(source,store,keyfile,mode,port=0):
    if mode=='snapshot':
        console=Path(sysconfig.get_path('scripts'))/('cursorsnapshot.exe' if os.name=='nt' else 'cursorsnapshot')
        command=[console,'serve','--source',source,'--store',store,'--key-file',keyfile,'--port',str(port)]
    else:
        command=[sys.executable,'-I',Path(__file__).resolve(),'--server',source,'--mode',mode,'--port',str(port)]
    started=time.perf_counter();process=subprocess.Popen([str(x) for x in command],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    line=process.stdout.readline()
    if not line:raise RuntimeError(('server failed',process.communicate(timeout=5)))
    ready=json.loads(line);assert ready['ready']
    return process,ready['port'],time.perf_counter()-started


def run_case(root,mode,writes,restart):
    import base64
    case=root/(mode+('-writes' if writes else '-static')+('-restart' if restart else ''));case.mkdir()
    source,store,keyfile=case/'source.sqlite',case/'manager.sqlite',case/'public-lab-key.txt'
    started=time.perf_counter();seed(source);seed_seconds=time.perf_counter()-started
    expected=full_truth(source);(case/'expected.jsonl').write_bytes(b''.join(raw(row)+b'\n' for row in expected))
    if mode=='snapshot':initialize(store,'manager')
    keyfile.write_bytes(b'cskey_'+base64.urlsafe_b64encode(KEY))
    process,port,start_seconds=launch(source,store,keyfile,mode)
    requests=0;records=[];cursor=None;last=None;offset=0;restart_seconds=0
    try:
        client=Client(f'http://127.0.0.1:{port}','lab')
        started=time.perf_counter()
        if mode=='snapshot':
            snapshot=client.post('/snapshots',{});requests+=1;cursor=snapshot['cursor']
        preparation_seconds=time.perf_counter()-started
        prepared_disk=store.stat().st_size if store.exists() else 0
        started=time.perf_counter();first=True
        while True:
            body={'cursor':cursor,'size':4} if mode=='snapshot' else {'last':last,'offset':offset,'size':4}
            response=client.post('/pages',body);requests+=1;rows=response['records'];records.extend(rows)
            if mode=='snapshot':cursor=response['next']
            elif rows:last=[rows[-1]['priority'],rows[-1]['order_id']];offset+=len(rows)
            (case/'consumer-checkpoint.json').write_bytes(raw({'records':records,'cursor':cursor,'last':last,'offset':offset}))
            if first:
                if writes:mutation(source,rows[0]['order_id'])
                if restart:
                    process.kill();process.communicate(timeout=5)
                    process,same_port,restart_seconds=launch(source,store,keyfile,mode,port);assert same_port==port
                    saved=json.loads((case/'consumer-checkpoint.json').read_bytes());records=saved['records'];cursor=saved['cursor'];last=saved['last'];offset=saved['offset']
                first=False
            if (mode=='snapshot' and cursor is None) or (mode!='snapshot' and len(rows)<4):break
        workflow_seconds=time.perf_counter()-started
        if mode=='snapshot':client.post('/release',{'snapshot':snapshot['snapshot']});requests+=1
    finally:process.kill();process.communicate(timeout=5)
    output=b''.join(raw(row)+b'\n' for row in records);(case/'actual.jsonl').write_bytes(output)
    expected_ids=[r['order_id'] for r in expected];actual_ids=[r['order_id'] for r in records]
    expected_map={r['order_id']:r for r in expected}
    return {'mode':mode,'writes_after_first_page':writes,'actual_server_process_kill_restart':restart,'rows':len(records),
        'missing':sorted(set(expected_ids)-set(actual_ids)),'extra':sorted(set(actual_ids)-set(expected_ids)),
        'duplicate_count':len(actual_ids)-len(set(actual_ids)),'changed_occurrences':sum(r['order_id'] in expected_map and r!=expected_map[r['order_id']] for r in records),
        'complete_typed_sequence_equals_frozen_sql':records==expected,'actual_http_requests_including_snapshot_release':requests,
        'source_preparation_seconds':seed_seconds,'server_start_seconds':start_seconds,'snapshot_preparation_seconds':preparation_seconds,
        'workflow_seconds_including_mutation_restart':workflow_seconds,'server_restart_seconds':restart_seconds,
        'snapshot_database_bytes':prepared_disk,'source_database_bytes':source.stat().st_size,
        'complete_output_bytes':len(output),'complete_output_sha256':hashlib.sha256(output).hexdigest()}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output');parser.add_argument('--server');parser.add_argument('--mode');parser.add_argument('--port',type=int,default=0);args=parser.parse_args()
    if args.server:return serve_control(args.server,args.mode,args.port)
    root=Path(args.output);root.mkdir();results=[]
    for writes,restart in ((False,False),(True,False),(True,True)):
        for mode in ('offset','live-keyset','read-transaction','snapshot'):
            result=run_case(root,mode,writes,restart);results.append(result)
            expected_correct=(not writes) or mode=='snapshot' or (mode=='read-transaction' and not restart)
            assert result['complete_typed_sequence_equals_frozen_sql']==expected_correct
    result={'scope':'LAB SQLite/HTTP controls, same initial20orders, NULL/BINARY order, size4 and same write schedule; keyset is live-correct, not an erroneous frozen algorithm',
        'control_costs':'snapshot includes creation/release HTTP, source preparation and server start separately; direct checkpoint JSON for every mode is not the product atomic SQLite exporter, independently tested elsewhere',
        'cases':results}
    (root/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
