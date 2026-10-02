"""Nonprinting receipt refresh and explicit recovery; no printer submission."""
import re
import time
from pathlib import Path

ORDER = re.compile(r'^[A-Z0-9]{8}-[A-Z0-9]{6}-[A-Z0-9]{5}$')


def receipt(core, state, oid, token):
    if not ORDER.fullmatch(oid):
        raise ValueError('INVALID_ORDER_REQUEST')
    # Serialize the read/query/transition with explicit recovery and submission.
    # An old status response must never restore a guard that a human resolved.
    with core.locked(state), core.connection(state) as db:
        row = db.execute('select state,job from print_requests where request_id=? and order_id=?', (token, oid)).fetchone()
        if not row:
            raise ValueError('UNKNOWN_PRINT_REQUEST')
        stored, job = row
        result = {'ok': True, 'state': stored, 'orderId': oid, 'requestId': token, 'job': job}
        if not job or stored in {'resolved', 'uncertain', 'submitting'}:
            return result
        try:
            status = core.job_status(job)
        except Exception:
            return {**result, 'ok': False, 'error': 'PRINTER_STATUS_UNAVAILABLE'}
        actual = status.get('job-state')
        if actual not in {3, 4, 5, 6, 7, 8, 9}:
            return {**result, 'ok': False, 'error': 'PRINTER_STATUS_UNAVAILABLE'}
        newstate = 'completed' if actual == 9 else 'printer_error' if actual in {7, 8} else 'submitted'
        core.mark_job_state(db, job, newstate)
        db.commit()
        return {**result, 'state': newstate, 'sheets': status.get('job-media-sheets-completed'),
                'printerState': actual}


def resolve(core, state, oid, acknowledge=False):
    """A human can release a failed/uncertain guard after inspecting the queue.

    Resolution never prints and never removes the old request or job history.
    A queued/processing job cannot be released while CUPS says it is active.
    """
    if not acknowledge or not ORDER.fullmatch(oid):
        raise ValueError('EXPLICIT_QUEUE_INSPECTION_ACKNOWLEDGEMENT_REQUIRED')
    with core.locked(state), core.connection(state) as db:
        row = db.execute('select state,job from orders where id=?', (oid,)).fetchone()
        if not row:
            raise ValueError('UNKNOWN_ORDER')
        oldstate, job = row
        pending = db.execute("select distinct job from print_requests where order_id=? and state in ('submitting','uncertain','submitted','printer_error') and job is not null", (oid,)).fetchall()
        jobs = {item[0] for item in pending}
        if job and oldstate not in {'completed', 'resolved'}: jobs.add(job)
        for previous in jobs:
            status = core.job_status(previous)
            if status.get('job-state') not in {7, 8, 9}:
                raise ValueError('PRINTER_JOB_STILL_ACTIVE')
            core.mark_job_state(db, previous, 'completed' if status['job-state'] == 9 else 'resolved')
        current = db.execute('select state from orders where id=?', (oid,)).fetchone()[0]
        if current == 'completed':
            db.commit()
            return {'ok': True, 'state': 'completed', 'orderId': oid, 'job': job}
        # Preserve the state transition as a receipt; do not erase an intent.
        db.execute("update orders set state='resolved' where id=?", (oid,))
        db.execute("update print_requests set state='resolved' where order_id=? and state in ('submitting','uncertain','submitted','printer_error')", (oid,))
        if job:
            db.execute("update print_history set state='resolved' where order_id=? and job=?", (oid, job))
        db.commit()
        return {'ok': True, 'state': 'resolved', 'orderId': oid, 'job': job}


def cleanup(core, state, retention_days):
    """Remove expired private PDFs only after their jobs are resolved/completed."""
    state = Path(state)
    cutoff = time.time() - retention_days * 86400
    with core.locked(state), core.connection(state) as db:
        if db.execute("select 1 from orders where state in ('submitting','uncertain','submitted','printer_error') limit 1").fetchone():
            return {'ok': True, 'deleted': 0, 'deferred': True}
        deleted = 0
        for name in ['browser-inputs', 'browser-paired', 'generated']:
            directory = state / name
            if not directory.is_dir() or directory.is_symlink():
                continue
            for path in directory.glob('*.pdf'):
                if path.is_symlink():
                    continue
                if path.stat().st_mtime < cutoff:
                    path.unlink()
                    deleted += 1
        return {'ok': True, 'deleted': deleted, 'deferred': False}
