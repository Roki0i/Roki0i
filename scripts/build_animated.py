#!/usr/bin/env python3
"""GitHub README animations from the two approved pixel-art mockups.

Pillow creates self-contained animated GIFs; no browser JS, remote image
hosting, runtime font downloads, or GitSkins dependencies.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'assets/source'
DST = ROOT / 'assets'
USER = 'Roki0i'
API = 'https://api.github.com'

# Tiny 5x7 bitmap glyphs: generator output is pixel-perfect and needs no fonts.
BITMAP = {
    '0':['01110','10001','10011','10101','11001','10001','01110'],
    '1':['00100','01100','00100','00100','00100','00100','01110'],
    '2':['01110','10001','00001','00010','00100','01000','11111'],
    '3':['11110','00001','00001','01110','00001','00001','11110'],
    '4':['00010','00110','01010','10010','11111','00010','00010'],
    '5':['11111','10000','10000','11110','00001','00001','11110'],
    '6':['01111','10000','10000','11110','10001','10001','01110'],
    '7':['11111','00001','00010','00100','01000','01000','01000'],
    '8':['01110','10001','10001','01110','10001','10001','01110'],
    '9':['01110','10001','10001','01111','00001','00001','11110'],
    ',':['00000','00000','00000','00000','00100','00100','01000'],
    '-':['00000','00000','00000','11111','00000','00000','00000'],
    ' ':['00000']*7,
    'A':['01110','10001','10001','11111','10001','10001','10001'],
    'B':['11110','10001','10001','11110','10001','10001','11110'],
    'C':['01111','10000','10000','10000','10000','10000','01111'],
    'D':['11110','10001','10001','10001','10001','10001','11110'],
    'E':['11111','10000','10000','11110','10000','10000','11111'],
    'G':['01111','10000','10000','10111','10001','10001','01110'],
    'I':['11111','00100','00100','00100','00100','00100','11111'],
    'L':['10000','10000','10000','10000','10000','10000','11111'],
    'M':['10001','11011','10101','10101','10001','10001','10001'],
    'N':['10001','11001','10101','10011','10001','10001','10001'],
    'O':['01110','10001','10001','10001','10001','10001','01110'],
    'P':['11110','10001','10001','11110','10000','10000','10000'],
    'R':['11110','10001','10001','11110','10100','10010','10001'],
    'S':['01111','10000','10000','01110','00001','00001','11110'],
    'T':['11111','00100','00100','00100','00100','00100','00100'],
    'U':['10001','10001','10001','10001','10001','10001','01110'],
    'V':['10001','10001','10001','10001','10001','01010','00100'],
    'W':['10001','10001','10001','10101','10101','10101','01010'],
    'Y':['10001','10001','01010','00100','00100','00100','00100'],
}


def pixel_text(image: Image.Image, s: str, center_x: int, y: int, scale: int, color: tuple[int, ...]):
    s = s.upper()
    if any(ch not in BITMAP for ch in s):
        raise ValueError(f'Unsupported glyph in {s!r}')
    width = (len(s) * 6 - 1) * scale
    x0 = center_x - width // 2
    draw = ImageDraw.Draw(image, 'RGBA' if image.mode == 'RGBA' else None)
    for index, ch in enumerate(s):
        for yy, row in enumerate(BITMAP[ch]):
            for xx, on in enumerate(row):
                if on == '1':
                    x = x0 + (index*6 + xx)*scale
                    draw.rectangle((x, y + yy*scale, x+scale-1, y+(yy+1)*scale-1), fill=color)
    return width


def get_json(url: str, token: str, payload: dict | None = None):
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    req = Request(url, method='POST' if data else 'GET', data=data, headers={
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json',
        'User-Agent': 'Roki-night-profile',
    })
    for attempt in range(3):
        try:
            with urlopen(req, timeout=30) as response:
                return json.load(response)
        except (HTTPError, URLError) as e:
            if isinstance(e, HTTPError) and e.code not in (403, 429, 500, 502, 503, 504):
                raise
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def metrics_from_api(user: str, token: str) -> dict:
    if not token:
        raise RuntimeError('GITHUB_TOKEN is required: statistics must not be fabricated')
    profile = get_json(f'{API}/users/{user}', token)
    repos = []
    for page in range(1, 101):
        batch = get_json(f'{API}/users/{user}/repos?per_page=100&page={page}&type=owner', token)
        if not isinstance(batch, list):
            raise RuntimeError('GitHub REST returned non-list repositories')
        repos.extend(batch)
        if len(batch) < 100:
            break
    else:
        raise RuntimeError('More than 100 pages of repositories; incomplete results refused')
    query = '''query($login: String!) {
        user(login: $login) {
          contributionsCollection {
            totalCommitContributions
            contributionCalendar {
              weeks { contributionDays { date contributionCount } }
            }
          }
        }
    }'''
    result = get_json(f'{API}/graphql', token, {'query':query,'variables':{'login':user}})
    if result.get('errors'):
        raise RuntimeError(f'GitHub GraphQL errors: {result["errors"]}')
    collection = result['data']['user']['contributionsCollection']
    days = [day for week in collection['contributionCalendar']['weeks'] for day in week['contributionDays']]
    days = sorted(days, key=lambda d:d['date'])[-30:]
    if len(days) != 30:
        raise RuntimeError('Contribution calendar did not provide 30 days')
    return {
        'commits': int(collection['totalCommitContributions']),
        'repos': int(profile['public_repos']),
        'languages': len({r['language'] for r in repos if not r.get('fork') and r.get('language')}),
        'activity': [int(d['contributionCount']) for d in days],
    }


def sample_metrics():
    return {'commits':1248,'repos':87,'languages':12,
            'activity':[0,2,1,0,4,1,3,0,1,2,1,4,0,3,1,2,0,5,3,2,1,4,0,2,1,1,3,2,0,1]}


def placeholder_metrics():
    return {'commits':None,'repos':None,'languages':None,
            'activity':[0]*30}


def composite_hero(base: Image.Image, t: int, total: int) -> Image.Image:
    layer = Image.new('RGBA',base.size,(0,0,0,0))
    d=ImageDraw.Draw(layer,'RGBA')
    phase=t/total
    # Twinkling square stars (slow, independent phases): 2-5 px, no flashing.
    for i,(x,y,color) in enumerate([
        (795,117,(255,205,136)), (1187,37,(195,171,242)),
        (1376,178,(255,242,222)),(1903,55,(245,243,230)),
        (2180,219,(212,195,245)),(1120,215,(190,176,230)),
    ]):
        alpha=int(44+115*(.5+.5*math.sin(2*math.pi*(phase+(i*.23)))))
        d.rectangle((x,y,x+4,y+4),fill=(*color,alpha))
    # Light shift on the golden caret already in the original artwork.
    alpha=int(20+120*(.5+.5*math.sin(2*math.pi*phase)))
    d.rectangle((1891,260,1900,350),fill=(255,207,119,alpha//4))
    # A few small drifting pixels of steam over the coffee cup.
    for i,(x,y) in enumerate([(628,422),(647,414),(660,439)]):
        yy=int(y-20*((phase+i*.23)%1))
        a=int(70*(1-((phase+i*.23)%1)))
        d.rectangle((x,yy,x+5,yy+5),fill=(245,238,233,a))
    return Image.alpha_composite(base,layer)


CARD_CENTERS=(718,1092,1485)


def draw_stats(base: Image.Image, metrics:dict, step:float, sample:bool, pulse:float=0) -> Image.Image:
    canvas=base.copy()
    # Clear the old mockup activity bars before drawing actual calendar data.
    previous=canvas.copy()
    activity_draw=ImageDraw.Draw(canvas)
    for y in range(542,638):
        rgba=previous.getpixel((1518,y))
        activity_draw.line((974,y,1517,y),fill=rgba,width=1)
    vals=[metrics['commits'], metrics['repos'], metrics['languages']]
    captions=['LAST YEAR','PUBLIC','PRIMARY']
    for i,(value,cx,caption) in enumerate(zip(vals,CARD_CENTERS,captions)):
        label='---' if value is None else format(value,',')
        scale=min(8,max(4,234//max(1,(6*len(label)-1))))
        # Show number changing from zero into verified data: visual-only tween.
        if value is not None and step < 1:
            intermediate=round(value*(1-(1-step)**3))
            label=format(intermediate,',')
        pixel_text(canvas,label,cx,372,scale,(248,240,231,255))
        pixel_text(canvas, 'AWAITING' if value is None else caption,cx,447,3,(252,184,101,255))
    d=ImageDraw.Draw(canvas,'RGBA')
    series=metrics['activity']
    max_n=max(max(series),1)
    for i,num in enumerate(series):
        x=977+i*17
        bar_height=2 if num==0 else 6+int(55*math.sqrt(num/max_n)*max(.05,step))
        y0=615-bar_height
        c=(125,120,194,255) if i%5 else (255,190,105,255)
        d.rectangle((x,y0,x+9,615),fill=c)
        if num>0 and i%5==0:
            d.rectangle((x,y0,x+9,y0+3),fill=(255,214,138,255))
    # Soft status indicator ensures even a placeholder card has subtle motion.
    glow=int(70+165*(.5+.5*math.sin(2*math.pi*pulse)))
    d.rectangle((1740,253,1747,260),fill=(glow,int(glow*.8),int(glow*.5),255))
    if sample:
        pixel_text(canvas,'SAMPLE',1682,228,2,(255,176,101,255))
    return canvas


def save_gif(frames:list[Image.Image], filename:Path, scale:float=.5, frame_ms:int=180) -> None:
    rgb=[]
    for frame in frames:
        size=(round(frame.width*scale),round(frame.height*scale))
        # pixel art is deliberately scaled with nearest neighbor
        rgb.append(frame.convert('RGB').resize(size,Image.Resampling.NEAREST))
    # Quantize every frame against one fixed palette to prevent shimmer.
    palette=rgb[0].quantize(colors=192,method=Image.Quantize.MEDIANCUT)
    output=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in rgb]
    filename.parent.mkdir(parents=True,exist_ok=True)
    output[0].save(filename,save_all=True,append_images=output[1:],duration=frame_ms,
                   loop=0,optimize=True,disposal=2,comment=b'Roki0i pixel profile animation')
    print(f'{filename.relative_to(ROOT)}: {filename.stat().st_size/1048576:.2f} MiB, {len(output)} frames')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['demo','placeholder','live'],default='placeholder')
    parser.add_argument('--only',choices=['hero','stats','both'],default='both')
    args=parser.parse_args()
    total=20
    if args.only in ('hero','both'):
        h=Image.open(SRC/'hero.png').convert('RGBA')
        save_gif([composite_hero(h,i,total) for i in range(total)], DST/'hero-animated.gif',.5,200)
    if args.only in ('stats','both'):
        if args.mode=='live':
            metrics=metrics_from_api(USER,os.environ.get('GITHUB_TOKEN',''))
        elif args.mode=='demo':
            metrics=sample_metrics()
        else:
            metrics=placeholder_metrics()
        for field in ('commits','repos','languages'):
            value=metrics[field]
            if value is not None and (not isinstance(value,int) or value<0):
                raise ValueError(f'Invalid stat {field}={value!r}')
        if len(metrics['activity'])!=30:
            raise ValueError('Activity needs 30 days')
        s=Image.open(SRC/'stats.png').convert('RGBA')
        # A few frames count up; the remainder rests on true final values.
        save_gif([draw_stats(s,metrics,min(1,i/8),args.mode=='demo',i/total) for i in range(total)],
            DST/('stats-demo.gif' if args.mode=='demo' else 'stats-animated.gif'),.5,200)

if __name__=='__main__':
    main()
