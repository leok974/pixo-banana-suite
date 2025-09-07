#!/usr/bin/env python3
import os
import argparse
import requests
import json

API_BASE = os.getenv('API_BASE', 'http://127.0.0.1:8000')

def main():
    parser = argparse.ArgumentParser(description='Create animations from frames')
    parser.add_argument('--frames', nargs='+', required=True, help='Frame paths')
    parser.add_argument('--basename', required=True, help='Output basename')
    parser.add_argument('--fps', type=int, default=8, help='Frames per second')
    parser.add_argument('--cols', type=int, default=4, help='Sprite sheet columns')
    
    args = parser.parse_args()
    
    payload = {
        'items': [{
            'frames': [f.replace('\\', '/') for f in args.frames],
            'basename': args.basename,
            'fps': args.fps,
            'sheet_cols': args.cols
        }]
    }
    
    print(f'POST {API_BASE}/animate')
    print(f'Animating {len(args.frames)} frames')
    
    try:
        response = requests.post(
            f'{API_BASE}/animate',
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        print('Success!')
        print(json.dumps(result, indent=2))
    except requests.exceptions.RequestException as e:
        print(f'Error: {e}')
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())