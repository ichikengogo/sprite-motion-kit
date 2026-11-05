"""Build only the audited source allowlist; exclude all production inputs/outputs."""
import argparse
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from check_public_release import inventory

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];files,errors=inventory(root)
    if errors:raise ValueError('\n'.join(errors))
    if a.output.exists():raise ValueError('Use a new output path')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(a.output,'w',ZIP_DEFLATED) as archive:
        for row in files:archive.write(root/row['path'],'sprite-motion-lab/'+row['path'])
    print(f'Wrote {len(files)} source files; production inputs and outputs are excluded.')
if __name__=='__main__':main()
