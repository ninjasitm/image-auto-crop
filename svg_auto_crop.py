#!/usr/bin/env python3
import sys, re, math, argparse, glob, shutil, os
from xml.etree import ElementTree as ET

def parse_transform(transform_str):
    if not transform_str: return (1,0,0,1,0,0)
    transform_str = transform_str.strip()
    m = re.match(r'matrix\s*\(([^)]+)\)', transform_str)
    if m:
        parts = [float(p) for p in re.split('[, ]+', m.group(1).strip()) if p!='']
        if len(parts) == 6: return tuple(parts)
    m = re.match(r'translate\s*\(([^)]+)\)', transform_str)
    if m:
        parts = [float(p) for p in re.split('[, ]+', m.group(1).strip()) if p!='']
        if len(parts) == 1: return (1,0,0,1,parts[0],0)
        elif len(parts) >= 2: return (1,0,0,1,parts[0],parts[1])
    return (1,0,0,1,0,0)

def multiply_matrix(m1, m2):
    a1,b1,c1,d1,e1,f1 = m1
    a2,b2,c2,d2,e2,f2 = m2
    return (a1*a2 + b1*c2, a1*b2 + b1*d2, c1*a2 + d1*c2, c1*b2 + d1*d2, a1*e2 + b1*f2 + e1, c1*e2 + d1*f2 + f1)

def apply_matrix_to_point(m, x, y):
    a,b,c,d,e,f = m
    return (a*x + b*y + e, c*x + d*y + f)

def find_points_in_d(d_string):
    nums = re.findall(r'[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?', d_string)
    pts = []
    for i in range(0,len(nums)-1,2):
        pts.append((float(nums[i]), float(nums[i+1])))
    return pts

def collect_bbox_for_element(el,parent_matrix, parent_is_background=False):
    local = parse_transform(el.get('transform'))
    cumulative = multiply_matrix(parent_matrix, local)
    minx,miny,maxx,maxy = (math.inf, math.inf, -math.inf, -math.inf)
    tag = el.tag
    # Skip background group if we detect one
    if el.get('id') == 'background-logo':
        parent_is_background = True
    if tag.endswith('path') and not parent_is_background:
        d = el.get('d')
        if d:
            for x,y in find_points_in_d(d):
                tx,ty = apply_matrix_to_point(cumulative, x, y)
                minx = min(minx, tx); miny = min(miny, ty); maxx = max(maxx, tx); maxy = max(maxy, ty)
    elif tag.endswith('circle'):
        cx=float(el.get('cx','0')); cy=float(el.get('cy','0')); r=float(el.get('r','0'))
        for (xx,yy) in [(cx-r,cy-r),(cx+r,cy+r)]:
            tx,ty = apply_matrix_to_point(cumulative, xx, yy)
            minx=min(minx, tx); miny=min(miny, ty); maxx=max(maxx, tx); maxy=max(maxy, ty)
    elif tag.endswith('rect') and not parent_is_background:
        x=float(el.get('x','0')); y=float(el.get('y','0')); w=float(el.get('width','0')); h=float(el.get('height','0'))
        # try to avoid background rects used as canvas placeholders or transparent rects
        style = el.get('style','')
        fill_op = el.get('fill-opacity') or 'none'
        if 'fill-opacity: 0' in style or fill_op == '0' or (w >= 1000 and h >= 1000):
            return (math.inf, math.inf, -math.inf, -math.inf)
        for xx,yy in [(x,y),(x+w,y+h)]:
            tx,ty = apply_matrix_to_point(cumulative, xx, yy)
            minx=min(minx,tx); miny=min(miny,ty); maxx=max(maxx,tx); maxy=max(maxy,ty)
    if tag.endswith('g') or tag.endswith('svg'):
        for child in el:
            cminx,cminy,cmaxx,cmaxy = collect_bbox_for_element(child, cumulative, parent_is_background)
            minx=min(minx,cminx); miny=min(miny,cminy); maxx=max(maxx,cmaxx); maxy=max(maxy,cmaxy)
    return (minx, miny, maxx, maxy)

def compute_svg_bbox(svg_path):
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    tree=ET.parse(svg_path); root=tree.getroot(); identity=(1,0,0,1,0,0)
    return collect_bbox_for_element(root, identity)

def apply_crop(svg_path, margin=8, backup=True, inplace=False):
    minx,miny,maxx,maxy = compute_svg_bbox(svg_path)
    if minx == math.inf:
        print(f"No geometry found in {svg_path}; skipping")
        return None
    left = (minx - margin)
    top = (miny - margin)
    width = (maxx - minx + 2*margin)
    height = (maxy - miny + 2*margin)

    # Load tree with namespace handling
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    tree = ET.parse(svg_path)
    root = tree.getroot()

    suggested = (left, top, width, height)
    print(f"{os.path.basename(svg_path)} -> minx,miny,maxx,maxy = {minx:.2f},{miny:.2f},{maxx:.2f},{maxy:.2f}")
    print(f"Suggested viewBox x,y,width,height with margin {margin} -> {suggested}")

    # Optionally modify the SVG
    if inplace:
        if backup:
            bak = svg_path + '.bak'
            shutil.copyfile(svg_path, bak)
            print(f"Backup created: {bak}")
        # remove large background rect/group if present
        to_remove = []
        for child in list(root):
            # Prefer removing group with id=background-logo
            if child.tag.endswith('g') and child.get('id') == 'background-logo':
                to_remove.append(child)
                continue
            # Detect transparent full-size rects
            if child.tag.endswith('rect'):
                try:
                    w = float(child.get('width','0'))
                    h = float(child.get('height','0'))
                except Exception:
                    w = h = 0
                if w > 1000 or h > 1000:
                    to_remove.append(child)
        for r in to_remove:
            print(f"Removing background element from {svg_path}")
            root.remove(r)

        vb = f"{left:.4f} {top:.4f} {width:.4f} {height:.4f}"
        root.set('viewBox', vb)
        # Set width/height as integer pixels matching the viewBox but rounded to nearest
        root.set('width', str(int(math.ceil(width))))
        root.set('height', str(int(math.ceil(height))))
        tree.write(svg_path, encoding='utf-8', xml_declaration=True)
        print(f"Applied crop to {svg_path}: viewBox={vb}")
    return suggested

def glob_files(patterns):
    files = []
    for p in patterns:
        if os.path.isdir(p):
            for root, dirs, filenames in os.walk(p):
                for fn in filenames:
                    if fn.lower().endswith('.svg'):
                        files.append(os.path.join(root, fn))
        else:
            # allow globs
            matches = glob.glob(p)
            files.extend(matches)
    return files

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compute and (optionally) crop SVGs to their tight bounding boxes')
    parser.add_argument('paths', nargs='+', help='SVG files, directories, or glob patterns')
    parser.add_argument('--margin', '-m', type=float, default=8, help='Margin to add around the bounding box')
    parser.add_argument('--apply', '-a', action='store_true', help='Apply cropping to files (overwrite)')
    parser.add_argument('--no-backup', dest='backup', action='store_false', help='Do not create a .bak backup when applying')
    parser.add_argument('--dry-run', dest='inplace', action='store_false', help='Only show suggestions; do not modify files')
    parser.add_argument('--inplace', dest='inplace', action='store_true', help='Modify files in-place')
    parser.set_defaults(inplace=False)
    args = parser.parse_args()

    files = glob_files(args.paths)
    if not files:
        print('No SVG files found for given paths.')
        sys.exit(1)

    for f in files:
        try:
            apply_crop(f, margin=args.margin, backup=args.backup, inplace=(args.apply and args.inplace))
        except Exception as e:
            print(f"Error processing {f}: {e}")
