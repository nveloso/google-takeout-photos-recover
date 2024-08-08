import argparse
import os

from src.recover_metadata import Metadata


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('takeout_folder', help='Folder where your google photos are located')
    parser.add_argument('output_folder',
                        help='Output folder where the photos and videos with metadata recovered will be saved')
    args = parser.parse_args()

    if not os.path.exists(args.takeout_folder):
        raise FileNotFoundError(f'The takeout_folder {args.takeout_folder} does not exist')
    return args


def main():
    args = parse_args()
    Metadata.recover(args.takeout_folder, args.output_folder)


if __name__ == '__main__':
    main()
