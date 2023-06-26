import pandas as pd
from pathlib import Path


def clean_links(path_from: str = Path(r'../data/01_raw/raw_links.csv'),
                path_to: str = Path(r'../data/02_intermediate/clean_links.csv')) -> None:
    """
    Clean duplicates and resave links.
    """
    df = pd.read_csv(path_from)
    df.drop_duplicates(inplace=True)
    df.to_csv(path_to, index=False)


if __name__ == '__main__':
    clean_links()
