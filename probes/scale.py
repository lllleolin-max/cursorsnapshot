"""Full real HTTP input/export, server death/resume and native frozen SQL oracle."""
import argparse
import base64
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sysconfig
import time
from cursorsnapshot import Client, initialize

KEY=b'public-cursorsnapshot-scale-key-32bytes'


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    root=Path(args.output);root.mkdir();results=[]
    console=Path(sysconfig.get_path('scripts'))/('cursorsnapshot.exe' if os.name=='nt' else 'cursorsnapshot')
    for size in (100,1000):
        case=root/str(size);case.mkdir();source,store,sink=case/'source.sqlite',case/'manager.sqlite',case/'export.sqlite'
        initialize(source,'source');initialize(store,'manager');keyfile=case/'public-lab-key.txt';keyfile.write_bytes(b'cskey_'+base64.urlsafe_b64encode(KEY))
        def serve(port=0):
            process=subprocess.Popen([str(console),'serve','--source',str(source),'--store',str(store),'--key-file',str(keyfile),'--port',str(port)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            line=process.stdout.readline()
            if not line:raise RuntimeError(('server failed',process.communicate(timeout=5)))
            ready=json.loads(line);assert ready['ready'];return process,ready['port']
        process,port=serve();client=Client(f'http://127.0.0.1:{port}','lab')
        try:
            started=time.perf_counter();input_bytes=0;input_digest=hashlib.sha256()
            for number in range(1,size+1):
                record={'tenant':'lab','order_id':number,'priority':None if number%7==0 else number%3,
                        'title':['\u4e2d','e\u0301','\u00e9'][number%3]+str(number),'total_cents':number,'category':'open'}
                wire=json.dumps(record,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8');input_digest.update(wire+b'\n');input_bytes+=len(wire)
                client.post('/orders',record)
            source_http_seconds=time.perf_counter()-started
            # Independent raw SQLite comparison deliberately uses an equivalent
            # NULL-rank expression rather than product order_sql/after_sql.
            with closing(sqlite3.connect(source)) as connection:
                connection.row_factory=sqlite3.Row
                expected=[dict(row) for row in connection.execute('SELECT * FROM orders WHERE tenant COLLATE BINARY=? ORDER BY (priority IS NOT NULL),priority,order_id',('lab',))]
            expected_raw=b''.join(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()+b'\n' for row in expected)
            (case/'expected.jsonl').write_bytes(expected_raw)
            started=time.perf_counter()
            partial=subprocess.run([str(console),'export','--endpoint',f'http://127.0.0.1:{port}','--tenant','lab','--output',str(sink),'--page-size','73','--max-pages','1'],capture_output=True,timeout=30)
            (case/'partial.stdout').write_bytes(partial.stdout);(case/'partial.stderr').write_bytes(partial.stderr)
            assert partial.returncode==0 and not partial.stderr
            partial_status=json.loads(partial.stdout);assert partial_status['records']==73 and not partial_status['done']
            snapshot_prepare_first_page_seconds=time.perf_counter()-started
            prepared_manager_bytes=store.stat().st_size
            client.post('/orders',{'tenant':'lab','order_id':1,'priority':99999,'title':'PUBLIC LAB changed after freeze','total_cents':999999,'category':'open'})
            client.post('/orders',{'tenant':'lab','order_id':size+100000,'priority':None,'title':'PUBLIC LAB extra live row','total_cents':777,'category':'open'})
            process.kill();process.communicate(timeout=5)
            process,same_port=serve(port);assert same_port==port
            started=time.perf_counter()
            resumed=subprocess.run([str(console),'resume','--output',str(sink),'--page-size','73'],capture_output=True,timeout=60)
            resume_seconds=time.perf_counter()-started
            (case/'resume.stdout').write_bytes(resumed.stdout);(case/'resume.stderr').write_bytes(resumed.stderr)
            assert resumed.returncode==0 and not resumed.stderr
            final=json.loads(resumed.stdout);assert final['done'] and final['released'] and final['records']==size
            dumped=subprocess.run([str(console),'dump','--output',str(sink)],capture_output=True,timeout=30)
            assert dumped.returncode==0 and not dumped.stderr
            (case/'actual.jsonl').write_bytes(dumped.stdout)
            observed=[json.loads(line) for line in dumped.stdout.splitlines()]
            assert observed==expected and sum(row['total_cents'] for row in observed)==size*(size+1)//2
            assert dumped.stdout==expected_raw and final['content_sha256']==hashlib.sha256(expected_raw).hexdigest()
            with closing(sqlite3.connect(sink)) as connection:
                count,total=connection.execute('SELECT count(*),sum(total_cents) FROM records').fetchone()
            assert (count,total)==(size,size*(size+1)//2)
            results.append({'orders':size,'source_actual_http_requests':size,'post_freeze_http_mutations':2,'page_size':73,
                'export_pages':(size+72)//73,'actual_server_process_kill_restart':True,'source_input_bytes':input_bytes,'source_input_sha256':input_digest.hexdigest(),
                'source_http_seconds':source_http_seconds,'snapshot_prepare_and_first_page_seconds':snapshot_prepare_first_page_seconds,'resume_seconds':resume_seconds,
                'native_expected_count':size,'sink_native_count':count,'hand_expected_total_cents':size*(size+1)//2,'sink_native_total_cents':total,
                'full_typed_sequence_equal':True,'complete_output_bytes':len(dumped.stdout),'complete_output_sha256':hashlib.sha256(dumped.stdout).hexdigest(),
                'snapshot_prepared_database_bytes':prepared_manager_bytes,'snapshot_after_release_database_bytes':store.stat().st_size,
                'source_database_bytes':source.stat().st_size,'sink_database_bytes':sink.stat().st_size})
        finally:process.kill();process.communicate(timeout=5)
    result={'scope':'LAB actual HTTP order writes and ordinary-installed CLI export/resume/dump with real server kill; native SQLite whole-sequence/count/sum oracle; no RSS/power-loss/Internet certificate','cases':results}
    (root/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
