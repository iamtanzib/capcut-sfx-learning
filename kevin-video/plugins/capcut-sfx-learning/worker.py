"""Process-isolated batch preprocessing; stdout goes to local job logs."""
import sys,subprocess
from concurrent.futures import ThreadPoolExecutor
import service as api

def one(job):
    path=api.job_path(job)/'prepare.log'
    with path.open('ab') as log:
        result=subprocess.run([sys.executable,__file__,'job',job],stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=api.s.CREATE_NO_WINDOW)
    if result.returncode:
        data=api.job_data(job)
        if data['status'] not in ('failed','ready'):data.update(status='failed',error='Worker stopped; inspect prepare.log');api.s.write_json(api.job_path(job)/'job.json',data)
    return result.returncode

if __name__=='__main__':
    if sys.argv[1]=='job':api.prepare_job(sys.argv[2])
    else:
        batch=api.batch_data(sys.argv[2])
        with ThreadPoolExecutor(max_workers=batch['workers']) as pool:list(pool.map(one,batch['jobs']))
