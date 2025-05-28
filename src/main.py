import hashlib
import logging
import os.path

import pandas as pd

from SCE.importer import import_file
from env import EnvConfig, env_setup


def md5sum(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096*4), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def main(econf: EnvConfig):

    logger = logging.getLogger('SCE')

    # File names are assumed to be those from the SCE website
    files = [
        'FRBNY-SCE-Public-Microdata-Complete-13-16.xlsx',
        'FRBNY-SCE-Public-Microdata-Complete-17-19.xlsx',
        'frbny-sce-public-microdata-latest.xlsx'
    ]

    df_all = []

    for file in files:
        path = os.path.join(econf.inputdir, file)

        hsh = md5sum(path)
        fn_cache = os.path.join(econf.cachedir, hsh + ".pkl.xz")
        if os.path.isfile(fn_cache):
            logger.info(f'Reading cached file {fn_cache}')
            df = pd.read_pickle(fn_cache)
        else:
            logger.info(f'Reading in {path}')
            # Skip first line which contains the license terms
            df = pd.read_excel(path, skiprows=1)
            df.to_pickle(fn_cache)

        df = import_file(df)

        df.append(df)

    df = pd.concat(df_all, axis=0)




if __name__ == '__main__':
    main(env_setup())
