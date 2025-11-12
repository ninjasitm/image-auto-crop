#!/usr/bin/env python3
import sys, re, math, argparse, glob, shutil, os
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except Exception:
    CAIROSVG_AVAILABLE = False
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

def apply_crop(svg_path, margin=8, backup=True, inplace=False, responsive=False, class_name=None, responsive_mode='percent', backup_overwrite=True):
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
            if os.path.exists(bak) and not backup_overwrite:
                print(f"Backup exists and overwrite disabled; skipping backup for {svg_path}")
            else:
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
        if responsive:
            # responsive behavior modes
            if responsive_mode == 'percent':
                root.set('width', '100%')
                root.set('height', '100%')
            elif responsive_mode == 'remove':
                if 'width' in root.attrib:
                    del root.attrib['width']
                if 'height' in root.attrib:
                    del root.attrib['height']
        else:
            root.set('width', str(int(math.ceil(width))))
            root.set('height', str(int(math.ceil(height))))
        if class_name:
            root.set('class', class_name)
        tree.write(svg_path, encoding='utf-8', xml_declaration=True)
        print(f"Applied crop to {svg_path}: viewBox={vb}")
    return suggested

def verify_file(svg_path, eps=1e-4, require_responsive=None, expected_class=None, responsive_mode=None):
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    tree = ET.parse(svg_path)
    root = tree.getroot()
    vb = root.get('viewBox')
    if not vb:
        print(f"{svg_path}: no viewBox present; cannot verify")
        return False
    x,y,w,h = [float(x) for x in vb.strip().split()]
    minx,miny,maxx,maxy = compute_svg_bbox(svg_path)
    ok = True
    if minx < x - eps or miny < y - eps or maxx > x + w + eps or maxy > y + h + eps:
        print(f"{svg_path}: geometry outside viewBox: bbox {minx:.4f},{miny:.4f},{maxx:.4f},{maxy:.4f} vs viewBox {x:.4f},{y:.4f},{w:.4f},{h:.4f}")
        ok = False
    # Check responsive width/height if required
    if require_responsive is not None:
        width = root.get('width')
        height = root.get('height')
        if require_responsive:
            if responsive_mode == 'percent' or responsive_mode is None:
                if width and width != '100%':
                    print(f"{svg_path}: width='{width}' (expected '100%' for responsive)")
                    ok = False
                if height and height != '100%':
                    print(f"{svg_path}: height='{height}' (expected '100%' for responsive)")
                    ok = False
            elif responsive_mode == 'remove':
                if 'width' in root.attrib or 'height' in root.attrib:
                    print(f"{svg_path}: width/height attributes present (expected removed for responsive-mode 'remove')")
                    ok = False
        else:
            # If not responsive, ensure width/height exist as integers
            if not width or not height:
                print(f"{svg_path}: missing width/height (not responsive)")
                ok = False
    # Check CSS class if expected
    if expected_class is not None:
        cls = root.get('class') or ''
        if expected_class not in cls.split():
            print(f"{svg_path}: class attribute '{cls}' does not include expected '{expected_class}'")
            ok = False
    return ok

def rasterize_file(svg_path, out_path=None, dpi=None):
    if not CAIROSVG_AVAILABLE:
        print('cairosvg not installed; rasterization unavailable. Install via pip install cairosvg')
        return None
    if out_path is None:
        out_path = os.path.splitext(svg_path)[0] + '.png'
    try:
        if dpi:
            cairosvg.svg2png(url=svg_path, write_to=out_path, dpi=dpi)
        else:
            cairosvg.svg2png(url=svg_path, write_to=out_path)
        print(f'Rasterized {svg_path} -> {out_path}')
        return out_path
    except Exception as e:
        print(f'Rasterization failed for {svg_path}: {e}')
        return None

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
    parser = argparse.ArgumentParser(description='Compute and (optionally) crop SVGs to their tight bounding boxes with optional verification, responsive flags, CSS class, and rasterization support')
    parser.add_argument('paths', nargs='+', help='SVG files, directories, or glob patterns')
    parser.add_argument('--margin', '-m', type=float, default=8, help='Margin to add around the bounding box')
    parser.add_argument('--apply', '-a', action='store_true', help='Apply cropping to files and write changes to disk (overwrite). Without this flag the script runs in dry-run mode')
    parser.add_argument('--no-backup', dest='backup', action='store_false', help='Do not create a .bak backup when applying')
    parser.add_argument('--backup-overwrite', dest='backup_overwrite', action='store_true', default=True, help='When creating .bak backups, overwrite an existing .bak if present (default)')
    parser.add_argument('--backup-no-overwrite', dest='backup_overwrite', action='store_false', help="Do not overwrite an existing .bak backup; if it exists, skip creating a new backup")
    parser.set_defaults(backup=True)
    parser.add_argument('--verify', '-v', action='store_true', help='Verify that artwork bbox fits inside viewBox (after apply if using --apply). If verification fails and --revert-on-fail was passed the original .bak will be restored.')
    parser.add_argument('--revert-on-fail', action='store_true', help='If --apply and --verify are used and verification fails, revert the change by restoring the .bak backup (if present)')
    parser.add_argument('--responsive', action='store_true', help='Set SVG root to responsive mode according to --responsive-mode when applying')
    parser.add_argument('--responsive-mode', choices=['percent','remove'], default='percent', help="responsive mode: 'percent' sets width/height='100%%'; 'remove' deletes width/height attributes")
    parser.add_argument('--svg-class', dest='svg_class', help='Add a CSS class attribute to the SVG root when applying (space-separated classes allowed)')
    parser.add_argument('--rasterize', action='store_true', help='Rasterize SVGs to PNGs using cairosvg (if installed)')
    parser.add_argument('--raster-dpi', type=float, help='Optional DPI to use for rasterization (default depends on cairosvg)')
    parser.add_argument('--raster-outdir', help='Optional directory to write PNGs into (default: same folder as SVG)')
    args = parser.parse_args()

    files = glob_files(args.paths)
    if args.apply and args.revert_on_fail and not args.backup:
        print('Warning: --revert-on-fail requested but --no-backup present; cannot revert without a backup')
    if args.apply and args.backup and not args.backup_overwrite:
        print('Note: --backup-no-overwrite set; existing .bak files will not be overwritten')
    if not files:
        print('No SVG files found for given paths.')
        sys.exit(1)

    overall_ok = True
    changed_files = []
    rasterized_files = []
    for f in files:
        try:
            if args.apply:
                apply_crop(f, margin=args.margin, backup=args.backup, inplace=True, responsive=args.responsive, class_name=args.svg_class, responsive_mode=args.responsive_mode, backup_overwrite=args.backup_overwrite)
                changed_files.append(f)
            else:
                # Dry-run suggestion
                apply_crop(f, margin=args.margin, backup=False, inplace=False)
            if args.verify:
                ok = verify_file(f, eps=1e-4, require_responsive=args.responsive if args.responsive else None, expected_class=args.svg_class, responsive_mode=args.responsive_mode if args.responsive else None)
                if not ok:
                    overall_ok = False
                    if args.apply and args.revert_on_fail:
                        bak = f + '.bak'
                        if os.path.exists(bak):
                            shutil.copyfile(bak, f)
                            print(f"Restored original from {bak} due to verification failure")
                            # After revert, we consider this file as not changed
                            if f in changed_files:
                                changed_files.remove(f)
            if args.rasterize:
                outdir = args.raster_outdir if args.raster_outdir else None
                out_path = None
                if outdir:
                    # ensure output dir exists
                    os.makedirs(outdir, exist_ok=True)
                    out_path = os.path.join(outdir, os.path.basename(os.path.splitext(f)[0] + '.png'))
                raster_output = rasterize_file(f, out_path=out_path, dpi=args.raster_dpi)
                if raster_output:
                    rasterized_files.append(raster_output)
        except Exception as e:
            print(f"Error processing {f}: {e}")
            overall_ok = False

    if args.verify and not overall_ok:
        print('Some SVGs failed verification; see messages above')
        sys.exit(2)

    # Summary
    print('\nSummary:')
    print(f'Processed {len(files)} SVGs; applied changes to {len(changed_files)}')
    if changed_files:
        for c in changed_files:
            print(f'  Updated: {c}')
    if rasterized_files:
        print(f'Rasterized {len(rasterized_files)} files:')
        for r in rasterized_files:
            print(f'  {r}')
