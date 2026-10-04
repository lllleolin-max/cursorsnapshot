"""Real HTTP order API and resumed export; all values are public laboratory data."""
from pathlib import Path
import tempfile
import threading
from cursorsnapshot import (Client, export_records, export_status, finish_export,
                            initialize, make_server, start_export, step_export)
from cursorsnapshot.model import canonical


def main():
    with tempfile.TemporaryDirectory(prefix='cursor-example-') as folder:
        root=Path(folder); source,store,output=root/'orders.sqlite',root/'snapshots.sqlite',root/'export.sqlite'
        initialize(source,'source');initialize(store,'manager')
        key=b'public-cursorsnapshot-example-key-32'
        server=make_server(source,store,key);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            client=Client(f'http://127.0.0.1:{server.server_port}','lab')
            for i in range(1,9):
                client.post('/orders',{'tenant':'lab','order_id':i,'priority':None if i%3==0 else i%2,'title':f'order-{i}','total_cents':i*100,'category':'open'})
            start_export(client,output);step_export(output,size=3)
            client.post('/orders',{'tenant':'lab','order_id':1,'priority':100,'title':'changed after freeze','total_cents':99999,'category':'open'})
            while not export_status(output)['done']:step_export(output,size=3)
            rows=list(export_records(output));assert len(rows)==8 and sum(r['total_cents'] for r in rows)==3600
            result=finish_export(output);result['frozen_amount_cents']=3600
            print(canonical(result).decode());return 0
        finally:server.shutdown();server.server_close();thread.join(3)


if __name__=='__main__':raise SystemExit(main())
