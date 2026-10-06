"""python3 tools/validate_bus.py [hyogo] -- 県別の市町村網羅と制度の必須項目を検証。"""
import argparse
import json
from pathlib import Path
from bus_pages import validate_bus


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pref', nargs='?')
    args = ap.parse_args()
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    files = [data_dir / f'{args.pref}-bus.json'] if args.pref else sorted(data_dir.glob('*-bus.json'))
    for file in files:
        bus = json.loads(file.read_text(encoding='utf-8'))
        pref = json.loads(file.with_name(file.name.replace('-bus', '-menkyo-henno')).read_text(encoding='utf-8'))
        validate_bus(bus, pref)
        print(f'OK {file.name}: {len(bus["cities"])} municipalities')


if __name__ == '__main__':
    main()
