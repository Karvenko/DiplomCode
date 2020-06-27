import os
import glob

IN_DIR = '../deals_raw'
OUT_DIR = '../deals_processed'

LAST_FILE = '../deals_processed/last_file'

def make_lock_file(filename, lock_file=LAST_FILE):
    with open(lock_file, 'w') as f:
        f.write(filename)
        
def make_cleanup(lock_file=LAST_FILE):
    if os.path.isfile(lock_file):
        try:
            with open(lock_file, 'r') as f:
                filename = f.readline()
            
            os.remove(OUT_DIR + '/' + filename)
            os.remove(lock_file)
        except:
            raise FileNotFoundError()
            
def get_file_names(in_dir=IN_DIR, out_dir=OUT_DIR):
    #Cleaning out dir
    make_cleanup()
    
    out_files = [f.split('\\')[-1].split('.')[0] for f in glob.glob(out_dir + '/' + '*.out')]
    in_files = set([f.split('\\')[-1].split('.')[0] for f in glob.glob(in_dir + '/' + '*.pbn')])
    for f in out_files:
        in_files.discard(f)
        
    return in_files