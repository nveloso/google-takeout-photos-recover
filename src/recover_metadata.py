import glob
import json
import os
import re
import shutil
from concurrent.futures.thread import ThreadPoolExecutor

import magic
from tqdm import tqdm

from src.supported_file_types.exceptions import ExifWriterError
from src.supported_file_types.jpg_writer import JPGWriter
from src.supported_file_types.png_writer import PNGWriter


class Metadata:
    # All keys must be lower case!!!
    _SUPPORTED_EXTENSIONS = {
        '.jpg': JPGWriter,
        '.jpeg': JPGWriter,
        '.heic': JPGWriter,
        '.tif': JPGWriter,
        '.tiff': JPGWriter,
        '.png': PNGWriter,
        '.webp': JPGWriter,
        '.gif': JPGWriter,
        '.mp4': JPGWriter
    }
    _MIME_TYPES_MAP = {
        'image/jpeg': ['.jpeg', '.jpg'],
        'image/heic': ['.heic'],
        'image/tiff': ['.tif', '.tiff'],
        'image/png': ['.png'],
        'image/webp': ['.webp'],
        'image/gif': ['.gif'],
        'video/mp4': ['.mp4'],
        'video/quicktime': ['.mp4']
    }

    @staticmethod
    def recover(root_folder: str, output_folder: str, worker: int=10) -> None:
        """
        Given a root_folder it will associate all files (images and videos) to their associated metadata file.
        After it will write the EXIF metadata present in the metadata file to the image/video file writing the new file
        to output_folder
        """
        files_with_metadata = Metadata._get_files_with_metadata(root_folder)
        print(f'{len(files_with_metadata)} file(s) to recover metadata')

        def process_media_file(media_file, metadata_file, root_folder, output_folder):
            output_filepath = Metadata._get_output_filename(root_folder, output_folder, media_file)
            if metadata_file is None:
                tqdm.write(f'Skipping {media_file} as there is no metadata associated. Saving to output folder')
                Metadata._copy_file(media_file, output_filepath)
                return

            tqdm.write(f'Recovering {media_file}')
            with open(metadata_file) as f:
                metadata = json.load(f)

            mime_type = magic.from_file(media_file, mime=True)
            valid_extensions = Metadata._MIME_TYPES_MAP.get(mime_type)
            if not valid_extensions:
                tqdm.write(f'Mime type {mime_type} is not supported. Skipping metadata file {metadata_file}. '
                           f'Saving image/video file to output folder')
                Metadata._copy_file(media_file, output_filepath)
                return

            output_dir = os.path.dirname(output_filepath)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            media_file_extension = os.path.splitext(media_file)[1].lower()
            original_output_filepath = output_filepath
            revert_file_extension = False
            if media_file_extension not in valid_extensions:
                # If the file we are processing has the incorrect extension let's swap it for the correct extension
                revert_file_extension = True
                media_file_extension = valid_extensions[0]
                output_filename = os.path.splitext(os.path.basename(output_filepath))[0]
                output_filepath = os.path.join(output_dir, output_filename + media_file_extension)
                Metadata._copy_file(media_file, output_filepath)
                media_file = output_filepath
                output_filepath = os.path.join(output_dir, f'{output_filename}_changed{media_file_extension}')

            exif_writer = Metadata._SUPPORTED_EXTENSIONS[media_file_extension]
            try:
                exif_writer.write(media_file, output_filepath, metadata)
            except ExifWriterError:
                tqdm.write('Ignoring exif write')
                Metadata._copy_file(media_file, output_filepath)

            if revert_file_extension:
                os.rename(output_filepath, original_output_filepath)
                os.remove(media_file)
                output_filepath = original_output_filepath

            creation_timestamp = int(metadata['creationTime']['timestamp'])
            os.utime(output_filepath, (creation_timestamp, creation_timestamp))

        with ThreadPoolExecutor(max_workers=worker) as executor:
            for media_file, metadata_file in files_with_metadata.items():
                executor.submit(process_media_file, media_file, metadata_file, root_folder, output_folder)

        print('Recovery of metadata completed')

    @staticmethod
    def _get_files_with_metadata(root_folder: str) -> dict[str, str]:
        """Given a folder let's join each file with its associated metadata"""
        files = Metadata._get_non_json_files(root_folder)
        files_with_metadata = Metadata._get_metadata_files(files)

        # Let's validate if we did not miss any metadata file
        metadata_files = set(files_with_metadata.values())
        for path in glob.glob(f'{root_folder}/**', recursive=True):
            if not os.path.isfile(path):
                continue

            extension = os.path.splitext(path)[1]
            if extension == '.json' and path not in metadata_files:
                tqdm.write(f'Cannot find associated image/video file with {path}')

        return files_with_metadata

    @staticmethod
    def _get_metadata_files(files: list[str]) -> dict[str, str | None]:
        """Find metadata file associated with a given file. Associate None if no metadata was found for a given file"""
        files_with_metadata = {}
        for file in files:
            # Let's check if the metadata file is just appending the .json extension
            metadata_file = Metadata._fuzzy_metadata_filename(file)
            if os.path.isfile(metadata_file):
                assert file not in files_with_metadata
                files_with_metadata[file] = metadata_file
                continue

            # Check if we should just change the extension to .json
            metadata_file = Metadata._change_extension(file)
            if os.path.isfile(metadata_file):
                assert file not in files_with_metadata
                files_with_metadata[file] = metadata_file
                continue

            # There is also a case where the metadata file for foo(1).jpg is foo.jpg(1).json
            filename, extension = os.path.splitext(file)
            parts = re.split(r'(\(\d+\))$', filename, maxsplit=1)
            if len(parts) != 3:
                if not Metadata._is_live_photo(file):
                    tqdm.write(f'Cannot find metadata for {file}')
                files_with_metadata[file] = None
                continue
            metadata_file = f'{parts[0]}{extension}{parts[1]}.json'
            if os.path.isfile(metadata_file):
                assert file not in files_with_metadata
                files_with_metadata[file] = metadata_file
                continue
            if not Metadata._is_live_photo(file):
                tqdm.write(f'Cannot find metadata for {file}')
            files_with_metadata[file] = None
        return files_with_metadata

    @staticmethod
    def _get_non_json_files(root_folder: str) -> list[str]:
        """Returns all non json files aka all images and videos"""
        files = []
        for path in glob.glob(f'{root_folder}/**', recursive=True):
            if not os.path.isfile(path):
                continue

            extension = os.path.splitext(path)[1]
            if extension != '.json':
                files.append(path)
        return files

    @staticmethod
    def _change_extension(file: str) -> str:
        """Changes the extension of a file to .json"""
        filepath = os.path.splitext(file)[0]
        filename = f'{os.path.basename(filepath)}.json'
        return os.path.join(os.path.dirname(filepath), Metadata._sanitize_metadata_filename(filename))

    @staticmethod
    def _fuzzy_metadata_filename(file: str) -> str:
        dirpath = os.path.dirname(file)
        filename = os.path.basename(file)

        match = re.search(r'^(.*)?(\(\d+\))?\.(.*)?$', filename)
        if match:
            pure_name, version, suffix = match.group(1), match.group(2), match.group(3)
        else:
            return ''

        if version is None:
            match = re.search('(.+)(\(\d+\))$', pure_name)
            if match:
                pure_name, version = match.group(1), match.group(2)

        expected_json_names = [filename,
                               f'{filename}.supplemental-metadata',
                               f'{pure_name}.{suffix}',
                               f'{pure_name}.{suffix}.supplemental-metadata' + (f'{version}' if version else '')]

        if pure_name.endswith('-edited') or pure_name.endswith('-edit'):
            expected_json_names.append(f'{re.sub(r'(-edited|-edit)$', '', pure_name)}.{suffix}')
            expected_json_names.append(
                f'{re.sub(r'(-edited|-edit)$', '', pure_name)}.{suffix}.supplemental-metadata' + (
                    f'{version}' if version else ''))

        expected_json_names = [name[:46] for name in expected_json_names]

        for name in expected_json_names:
            metadata_files = glob.glob(f"{dirpath}/{name}.json", recursive=False)
            if len(metadata_files) == 1:
                return metadata_files[0]

        expected_json_names = [f'{pure_name}.{suffix}.supplemental-metadata' + (f'{version}' if version else ''),
                               f'{pure_name}.{suffix}.supplemental-metadata']

        if suffix.lower() == 'mp4':
            for alt_suffix in ['heic', 'mov', 'jpeg', 'jpg']:
                expected_json_names.append(f'{pure_name}.{alt_suffix}.supplemental-metadata' + (f'{version}' if version else ''))
                expected_json_names.append(f'{pure_name}.{alt_suffix}.supplemental-metadata')

        expected_json_names.append(f'{pure_name}.*supplemental-metadata' + (f'{version}' if version else ''))
        expected_json_names = [name[:46] for name in expected_json_names]

        for name in expected_json_names:
            metadata_files = glob.glob(f"{dirpath}/{name}.json", recursive=False)
            if len(metadata_files) == 1:
                return metadata_files[0]

        expected_json_names = [name[:45] for name in expected_json_names]
        for name in expected_json_names:
            metadata_files = glob.glob(f"{dirpath}/{name}.json", recursive=False)
            if len(metadata_files) == 1:
                return metadata_files[0]

        return ''


    @staticmethod
    def _sanitize_metadata_filename(metadata_file: str) -> str:
        """
        Google takeout truncates the filename. Maximum characters allowed are 51. The .json extension has 5 characters
        including the dot. 51 - 5 = 46
        This method sanitizes the filename to meet google's takeout criteria
        """
        metadata_filepath = os.path.splitext(metadata_file)[0]
        metadata_filename = os.path.basename(metadata_filepath)[:46]
        return os.path.join(os.path.dirname(metadata_filepath), f'{metadata_filename}.json')

    @staticmethod
    def _is_live_photo(file: str) -> bool:
        """Check if the given file is a live photo from iOS"""
        file_path = os.path.splitext(file)[0]
        return os.path.isfile(f'{file_path}.heic')

    @staticmethod
    def _copy_file(source: str, destination: str) -> None:
        output_dir_name = os.path.dirname(destination)
        if not os.path.isdir(output_dir_name):
            os.makedirs(output_dir_name)
        shutil.copy2(source, os.path.normpath(destination))

    @staticmethod
    def _get_output_filename(root_folder: str, output_folder: str, image_path: str) -> str:
        """
        Returns the output folder by just changing the name of the parent folder. For example, if root_folder is google
        and the image_path is google/takeout/photos2024/foo.jpg the resulting output folder must be
        <output_folder>/takeout/photos2024/foo.jpg
        """
        new_image_name = os.path.basename(image_path)
        image_path_dir = os.path.dirname(image_path)
        relative_to_new_image_folder = os.path.relpath(image_path_dir, root_folder)
        return os.path.join(output_folder, relative_to_new_image_folder, new_image_name)
