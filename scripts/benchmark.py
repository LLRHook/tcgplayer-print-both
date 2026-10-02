#!/usr/bin/env python3
"""Warmed synthetic PDF parse/build benchmark; never submits a print job."""
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'native'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import tcgprint
from fixtures import make_pdf


def measure():
    results = []
    with tempfile.TemporaryDirectory() as folder:
        state = Path(folder)
        for pages, budget in [(3, 5), (30, 30)]:
            source = make_pdf(state / f'input-{pages}.pdf', pages=pages)
            durations = []
            for run in range(4):
                start = time.perf_counter()
                groups = tcgprint.parse(source)
                tcgprint.build(source, state / 'out/paired.pdf', groups, {'return_address': ['Example Store', '123 Example Street', 'Example City, VA 00000']})
                elapsed = time.perf_counter() - start
                if run: durations.append(elapsed)
            median = statistics.median(durations)
            if median > budget: raise RuntimeError(f'{pages}-page conversion exceeded {budget}s budget')
            results.append({'originalPages': pages, 'outputPages': pages + 1, 'runsAfterWarmup': len(durations), 'medianSeconds': round(median, 3), 'budgetSeconds': budget})
    print(json.dumps({'conversion': results, 'printerSubmitted': False}, indent=2))
    return results


if __name__ == '__main__': measure()
