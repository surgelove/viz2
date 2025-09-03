from flask import Flask, render_template, jsonify, request
from collections import defaultdict
from datetime import datetime
import json
import traceback

try:
    from aia_utiilities_test import Redis_Utilities
except Exception:
    # If the project module isn't importable for some reason, define a stub
    Redis_Utilities = None

import os

# Ensure Flask finds templates in the repository-level `templates/` directory
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)

# Default redis connection settings (match your main.py constants if desired)
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
PREFIX_INPUT = "prices"
CONFIG_DIR = os.path.join(BASE_DIR, 'config')


def load_configs():
    configs = {}
    if not os.path.isdir(CONFIG_DIR):
        return configs
    for fname in os.listdir(CONFIG_DIR):
        if not fname.lower().endswith('.json'):
            continue
        key = os.path.splitext(fname)[0]
        path = os.path.join(CONFIG_DIR, fname)
        try:
            with open(path, 'r') as f:
                configs[key] = json.load(f)
        except Exception:
            configs[key] = None
    return configs


# load at module import
CONFIGS = load_configs()


def parse_timestamp(ts):
    # Try to leave timestamps as strings; but normalize if datetime passed
    if ts is None:
        return None
    if isinstance(ts, str):
        return ts
    try:
        return ts.isoformat()
    except Exception:
        return str(ts)


def get_grouped_data(prefix=None):
    """Read records from Redis (via Redis_Utilities) and group by instrument.

    Returns a dict: { instrument: { 'records': [..], 'chart': { 'timestamps': [...], 'prices': [...] } } }
    """
    if prefix is None:
        prefix = PREFIX_INPUT

    grouped = defaultdict(list)
    try:
        if Redis_Utilities is None:
            return {}
        r = Redis_Utilities(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        # read_all expects a prefix like 'prices:*' or 'prices'
        # pass prefix without trailing :* because read_all does scan_iter(f"{prefix}:*")
        items = r.read_all(prefix)
    except Exception:
        # Don't propagate Redis errors to the web UI; return empty data and log
        traceback.print_exc()
        return {}

    for item in items:
        # item is expected to be a dict with at least 'instrument' and 'timestamp' and 'price'
        inst = item.get('instrument') or 'unknown'
        grouped[inst].append(item)

    out = {}
    for inst, records in grouped.items():
        # sort by timestamp if possible
        try:
            records.sort(key=lambda x: x.get('timestamp'))
        except Exception:
            pass
        timestamps = [parse_timestamp(r.get('timestamp')) for r in records]
        # collect all field names except timestamp
        field_names = set()
        for r in records:
            for k in r.keys():
                if k != 'timestamp':
                    field_names.add(k)

        # build series per field, coercing to float when possible; keep original values for table
        series = []
        for fname in sorted(field_names):
            values = []
            is_numeric = True
            for r in records:
                v = r.get(fname)
                # try to coerce to float for plotting
                try:
                    if v is None:
                        values.append(None)
                    else:
                        fv = float(v)
                        values.append(fv)
                except Exception:
                    # non-numeric value; mark and store None for chart
                    is_numeric = False
                    values.append(None)
            series.append({
                'field': fname,
                'values': values,
                'is_numeric': is_numeric,
            })

        out[inst] = {
            'records': records,
            'chart': {
                'timestamps': timestamps,
                'series': series,
            }
        }
    return out


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data')
def api_data():
    prefix = request.args.get('prefix')
    data = get_grouped_data(prefix)
    return jsonify({
        'instruments': data,
        'configs': CONFIGS
    })


if __name__ == '__main__':
    app.run(debug=True)
