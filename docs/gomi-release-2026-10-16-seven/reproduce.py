"""Reconstruct approved data in a temporary fixture; never writes the checkout."""
import hashlib, pathlib, shutil, subprocess, sys, tempfile
HERE=pathlib.Path(__file__).resolve().parent
REPO=HERE.parent.parent
with tempfile.TemporaryDirectory() as tmp:
    root=pathlib.Path(tmp)
    shutil.copytree(HERE/'inputs',root,dirs_exist_ok=True)
    prep=root/'調査/2026-10-16_ごみ支援公開確認'
    prep.mkdir(parents=True,exist_ok=True)
    for name in ('prepare_release.py','plan.json','owner-approval.json'):
        shutil.copy2(HERE/name,prep/name)
    fixture=root/'gomi-release-preview'; (fixture/'data').mkdir(parents=True)
    shutil.copy2(HERE/'base-data.json',fixture/'data/gomi-support.json')
    shutil.copytree(REPO/'tools',fixture/'tools',ignore=shutil.ignore_patterns('__pycache__'))
    for master in (REPO/'data').glob('*-menkyo-henno.json'):
        shutil.copy2(master,fixture/'data'/master.name)
    # Original HEAD check resolves through the real checkout's Git metadata.
    # Use the approved base snapshot, independent of the current checkout HEAD.
    subprocess.run(['git','init','-q',str(fixture)],check=True)
    base=__import__('json').loads((HERE/'plan.json').read_text())['pre_release_head']
    # git archive does not carry commits; create a reference to the original object store.
    gitdir=subprocess.check_output(['git','-C',str(REPO),'rev-parse','--git-common-dir'],text=True).strip()
    gitdir=(REPO/gitdir).resolve()
    (fixture/'.git/objects/info/alternates').write_text(str(gitdir/'objects')+'\n')
    (fixture/'.git/HEAD').write_text(base+'\n')
    out=root/'release.json'
    subprocess.run([sys.executable,str(prep/'prepare_release.py'),'--approval',str(prep/'owner-approval.json'),'--out',str(out)],check=True)
    assert out.read_bytes()==(REPO/'data/gomi-support.json').read_bytes(), 'Published data differs'
    print('OK: approved release data reproduced byte-for-byte')
