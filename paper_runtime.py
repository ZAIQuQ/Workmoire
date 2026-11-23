"""Transient paper jobs and content-free duration samples for honest estimates."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import secrets
import statistics
import threading
import time
import os


class PaperFailure(ValueError):
    """A fixed public message and content-free diagnostic codes."""

    def __init__(self, code, message, checks=()):
        super().__init__(message)
        self.code = code
        self.checks = checks

    def fields(self):
        return {'error_code': self.code, 'failed_checks': list(self.checks)}


def log_paper_job(trace_id, event, stage, elapsed, failure=None):
    entry = {'trace_id': trace_id, 'event': event, 'stage': stage, 'elapsed_seconds': round(elapsed, 1)}
    if failure:
        entry.update(failure.fields())
    print('paper_analysis ' + json.dumps(entry, separators=(',', ':')), flush=True)


class PaperRuntime:
    def __init__(self,root:Path,profile:str,fallback=45):
        self.root=Path(root);self.path=self.root/'paper-timings.json';self.profile=profile;self.fallback=fallback
        self.lock=threading.RLock();self.jobs={};self.samples=[]
        try:
            data=json.loads(self.path.read_text())
            if isinstance(data,dict) and data.get('profile')==profile:
                self.samples=[row for row in data.get('samples',[]) if isinstance(row,dict) and isinstance(row.get('seconds'),(int,float)) and 0<row['seconds']<600 and isinstance(row.get('characters'),int)][-40:]
        except (OSError,ValueError,TypeError):pass
    def estimate(self,characters):
        with self.lock:
            bucket=lambda n:0 if n<12000 else 1 if n<35000 else 2
            near=[s['seconds'] for s in self.samples if bucket(s['characters'])==bucket(characters)]
            values=sorted(near or [s['seconds'] for s in self.samples])
            if not values:return {'seconds':self.fallback,'low':round(self.fallback*.55),'high':round(self.fallback*1.8),'samples':0}
            median=max(1,statistics.median(values));low=max(.5,min(values[int((len(values)-1)*.2)]*.8,median*.8));high=max(median*1.35,values[math.ceil((len(values)-1)*.9)]*1.2,low+1)
            if len(values)<4:low=min(low,median*.55);high=max(high,median*1.6)
            return {'seconds':round(median,1),'low':round(low,1),'high':round(high,1),'samples':len(values)}
    def record(self,characters,seconds):
        if not 0<seconds<600:return
        with self.lock:
            self.samples=(self.samples+[{'characters':characters,'seconds':round(seconds,3)}])[-40:]
            self.root.mkdir(parents=True,exist_ok=True)
            temporary=self.path.with_name('.paper-timings-'+secrets.token_hex(8))
            try:
                fd=os.open(temporary,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
                with os.fdopen(fd,'w') as stream:json.dump({'profile':self.profile,'samples':self.samples},stream)
                os.replace(temporary,self.path)
            finally:temporary.unlink(missing_ok=True)
    def _clean(self):
        now=time.monotonic()
        for key in list(self.jobs):
            if self.jobs[key]['status']!='running' and now-self.jobs[key]['finished']>900:self._expire(key)
        for key in list(self.jobs):
            if len(self.jobs)<8:break
            if self.jobs[key]['status']!='running':self._expire(key)
    def _expire(self,key):
        with self.lock:
            job=self.jobs.pop(key,None)
            if job and job.get('_timer'):job['_timer'].cancel()
    def start(self,owner,payload,work):
        digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        with self.lock:
            self._clean()
            for job in self.jobs.values():
                if job['status']=='running':
                    if job['owner']==owner and job['digest']==digest:return self._view(job)
                    raise ValueError('已有一项论文分析正在进行，请稍候')
            job={'id':secrets.token_hex(16),'owner':owner,'digest':digest,'status':'running','stage':'preparing','started':time.monotonic(),'finished':0,'characters':len(payload.get('text','')),'estimate':self.estimate(len(payload.get('text','')))}
            self.jobs[job['id']]=job
        def progress(stage, failure=None):
            with self.lock:
                job['stage'] = stage
            log_paper_job(job['id'], 'retry' if failure else 'stage', stage,
                          time.monotonic() - job['started'], failure)
        def run():
            try:
                log_paper_job(job['id'], 'started', 'preparing', 0)
                result=work(progress)
                finished=time.monotonic()
                try:self.record(job['characters'],finished-job['started'])
                except OSError:pass
                with self.lock:job.update(status='completed',stage='completed',result=result,finished=finished)
                log_paper_job(job['id'], 'completed', 'completed', finished - job['started'])
            except Exception as error:
                if isinstance(error, PaperFailure):
                    failure = error
                elif isinstance(error, ValueError) and job['stage'] == 'preparing':
                    failure = PaperFailure('invalid_material', '论文材料无法用于分析，请核对所选 PDF 和来源链接后重试。')
                else:
                    failure = PaperFailure('internal_error', '论文分析暂时失败，请重试。')
                finished = time.monotonic()
                with self.lock:
                    stage = job['stage']
                    job.update(status='failed', error=str(failure), finished=finished, **failure.fields())
                log_paper_job(job['id'], 'failed', stage, finished - job['started'], failure)
            finally:
                with self.lock:
                    if job['id'] in self.jobs:
                        timer=threading.Timer(900,self._expire,args=(job['id'],));timer.daemon=True;job['_timer']=timer;timer.start()
        threading.Thread(target=run,daemon=True,name='paper-summary').start()
        with self.lock:return self._view(job)
    def _view(self,job):
        elapsed=(job['finished'] or time.monotonic())-job['started'];estimate=job['estimate'];done=job['status']=='completed'
        result={'job_id':job['id'],'trace_id':job['id'],'status':job['status'],'stage':job['stage'],'elapsed_seconds':round(elapsed,1),'estimate':estimate,'progress_kind':'estimated','progress':100 if done else min(95,round(elapsed/max(1,estimate['seconds'])*90)), 'over_estimate':elapsed>estimate['high']}
        if done:result['result']=job['result']
        if job['status']=='failed':
            result.update(error=job['error'], error_code=job['error_code'], failed_checks=job['failed_checks'][:])
        return result
    def get(self,owner,job_id):
        with self.lock:
            self._clean();job=self.jobs.get(job_id)
            return self._view(job) if job and job['owner']==owner else None
