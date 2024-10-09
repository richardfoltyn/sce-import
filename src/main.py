import os.path

import pandas as pd

from SCE.importer import import_file


def main():

    userdir = os.path.expanduser('~')
    # Folder where SCE microdata is located
    datadir = os.path.join(userdir, 'data', 'SCE')
    rundir = os.path.join(userdir, 'run', 'SCE')
    logdir = os.path.join(rundir, 'logs')
    resultdir = os.path.join(rundir, 'output')

    for d in logdir, resultdir:
        os.makedirs(d, exist_ok=True)

    # File names are assumed to be those from the SCE website
    files = [
        'FRBNY-SCE-Public-Microdata-Complete-13-16.xlsx',
        'FRBNY-SCE-Public-Microdata-Complete-17-19.xlsx',
        'frbny-sce-public-microdata-latest.xlsx'
    ]

    df_all = []

    for file in files:
        path = os.path.join(datadir, file)

        df = import_file(path)

        df.append(df)

    df = pd.concat(df_all, axis=0)




if __name__ == '__main__':
    main()
